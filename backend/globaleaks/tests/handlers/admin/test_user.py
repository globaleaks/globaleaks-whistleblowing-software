from twisted.internet.defer import inlineCallbacks

from globaleaks import models
from globaleaks.handlers.admin import user
from globaleaks.sessions import Sessions
from globaleaks.tests import helpers


class TestSessionRevocationOnUpdate(helpers.TestInstanceHandler):
    _handler = user.UserInstance
    _test_desc = {
        'model': models.User,
        'create': user.create_user,
        'data': {
            'role': 'receiver',
            'name': 'Mario Rossi',
            'mail_address': 'receiver@theguardian.com',
            'language': 'en'
        }
    }

    def get_dummy_request(self):
        data = helpers.TestInstanceHandler.get_dummy_request(self)
        data['pgp_key_remove'] = False
        return data

    @inlineCallbacks
    def test_update_revokes_target_user_session(self):
        data = self.get_dummy_request()
        data = yield self._test_desc['create'](1, self.session, data, 'en')

        for k, v in self._test_desc['data'].items():
            data[k] = v

        # The target user holds an active session that must be revoked
        Sessions.new(1, data['id'], 1, 'receiver')

        handler = self.request(data, role='admin')
        yield handler.put(data['id'])

        self.assertFalse(any(s.user_id == data['id'] for s in Sessions.values()))

    @inlineCallbacks
    def test_update_preserves_operator_own_session(self):
        data = self.get_dummy_request()
        data = yield self._test_desc['create'](1, self.session, data, 'en')

        for k, v in self._test_desc['data'].items():
            data[k] = v

        # An administrator editing their own record must stay logged in
        handler = self.request(data, role='admin', user_id=data['id'])
        yield handler.put(data['id'])

        self.assertTrue(any(s.user_id == data['id'] for s in Sessions.values()))

    @inlineCallbacks
    def test_delete_revokes_target_user_session(self):
        data = self.get_dummy_request()
        data = yield self._test_desc['create'](1, self.session, data, 'en')

        # The deleted user holds an active session that must be revoked
        Sessions.new(1, data['id'], 1, 'receiver')

        handler = self.request(data, role='admin')
        yield handler.delete(data['id'])

        self.assertFalse(any(s.user_id == data['id'] for s in Sessions.values()))


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
