import json
from twisted.internet.defer import inlineCallbacks

from globaleaks import models
from globaleaks.handlers.base import BaseHandler
from globaleaks.handlers.support import db_reconcile_support_user_access, \
                                         decrypt_tenant_support_private_key
from globaleaks.handlers.user import serialize_user_profile, \
                                     user_permissions
from globaleaks.models import config, UserProfile
from globaleaks.models.config import DEFAULT_PROFILE_ID
from globaleaks.orm import db_get, transact, tw
from globaleaks.rest import errors, requests
from globaleaks.sessions import Sessions
from globaleaks.utils.utility import uuid4


def session_admin_permissions(user_session):
    """
    The administrative areas the operator manages, the single notion of "what

    :param user_session: The session of the operator
    :return: The set of administrative permissions held by the session
    """
    return {perm for perm in models.admin_permissions if user_session.has_permission(perm)}


def db_enforce_grantable(user_session, permissions=None, roles=None):
    """
    Prevent an operator from conferring, through a user or a profile, an

    :param user_session: The session of the operator, or None for a system op
    :param permissions: The permissions map being conferred, if any
    :param roles: The roles being conferred, if any
    """
    if user_session is None:
        return

    if permissions:
        granted = {perm for perm, value in permissions.items() if value and perm in models.admin_permissions}
        if granted - session_admin_permissions(user_session):
            raise errors.ForbiddenOperation

    # The privilege of a session is its active role, not the role list
    if roles and 'admin' in roles and user_session.role != 'admin':
        raise errors.ForbiddenOperation


def db_enforce_assignable_profile(session, tid, user_session, profile_id, role):
    """
    Validate the binding of a user to a shared profile

    :param session: An ORM session
    :param tid: A tenant ID
    :param user_session: The session of the operator, or None for a system op
    :param profile_id: The ID of the profile being bound
    :param role: The role requested for the user
    :return: The profile object
    """
    tids = {tid}
    pid = config.db_get_pid(session, tid)
    if pid:
        tids.add(pid)

    profile = session.query(models.UserProfile) \
                     .filter(models.UserProfile.id == profile_id,
                             models.UserProfile.tid.in_(tids)).one_or_none()

    if profile is None or role not in profile.roles_list:
        raise errors.InputValidationError("Invalid profile reference")

    db_enforce_grantable(user_session,
                         {perm: True for perm in profile.permissions_list},
                         profile.roles_list)

    return profile


def db_enforce_administrable(session, tid, user_session, permissions, user_ids):
    """
    Prevent an operator from administering an account or a profile above its

    :param session: An ORM session
    :param tid: A tenant ID
    :param user_session: The session of the operator, or None for a system op
    :param permissions: The permissions currently held by the subject
    :param user_ids: The IDs of the users the operation administers
    """
    if user_session is None:
        return

    if {perm for perm in permissions if perm in models.admin_permissions} - session_admin_permissions(user_session):
        raise errors.ForbiddenOperation

    protected_users = config.db_get_protected_users(session, tid)
    if user_session.user_id not in protected_users and set(user_ids) & set(protected_users):
        raise errors.ForbiddenOperation


def sync_roles(session, profile, request, sync_users=True):
    roles = request['roles']

    if not request['roles'] or request['role'] not in request['roles']:
        raise errors.InputValidationError("Invalid roles")

    current_roles = {r.role for r in profile.roles}
    roles_set = set(roles)

    # Removed from the collection as well: a row only marked for deletion would still describe the
    # profile
    for role in list(profile.roles):
        if role.role not in roles_set:
            profile.roles.remove(role)
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

    # Removed from the collection as well as from the database, as the roles
    # and the permissions are: the profile describes itself by what it holds.
    for association in list(profile.contexts):
        if association.context_id not in requested:
            profile.contexts.remove(association)
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

    permissions = [perm for perm, value in permissions.items() if value and perm in user_permissions]

    current_permissions = {p.permission for p in profile.permissions}
    permissions_set = set(permissions)

    # Removed from the collection as well as from the database, for the same
    # reason the roles are: what is revoked must not be described as granted.
    for permission in list(profile.permissions):
        if permission.permission not in permissions_set:
            profile.permissions.remove(permission)
            session.delete(permission)

    # Add new roles
    for permission_name in permissions_set - current_permissions:
        profile.permissions.append(models.UserProfilePermission({'profile_id': profile.id, 'permission': permission_name}))


def db_resolve_default_user_profile(session, tid):
    """
    Resolve the profile assigned by default to the users created on a tenant

    :param session: An ORM session
    :param tid: A tenant ID
    :return: The role and the profile ID to be assigned to the created user;
    """
    # Read the tenant specific value (inherited from the tenant profile)
    # falling back on the root tenant configuration set via Settings/Advanced
    default_user_profile = config.ConfigFactory(session, tid).get_val('default_user_profile') or \
                           config.ConfigFactory(session, 1).get_val('default_user_profile')

    if default_user_profile in ('admin', 'analyst', 'auditor', 'custodian', 'recipient'):
        # Role keyword: create the user with the given role and a
        # standard per-user profile
        return 'receiver' if default_user_profile == 'recipient' else default_user_profile, ''

    if not default_user_profile or default_user_profile == 'none':
        return '', ''

    # Profile reference: create the user with the role and profile
    # of the referenced user profile
    tids = {tid, DEFAULT_PROFILE_ID}
    pid = config.db_get_pid(session, tid)
    if pid:
        tids.add(pid)

    profile = session.query(models.UserProfile) \
                     .filter(models.UserProfile.id == default_user_profile,
                             models.UserProfile.tid.in_(tids)).one_or_none()
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
        raise errors.ResourceNotFound

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
    db_enforce_grantable(user_session, request.get('permissions'), request.get('roles'))
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
    db_enforce_grantable(user_session, request.get('permissions'), request.get('roles'))

    affected_users = session.query(models.User) \
                            .filter(models.User.tid == tid,
                                    models.User.profile_id == profile_id) \
                            .all()

    current_profile = db_get(session,
                             models.UserProfile,
                             (models.UserProfile.tid == tid,
                              models.UserProfile.id == profile_id))

    db_enforce_administrable(session, tid, user_session,
                             current_profile.permissions_list,
                             [user.id for user in affected_users])
    support_private_key = decrypt_tenant_support_private_key(user_session, tid, session)
    profile = db_update_user_profile(session, tid, profile_id, request)
    admin_capable = 'admin' in request['roles']

    for user in affected_users:
        db_reconcile_support_user_access(session, tid, user, support_private_key, admin_capable=admin_capable)

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
    # The profiles are readable by the operators that bind them to users too,
    # while their mutation is confined to the profile managers.
    require_permission = {'get': ('can_manage_users', 'can_manage_user_profiles'),
                          'post': 'can_manage_user_profiles'}
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
    require_permission = {'get': ('can_manage_users', 'can_manage_user_profiles'),
                          'put': 'can_manage_user_profiles',
                          'delete': 'can_manage_user_profiles'}
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
