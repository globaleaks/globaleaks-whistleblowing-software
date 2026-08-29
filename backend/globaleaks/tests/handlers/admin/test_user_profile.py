from twisted.internet.defer import inlineCallbacks, maybeDeferred

from globaleaks import models
from globaleaks.models import config as models_config
from globaleaks.handlers.admin import user_profile
from globaleaks.orm import transact
from globaleaks.rest import errors
from globaleaks.tests import helpers


@transact
def protect_a_user(session, tid):
    """
    Have the site protect one of its accounts, and return it
    """
    user = session.query(models.User).filter(models.User.tid == tid).first()

    models_config.db_set_config_variable(session, tid, 'protected_users', [user.id])

    return user.id


@transact
def create_profile(session, tid, request):
    """
    Enter a profile on a site and return its identifier
    """
    return user_profile.db_create_user_profile(session, tid, request)['id']


@transact
def profile_of_a_user(session, tid):
    """
    Return the profile of an account of the site, and the account holding it
    """
    user = session.query(models.User) \
                  .filter(models.User.tid == tid,
                          models.User.profile_id.isnot(None)).first()

    return user.profile_id


def profile_desc(**kwargs):
    request = {
        'name': 'Profile',
        'role': 'receiver',
        'roles': ['receiver'],
        'permissions': {'can_mask_information': True},
        'contexts': []
    }
    request.update(kwargs)

    return request


class TestUserProfilesCollection(helpers.TestHandlerWithPopulatedDB):
    """
    The profiles of the accounts of a site are configured as any other object
    """
    _handler = user_profile.UserProfilesCollection

    @inlineCallbacks
    def test_get(self):
        handler = self.request(role='admin')
        response = yield handler.get()

        self.assertTrue(len(response) > 0)
        for entry in response:
            self.assertIn('id', entry)
            self.assertIn('permissions', entry)

    @inlineCallbacks
    def test_post(self):
        handler = self.request(profile_desc(), role='admin')
        response = yield handler.post()

        self.assertEqual(response['name'], 'Profile')
        self.assertEqual(response['role'], 'receiver')
        self.assertTrue(response['permissions']['can_mask_information'])

    @inlineCallbacks
    def test_post_discards_a_permission_the_platform_does_not_know(self):
        # A permission is granted by being named: a name the platform does not
        # know is dropped instead of being stored, so that a typo in an import
        # cannot grant anything
        handler = self.request(profile_desc(permissions={'can_do_anything': True,
                                                         'can_mask_information': True}),
                               role='admin')
        response = yield handler.post()

        self.assertNotIn('can_do_anything', response['permissions'])
        self.assertTrue(response['permissions']['can_mask_information'])


class TestUserProfileInstance(helpers.TestHandlerWithPopulatedDB):
    """
    A profile is read, altered and dropped by whoever manages the profiles of
    """
    _handler = user_profile.UserProfileInstance

    @inlineCallbacks
    def setUp(self):
        yield helpers.TestHandlerWithPopulatedDB.setUp(self)

        collection = self.request(profile_desc(),
                                  role='admin',
                                  handler_cls=user_profile.UserProfilesCollection)

        self.profile = yield collection.post()

    @inlineCallbacks
    def test_get(self):
        handler = self.request(role='admin')
        response = yield handler.get(self.profile['id'])

        self.assertEqual(response['id'], self.profile['id'])
        self.assertEqual(response['name'], 'Profile')

    @inlineCallbacks
    def test_put(self):
        handler = self.request(profile_desc(name='Renamed',
                                            permissions={'can_redact_information': True}),
                               role='admin')

        response = yield handler.put(self.profile['id'])

        self.assertEqual(response['name'], 'Renamed')
        self.assertTrue(response['permissions']['can_redact_information'])
        # What is not named any more is taken away: the permissions of a
        # profile are the ones it declares, not the ones it accumulated. The
        # answer says so as well, and not only the profile read afterwards: the
        # interface redraws on the answer, and would otherwise keep showing a
        # permission that has just been revoked.
        self.assertFalse(response['permissions']['can_mask_information'])

        reread = self.request(role='admin')
        stored = yield reread.get(self.profile['id'])
        self.assertTrue(stored['permissions']['can_redact_information'])
        self.assertFalse(stored['permissions']['can_mask_information'])

    @inlineCallbacks
    def test_delete(self):
        handler = self.request(role='admin')

        yield handler.delete(self.profile['id'])

        collection = self.request(role='admin',
                                  handler_cls=user_profile.UserProfilesCollection)
        response = yield collection.get()

        self.assertNotIn(self.profile['id'], [entry['id'] for entry in response])

    @inlineCallbacks
    def test_delete_of_a_profile_an_account_is_bound_to_is_refused(self):
        # The profile is what says the role and the permissions of its
        # accounts: dropping it while an account holds it would leave that
        # account saying nothing about itself
        bound = yield profile_of_a_user(1)

        handler = self.request(role='admin')

        yield self.assertFailure(maybeDeferred(handler.delete, bound),
                                 errors.ForbiddenOperation)

    @inlineCallbacks
    def test_whoever_binds_the_profiles_reads_them_without_altering_them(self):
        # Binding a profile to an account is managing the accounts, and asks to
        # see the profiles on offer; changing what a profile grants is another
        # matter, and asks for the permission over the profiles themselves.
        binding = {'can_manage_users': True, 'can_manage_user_profiles': False}

        reader = self.request(role='admin', permissions=dict(binding))
        yield reader.get(self.profile['id'])

        writer = self.request(profile_desc(name='Renamed'),
                              role='admin',
                              permissions=dict(binding))

        yield self.assertFailure(maybeDeferred(writer.put, self.profile['id']),
                                 errors.ForbiddenOperation)


