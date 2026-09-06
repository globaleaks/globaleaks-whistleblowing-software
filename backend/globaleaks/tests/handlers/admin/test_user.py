from twisted.internet.defer import inlineCallbacks

from globaleaks import models
from globaleaks.handlers.admin import user
from globaleaks.handlers.admin.user_profile import db_create_user_profile
from globaleaks.handlers.base import BaseHandler
from globaleaks.handlers.user import serialize_user
from globaleaks.models.config import db_set_config_variable
from globaleaks.orm import transact, tw
from globaleaks.rest import errors
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
        Sessions.new(1, data['id'], 1, 'receiver1', 'receiver')

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
        Sessions.new(1, data['id'], 1, 'receiver1', 'receiver')

        handler = self.request(None, role='admin')
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
        data['role'] = self._test_desc['data']['role']
        data['roles'] = [self._test_desc['data']['role']]
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
        data['role'] = self._test_desc['data']['role']
        data['roles'] = [self._test_desc['data']['role']]
        data['pgp_key_remove'] = False
        return data

    @inlineCallbacks
    def test_delete_requires_confirmation(self):
        self.patch(BaseHandler, 'check_confirmation', BaseHandler.real_check_confirmation)

        data = self.get_dummy_request()
        data = yield self._test_desc['create'](1, self.session, data, 'en')

        handler = self.request(None, role='admin')

        yield self.assertFailure(handler.delete(data['id']), errors.InvalidAuthentication)

    @inlineCallbacks
    def test_delete_with_confirmation(self):
        self.patch(BaseHandler, 'check_confirmation', BaseHandler.real_check_confirmation)

        confirmation = helpers.VALID_CONFIRMATION

        data = self.get_dummy_request()
        data = yield self._test_desc['create'](1, self.session, data, 'en')

        handler = self.request(None, role='admin', headers={'x-confirmation': confirmation})

        yield handler.delete(data['id'])


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


class TestProtectedUserDeletion(helpers.TestHandlerWithPopulatedDB):
    # A freshly initialized database is required so that the protected_users
    # config row (added after the archived test database was generated) is
    # present and can be set.
    initialize_test_database_using_archived_db = False

    _handler = user.UserInstance

    @inlineCallbacks
    def test_delete_forbidden_for_protected_user(self):
        yield tw(db_set_config_variable, 1, 'protected_users', [self.dummy_receiver_1['id']])

        handler = self.request(None, role='admin')

        yield self.assertFailure(handler.delete(self.dummy_receiver_1['id']),
                                 errors.ForbiddenOperation)

@transact
def get_profile_permissions(session, profile_id):
    return {p[0] for p in session.query(models.UserProfilePermission.permission)
                                 .filter(models.UserProfilePermission.profile_id == profile_id)}


@transact
def get_user_desc(session, username):
    u = session.query(models.User).filter(models.User.username == username).one()
    return u.id, u.profile_id, serialize_user(session, u, 'en')


@transact
def create_shared_profile(session):
    return db_create_user_profile(session, 1, {
        'name': 'Shared',
        'role': 'receiver',
        'roles': ['receiver'],
        'permissions': {'can_postpone_expiration': True}
    })['id']


@transact
def create_profile(session, tid, name, role, roles, permissions):
    return db_create_user_profile(session, tid, {
        'name': name,
        'role': role,
        'roles': roles,
        'permissions': permissions
    })['id']


class TestGrantEnforcement(helpers.TestHandlerWithPopulatedDB):
    """
    The operations on users and profiles are confined to the privilege of the
    """
    _handler = user.UsersCollection

    # An administrator confined to the sole management of the users
    scoped = {p: p == 'can_manage_users' for p in models.admin_permissions}

    def get_dummy_create_request(self, role):
        request = models.User().dict('en')
        request['role'] = role
        request['roles'] = [role]
        request['profile'] = {}
        request['name'] = 'Created User'
        request['mail_address'] = 'created@example.org'
        request['language'] = 'en'
        request['pgp_key_remove'] = False
        request['send_activation_link'] = False
        return request
