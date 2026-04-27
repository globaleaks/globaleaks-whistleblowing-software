from datetime import timedelta
import json
from unittest.mock import patch
from globaleaks.utils.crypto import GCE
from twisted.internet.defer import inlineCallbacks, succeed

from globaleaks import models
from globaleaks.handlers.whistleblower.submission import db_assign_submission_progressive
from globaleaks.jobs.antivirus_decryptor import update_verification_status
from globaleaks.jobs.delivery import Delivery, save_antivirus_status
from globaleaks.jobs.notification import MailGenerator, Notification
from globaleaks.models.config import db_set_config_variable
from globaleaks.orm import transact, tw
from globaleaks.tests import helpers
from globaleaks.utils.utility import datetime_never, datetime_now, datetime_null

import globaleaks.jobs.notification as notif_mod

THRESHOLD_TO_EXPECTED_EMAILS = {28: 5, 14: 4, 7: 3, 3: 2, 1: 1}
THRESHOLDS = list(THRESHOLD_TO_EXPECTED_EMAILS.keys())


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

        yield self.test_model_count(models.Mail, 0)


class TestPeriodicExpirationReminders(helpers.TestGLWithPopulatedDB):
    @transact
    def create_expiring_tip(self, session, tid, context_id, user_ids, days_until_exp):
        itip = models.InternalTip()
        itip.context_id = context_id
        itip.tid = tid
        itip.progressive = db_assign_submission_progressive(session, tid)
        itip.status = 'opened'
        itip.expiration_date = datetime_now() + timedelta(days=days_until_exp)
        itip.creation_date = datetime_now()
        itip.update_date = datetime_now()
        itip.last_access = datetime_now()

        itip.receipt_hash = GCE.generate_receipt()
        itip.crypto_prv_key = "test_prv_key"
        itip.crypto_pub_key = "test_pub_key"
        itip.crypto_tip_pub_key = "test_tip_pub_key"
        itip.crypto_tip_prv_key = "test_tip_prv_key"
        itip.deprecated_crypto_files_pub_key = "test_files_pub_key"

        session.add(itip)
        session.flush()

        user_ids = [user_ids[0]]
        for user_id in user_ids:
            rtip = models.ReceiverTip()
            rtip.internaltip_id = itip.id
            rtip.receiver_id = user_id
            session.add(rtip)
            session.flush()

        return itip.id

    @inlineCallbacks
    def run_simulation(
        self,
        downtime_hours=None,
        downtime_start_hour=0,
        downtime_every_x_days=1,
        days=90
    ):
        """
        Simulate notifications with optional periodic daily downtime period.
        - downtime_hours: number of hours per downtime (default 3)
        - downtime_start_hour: starting hour of downtime (default 0)
        - downtime_every_x_days: frequency (e.g., 1 = every day, 3 = every 3rd day)
        """
        notif = Notification()
        notif.skip_sleep = True
        MailGenerator.simulate_mode = True
        MailGenerator.reset_stats()

        orig_datetime_now = notif_mod.datetime_now
        baseline = datetime_now()

        downtime_hours = downtime_hours or 3
        downtime_start_hour = downtime_start_hour or 0
        downtime_every_x_days = downtime_every_x_days or 1

        for day in range(days):
            is_downtime_day = (day % downtime_every_x_days == 0)

            if is_downtime_day and downtime_hours < 24:
                current_time = baseline + timedelta(days=day)
                notif_mod.datetime_now = lambda: current_time
                yield notif.generate_emails()

        notif_mod.datetime_now = orig_datetime_now

        return MailGenerator.sent_reminders, MailGenerator.simulation_stats

    @inlineCallbacks
    def _test_threshold(self, threshold, downtime_hours=None, downtime_every_x_days=1, offset=0):
        """Core test logic parameterized by threshold and downtime"""
        context_id = self.dummyContext['id']

        # Alternate every 5 days between sending to both users and to user 1 only.
        for i in range(1, 30, 5):
            if i % 2:
                user_ids = [self.dummyReceiver_1['id'], self.dummyReceiver_2['id']]
            else:
                user_ids = [self.dummyReceiver_1['id']]

            yield self.create_expiring_tip(1, context_id, user_ids, days_until_exp=threshold + i)

        self.state.tenants[1].cache.notification.tip_expiration_threshold = threshold

        sent_reminders, simulation_stats = yield self.run_simulation(
            downtime_hours=downtime_hours,
            downtime_every_x_days=downtime_every_x_days,
            days=90
        )

        expected_count = THRESHOLD_TO_EXPECTED_EMAILS[threshold]
        expected_count -= offset

        # Per-user validation
        for uid in user_ids:
            user_data = simulation_stats['users'].get(str(uid), {})
            reminders_per_report = user_data.get('reminders_per_report', {})
            for report_id, reminders in reminders_per_report.items():
                self.assertGreaterEqual(
                    len(reminders), expected_count,
                    f"Each report should have at least {expected_count} reminders"
                )


