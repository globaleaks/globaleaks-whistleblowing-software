import json
from twisted.internet.defer import inlineCallbacks

from globaleaks import models
from globaleaks.handlers.base import BaseHandler
from globaleaks.handlers.user import serialize_user_profile, \
                                     user_permissions
from globaleaks.handlers.user.reset_password import db_generate_password_reset_token
from globaleaks.models import config, UserProfile, fill_localized_keys
from globaleaks.orm import db_get, db_log, transact, tw
from globaleaks.rest import errors, requests
from globaleaks.sessions import Sessions
from globaleaks.utils.utility import uuid4


def sync_roles(session, profile, request, sync_users=True):
    roles = request['roles']

    if not request['roles'] or request['role'] not in request['roles']:
        raise errors.InputValidationError("Invalid roles")

    current_roles = {r.role for r in profile.roles}
    roles_set = set(roles)

    # Remove old roles
    for role in list(profile.roles):
        if role.role not in roles_set:
            session.delete(role)

    # Add new roles
    for role_name in roles_set - current_roles:
        profile.roles.append(models.UserProfileRole({'profile_id': profile.id, 'role': role_name}))

    if sync_users:
        for user in session.query(models.User).filter(models.User.profile_id == profile.id, models.User.role.notin_(roles)):
            user.role = request['role']


def db_local_context_of(session, tid, template_id):
    """
    Resolve on a tenant the channel a profile association refers to

    The associations of a user profile name the channels of the tenant the
    profile lives on: on the tenants inheriting the profile they resolve to
    the derived channels.

    :param session: An ORM session
    :param tid: The tenant ID of the user
    :param template_id: The channel named by the association
    :return: The local channel or None
    """
    return session.query(models.Context) \
                  .filter(models.Context.tid == tid,
                          (models.Context.id == template_id) |
                          (models.Context.template_id == template_id)) \
                  .one_or_none()


def db_attach_user_to_profile_contexts(session, user, profile):
    """
    Make a receiver a recipient of the channels associated to its profile

    :param session: An ORM session
    :param user: The user to attach
    :param profile: The profile of the user
    """
    if user.role != 'receiver':
        return

    for template_id in profile.contexts_list:
        context = db_local_context_of(session, user.tid, template_id)
        if context is None:
            continue

        if session.query(models.ReceiverContext) \
                  .filter(models.ReceiverContext.context_id == context.id,
                          models.ReceiverContext.receiver_id == user.id).count():
            continue

        session.add(models.ReceiverContext({'context_id': context.id,
                                            'receiver_id': user.id,
                                            'order': 0}))


def db_detach_user_from_profile_contexts(session, user, profile):
    """
    Remove a receiver from the channels associated to a profile it leaves

    :param session: An ORM session
    :param user: The user to detach
    :param profile: The profile the user leaves
    """
    for template_id in profile.contexts_list:
        context = db_local_context_of(session, user.tid, template_id)
        if context is not None:
            session.query(models.ReceiverContext) \
                   .filter(models.ReceiverContext.context_id == context.id,
                           models.ReceiverContext.receiver_id == user.id).delete()


def sync_contexts(session, profile, request, sync_users=True):
    """
    Align the channels associated to a profile and the receivers they carry

    The channels added to a profile gain as receivers every user holding the
    profile, on every tenant; the channels removed lose them. The reports
    already received stay with their recipients: attaching and detaching a
    receiver decides the reports to come, never the ones at rest.
    """
    if 'contexts' not in request:
        return

    requested = set(request['contexts'])

    # The associations name channels of the tenant the profile lives on
    valid_ids = {c.id for c in session.query(models.Context)
                                      .filter(models.Context.tid == profile.tid)}
    if requested - valid_ids:
        raise errors.InputValidationError("Invalid context reference")

    current = {c.context_id for c in profile.contexts}

    for association in list(profile.contexts):
        if association.context_id not in requested:
            session.delete(association)

    for context_id in requested - current:
        profile.contexts.append(models.UserProfileContext({'profile_id': profile.id,
                                                           'context_id': context_id}))

    if not sync_users:
        return

    users = session.query(models.User) \
                   .filter(models.User.profile_id == profile.id,
                           models.User.role == 'receiver').all()

    for user in users:
        for template_id in requested - current:
            context = db_local_context_of(session, user.tid, template_id)
            if context is not None and not session.query(models.ReceiverContext) \
                    .filter(models.ReceiverContext.context_id == context.id,
                            models.ReceiverContext.receiver_id == user.id).count():
                session.add(models.ReceiverContext({'context_id': context.id,
                                                    'receiver_id': user.id,
                                                    'order': 0}))

        for template_id in current - requested:
            context = db_local_context_of(session, user.tid, template_id)
            if context is not None:
                session.query(models.ReceiverContext) \
                       .filter(models.ReceiverContext.context_id == context.id,
                               models.ReceiverContext.receiver_id == user.id).delete()


