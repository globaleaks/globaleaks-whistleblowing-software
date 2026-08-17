from twisted.internet.defer import inlineCallbacks

from globaleaks import models
from globaleaks.handlers.admin import context, tenant, user, user_profile
from globaleaks.models.config import ConfigFactory
from globaleaks.orm import transact
from globaleaks.rest import errors
from globaleaks.state import State, TenantState
from globaleaks.tests import helpers


@transact
def update_profile_of(session, tid, profile_id, request):
    return user_profile.db_update_user_profile(session, tid, profile_id, request)


class TestUserProfilesCollection(helpers.TestCollectionHandler):
    _handler = user_profile.UserProfilesCollection
    _test_desc = {
        'model': models.UserProfile,
        'create': user_profile.create_user_profile,
        'data': {}
    }

    def get_dummy_request(self):
        data = helpers.TestCollectionHandler.get_dummy_request(self)
        data['roles'] = ['admin']
        data['permissions'] = user.user_permissions
        return data


class TestUserProfileInstance(helpers.TestInstanceHandler):
    _handler = user_profile.UserProfileInstance
    _test_desc = {
        'model': models.UserProfile,
        'create': user_profile.create_user_profile,
        'data': {}
    }

    def get_dummy_request(self):
        data = helpers.TestInstanceHandler.get_dummy_request(self)
        data['role'] = 'admin'
        data['roles'] = ['admin']
        data['permissions'] = user.user_permissions
        return data


class TestUserProfileGating(helpers.TestHandlerWithPopulatedDB):
    """
    The mutation of the profiles requires the dedicated permission, while the
    operators entitled to manage users keep reading them to bind them.
    """
    _handler = user_profile.UserProfilesCollection

    users_only = {p: p == 'can_manage_users' for p in models.admin_permissions}
    profiles_only = {p: p == 'can_manage_user_profiles' for p in models.admin_permissions}

    def get_dummy_profile_request(self):
        request = models.UserProfile().dict('en')
        request['name'] = 'Gated'
        request['role'] = 'receiver'
        request['roles'] = ['receiver']
        request['contexts'] = []
        request['permissions'] = {p: False for p in models.user_permissions}
        return request

    @inlineCallbacks
    def test_profiles_stay_readable_to_the_user_managers(self):
        handler = self.request(role='admin', permissions=dict(self.users_only))
        yield handler.get()

    def test_creation_requires_the_profile_permission(self):
        data = self.get_dummy_profile_request()

        handler = self.request(data, role='admin', permissions=dict(self.users_only))
        self.assertRaises(errors.ForbiddenOperation, handler.post)

    @inlineCallbacks
    def test_creation_allowed_by_the_profile_permission(self):
        data = self.get_dummy_profile_request()

        handler = self.request(data, role='admin', permissions=dict(self.profiles_only))
        yield handler.post()

    @inlineCallbacks
    def test_altering_a_profile_above_the_operator_scope_is_forbidden(self):
        data = self.get_dummy_profile_request()
        data['role'] = 'admin'
        data['roles'] = ['admin']
        data['permissions']['can_manage_settings'] = True
        profile = yield user_profile.create_user_profile(1, None, data, 'en')

        # The request strips the permission: conferring nothing, it would pass
        # the grant gate; the current privilege of the profile blocks it
        data['permissions']['can_manage_settings'] = False

        operator = dict(self.profiles_only)
        handler = self.request(data, role='admin', permissions=operator,
                               handler_cls=user_profile.UserProfileInstance)
        yield self.assertFailure(handler.put(profile['id']), errors.ForbiddenOperation)

    @inlineCallbacks
    def test_update_and_deletion_require_the_profile_permission(self):
        data = self.get_dummy_profile_request()
        profile = yield user_profile.create_user_profile(1, None, data, 'en')

        handler = self.request(data, role='admin', permissions=dict(self.users_only),
                               handler_cls=user_profile.UserProfileInstance)
        self.assertRaises(errors.ForbiddenOperation, handler.put, profile['id'])

        handler = self.request(None, role='admin', permissions=dict(self.users_only),
                               handler_cls=user_profile.UserProfileInstance)
        self.assertRaises(errors.ForbiddenOperation, handler.delete, profile['id'])


@transact
def get_profile_uuid(session, tid):
    return ConfigFactory(session, tid).get_val('uuid')


@transact
def get_derived_contexts(session, tid):
    return {c.template_id: {'id': c.id, 'name': c.name, 'tip_timetolive': c.tip_timetolive}
            for c in session.query(models.Context).filter(models.Context.tid == tid,
                                                          models.Context.template_id != '')}


@transact
def get_receiver_context_ids(session, user_id):
    return [r.context_id for r in session.query(models.ReceiverContext)
                                         .filter(models.ReceiverContext.receiver_id == user_id)]


@transact
def file_report_on(session, tid, context_id):
    itip = models.InternalTip()
    itip.tid = tid
    itip.context_id = context_id
    itip.progressive = 1
    itip.receipt_hash = 'x' * 64
    session.add(itip)


