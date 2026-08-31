from twisted.internet.defer import inlineCallbacks, maybeDeferred

from globaleaks import models
from globaleaks.handlers.admin import user_profile
from globaleaks.orm import transact
from globaleaks.rest import errors
from globaleaks.tests import helpers


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