class FakeOperator:
    """
    The session of an operator, reduced to what the guards read of it
    """
    def __init__(self, role='admin', permissions=None, user_id='operator'):
        self.role = role
        self.user_id = user_id
        self.permissions = permissions or {}

    def has_permission(self, permission):
        return self.permissions.get(permission, False)


class TestGrantable(helpers.TestGL):
    """
    An operator confers, through an account or a profile, no more than it holds
    """

    def test_what_an_operator_may_confer(self):
        manages_users = FakeOperator(permissions={'can_manage_users': True})

        cases = [
            ("a system operation confers whatever it needs",
             None, {'can_manage_sites': True}, ['admin'], True),
            ("what is held is conferred",
             manages_users, {'can_manage_users': True}, None, True),
            ("what is not held is not conferred",
             manages_users, {'can_manage_sites': True}, None, False),
            ("what is withheld is not a conferral",
             manages_users, {'can_manage_sites': False}, None, True),
            ("a permission that is not administrative is not gated here",
             manages_users, {'can_mask_information': True}, None, True),
            ("an administrator confers the administrative role",
             manages_users, None, ['admin'], True),
            ("whoever is not an administrator does not confer it",
             FakeOperator(role='receiver'), None, ['admin'], False),
            ("another role is conferred by whoever is not an administrator",
             FakeOperator(role='receiver'), None, ['receiver'], True),
        ]

        for reason, operator, permissions, roles, allowed in cases:
            with self.subTest(reason=reason):
                if allowed:
                    user_profile.db_enforce_grantable(operator, permissions, roles)
                else:
                    self.assertRaises(errors.ForbiddenOperation,
                                      user_profile.db_enforce_grantable,
                                      operator, permissions, roles)


class TestAdministrable(helpers.TestGLWithPopulatedDB):
    """
    An operator administers no account that stands above it
    """

    @transact
    def enforce(self, session, operator, permissions, user_ids):
        user_profile.db_enforce_administrable(session, 1, operator, permissions, user_ids)

    @inlineCallbacks
    def test_a_system_operation_administers_whatever_it_reaches(self):
        yield self.enforce(None, ['can_manage_sites'], ['whoever'])

    @inlineCallbacks
    def test_an_account_holding_more_is_not_administered(self):
        manages_users = FakeOperator(permissions={'can_manage_users': True})

        yield self.enforce(manages_users, ['can_manage_users'], [])

        yield self.assertFailure(self.enforce(manages_users, ['can_manage_sites'], []),
                                 errors.ForbiddenOperation)

    @inlineCallbacks
    def test_a_protected_account_is_administered_by_a_protected_one_alone(self):
        every_permission = {p: True for p in models.admin_permissions}
        protected = yield protect_a_user(1)

        outsider = FakeOperator(permissions=every_permission, user_id='outsider')
        yield self.assertFailure(self.enforce(outsider, [], [protected]),
                                 errors.ForbiddenOperation)

        insider = FakeOperator(permissions=every_permission, user_id=protected)
        yield self.enforce(insider, [], [protected])


class TestAssignableProfile(helpers.TestGLWithPopulatedDB):
    """
    A profile is bound to an account of the site it lives on, for a role it says
    """

    @transact
    def assign(self, session, tid, operator, profile_id, role):
        return user_profile.db_enforce_assignable_profile(session, tid, operator, profile_id, role).id

    @inlineCallbacks
    def test_a_profile_of_the_site_is_bound_for_a_role_it_carries(self):
        profile = yield create_profile(1, profile_desc(name='Bindable'))

        bound = yield self.assign(1, FakeOperator(), profile, 'receiver')
        self.assertEqual(bound, profile)

    @inlineCallbacks
    def test_a_role_the_profile_does_not_carry_is_refused(self):
        profile = yield create_profile(1, profile_desc(name='Receiving'))

        yield self.assertFailure(self.assign(1, FakeOperator(), profile, 'custodian'),
                                 errors.InputValidationError)

    @inlineCallbacks
    def test_a_profile_that_does_not_exist_is_refused(self):
        yield self.assertFailure(self.assign(1, FakeOperator(), 'x' * 36, 'receiver'),
                                 errors.InputValidationError)

    @inlineCallbacks
    def test_a_profile_of_another_site_is_not_bound(self):
        # The binding names a profile of the site, or of the profile the site
        # derives from: one that lives on another site is not reachable
        profile = yield create_profile(1, profile_desc(name='Elsewhere'))

        yield self.assertFailure(self.assign(2, FakeOperator(), profile, 'receiver'),
                                 errors.InputValidationError)

    @inlineCallbacks
    def test_a_profile_conferring_more_than_the_operator_holds_is_refused(self):
        profile = yield create_profile(1, profile_desc(name='Administering',
                                                       role='admin',
                                                       roles=['admin'],
                                                       permissions={'can_manage_sites': True}))

        operator = FakeOperator(permissions={'can_manage_users': True})

        yield self.assertFailure(self.assign(1, operator, profile, 'admin'),
                                 errors.ForbiddenOperation)
