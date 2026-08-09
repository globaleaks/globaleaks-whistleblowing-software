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


@transact
def get_mail_routing_flags(session):
    return [m.secondary_smtp for m in session.query(models.Mail)]


class TestSecondarySMTPRouting(helpers.TestGLWithPopulatedDB):
    @inlineCallbacks
    def generate_submission_mails(self):
        # The routing is asserted on the notifications a submission produces, so
        # the expiration alert is switched off: the reports of the populated
        # database fall inside its horizon and would add emails of a type the
        # tests do not select, making the assertions depend on the configured
        # threshold rather than on the routing.
        self.state.tenants[1].cache.notification.tip_expiration_threshold = 0

        yield self.perform_full_submission_actions()
        yield Delivery().run()

        notification = Notification()
        notification.skip_sleep = True
        yield notification.generate_emails()

    @inlineCallbacks
    def test_selected_types_are_routed_to_smtp2(self):
        # Route the notification types produced by a submission through smtp2
        yield tw(db_set_config_variable, 1, 'smtp2_enabled', True)
        yield tw(db_set_config_variable, 1, 'smtp2_template_types', ['tip', 'tip_update'])

        yield self.generate_submission_mails()

        flags = yield get_mail_routing_flags()

        self.assertTrue(len(flags) > 0)
        self.assertTrue(all(flags))

    @inlineCallbacks
    def test_unselected_types_are_not_routed_to_smtp2(self):
        # smtp2 is enabled but none of the produced types are selected
        yield tw(db_set_config_variable, 1, 'smtp2_enabled', True)
        yield tw(db_set_config_variable, 1, 'smtp2_template_types', [])

        yield self.generate_submission_mails()

        flags = yield get_mail_routing_flags()

        self.assertTrue(len(flags) > 0)
        self.assertFalse(any(flags))


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
