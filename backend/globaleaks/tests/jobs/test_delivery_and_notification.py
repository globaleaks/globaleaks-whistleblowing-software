from datetime import timedelta
from twisted.internet.defer import inlineCallbacks

from globaleaks import models
from globaleaks.jobs.delivery import Delivery
from globaleaks.jobs.notification import Notification
from globaleaks.models.config import db_set_config_variable
from globaleaks.orm import transact, tw
from globaleaks.tests import helpers
from globaleaks.utils.utility import datetime_never, datetime_now, datetime_null

@transact
def simulate_unread_tips(session):
    # Simulate that 8 days has passed recipients have not accessed reports
    for user in session.query(models.User):
        user.reminder_date = datetime_null()

    for rtip in session.query(models.ReceiverTip):
        rtip.last_access = datetime_null()

    for itip in session.query(models.InternalTip):
        itip.update_date = datetime_now() - timedelta(8)


@transact
def enable_reminders(session):
    for itip in session.query(models.InternalTip):
        itip.reminder_date = datetime_now() - timedelta(1)

@transact
def disable_reminders(session):
    for itip in session.query(models.InternalTip):
        itip.reminder_date = datetime_never()


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

        # Disable the unread reminder and ensure no unread reminders are sent
        tw(db_set_config_variable, 1, 'timestamp_daily_notifications', 0)
        save_var = self.state.tenants[1].cache.unread_reminder_time
        self.state.tenants[1].cache.unread_reminder_time = 0
        yield notification.generate_emails()
        yield self.test_model_count(models.Mail, 0)

        # Re-enable the unread reminder and ensure unread reminders are sent
        tw(db_set_config_variable, 1, 'timestamp_daily_notifications', 0)
        self.state.tenants[1].cache.unread_reminder_time = save_var
        yield notification.generate_emails()
        yield self.test_model_count(models.Mail, 2)

        yield notification.spool_emails()

        tw(db_set_config_variable, 1, 'timestamp_daily_notifications', 0)
        yield enable_reminders()
        yield notification.generate_emails()
        yield self.test_model_count(models.Mail, 2)
        yield notification.spool_emails()
        yield disable_reminders()

        tw(db_set_config_variable, 1, 'timestamp_daily_notifications', 0)
        yield notification.generate_emails()
        yield self.test_model_count(models.Mail, 0)

        yield self.set_itips_expiration_as_near_to_expire()

        # Disable the expiration reminders and ensure expiration reminders are not sent
        tw(db_set_config_variable, 1, 'timestamp_daily_notifications', 0)
        save_var = self.state.tenants[1].cache.notification.tip_expiration_threshold
        self.state.tenants[1].cache.notification.tip_expiration_threshold = 0
        yield notification.generate_emails()
        yield self.test_model_count(models.Mail, 0)

        # Re-enable the expiration reminders and ensure expiration reminders are sent
        tw(db_set_config_variable, 1, 'timestamp_daily_notifications', 0)
        self.state.tenants[1].cache.notification.tip_expiration_threshold = save_var
        yield notification.generate_emails()
        yield self.test_model_count(models.Mail, 2)

        yield notification.spool_emails()

        yield self.test_model_count(models.Mail, 0)