def sync_permissions(session, profile, request):
    permissions = request['permissions']

    if profile.tid != 1 and permissions.get('can_forward_reports'):
        permissions['can_mask_information'] = False
        permissions['can_redact_information'] = False
        permissions['can_delete_submission'] = False

    permissions = [perm for perm, value in permissions.items() if value]

    current_permissions = {p.permission for p in profile.permissions}
    permissions_set = set(permissions)

    # Remove old roles
    for permission in list(profile.permissions):
        if permission.permission not in permissions_set:
            session.delete(permission)

    # Add new roles
    for permission_name in permissions_set - current_permissions:
        profile.permissions.append(models.UserProfilePermission({'profile_id': profile.id, 'permission': permission_name}))


def db_resolve_default_user_profile(session, tid):
    """
    Resolve the profile assigned by default to the users created on a tenant

    The configuration holds either a role keyword, in which case the user is
    created with the given role and a profile of its own, or the reference of a
    user profile, in which case the user inherits its role and its permissions.

    :param session: An ORM session
    :param tid: A tenant ID
    :return: The role and the profile ID to be assigned to the created user;
             the role is empty when the tenant creates no user by default
    """
    # Read the tenant specific value (inherited from the tenant profile)
    # falling back on the root tenant configuration set via Settings/Advanced
    default_user_profile = config.ConfigFactory(session, tid).get_val('default_user_profile') or \
                           config.ConfigFactory(session, 1).get_val('default_user_profile')

    if default_user_profile in ('admin', 'analyst', 'custodian', 'recipient'):
        # Role keyword: create the user with the given role and a
        # standard per-user profile
        return 'receiver' if default_user_profile == 'recipient' else default_user_profile, ''

    if not default_user_profile or default_user_profile == 'none':
        return '', ''

    # Profile reference: create the user with the role and profile
    # of the referenced user profile
    profile = session.query(models.UserProfile).filter(models.UserProfile.id == default_user_profile).one_or_none()
    if profile is None:
        raise errors.InputValidationError

    return profile.role, profile.id


def db_create_user_profile(session, tid, request, sync_users=True):
    """
    Transaction for creating a new user

    :param session: An ORM session
    :param tid: A tenant ID
    :param request: The request data
    :return: The serialized descriptor of the created object
    """
    if 'id' not in request or not request['id']:
        request['id'] = uuid4()

    request['tid'] = tid
    profile = models.UserProfile(request)
    profile.role = request['role']

    sync_roles(session, profile, request, sync_users=sync_users)
    sync_permissions(session, profile, request)
    sync_contexts(session, profile, request, sync_users=sync_users)

    session.add(profile)

    return serialize_user_profile(session, profile)


@transact
def delete_user_profile(session, tid, profile_id):
    profile = session.query(models.UserProfile).filter(models.UserProfile.tid == tid, models.UserProfile.id == profile_id).first()

    if not profile:
        raise ValueError

    if session.query(models.User).filter(models.User.profile_id == profile_id).first():
        raise errors.ForbiddenOperation

    session.delete(profile)


@transact
def create_user_profile(session, tid, user_session, request, language):
    """
    Transaction for creating a new user

    :param session: An ORM session
    :param tid: A tenant ID
    :param request: The request data
    :return: The serialized descriptor of the created object
    """
    return db_create_user_profile(session, tid, request)