class TestTenantProfileChannels(helpers.TestGLWithPopulatedDB):
    """
    The channels of a tenant profile are templates: the tenants created with
    the profile derive their channels from them and follow their updates, and
    the receivers reach the channels through the user profiles they hold.
    """
    @inlineCallbacks
    def setUp(self):
        yield helpers.TestGLWithPopulatedDB.setUp(self)

        # A tenant profile carrying one channel and one recipient profile
        # associated to it
        profile = yield tenant.create_and_initialize(
            {'name': 'Profile', 'active': True, 'subdomain': '', 'profile': 'default'},
            is_profile=True)
        self.profile_tid = profile['id']

        contexts = yield context.get_contexts(self.profile_tid, 'en')
        self.template_id = contexts[0]['id']

        profile_desc = models.UserProfile().dict('en')
        profile_desc['name'] = 'Operators'
        profile_desc['role'] = 'receiver'
        profile_desc['roles'] = ['receiver']
        profile_desc['contexts'] = [self.template_id]
        profile_desc['permissions'] = {p: False for p in models.user_permissions}
        self.user_profile = yield user_profile.create_user_profile(
            self.profile_tid, None, profile_desc, 'en')

        # A tenant created with the profile
        profile_uuid = yield get_profile_uuid(self.profile_tid)
        child = yield tenant.create_and_initialize(
            {'name': 'Child', 'active': True, 'subdomain': '', 'profile': profile_uuid})
        self.child_tid = child['id']

        # the tenants created by the test gain their in-memory state, as the
        # cache refresh of the production path would provide; the state is
        # global and the entries are dropped with the test
        for tid in (self.profile_tid, self.child_tid):
            State.tenants[tid] = TenantState()
            self.addCleanup(State.tenants.pop, tid, None)

    @inlineCallbacks
    def create_child_receiver(self):
        user_desc = models.User().dict('en')
        user_desc['username'] = 'operator'
        user_desc['name'] = 'Operator'
        user_desc['mail_address'] = 'operator@example.org'
        user_desc['role'] = 'receiver'
        user_desc['profile_id'] = self.user_profile['id']
        user_desc['roles'] = ['receiver']
        user_desc['profile'] = {}
        user_desc['pgp_key_remove'] = False
        created = yield user.create_user(self.child_tid, None, user_desc, 'en')
        return created

    @inlineCallbacks
    def test_the_tenant_derives_the_channels_of_its_profile(self):
        derived = yield get_derived_contexts(self.child_tid)

        self.assertIn(self.template_id, derived)

    @inlineCallbacks
    def test_the_derived_channel_follows_the_updates_of_its_template(self):
        request = models.Context().dict('en')
        request['name'] = 'Renamed'
        request['tip_timetolive'] = 42
        request['receivers'] = []
        yield context.update_context(self.profile_tid, self.template_id, request, 'en')

        derived = yield get_derived_contexts(self.child_tid)
        self.assertEqual(derived[self.template_id]['tip_timetolive'], 42)
        self.assertEqual(derived[self.template_id]['name'].get('en'), 'Renamed')

    @inlineCallbacks
    def test_a_channel_added_to_the_profile_reaches_the_tenant(self):
        request = models.Context().dict('en')
        request['name'] = 'Added'
        request['receivers'] = []
        added = yield context.create_context(self.profile_tid, None, request, 'en')

        derived = yield get_derived_contexts(self.child_tid)
        self.assertIn(added['id'], derived)

    @inlineCallbacks
    def test_the_receiver_reaches_the_channels_of_its_profile(self):
        created = yield self.create_child_receiver()

        derived = yield get_derived_contexts(self.child_tid)
        attached = yield get_receiver_context_ids(created['id'])
        self.assertEqual(attached, [derived[self.template_id]['id']])

    @inlineCallbacks
    def test_the_receivers_follow_the_channels_of_their_profile(self):
        created = yield self.create_child_receiver()

        request = models.Context().dict('en')
        request['name'] = 'Added'
        request['receivers'] = []
        added = yield context.create_context(self.profile_tid, None, request, 'en')

        # The channel associated to the profile attaches its holders, the
        # channel dissociated detaches them
        profile_desc = dict(self.user_profile)
        profile_desc['contexts'] = [self.template_id, added['id']]
        yield update_profile_of(self.profile_tid, self.user_profile['id'], profile_desc)

        derived = yield get_derived_contexts(self.child_tid)
        attached = yield get_receiver_context_ids(created['id'])
        self.assertEqual(sorted(attached),
                         sorted([derived[self.template_id]['id'], derived[added['id']]['id']]))

        profile_desc['contexts'] = [added['id']]
        yield update_profile_of(self.profile_tid, self.user_profile['id'], profile_desc)

        attached = yield get_receiver_context_ids(created['id'])
        self.assertEqual(attached, [derived[added['id']]['id']])

    @inlineCallbacks
    def test_a_derived_channel_is_neither_updated_nor_deleted_directly(self):
        derived = yield get_derived_contexts(self.child_tid)
        derived_id = derived[self.template_id]['id']

        request = models.Context().dict('en')
        request['name'] = 'Local'
        request['tip_timetolive'] = 7
        request['receivers'] = []
        yield context.update_context(self.child_tid, derived_id, request, 'en')

        # the configuration is inherited from the template and stays
        derived = yield get_derived_contexts(self.child_tid)
        self.assertNotEqual(derived[self.template_id]['tip_timetolive'], 7)

        yield self.assertFailure(context.delete_context(self.child_tid, derived_id),
                                 errors.ForbiddenOperation)

    @inlineCallbacks
    def test_a_template_with_reports_on_a_derived_channel_is_not_deleted(self):
        derived = yield get_derived_contexts(self.child_tid)
        yield file_report_on(self.child_tid, derived[self.template_id]['id'])

        yield self.assertFailure(context.delete_context(self.profile_tid, self.template_id),
                                 errors.ForbiddenOperation)

    @inlineCallbacks
    def test_a_template_without_reports_is_deleted_with_its_derived_channels(self):
        yield context.delete_context(self.profile_tid, self.template_id)

        derived = yield get_derived_contexts(self.child_tid)
        self.assertNotIn(self.template_id, derived)
