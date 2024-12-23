# -*- coding: utf-8 -*-
# Implement the notification of new submissions
import itertools

from datetime import datetime, timedelta
from sqlalchemy import not_
from twisted.internet import defer

from globaleaks import models
from globaleaks.handlers.admin.node import db_admin_serialize_node
from globaleaks.handlers.admin.notification import db_get_notification
from globaleaks.handlers.user import user_serialize_user
from globaleaks.jobs.job import LoopingJob
from globaleaks.models import serializers
from globaleaks.models.config import ConfigFactory
from globaleaks.orm import db_del, transact, tw
from globaleaks.utils.log import log
from globaleaks.utils.templating import Templating
from globaleaks.utils.utility import datetime_now, deferred_sleep


def gen_cache_key(*args):
    return '-'.join(['{}'.format(arg) for arg in args])


class MailGenerator(object):
    def __init__(self, state):
        self.state = state
        self.cache = {}

    def serialize_config(self, session, key, tid, language):
        cache_key = gen_cache_key(key, tid, language)
        cache_obj = None

        if cache_key not in self.cache:
            if key == 'node':
                cache_obj = db_admin_serialize_node(session, tid, language)
            elif key == 'notification':
                cache_obj = db_get_notification(session, tid, language)

            self.cache[cache_key] = cache_obj

        return self.cache[cache_key]

    def process_mail_creation(self, session, tid, data):
        user_id = data['user']['id']
        language = data['user']['language']

        # Do not spool emails if the receiver has disabled notifications
        if not data['user']['notification'] or ('tip' in data and not data['tip']['enable_notifications']):
            log.debug("Discarding emails for %s due to receiver's preference.", user_id)
            return

        data['node'] = self.serialize_config(session, 'node', tid, language)

        if data['node']['mode'] == 'default':
            data['notification'] = self.serialize_config(session, 'notification', tid, language)
        else:
            data['notification'] = self.serialize_config(session, 'notification', 1, language)

        subject, body = Templating().get_mail_subject_and_body(data)

        session.add(models.Mail({
            'address': data['user']['mail_address'],
            'subject': subject,
            'body': body,
            'tid': tid,
        }))

    @transact
    def generate(self, session):
        now = datetime_now()

        config = ConfigFactory(session, 1)
        timestamp_daily_notifications = config.get_val('timestamp_daily_notifications')

        rtips_ids = {}
        silent_tids = []

        reminder_time = self.state.tenants[1].cache.unread_reminder_time if 1 in self.state.tenants else 7

        for tid in self.state.tenants:
            tenant = session.query(models.Tenant).filter(models.Tenant.id == tid).one_or_none()
            cache = self.state.tenants[tid].cache
            if (cache.notification and cache.enable_notification_emails_recipient) or tenant.external:
                silent_tids.append(tid)

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

        for user, rtip, itip, obj in itertools.chain(results1, results2, results3):
            tid = user.tid

            if (tid in silent_tids) or \
                rtips_ids.get(rtip.id, False) or \
                rtip.last_notification > rtip.last_access or \
                (isinstance(obj, models.Comment) and \
                 (obj.author_id == user.id or
                  obj.visibility == models.EnumVisibility.personal.name)):
                obj.new = False
                continue

            obj.new = False
            rtip.last_notification = now

            rtips_ids[rtip.id] = True

            try:
                if isinstance(obj, models.ReceiverTip):
                    data = {'type': 'tip'}
                else:
                    data = {'type': 'tip_update'}

                data['user'] = user_serialize_user(session, user, user.language)
                data['tip'] = serializers.serialize_rtip(session, itip, rtip, user.language)

                self.process_mail_creation(session, tid, data)
            except:
                pass

        if now < datetime.fromtimestamp(timestamp_daily_notifications) + timedelta(1):
            return

        config.set_val('timestamp_daily_notifications', now)

        for user in session.query(models.User).filter(models.User.id == models.ReceiverTip.receiver_id,
                                                      not_(models.User.id.in_(silent_tids)),
                                                      models.User.reminder_date < now - timedelta(reminder_time),
                                                      models.ReceiverTip.last_access < models.InternalTip.update_date,
                                                      models.ReceiverTip.internaltip_id == models.InternalTip.id,
                                                      models.InternalTip.update_date < now - timedelta(reminder_time)).distinct():
            user.reminder_date = now
            data = {'type': 'unread_tips'}

            try:
                data['user'] = user_serialize_user(session, user, user.language)
                self.process_mail_creation(session, user.tid, data)
            except:
                pass

        for user in session.query(models.User).filter(models.User.id == models.ReceiverTip.receiver_id,
                                                      not_(models.User.id.in_(silent_tids)),
                                                      models.ReceiverTip.internaltip_id == models.InternalTip.id,
                                                      models.InternalTip.reminder_date < now).distinct():

            data = {'type': 'tip_reminder'}

            try:
                data['user'] = user_serialize_user(session, user, user.language)
                self.process_mail_creation(session, user.tid, data)
            except:
                pass



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
            sent = yield self.state.sendmail(mail['tid'], mail['address'], mail['subject'], mail['body'], mail.get('secondary_smtp', False))
            if sent:
                yield tw(db_del, models.Mail, models.Mail.id == mail['id'])

            yield deferred_sleep(1)

    @defer.inlineCallbacks
    def operation(self):
        yield self.generate_emails()
        yield self.spool_emails()