def db_update_user_profile(session, tid, profile_id, request):
    """
    Update the user profile in the database.

    :param session: An ORM session
    :param tid: A tenant ID
    :param profile_id: The ID of the profile to update
    :param request: The new data for updating the user profile
    :return: The updated user object
    """
    profile = db_get(session,
                     models.UserProfile,
                     (models.UserProfile.tid == tid,
                      models.UserProfile.id == profile_id))

    profile.update(request)

    sync_roles(session, profile, request)
    sync_permissions(session, profile, request)
    sync_contexts(session, profile, request)

    return serialize_user_profile(session, profile)


@transact
def update_user_profile(session, tid, user_session, profile_id, request):
    """
    Update the user profile in the database.

    :param session: An ORM session
    :param tid: A tenant ID
    :param profile_id: The ID of the user to update
    :param request: The new data for updating the user profile
    :return: The updated user object
    """
    affected_users = session.query(models.User) \
                            .filter(models.User.tid == tid,
                                    models.User.profile_id == profile_id) \
                            .all()
    profile = db_update_user_profile(session, tid, profile_id, request)

    return profile, [user.id for user in affected_users]


def db_get_user_profile(session, tid, id):
    """
    Return specific profile or user.
    """
    profile = session.query(models.UserProfile).filter(models.UserProfile.id == id, models.UserProfile.tid == tid).first()
    if profile:
        return serialize_user_profile(session, profile)

    raise errors.ResourceNotFound


@transact
def get_user_profiles(session, tid):
    """
    Retrieve all user profiles from the database.

    :param session: ORM session
    :return: List of user profiles in serialized form
    """
    ret = []

    pid = config.db_get_pid(session, tid)

    if tid != pid:
        profile_user_ids = [user_id[0] for user_id in session.query(models.User.id).filter(models.User.tid == pid).all()]
        profiles = session.query(UserProfile).filter(UserProfile.tid == pid).all()

        for profile in profiles:
            ret.append(serialize_user_profile(session, profile))
            ret[-1]['custom'] = profile.id in profile_user_ids

    user_ids = [user_id[0] for user_id in session.query(models.User.id).filter(models.User.tid == tid).all()]
    profiles = session.query(models.UserProfile).filter(models.UserProfile.tid == tid).all()
    for profile in profiles:
        ret.append(serialize_user_profile(session, profile))
        ret[-1]['custom'] = profile.id in user_ids

    return ret


class UserProfilesCollection(BaseHandler):
    check_roles = 'admin'
    invalidate_cache = True

    def get(self):
        """
        Return all the users.
        """
        return get_user_profiles(self.request.tid)

    @inlineCallbacks
    def post(self):
        """
        Create a new user profile.
        """
        request = json.loads(self.request.content.read())

        # The profiles exported before the channels were part of them carry no
        # association: an import defaults it to none
        request.setdefault('contexts', [])

        request = yield self.validate_request(json.dumps(request), requests.AdminUserProfileDesc)
        profile = yield create_user_profile(self.request.tid, self.session, request, self.request.language)
        return profile


class UserProfileInstance(BaseHandler):
    check_roles = 'admin'
    invalidate_cache = True

    def get(self, profile_id):
        """
        Retrieve the specified user profile.
        """
        return tw(db_get_user_profile, self.request.tid, profile_id)

    @inlineCallbacks
    def put(self, profile_id):
        """
        Update the specified user profile.
        """
        request = json.loads(self.request.content.read())
        profile_request = yield self.validate_request(json.dumps(request), requests.AdminUserProfileDesc)
        profile, affected_user_ids = yield update_user_profile(
            self.request.tid,
            self.session,
            profile_id,
            profile_request
        )
        for user_id in affected_user_ids:
            Sessions.revoke_user(self.request.tid, user_id)

        return profile

    def delete(self, profile_id):
        """
        Delete the specified user profile.
        """
        return delete_user_profile(self.request.tid, profile_id)
