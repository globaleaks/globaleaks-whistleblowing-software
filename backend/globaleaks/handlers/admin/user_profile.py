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
from globaleaks.utils.utility import uuid4


def sync_roles(session, profile, request):
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

    # Sync users using this profile
    for user in session.query(models.User).filter(models.User.profile_id == profile.id, models.User.role.notin_(roles)):
        user.role = request['role']


def sync_permissions(session, profile, request):
    permissions = request['permissions']
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


def db_create_user_profile(session, tid, request):
    """
    Transaction for creating a new user

    :param session: An ORM session
    :param tid: A tenant ID
    :param request: The request data
    :return: The serialized descriptor of the created object
    """
    if not request.get('id'):
        request['id'] = uuid4()

    request['tid'] = tid
    profile = models.UserProfile(request)
    profile.role = request['role']

    sync_roles(session, profile, request)
    sync_permissions(session, profile, request)

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

    return serialize_user_profile(session, profile)


@transact
def update_user_profile(session, tid, profile_id, request):
    """
    Update the user profile in the database.

    :param session: An ORM session
    :param tid: A tenant ID
    :param profile_id: The ID of the user to update
    :param request: The new data for updating the user profile
    :return: The updated user object
    """
    return db_update_user_profile(session, tid, profile_id, request)


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
        subquery = session.query(UserProfile.id).filter(UserProfile.tid == pid, UserProfile.id == models.User.id)
        profiles = session.query(UserProfile).filter(UserProfile.tid == pid, UserProfile.id.notin_(subquery)).all()

        for profile in profiles:
            ret.append(serialize_user_profile(session, profile))
            ret[-1]['custom'] = False

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
        profile = yield update_user_profile(self.request.tid, profile_id, profile_request)
        return profile

    def delete(self, profile_id):
        """
        Delete the specified user profile.
        """
        return delete_user_profile(self.request.tid, profile_id)
