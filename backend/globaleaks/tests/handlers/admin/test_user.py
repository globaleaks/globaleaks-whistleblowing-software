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

        desc['profile']['permissions']['can_forward_reports'] = True

        handler = self.request(desc, role='admin')
        yield handler.put(user_id)

        permissions = yield get_profile_permissions(profile_id)
        self.assertIn('can_forward_reports', permissions)

    @inlineCallbacks
    def test_put_does_not_update_the_permissions_of_a_shared_profile(self):
        user_id, _, desc = yield get_user_desc('receiver2')

        profile_id = yield create_shared_profile()

        desc['profile_id'] = profile_id
        desc['profile']['permissions']['can_forward_reports'] = True

        handler = self.request(desc, role='admin')
        yield handler.put(user_id)

        permissions = yield get_profile_permissions(profile_id)
        self.assertNotIn('can_forward_reports', permissions)

    @inlineCallbacks
    def test_put_discards_unknown_permissions(self):
        user_id, profile_id, desc = yield get_user_desc('receiver1')

        desc['profile']['permissions']['can_pwn_everything'] = True

        handler = self.request(desc, role='admin')
        yield handler.put(user_id)

        permissions = yield get_profile_permissions(profile_id)
        self.assertNotIn('can_pwn_everything', permissions)

    @inlineCallbacks
    def test_put_of_a_forwarding_recipient_of_a_tenant_drops_the_conflicting_permissions(self):
        user_id, profile_id, desc = yield get_user_desc('receiver1')

        yield tw(lambda session: session.query(models.UserProfile)
                                        .filter(models.UserProfile.id == profile_id)
                                        .update({'tid': 2}))

        desc['profile']['permissions']['can_forward_reports'] = True
        desc['profile']['permissions']['can_mask_information'] = True
        desc['profile']['permissions']['can_delete_submission'] = True

        handler = self.request(desc, role='admin')
        yield handler.put(user_id)

        permissions = yield get_profile_permissions(profile_id)
        self.assertIn('can_forward_reports', permissions)
        self.assertNotIn('can_mask_information', permissions)
        self.assertNotIn('can_delete_submission', permissions)

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
