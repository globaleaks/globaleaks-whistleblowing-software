# Implement the notification of new submissions
import itertools

from datetime import datetime, date, timedelta
from sqlalchemy import not_
from sqlalchemy.sql.expression import func
from twisted.internet import defer

from globaleaks import models
from globaleaks.handlers.admin.node import db_admin_serialize_node
from globaleaks.handlers.admin.notification import db_get_notification
from globaleaks.handlers.public import db_get_submission_statuses
from globaleaks.handlers.user import user_serialize_user
from globaleaks.jobs.job import LoopingJob
from globaleaks.models import serializers
from globaleaks.models.config import ConfigFactory
from globaleaks.orm import db_del, transact, tw
from globaleaks.utils.log import log
from globaleaks.utils.templating import Templating, mail_uses_smtp2
from globaleaks.utils.utility import datetime_now, deferred_sleep


def gen_cache_key(*args):
    return '-'.join([f'{arg}' for arg in args])


def _to_datetime(val):
    if val is None:
        return None
    if isinstance(val, datetime):
        return val
    if isinstance(val, date):
        return datetime.combine(val, datetime.min.time())
    if isinstance(val, str):
        try:
            return datetime.fromisoformat(val)
        except ValueError:
            return None
    return None


class MailGenerator:
    simulate_mode = False
    sent_reminders = {}
    simulation_stats = {'users': {}, 'totals': {'grouped_emails': 0, 'total_reminders': 0}}

    def __init__(self, state):
        self.state = state
        self.cache = {}

    @classmethod
    def reset_stats(cls):
        cls.sent_reminders.clear()
        cls.simulation_stats = {'users': {}, 'totals': {'grouped_emails': 0, 'total_reminders': 0}}

    def serialize_config(self, session, key, tid, language):
        cache_key = gen_cache_key(key, tid, language)
        cache_obj = None

        if cache_key not in self.cache:
            if key == 'node':
                cache_obj = db_admin_serialize_node(session, tid, language)
            elif key == 'notification':
                cache_obj = db_get_notification(session, tid, language)
            elif key == 'submission_statuses':
                cache_obj = db_get_submission_statuses(session, tid, language)

            self.cache[cache_key] = cache_obj

        return self.cache[cache_key]

    def process_mail_creation(self, session, tid, data):
        user_id = data['user']['id']
        language = data['user']['language']

        # Do not generate emails if the user has disabled notifications
        if not data['user']['notification'] or ('tip' in data and not data['tip']['enable_notifications']):
            log.debug("Discarding emails for %s due to user's preference.", user_id)
            return

        data['node'] = self.serialize_config(session, 'node', tid, language)

        data['notification'] = self.serialize_config(session, 'notification', tid, language)

        if 'tip' in data:
            data['submission_statuses'] = self.serialize_config(session, 'submission_statuses', tid, language)

        subject, body = Templating().get_mail_subject_and_body(data)

        session.add(models.Mail({
            'address': data['user']['mail_address'],
            'subject': subject,
            'body': body,
            'tid': tid,
            'secondary_smtp': mail_uses_smtp2(data['notification'], data['type']),
        }))

    def db_generate_emails_for_expiring_reports(self, session, tid):
        tip_expiration_threshold = self.state.tenants[tid].cache.notification.tip_expiration_threshold
        if tip_expiration_threshold <= 0:
            return

        threshold = datetime_now() + timedelta(days=tip_expiration_threshold)

        result = session.query(models.User, func.count(models.InternalTip.id), func.min(models.InternalTip.expiration_date)) \
                        .filter(models.InternalTip.tid == tid,
                                models.ReceiverTip.internaltip_id == models.InternalTip.id,
                                models.InternalTip.expiration_date < threshold,
                                models.User.id == models.ReceiverTip.receiver_id) \
                        .group_by(models.User.id) \
                        .having(func.count(models.InternalTip.id) > 0) \
                        .all()

        for x in result:
            user = x[0]
            expiring_submission_count = x[1]
            earliest_expiration_date = x[2]

            user_desc = user_serialize_user(session, user, user.language)

            data = {
                'type': 'tip_expiration_summary',
                'node': db_admin_serialize_node(session, tid, user.language),
                'user': user_desc,
                'expiring_submission_count': expiring_submission_count,
                'earliest_expiration_date': earliest_expiration_date
            }

            # Do not generate emails if the receiver has disabled notifications
            if not data['user']['notification']:
                log.debug("Discarding emails for %s due to receiver's preference.", user.id)
                continue

            data['notification'] = db_get_notification(session, tid, user.language)

            subject, body = Templating().get_mail_subject_and_body(data)

            session.add(models.Mail({
                'tid': tid,
                'address': user_desc['mail_address'],
                'subject': subject,
                'body': body,
                'secondary_smtp': mail_uses_smtp2(data['notification'], data['type'])
            }))


    def db_generate_email_for_unread_reports(self, session, now, silent_tids):
        reminder_time = self.state.tenants[1].cache.unread_reminder_time
        if reminder_time <= 0:
            return

        for user in session.query(models.User).filter(models.User.id == models.ReceiverTip.receiver_id,
                                                      not_(models.User.tid.in_(silent_tids)),
                                                      models.User.reminder_date < now - timedelta(reminder_time),
                                                      models.ReceiverTip.last_access < models.InternalTip.update_date,
                                                      models.ReceiverTip.internaltip_id == models.InternalTip.id,
                                                      models.InternalTip.update_date < now - timedelta(reminder_time)).distinct():
            user.reminder_date = now
            data = {'type': 'unread_tips'}

            try:
                data['user'] = user_serialize_user(session, user, user.language)
                self.process_mail_creation(session, user.tid, data)
            except Exception as e:
                log.err("Unable to generate a user notification: %s", e, tid=user.tid)

    def silent_tids(self):
        """
        The tenants that do not notify their recipients
        """
        silent_tids = []

        for tid in self.state.tenants:
            cache = self.state.tenants[tid].cache
            if cache.notification and not cache.notification.enable_receiver_notification_emails:
                silent_tids.append(tid)

        return silent_tids

    @staticmethod
    def db_new_content(session):
        """
        The content still to be announced to its recipients: the reports, the comments and the
        files, in the order they arrived
        """
        results1 = session.query(models.User, models.ReceiverTip, models.InternalTip, models.ReceiverTip) \
            .filter(models.User.id == models.ReceiverTip.receiver_id,
                    models.InternalTip.id == models.ReceiverTip.internaltip_id,
                    models.ReceiverTip.new.is_(True)) \
            .order_by(models.InternalTip.creation_date)

        results2 = session.query(models.User, models.ReceiverTip, models.InternalTip, models.Comment) \
            .filter(models.User.id == models.ReceiverTip.receiver_id,
                    models.ReceiverTip.internaltip_id == models.Comment.internaltip_id,
                    models.InternalTip.id == models.ReceiverTip.internaltip_id,
                    models.Comment.new.is_(True)) \
            .order_by(models.Comment.creation_date)

        results3 = session.query(models.User, models.ReceiverTip, models.InternalTip, models.WhistleblowerFile) \
            .filter(models.User.id == models.ReceiverTip.receiver_id,
                    models.ReceiverTip.id == models.WhistleblowerFile.receivertip_id,
                    models.InternalTip.id == models.ReceiverTip.internaltip_id,
                    models.InternalFile.id == models.WhistleblowerFile.internalfile_id,
                    models.WhistleblowerFile.new.is_(True)) \
            .order_by(models.InternalFile.creation_date)

        results4 = session.query(models.User, models.ReceiverTip, models.InternalTip, models.ReceiverFile) \
                          .filter(models.User.id == models.ReceiverTip.receiver_id,
                                  models.ReceiverTip.internaltip_id == models.ReceiverFile.internaltip_id,
                                  models.InternalTip.id == models.ReceiverTip.internaltip_id,
                                  models.ReceiverFile.new.is_(True)) \
                          .order_by(models.ReceiverFile.creation_date)

        return itertools.chain(results1, results2, results3, results4)

    @staticmethod
    def is_not_announced(user, rtip, itip, obj, silent, announced):
        """
        Whether a piece of content is not announced to a recipient: on a site that does not notify,
        on a report announced in this run or read since the last announcement, authored by the
        recipient itself, or personal
        """
        return silent or \
            announced or \
            rtip.last_notification > rtip.last_access or \
            (isinstance(obj, models.ReceiverTip) and itip.operator_id == user.id) or \
            (isinstance(obj, (models.Comment, models.ReceiverFile)) and
             (obj.author_id == user.id or
              obj.visibility == models.EnumVisibility.personal.name))

    def announce_new_content(self, session, now_dt, silent_tids):
        """
        Announce to the recipients the content that arrived on their reports, once per report
        """
        rtips_ids = {}

        for user, rtip, itip, obj in self.db_new_content(session):
            tid = user.tid

            if self.is_not_announced(user, rtip, itip, obj, tid in silent_tids, rtips_ids.get(rtip.id, False)):
                obj.new = False
                continue

            try:
                if isinstance(obj, models.ReceiverTip):
                    # A report created by an exchange is announced as the exchange, not as a new
                    # report
                    data = {'type': 'transmission' if itip.type == 'exchange' else 'tip'}
                else:
                    data = {'type': 'tip_update'}

                data['user'] = user_serialize_user(session, user, user.language)
                data['tip'] = serializers.serialize_rtip(session, itip, rtip, user.language)

                self.process_mail_creation(session, tid, data)

                # Mark the report as notified only after the mail has been
                # successfully created, so that a rendering failure leaves the
                # report eligible for retry on the next run instead of being
                # silently and permanently flagged as notified.
                obj.new = False
                rtip.last_notification = now_dt
                rtips_ids[rtip.id] = True
            except Exception:
                log.err("Unable to generate notification for report %s", rtip.id, tid=tid)

    def send_reminders(self, session, now_dt, silent_tids):
        """
        Remind the recipients of the reports whose reminder date has come
        """
        for user in session.query(models.User).filter(models.User.id == models.ReceiverTip.receiver_id,
                                                      not_(models.User.tid.in_(silent_tids)),
                                                      models.ReceiverTip.internaltip_id == models.InternalTip.id,
                                                      models.InternalTip.reminder_date < now_dt).distinct():

            data = {'type': 'tip_reminder'}

            try:
                data['user'] = user_serialize_user(session, user, user.language)
                self.process_mail_creation(session, user.tid, data)
            except Exception as e:
                log.err("Unable to generate a user notification: %s", e, tid=user.tid)

    @staticmethod
    def crossed_threshold(exp_dt, now_dt, thresholds):
        """
        The latest reminder threshold an expiration has crossed, with the date it was crossed on
        """
        applicable = []
        for t in thresholds:
            target_dt = exp_dt - timedelta(days=t)
            if target_dt <= now_dt:
                applicable.append((t, target_dt))

        if not applicable:
            return None

        return max(applicable, key=lambda x: x[1])

    def collect_expiration_reminders(self, session, now_dt, now_date, silent_tids):
        """
        Collect, by recipient, the reports whose expiration has crossed a reminder threshold the
        recipient has not been reminded of yet

        :return: The reminders by recipient, None when the expirations are beyond the threshold
        """
        thresholds = [28, 14, 7, 3, 1]

        max_threshold = self.state.tenants[1].cache.notification.tip_expiration_threshold

        rows = session.query(models.User, models.ReceiverTip, models.InternalTip) \
            .filter(models.User.id == models.ReceiverTip.receiver_id,
                    models.ReceiverTip.internaltip_id == models.InternalTip.id,
                    models.InternalTip.status == 'opened',
                    models.InternalTip.expiration_date.isnot(None),
                    models.InternalTip.expiration_date > now_dt,
                    models.InternalTip.expiration_date <= now_dt + timedelta(days=max_threshold)) \
            .order_by(models.InternalTip.expiration_date)

        notifications_by_user = {}
        for user, rtip, itip in rows:
            tid = user.tid
            if tid in silent_tids:
                continue

            exp_dt = _to_datetime(itip.expiration_date)
            if not exp_dt:
                continue

            threshold_days = self.state.tenants[1].cache.notification.tip_expiration_threshold
            if exp_dt - now_dt > timedelta(days=threshold_days):
                return None

            chosen = self.crossed_threshold(exp_dt, now_dt, thresholds)
            if chosen is None:
                continue

            chosen_threshold, chosen_target_dt = chosen

            last_sent_dt = _to_datetime(user.last_expiration_reminder_date)

            if last_sent_dt is None or last_sent_dt < chosen_target_dt:
                days_until_exp = (exp_dt.date() - now_date).days
                notifications_by_user.setdefault(user.id, {'user_obj': user, 'tid': tid, 'entries': []})['entries'].append({
                    'itip': itip,
                    'rtip': rtip,
                    'threshold': chosen_threshold,
                    'target_dt': chosen_target_dt,
                    'days_until_exp': days_until_exp
                })

        return notifications_by_user

    def record_simulated_reminders(self, user, entries):
        """
        Count, in place of sending, the reminders a recipient would be sent
        """
        uid = str(user.id)
        user_stats = self.simulation_stats['users'].setdefault(uid, {
            'grouped_mails': 0,
            'total_reminders': 0,
            'reminders_per_report': {}
        })

        # Count grouped email for this user
        user_stats['grouped_mails'] += 1
        self.simulation_stats['totals']['grouped_emails'] += 1

        # Track each report’s reminder
        for e in entries:
            key = (user.id, e['itip'].id)
            self.sent_reminders.setdefault(key, []).append(e['threshold'])
            user_stats['reminders_per_report'].setdefault(str(e['itip'].id), []).append(e['threshold'])

            # Increment totals
            user_stats['total_reminders'] += 1
            self.simulation_stats['totals']['total_reminders'] += 1

    def send_expiration_reminders(self, session, now_dt, notifications_by_user):
        """
        Send each recipient a single summary of the reports about to expire
        """
        for _, payload in notifications_by_user.items():
            user = payload['user_obj']
            tid = payload['tid']
            entries = payload['entries']

            try:
                serialized_user = user_serialize_user(session, user, user.language)
            except Exception as e:
                log.err("Unable to serialize user %s for the expiration reminder: %s", user.id, e)
                continue

            tips_serialized = []
            for e in entries:
                tip_ser = serializers.serialize_rtip(session, e['itip'], e['rtip'], user.language)
                tip_ser['days_until_exp'] = e['days_until_exp']
                tip_ser['reminder_threshold'] = e['threshold']
                tips_serialized.append(tip_ser)

            if self.simulate_mode:
                self.record_simulated_reminders(user, entries)

            if not tips_serialized:
                continue

            data = {
                'type': 'tip_expiration_summary',
                'user': serialized_user,
                'expiring_submission_count': len(tips_serialized),
                'earliest_expiration_date': min([e['itip'].expiration_date for e in entries]),
                'tips': tips_serialized
            }
            try:
                self.process_mail_creation(session, tid, data)
            except Exception as e:
                log.err("Unable to create the expiration reminder for user %s: %s", user.id, e)
                continue

            user.last_expiration_reminder_date = now_dt

    @transact
    def generate(self, session):
        now_dt = datetime_now()
        now_date = now_dt.date()

        config = ConfigFactory(session, 1)
        timestamp_daily_notifications = config.get_val('timestamp_daily_notifications')

        silent_tids = self.silent_tids()

        self.announce_new_content(session, now_dt, silent_tids)

        if now_dt < datetime.fromtimestamp(timestamp_daily_notifications) + timedelta(1):
            return

        config.set_val('timestamp_daily_notifications', now_dt)

        for tid in self.state.tenants:
            self.db_generate_emails_for_expiring_reports(session, tid)

        self.db_generate_email_for_unread_reports(session, now_dt, silent_tids)

        self.send_reminders(session, now_dt, silent_tids)

        notifications_by_user = self.collect_expiration_reminders(session, now_dt, now_date, silent_tids)
        if notifications_by_user is None:
            return

        self.send_expiration_reminders(session, now_dt, notifications_by_user)


@transact
def get_mails_from_the_pool(session):
    """
    Fetch up to 100 email from the pool of email to be sent
    """
    ret = []

    for mail in session.query(models.Mail).order_by(models.Mail.creation_date).limit(100):
        ret.append({
            'id': mail.id,
            'address': mail.address,
            'subject': mail.subject,
            'body': mail.body,
            'tid': mail.tid,
            'secondary_smtp': mail.secondary_smtp
        })

    return ret


class Notification(LoopingJob):
    interval = 10
    monitor_interval = 3 * 60

    def generate_emails(self):
        return MailGenerator(self.state).generate()

    @defer.inlineCallbacks
    def spool_emails(self):
        mails = yield get_mails_from_the_pool()
        for mail in mails:
            sent = yield self.state.sendmail(mail['tid'], mail['address'], mail['subject'], mail['body'], use_smtp2=mail['secondary_smtp'])
            if sent:
                yield tw(db_del, models.Mail, models.Mail.id == mail['id'])

            yield deferred_sleep(1)

    @defer.inlineCallbacks
    def operation(self):
        yield self.generate_emails()
        yield self.spool_emails()