def make_test(threshold, downtime_hours=None, downtime_every_x_days=1, offset=0):
    @inlineCallbacks
    def test(self):
        yield self._test_threshold(threshold, downtime_hours=downtime_hours, downtime_every_x_days=downtime_every_x_days, offset=offset)
    return test


class TestAntivirusDeliveryToggle(helpers.TestGLWithPopulatedDB):
    @transact
    def set_antivirus_enabled(self, session, enabled):
        db_set_config_variable(session, 1, 'antivirus_enabled', enabled)

    @transact
    def get_first_internal_file_id(self, session):
        return session.query(models.InternalFile.id).order_by(models.InternalFile.creation_date).first()[0]

    @transact
    def get_internal_file_states(self, session):
        return [(ifile.state, ifile.verification_date) for ifile in session.query(models.InternalFile).all()]

    @transact
    def get_internal_file_state(self, session, file_id):
        ifile = session.query(models.InternalFile).filter_by(id=file_id).one()
        return ifile.state, ifile.verification_date

    @inlineCallbacks
    def test_delivery_keeps_files_pending_when_antivirus_disabled(self):
        yield self.perform_minimal_submission_actions()
        yield self.set_antivirus_enabled(False)
        yield Delivery().run()

        file_states = yield self.get_internal_file_states()
        self.assertTrue(file_states)
        for state, verification_date in file_states:
            self.assertEqual(state, 'pending')
            self.assertIsNone(verification_date)

    @inlineCallbacks
    def test_delivery_keeps_files_pending_on_scan_error(self):
        yield self.perform_minimal_submission_actions()
        yield self.set_antivirus_enabled(True)

        with patch('globaleaks.jobs.delivery.FileAnalysis.scan_file', return_value=succeed('error')):
            yield Delivery().run()

        file_states = yield self.get_internal_file_states()
        self.assertTrue(file_states)
        for state, verification_date in file_states:
            self.assertEqual(state, 'pending')
            self.assertIsNone(verification_date)

    @inlineCallbacks
    def test_delivery_discards_inflight_scan_result_after_antivirus_is_disabled(self):
        yield self.perform_minimal_submission_actions()
        yield self.set_antivirus_enabled(True)
        file_id = yield self.get_first_internal_file_id()

        yield self.set_antivirus_enabled(False)
        yield save_antivirus_status(file_id, 'safe', 'internal')

        state, verification_date = yield self.get_internal_file_state(file_id)
        self.assertEqual(state, 'pending')
        self.assertIsNone(verification_date)

    @inlineCallbacks
    def test_decryptor_discards_inflight_scan_result_after_antivirus_is_disabled(self):
        yield self.perform_minimal_submission_actions()
        yield self.set_antivirus_enabled(True)
        file_id = yield self.get_first_internal_file_id()

        yield self.set_antivirus_enabled(False)
        yield update_verification_status(file_id, 'safe')

        state, verification_date = yield self.get_internal_file_state(file_id)
        self.assertEqual(state, 'pending')
        self.assertIsNone(verification_date)


# Dynamically attach test cases
for threshold in THRESHOLDS:
    # No downtime
    setattr(
        TestPeriodicExpirationReminders,
        f"test_threshold_{threshold}_no_downtime_all_emails_sent",
        make_test(threshold)
    )

    # 3-hour nightly downtime every day
    setattr(
        TestPeriodicExpirationReminders,
        f"test_threshold_{threshold}_downtime_of_3h_every_day_all_emails_sent",
        make_test(threshold, downtime_hours=3, downtime_every_x_days=1)
    )

    # 24-hour downtime every 10 days
    setattr(
        TestPeriodicExpirationReminders,
        f"test_threshold_{threshold}_downtime_of_24h_every_10days_1_emails_off",
        make_test(threshold, downtime_hours=24, downtime_every_x_days=10, offset=1)
    )
