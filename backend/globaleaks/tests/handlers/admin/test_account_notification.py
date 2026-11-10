from sqlalchemy.exc import NoResultFound
from twisted.internet.defer import inlineCallbacks

from globaleaks import models
from globaleaks.handlers.admin import context, field, operation, user, user_profile
from globaleaks.handlers.admin.notification import db_notify_account_change
from globaleaks.models.config import ConfigL10NFactory
from globaleaks.orm import transact, tw
from globaleaks.rest import errors
from globaleaks.tests import helpers


@transact
def get_alerts(session):
    return [(mail.tid, mail.address, mail.subject, mail.body)
            for mail in session.query(models.Mail).order_by(models.Mail.creation_date)]


@transact
def configure_user(session, user_id, **values):
    session.query(models.User).filter(models.User.id == user_id).update(values)


@transact
def notify_then_fail(session, user_id):
    account = session.query(models.User).filter(models.User.id == user_id).one()
    db_notify_account_change(session, account, 'deleted')
    raise errors.ForbiddenOperation


@transact
def set_translation(session):
    session.add(models.EnabledLanguage({'tid': 1, 'name': 'fr'}))
    session.flush()
    config = ConfigL10NFactory(session, 1)
    config.set_val('fr', 'account_change_mail_template', 'Bonjour {RecipientName}: {Action}')
    config.set_val('fr', 'account_change_disabled', 'Votre compte a été désactivé')


