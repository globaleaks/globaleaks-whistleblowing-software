from twisted.internet.defer import inlineCallbacks

from globaleaks import models
from globaleaks.handlers.admin import user
from globaleaks.handlers.admin import user_profile
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
        yield tw(db_set_config_variable, 1, 'protected_users', [self.dummyReceiver_1['id']])

        handler = self.request(None, role='admin')

        yield self.assertFailure(handler.delete(self.dummyReceiver_1['id']),
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


class TestUserPermissions(helpers.TestHandlerWithPopulatedDB):
    _handler = user.UserInstance

    @inlineCallbacks
    def test_put_updates_the_permissions_of_the_personal_profile(self):
        user_id, profile_id, desc = yield get_user_desc('receiver1')

        self.assertEqual(user_id, profile_id)

        desc['profile']['permissions']['can_send_communications'] = True

        handler = self.request(desc, role='admin')
        yield handler.put(user_id)

        permissions = yield get_profile_permissions(profile_id)
        self.assertIn('can_send_communications', permissions)

    @inlineCallbacks
    def test_put_does_not_update_the_permissions_of_a_shared_profile(self):
        user_id, _, desc = yield get_user_desc('receiver2')

        profile_id = yield create_shared_profile()

        desc['profile_id'] = profile_id
        desc['profile']['permissions']['can_send_communications'] = True

        handler = self.request(desc, role='admin')
        yield handler.put(user_id)

        permissions = yield get_profile_permissions(profile_id)
        self.assertNotIn('can_send_communications', permissions)

    @inlineCallbacks
    def test_put_discards_unknown_permissions(self):
        user_id, profile_id, desc = yield get_user_desc('receiver1')

        desc['profile']['permissions']['can_pwn_everything'] = True

        handler = self.request(desc, role='admin')
        yield handler.put(user_id)

        permissions = yield get_profile_permissions(profile_id)
        self.assertNotIn('can_pwn_everything', permissions)


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
    operator: no path may result in an account more privileged than the
    operator that shapes it.
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

    @inlineCallbacks
    def test_created_admin_inherits_the_scope_of_its_creator(self):
        data = self.get_dummy_create_request('admin')

        handler = self.request(data, role='admin', permissions=dict(self.scoped))
        response = yield handler.post()

        permissions = yield get_profile_permissions(response['id'])
        self.assertEqual(permissions & set(models.admin_permissions), {'can_manage_users'})

    @inlineCallbacks
    def test_binding_a_profile_of_an_unrelated_tenant_is_forbidden(self):
        profile_id = yield create_profile(1, 'Alien', 'receiver', ['receiver'], {})

        yield tw(lambda session: session.query(models.UserProfile)
                                        .filter(models.UserProfile.id == profile_id)
                                        .update({'tid': 2}))

        data = self.get_dummy_create_request('receiver')
        data['profile_id'] = profile_id

        handler = self.request(data, role='admin')
        yield self.assertFailure(handler.post(), errors.InputValidationError)

    @inlineCallbacks
    def test_binding_a_profile_not_allowing_the_role_is_forbidden(self):
        profile_id = yield create_profile(1, 'Recipients', 'receiver', ['receiver'], {})

        data = self.get_dummy_create_request('custodian')
        data['profile_id'] = profile_id

        handler = self.request(data, role='admin')
        yield self.assertFailure(handler.post(), errors.InputValidationError)

    @inlineCallbacks
    def test_binding_a_profile_above_the_operator_scope_is_forbidden(self):
        profile_id = yield create_profile(1, 'Configurators', 'admin', ['admin'], {'can_manage_settings': True})

        data = self.get_dummy_create_request('admin')
        data['profile_id'] = profile_id

        handler = self.request(data, role='admin', permissions=dict(self.scoped))
        yield self.assertFailure(handler.post(), errors.ForbiddenOperation)

    @inlineCallbacks
    def test_binding_a_profile_within_the_operator_scope_is_allowed(self):
        profile_id = yield create_profile(1, 'Managers', 'admin', ['admin'], {'can_manage_users': True})

        data = self.get_dummy_create_request('admin')
        data['profile_id'] = profile_id

        handler = self.request(data, role='admin', permissions=dict(self.scoped))
        response = yield handler.post()

        self.assertEqual(response['profile_id'], profile_id)

    @inlineCallbacks
    def test_binding_an_operational_profile_is_allowed_to_a_scoped_operator(self):
        profile_id = yield create_profile(1, 'Operatives', 'receiver', ['receiver'],
                                          {'can_postpone_expiration': True, 'can_delete_submission': True})

        data = self.get_dummy_create_request('receiver')
        data['profile_id'] = profile_id

        handler = self.request(data, role='admin', permissions=dict(self.scoped))
        response = yield handler.post()

        self.assertEqual(response['profile_id'], profile_id)

    @inlineCallbacks
    def test_switching_a_user_to_a_profile_above_the_operator_scope_is_forbidden(self):
        profile_id = yield create_profile(1, 'Delegates', 'receiver', ['receiver'], {'can_manage_settings': True})

        user_id, _, desc = yield get_user_desc('receiver1')
        desc['profile_id'] = profile_id

        handler = self.request(desc, role='admin', permissions=dict(self.scoped), handler_cls=user.UserInstance)
        yield self.assertFailure(handler.put(user_id), errors.ForbiddenOperation)

    @inlineCallbacks
    def test_switching_the_role_outside_the_profile_roles_is_forbidden(self):
        profile_id = yield create_profile(1, 'Recipients', 'receiver', ['receiver'], {})

        user_id, _, desc = yield get_user_desc('receiver1')
        desc['profile_id'] = profile_id
        desc['role'] = 'custodian'

        handler = self.request(desc, role='admin', handler_cls=user.UserInstance)
        yield self.assertFailure(handler.put(user_id), errors.InputValidationError)

    @inlineCallbacks
    def test_promotion_by_a_scoped_admin_confers_its_scope(self):
        user_id, _, desc = yield get_user_desc('receiver1')
        desc['role'] = 'admin'
        desc['profile'] = {}

        handler = self.request(desc, role='admin', permissions=dict(self.scoped), handler_cls=user.UserInstance)
        yield handler.put(user_id)

        permissions = yield get_profile_permissions(user_id)
        self.assertEqual(permissions & set(models.admin_permissions), {'can_manage_users'})

    @inlineCallbacks
    def test_granting_an_unheld_administrative_permission_is_forbidden(self):
        user_id, _, desc = yield get_user_desc('receiver1')
        desc['profile']['permissions']['can_manage_settings'] = True

        handler = self.request(desc, role='admin', permissions=dict(self.scoped), handler_cls=user.UserInstance)
        yield self.assertFailure(handler.put(user_id), errors.ForbiddenOperation)

    @inlineCallbacks
    def test_administering_an_account_above_the_operator_scope_is_forbidden(self):
        data = self.get_dummy_create_request('admin')
        target = yield user.create_user(1, None, data, 'en')

        target['profile'] = {}
        handler = self.request(target, role='admin', permissions=dict(self.scoped), handler_cls=user.UserInstance)
        yield self.assertFailure(handler.put(target['id']), errors.ForbiddenOperation)

        handler = self.request(None, role='admin', permissions=dict(self.scoped), handler_cls=user.UserInstance)
        yield self.assertFailure(handler.delete(target['id']), errors.ForbiddenOperation)

        # The account survived the refused deletion
        permissions = yield get_profile_permissions(target['id'])
        self.assertIn('can_manage_settings', permissions)


class TestProtectedAdministration(helpers.TestHandlerWithPopulatedDB):
    """
    A protected user, and the profile it is bound to, are administered only by
    protected users.
    """
    _handler = user.UserInstance

    @inlineCallbacks
    def test_updating_a_protected_user_requires_a_protected_operator(self):
        user_id, _, desc = yield get_user_desc('receiver1')

        yield tw(db_set_config_variable, 1, 'protected_users', [user_id])

        handler = self.request(desc, role='admin')
        yield self.assertFailure(handler.put(user_id), errors.ForbiddenOperation)

    @inlineCallbacks
    def test_a_protected_operator_administers_a_protected_user(self):
        user_id, _, desc = yield get_user_desc('receiver1')

        yield tw(db_set_config_variable, 1, 'protected_users', [self.dummyAdmin['id'], user_id])

        handler = self.request(desc, role='admin')
        yield handler.put(user_id)

    @inlineCallbacks
    def test_altering_the_profile_of_a_protected_user_requires_a_protected_operator(self):
        profile_id = yield create_profile(1, 'Sheltered', 'receiver', ['receiver'], {})

        user_id, _, desc = yield get_user_desc('receiver1')
        desc['profile_id'] = profile_id

        handler = self.request(desc, role='admin')
        yield handler.put(user_id)

        yield tw(db_set_config_variable, 1, 'protected_users', [user_id])

        request = {'name': 'Sheltered', 'role': 'receiver', 'roles': ['receiver'],
                   'contexts': [],
                   'permissions': {p: False for p in models.user_permissions}}
        handler = self.request(request, role='admin', handler_cls=user_profile.UserProfileInstance)
        yield self.assertFailure(handler.put(profile_id), errors.ForbiddenOperation)