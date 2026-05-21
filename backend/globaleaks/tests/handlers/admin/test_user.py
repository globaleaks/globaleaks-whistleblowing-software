from twisted.internet import defer
from twisted.internet.defer import returnValue

from globaleaks import models
from globaleaks.handlers.admin import user
from globaleaks.orm import transact
from globaleaks.tests import helpers


class TestAdminCollection(helpers.TestCollectionHandler):
    _handler = user.UsersCollection
    _test_desc = {
        'model': models.User,
        'create': user.create_user,
        'data': {
            'role': 'admin',
            'name': 'Mario Rossi',
            'mail_address': 'admin@theguardian.com',
            'language': 'en',
            'send_activation_link': True
        }
    }

    def get_dummy_request(self):
        data = helpers.TestCollectionHandler.get_dummy_request(self)
        data['pgp_key_remove'] = False
        return data


class TestAdminInstance(helpers.TestInstanceHandler):
    _handler = user.UserInstance
    _test_desc = {
        'model': models.User,
        'create': user.create_user,
        'data': {
            'role': 'admin',
            'mail_address': 'admin@theguardian.com',
            'language': 'en',
            'send_activation_link': True
        }
    }

    def get_dummy_request(self):
        data = helpers.TestInstanceHandler.get_dummy_request(self)
        data['pgp_key_remove'] = False
        return data


class TestReceiverCollection(TestAdminCollection):
    _test_desc = {
        'model': models.User,
        'create': user.create_user,
        'data': {
            'role': 'receiver',
            'name': 'Mario Rossi',
            'mail_address': 'receiver@theguardian.com',
            'language': 'en',
            'send_activation_link': True
        }
    }


class TestReceiverInstance(TestAdminInstance):
    _test_desc = {
        'model': models.User,
        'create': user.create_user,
        'data': {
            'role': 'receiver',
            'name': 'Mario Rossi',
            'mail_address': 'receiver@theguardian.com',
            'language': 'en',
            'send_activation_link': True
        }
    }


class TestCustodianCollection(TestAdminCollection):
    _test_desc = {
        'model': models.User,
        'create': user.create_user,
        'data': {
            'role': 'custodian',
            'name': 'Mario Rossi',
            'mail_address': 'custodian@theguardian.com',
            'language': 'en',
            'send_activation_link': True
        }
    }


class TestCustodianInstance(TestAdminInstance):
    _test_desc = {
        'model': models.User,
        'create': user.create_user,
        'data': {
            'role': 'custodian',
            'mail_address': 'custodian@theguardian.com',
            'language': 'en'
        }
    }


class TestAdminSecurityAlertOnUserUpdate(helpers.TestHandlerWithPopulatedDB):
    _handler = user.UserInstance

    def get_dummy_request(self):
        return dict(self.dummyReceiver_1)

    @defer.inlineCallbacks
    def test_email_change_sends_notification(self):
        yield self.test_model_count(models.Mail, 0)

        request_data = self.get_dummy_request()
        request_data['mail_address'] = 'new-email@example.com'

        handler = self.request(request_data, role='admin', user_id=self.dummyReceiver_1['id'])
        yield handler.put(self.dummyReceiver_1['id'])

        yield self.test_model_count(models.Mail, 1)

    @defer.inlineCallbacks
    def test_notification_disabled_sends_notification(self):
        yield self.test_model_count(models.Mail, 0)

        request_data = self.get_dummy_request()
        request_data['notification'] = False

        handler = self.request(request_data, role='admin', user_id=self.dummyReceiver_1['id'])
        yield handler.put(self.dummyReceiver_1['id'])

        yield self.test_model_count(models.Mail, 1)

    @defer.inlineCallbacks
    def test_account_disabled_sends_notification(self):
        yield self.test_model_count(models.Mail, 0)

        request_data = self.get_dummy_request()
        request_data['enabled'] = False

        handler = self.request(request_data, role='admin', user_id=self.dummyReceiver_1['id'])
        yield handler.put(self.dummyReceiver_1['id'])

        yield self.test_model_count(models.Mail, 1)

    @defer.inlineCallbacks
    def test_multiple_changes_send_single_notification(self):
        yield self.test_model_count(models.Mail, 0)

        request_data = self.get_dummy_request()
        request_data['mail_address'] = 'another@example.com'
        request_data['notification'] = False

        handler = self.request(request_data, role='admin', user_id=self.dummyReceiver_1['id'])
        yield handler.put(self.dummyReceiver_1['id'])

        # Two changes in one PUT → exactly one mail
        yield self.test_model_count(models.Mail, 1)

    @defer.inlineCallbacks
    def test_no_notification_when_nothing_security_relevant_changed(self):
        yield self.test_model_count(models.Mail, 0)

        request_data = self.get_dummy_request()
        # name change only — not security-relevant, should not trigger mail
        request_data['name'] = 'New Name'

        handler = self.request(request_data, role='admin', user_id=self.dummyReceiver_1['id'])
        yield handler.put(self.dummyReceiver_1['id'])

        yield self.test_model_count(models.Mail, 0)

    @defer.inlineCallbacks
    def test_no_notification_when_reenabling(self):
        yield self.test_model_count(models.Mail, 0)

        # First disable notifications (this WILL send a mail)
        request_data = self.get_dummy_request()
        request_data['notification'] = False
        handler = self.request(request_data, role='admin', user_id=self.dummyReceiver_1['id'])
        yield handler.put(self.dummyReceiver_1['id'])
        yield self.test_model_count(models.Mail, 1)

        # Now re-enable notifications — this must NOT send another mail
        request_data2 = self.get_dummy_request()
        request_data2['notification'] = True
        handler2 = self.request(request_data2, role='admin', user_id=self.dummyReceiver_1['id'])
        yield handler2.put(self.dummyReceiver_1['id'])
        yield self.test_model_count(models.Mail, 1)  # Still 1, not 2

    @defer.inlineCallbacks
    def test_email_change_notifies_old_address(self):
        old_email = self.dummyReceiver_1['mail_address']
        new_email = 'new-address@example.com'

        request_data = self.get_dummy_request()
        request_data['mail_address'] = new_email

        handler = self.request(request_data, role='admin', user_id=self.dummyReceiver_1['id'])
        yield handler.put(self.dummyReceiver_1['id'])

        @transact
        def get_mail_addresses(session):
            return [mail.address for mail in session.query(models.Mail).all()]

        addresses = yield get_mail_addresses()
        self.assertEqual(len(addresses), 1)
        self.assertEqual(addresses[0], old_email)


class TestAdminSecurityAlertOnUserDelete(helpers.TestHandlerWithPopulatedDB):
    _handler = user.UserInstance

    @defer.inlineCallbacks
    def test_deletion_sends_notification(self):
        yield self.test_model_count(models.Mail, 0)

        handler = self.request({}, role='admin')
        yield handler.delete(self.dummyReceiver_1['id'])

        yield self.test_model_count(models.Mail, 1)