class TestAccountNotifications(helpers.TestHandlerWithPopulatedDB):
    _handler = user.UserInstance
    pgp_configuration = 'NONE'

    @inlineCallbacks
    def setUp(self):
        yield helpers.TestHandlerWithPopulatedDB.setUp(self)
        self.account_id = self.dummy_receiver_1['id']
        self.operator = self.request(role='admin').session

    @inlineCallbacks
    def update_account(self, **changes):
        request = yield tw(user.get_user, 1, self.account_id)
        request['pgp_key_remove'] = False
        request.update(changes)
        return (yield tw(user.db_update_user, 1, self.operator, self.account_id, request, 'en'))

    @inlineCallbacks
    def assert_alert(self, action, address=None):
        alerts = yield get_alerts()
        self.assertEqual(len(alerts), 1)
        tid, destination, subject, body = alerts[0]
        self.assertEqual(tid, 1)
        self.assertEqual(destination, address or self.dummy_receiver_1['mail_address'])
        self.assertEqual(subject, 'Account configuration changed')
        self.assertIn(self.dummy_receiver_1['name'], body)
        self.assertIn(action, body)
        self.assertNotIn('{Action}', body)

    @inlineCallbacks
    def test_disabling_notifies_once(self):
        yield self.update_account(enabled=False)
        yield self.update_account(enabled=False)
        yield self.assert_alert('Your account has been disabled')

    @inlineCallbacks
    def test_email_change_notifies_previous_address(self):
        yield self.update_account(mail_address='new@example.org')
        yield self.assert_alert('The email configured on your account has been changed')

    @inlineCallbacks
    def test_each_sensitive_change_notifies_the_previous_address(self):
        yield self.update_account(mail_address='new@example.org', enabled=False)
        alerts = yield get_alerts()
        self.assertEqual(len(alerts), 2)
        self.assertEqual({alert[1] for alert in alerts}, {self.dummy_receiver_1['mail_address']})
        self.assertTrue(any('Your account has been disabled' in alert[3] for alert in alerts))
        self.assertTrue(any('The email configured on your account has been changed' in alert[3] for alert in alerts))

    @inlineCallbacks
    def test_unrelated_update_does_not_notify(self):
        yield self.update_account(name='New name')
        self.assertEqual((yield get_alerts()), [])

    @inlineCallbacks
    def test_enabling_does_not_notify(self):
        yield configure_user(self.account_id, enabled=False)
        yield self.update_account(enabled=True)
        self.assertEqual((yield get_alerts()), [])

    @inlineCallbacks
    def test_missing_email_does_not_queue_empty_recipient(self):
        yield configure_user(self.account_id, mail_address='')
        yield self.update_account(enabled=False)
        self.assertEqual((yield get_alerts()), [])

    @inlineCallbacks
    def test_deleted_account_receives_alert(self):
        yield tw(user.db_delete_user, 1, self.operator, self.account_id, None)
        yield self.assert_alert('Your account has been deleted')
        yield self.assertFailure(tw(user.get_user, 1, self.account_id), errors.ResourceNotFound)

    @inlineCallbacks
    def test_deleting_another_tenants_account_does_not_notify(self):
        yield self.assertFailure(tw(user.db_delete_user, 2, self.operator, self.account_id, None), NoResultFound)
        self.assertEqual((yield get_alerts()), [])

    @inlineCallbacks
    def test_password_reset_notifies(self):
        yield operation.set_user_password(1, self.operator, self.account_id, helpers.VALID_KEY)
        yield self.assert_alert('Your password has been reset')

    @inlineCallbacks
    def test_failed_change_rolls_back_notification(self):
        yield self.assertFailure(notify_then_fail(self.account_id), errors.ForbiddenOperation)
        self.assertEqual((yield get_alerts()), [])

    @inlineCallbacks
    def test_uses_recipient_language(self):
        yield set_translation()
        yield configure_user(self.account_id, language='fr')
        yield self.update_account(enabled=False)
        alerts = yield get_alerts()
        self.assertEqual(len(alerts), 1)
        self.assertEqual(alerts[0][3], 'Bonjour ' + self.dummy_receiver_1['name'] + ': Votre compte a été désactivé')

    @inlineCallbacks
    def test_channel_removal_notifies_only_removed_receiver(self):
        channel = yield context.get_context(1, self.dummy_context['id'], 'en')
        channel['receivers'].remove(self.account_id)
        yield context.update_context(1, channel['id'], channel, 'en')
        yield self.assert_alert('You have been removed from a channel')
        yield context.update_context(1, channel['id'], channel, 'en')
        yield self.assert_alert('You have been removed from a channel')

    @inlineCallbacks
    def test_channel_reordering_does_not_notify(self):
        channel = yield context.get_context(1, self.dummy_context['id'], 'en')
        channel['receivers'].reverse()
        yield context.update_context(1, channel['id'], channel, 'en')
        self.assertEqual((yield get_alerts()), [])

    @inlineCallbacks
    def test_invalid_channel_update_does_not_notify(self):
        channel = yield context.get_context(1, self.dummy_context['id'], 'en')
        channel['receivers'] = ['00000000-0000-0000-0000-000000000000']
        yield self.assertFailure(context.update_context(1, channel['id'], channel, 'en'), errors.InputValidationError)
        self.assertEqual((yield get_alerts()), [])

    @inlineCallbacks
    def make_option(self):
        request = helpers.get_dummy_field()
        request['instance'] = 'template'
        request['options'][0]['trigger_receiver'] = [self.account_id]
        created = yield field.create_field(1, request, 'en')
        return created

    @inlineCallbacks
    def test_question_option_removal_notifies(self):
        created = yield self.make_option()
        option = created['options'][0]
        option['trigger_receiver'] = []
        yield tw(field.db_update_fieldoption, created['id'], option['id'], option, 'en', 0)
        yield self.assert_alert('You have been removed from a question option association')

    @inlineCallbacks
    def test_deleting_all_options_notifies(self):
        created = yield self.make_option()
        yield tw(field.db_update_fieldoptions, created['id'], [], 'en')
        yield self.assert_alert('You have been removed from a question option association')

    @inlineCallbacks
    def test_profile_channel_removal_notifies(self):
        @transact
        def remove_channel(session):
            account = session.query(models.User).filter(models.User.id == self.account_id).one()
            user_profile.sync_contexts(session, account.profile, {'contexts': [self.dummy_context['id']]})
            session.flush()
            user_profile.sync_contexts(session, account.profile, {'contexts': []})

        yield remove_channel()
        yield self.assert_alert('You have been removed from a channel')
