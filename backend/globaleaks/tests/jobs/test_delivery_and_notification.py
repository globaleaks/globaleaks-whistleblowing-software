from datetime import timedelta
from globaleaks.utils.crypto import GCE
from twisted.internet.defer import inlineCallbacks

from globaleaks import models
from globaleaks.jobs.delivery import Delivery
from globaleaks.jobs.notification import MailGenerator, Notification
from globaleaks.models.config import ConfigFactory
from globaleaks.orm import transact
from globaleaks.tests import helpers
from globaleaks.utils.utility import datetime_now, datetime_null
import globaleaks.jobs.notification as notif_mod

THRESHOLDS = [28, 14, 7, 3, 1] 

@transact
def simulate_unread_tips(session):
    ConfigFactory(session, 1).set_val('timestamp_daily_notifications', 0)

    # Simulate that 8 days has passed recipients have not accessed reports
    for user in session.query(models.User):
        user.reminder_date = datetime_null()

    for rtip in session.query(models.ReceiverTip):
        rtip.last_access = datetime_null()

    for itip in session.query(models.InternalTip):
        itip.update_date = datetime_now() - timedelta(8)


@transact
def simulate_reminders(session):
    ConfigFactory(session, 1).set_val('timestamp_daily_notifications', 0)

    for itip in session.query(models.InternalTip):
        itip.reminder_date = datetime_now() - timedelta(1)


class TestNotification(helpers.TestGLWithPopulatedDB):
    @inlineCallbacks
    def test_notification(self):
        yield self.test_model_count(models.User, 9)

        yield self.test_model_count(models.InternalTip, 0)
        yield self.test_model_count(models.ReceiverTip, 0)
        yield self.test_model_count(models.InternalFile, 0)
        yield self.test_model_count(models.ReceiverFile, 0)
        yield self.test_model_count(models.Comment, 0)
        yield self.test_model_count(models.Mail, 0)

        yield self.perform_full_submission_actions()

        yield self.test_model_count(models.InternalTip, 2)
        yield self.test_model_count(models.ReceiverTip, 4)
        yield self.test_model_count(models.InternalFile, 4)
        yield self.test_model_count(models.WhistleblowerFile, 0)
        yield self.test_model_count(models.ReceiverFile, 0)
        yield self.test_model_count(models.Comment, 4)
        yield self.test_model_count(models.Mail, 0)

        yield Delivery().run()

        yield self.test_model_count(models.InternalTip, 2)
        yield self.test_model_count(models.ReceiverTip, 4)
        yield self.test_model_count(models.InternalFile, 4)
        yield self.test_model_count(models.WhistleblowerFile, 8)
        yield self.test_model_count(models.ReceiverFile, 0)
        yield self.test_model_count(models.Comment, 4)
        yield self.test_model_count(models.Mail, 0)

        notification = Notification()
        notification.skip_sleep = True

        yield notification.generate_emails()

        yield self.test_model_count(models.Mail, 4)

        yield notification.spool_emails()

        yield self.test_model_count(models.Mail, 0)

        yield simulate_unread_tips()

        yield notification.generate_emails()

        yield self.test_model_count(models.Mail, 2)

        yield notification.spool_emails()

        yield simulate_reminders()

        yield notification.generate_emails()

        yield self.test_model_count(models.Mail, 2)

        yield notification.spool_emails()

        yield notification.generate_emails()

        yield self.test_model_count(models.Mail, 0)

        yield notification.spool_emails()

        yield self.test_model_count(models.Mail, 0)


class TestPeriodicExpirationReminders(helpers.TestGLWithPopulatedDB):

    @transact
    def create_expiring_tip(self, session, user_id, days_until_exp):
        context = session.query(models.Context).first()
        user = session.query(models.User).get(user_id)

        itip = models.InternalTip()
        itip.context_id = context.id
        itip.tid = context.tid
        itip.status = 'opened'
        itip.expiration_date = datetime_now() + timedelta(days=days_until_exp)
        itip.creation_date = datetime_now()
        itip.update_date = datetime_now()
        itip.last_access = datetime_now()

        max_prog = session.query(models.InternalTip.progressive) \
            .filter(models.InternalTip.tid == context.tid) \
            .order_by(models.InternalTip.progressive.desc()).first()
        itip.progressive = (max_prog[0] + 1) if max_prog and max_prog[0] is not None else 1

        itip.receipt_hash = GCE.generate_receipt()
        itip.crypto_prv_key = "test_prv_key"
        itip.crypto_pub_key = "test_pub_key"
        itip.crypto_tip_pub_key = "test_tip_pub_key"
        itip.crypto_tip_prv_key = "test_tip_prv_key"
        itip.deprecated_crypto_files_pub_key = "test_files_pub_key"

        session.add(itip)
        session.flush()

        rtip = models.ReceiverTip()
        rtip.internaltip_id = itip.id
        rtip.receiver_id = user.id
        session.add(rtip)
        session.flush()

        return itip.id

    @transact
    def get_first_two_receivers(self, session):
        users = session.query(models.User).filter(models.User.role == 'receiver').limit(2).all()
        return [u.id for u in users]

    @inlineCallbacks
    def run_simulation(self, downtime_days=None, days=90):
        notif = Notification()
        notif.skip_sleep = True
        MailGenerator.simulate_mode = True

        orig_datetime_now = notif_mod.datetime_now
        baseline = datetime_now()

        for day in range(days):
            if downtime_days and day in downtime_days:
                continue

            fake_now = baseline + timedelta(days=day)
            notif_mod.datetime_now = lambda: fake_now

            yield notif.generate_emails()

        notif_mod.datetime_now = orig_datetime_now

        return MailGenerator.sent_reminders

    @inlineCallbacks
    def test_full_year_no_downtime(self):
        user_ids = yield self.get_first_two_receivers()
        created_map = {}
        for uid in user_ids:
            itip_id = yield self.create_expiring_tip(uid, days_until_exp=30)
            created_map.setdefault(uid, []).append(itip_id)

        self.state.tenants[1].cache.notification.tip_expiration_threshold = 28
        sent_reminders = yield self.run_simulation(downtime_days=None, days=90)
        
        for uid, itip_list in created_map.items():
            for itip in itip_list:
                sent = sent_reminders.get((uid, itip), [])
                self.assertEqual(len(sent), 5)

    @inlineCallbacks
    def test_full_year_with_downtime(self):
        user_ids = yield self.get_first_two_receivers()
        created_map = {}
        for uid in user_ids:
            itip_id = yield self.create_expiring_tip(uid, days_until_exp=30)
            created_map.setdefault(uid, []).append(itip_id)
            
        self.state.tenants[1].cache.notification.tip_expiration_threshold = 28
        downtime_days = set(range(10, 90, 10))
        
        sent_reminders = yield self.run_simulation(downtime_days=downtime_days, days=90)
       
        for uid, itip_list in created_map.items():
            for itip in itip_list:
                sent = sent_reminders.get((uid, itip), [])
                self.assertGreaterEqual(len(sent), 3)