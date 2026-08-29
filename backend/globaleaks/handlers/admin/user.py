import copy
import json
from nacl.encoding import Base64Encoder
from sqlalchemy import func
from twisted.internet.defer import inlineCallbacks

from globaleaks import models
from globaleaks.handlers.admin.operation import set_tmp_key
from globaleaks.handlers.admin.user_profile import db_attach_user_to_profile_contexts, db_create_user_profile, db_detach_user_from_profile_contexts, db_enforce_administrable, db_enforce_assignable_profile, db_enforce_grantable, db_update_user_profile, sync_permissions
from globaleaks.handlers.base import BaseHandler
from globaleaks.handlers.user import db_reconcile_statistical_key, \
                                     parse_pgp_options, \
                                     serialize_user, \
                                     user_permissions
from globaleaks.handlers.user.reset_password import db_generate_password_reset_token
from globaleaks.models import config, Config, UserProfile, fill_localized_keys
from globaleaks.models.config import db_get_protected_users
from globaleaks.orm import db_del, db_get, db_log, transact, tw
from globaleaks.rest import errors, requests
from globaleaks.sessions import Sessions
from globaleaks.state import State
from globaleaks.transactions import db_get_user
from globaleaks.utils.crypto import GCE, generateRandomPassword, sha256
from globaleaks.utils.utility import datetime_null, uuid4


def db_default_profile_permissions(role, user_session=None):
    """
    Build the default permissions of the personal profile of a user

    An administrator is provisioned able to manage every administrative area,
    so it starts holding the whole set of administrative permissions; they can
    be removed afterwards to scope the administrator to a subset of the areas.
    When the provisioning is performed by an operator, the defaults are
    clamped to the areas the operator itself manages: an administrator
    confined to a subset of the areas provisions administrators confined the
    same way. A system operation (no session, e.g. the wizard) provisions the
    whole set.

    :param role: The role of the user the profile belongs to
    :param user_session: The session of the operator, or None for a system op
    :return: The default permissions map for the profile
    """
    permissions = copy.deepcopy(user_permissions)

    if role == 'admin':
        for permission in models.admin_permissions:
            permissions[permission] = user_session is None or user_session.has_permission(permission)

    return permissions


def db_create_user(session, tid, user_session, request, language, defer_password_setup=False):
    """
    Transaction for creating a new user

    :param session: An ORM session
    :param tid: A tenant ID
    :param user_session: The session of the user performing the operation
    :param request: The request data
    :param language: The language of the request
    :param defer_password_setup: Whether the account is created holding no
                                 password, its user being required to set one
                                 before proceeding
    :return: The serialized descriptor of the created object
    """
    existing_user = session.query(models.User).filter(models.User.tid == tid, models.User.username == request['username']).first()
    if existing_user:
        raise errors.DuplicateUserError

    config = models.config.ConfigFactory(session, tid)
    encryption = config.get_val('encryption')

    fill_localized_keys(request, models.User.localized_keys, language)

    request['tid'] = tid
    request['id'] = uuid4()

    if not request['username']:
        request['username'] = request['id']

    if not request['profile_id'] or request['profile_id'] == 'none':
        request['profile_id'] = request['id']

        profile = {
          'id': request['id'],
          'role': request['role'],
          'roles':  [request['role']],
          'permissions':  db_default_profile_permissions(request['role'], user_session)
        }

        db_create_user_profile(session, tid, profile)

    if not request['public_name']:
        request['public_name'] = request['name']

    user = models.User(request)
    user.salt = GCE.generate_salt(config.get_val('receipt_salt') + ":" + user.username)
    user.language = request['language']

    # The various options related in manage PGP keys are used here.
    parse_pgp_options(user, request)

    if defer_password_setup:
        # The account holds no password: an empty hash marks an account whose
        # user is authenticated elsewhere and is required to set a password
        # before proceeding, the encryption material of the account being
        # initialized at that point
        user.hash = ''
    else:
        password = request.get('password', '')
        if not password:
            password = generateRandomPassword(16)
            key = Base64Encoder.decode(GCE.derive_key(password, user.salt).encode())
        else:
            key = Base64Encoder.decode(password)

        user.hash = sha256(key)

    session.add(user)

    session.flush()

    # After flush align date to user.creation_date
    user.password_change_date = user.creation_date

    # A receiver bound to a shared profile is a recipient of the channels the
    # profile is associated to
    if user.profile_id != user.id:
        profile = session.query(models.UserProfile) \
                         .filter(models.UserProfile.id == user.profile_id).one_or_none()
        if profile is not None:
            db_attach_user_to_profile_contexts(session, user, profile)

    if user_session:
        db_log(session, tid=tid, type='create_user', user_id=user_session.user_id, object_id=user.id)

    if request.get('send_activation_link', False):
        token = db_generate_password_reset_token(session, user)
        if user_session:
            db_log(session, tid=tid, type='send_password_reset_email', user_id=user_session.user_id, object_id=user.id)
    else:
        token = None

    crypto_escrow_pub_key_tenant_1 = models.config.ConfigFactory(session, 1).get_val('crypto_escrow_pub_key')
    crypto_escrow_pub_key_tenant_n = config.get_val('crypto_escrow_pub_key')

    if not defer_password_setup and \
       ((encryption and crypto_escrow_pub_key_tenant_1) or crypto_escrow_pub_key_tenant_n or (encryption and request.get('password'))):
        cc, user.crypto_pub_key = GCE.generate_keypair()
        user.crypto_prv_key = Base64Encoder.encode(GCE.symmetric_encrypt(key, cc))
        user.crypto_bkp_key, user.crypto_rec_key = GCE.generate_recovery_key(cc)

        if user_session:
            if token:
                set_tmp_key(session, user_session, user, token, cc)

            current_user = db_get(session, models.User, models.User.id == user_session.user_id)
            db_reconcile_statistical_key(session, tid, current_user, user_session.cc)

    # The account holding no password holds no encryption material yet: the
    # keys, and with them the copies kept by the escrows, are generated upon
    # the setup of the password performed by its user
    if defer_password_setup or (not crypto_escrow_pub_key_tenant_1 and not crypto_escrow_pub_key_tenant_n):
        return user

    if crypto_escrow_pub_key_tenant_1:
        user.crypto_escrow_bkp1_key = Base64Encoder.encode(GCE.asymmetric_encrypt(crypto_escrow_pub_key_tenant_1, cc))

    if tid != 1 and crypto_escrow_pub_key_tenant_n:
        user.crypto_escrow_bkp2_key = Base64Encoder.encode(GCE.asymmetric_encrypt(crypto_escrow_pub_key_tenant_n, cc))

    return user


def db_get_user_stats(session, tid, user_id):
    """
    Get statistics about a user's report access

    :param session: An ORM session
    :param tid: A tenant ID
    :param user_id: The ID of the user
    :return: A dictionary with user statistics
    """
    total_reports = session.query(func.count(models.ReceiverTip.id)).filter(
        models.ReceiverTip.receiver_id == user_id
    ).scalar() or 0

    user_tips = session.query(models.ReceiverTip.internaltip_id).filter(
        models.ReceiverTip.receiver_id == user_id
    ).subquery()

    exclusive_reports = 0
    for (internaltip_id,) in session.query(user_tips.c.internaltip_id):
        recipient_count = session.query(func.count(models.ReceiverTip.id)).filter(
            models.ReceiverTip.internaltip_id == internaltip_id
        ).scalar() or 0
        if recipient_count == 1:
            exclusive_reports += 1

    last_update = session.query(func.max(models.InternalTip.update_date)).join(
        models.ReceiverTip,
        models.InternalTip.id == models.ReceiverTip.internaltip_id
    ).filter(
        models.ReceiverTip.receiver_id == user_id
    ).scalar()

    if not last_update:
        last_update = datetime_null()

    return {
        'total_reports': total_reports,
        'exclusive_reports': exclusive_reports,
        'last_update': last_update.isoformat()
    }


def db_delete_user(session, tid, user_session, user_id, check):
    db_get(session, models.User, models.User.id == user_session.user_id)

    user = db_get(session, models.User, models.User.id == user_id)

    if user_session.user_id == user_id:
        # Prevent users to delete themeselves
        raise errors.ForbiddenOperation
    elif user.crypto_escrow_prv_key and not user_session.ek:
        # Prevent users to delete privileged users when escrow keys could be invalidated
        raise errors.ForbiddenOperation
    elif user.id in db_get_protected_users(session, tid):
        # Prevent deletion of protected users
        raise errors.ForbiddenOperation

    db_enforce_administrable(session, tid, user_session, user.permissions_list, [user.id])

    stats = db_get_user_stats(session, tid, user_id)

    if check:
        stats_changed = (
            stats['total_reports'] != check['total_reports'] or
            stats['exclusive_reports'] != check['exclusive_reports'] or
            stats['last_update'] != check['last_update']
        )

        if stats_changed:
            raise errors.OperationConflict

    db_del(session, models.User, (models.User.tid == tid, models.User.id == user_id))

    if user.profile_id == user_id:
        # Delete the personal profile of the users configured with a standard role
        db_del(session, models.UserProfile, models.UserProfile.id == user_id)

    db_log(session, tid=tid, type='delete_user', user_id=user_session.user_id, object_id=user_id, data=stats)


@transact
def create_user(session, tid, user_session, request, language):
    """
    Transaction for creating a new user

    :param session: An ORM session
    :param tid: A tenant ID
    :param request: The request data
    :param language: The language of the request
    :return: The serialized descriptor of the created object
    """
    db_enforce_grantable(user_session,
                         (request.get('profile') or {}).get('permissions'),
                         [request['role']] if request.get('role') else None)

    if request.get('profile_id') and request['profile_id'] != 'none':
        db_enforce_assignable_profile(session, tid, user_session, request['profile_id'], request['role'])

    user = db_create_user(session, tid, user_session, request, language)
    return serialize_user(session, user, language)


def db_update_user_permissions(session, user, request):
    """
    Apply on the profile of a user the permissions carried by a user update request

    The permissions are stored on the profile of the user that remains their only
    source of truth; the user editor acts as the interface of the personal profile
    of the users that do not use a profile shared with other users.

    :param session: An ORM session
    :param user: The user object of the update
    :param request: The request data
    :return: A boolean indicating if the permissions of the user changed
    """
    permissions = (request.get('profile') or {}).get('permissions')

    if user.id != user.profile_id or not isinstance(permissions, dict):
        return False

    permissions = {k: v for k, v in permissions.items() if k in user_permissions}

    current_permissions = set(user.profile.permissions_list)

    sync_permissions(session, user.profile, {'permissions': permissions})
    session.flush()

    updated_permissions = {p[0] for p in session.query(models.UserProfilePermission.permission)
                                                .filter(models.UserProfilePermission.profile_id == user.profile_id)}

    return current_permissions != updated_permissions


def db_update_user(session, tid, user_session, user_id, request, language):
    """
    Transaction for updating an existing user

    :param session: An ORM session
    :param tid: A tenant ID
    :param user_session: The current user session
    :param user_id: The ID of the user to update
    :param request: The request data
    :param language: The language of the request
    :return: The serialized descriptor of the updated object
    """
    fill_localized_keys(request, models.User.localized_keys, language)

    db_enforce_grantable(user_session,
                         (request.get('profile') or {}).get('permissions'),
                         [request['role']] if request.get('role') else None)

    user = db_get_user(session, tid, user_id)

    db_enforce_administrable(session, tid, user_session, user.permissions_list, [user.id])

    # A binding to a shared profile is validated whenever it is established or
    # the role of its user changes: the profile must be assignable by the
    # operator and the role must be among the ones the profile allows.
    if request['profile_id'] not in ('', 'none', user_id) and \
       (request['profile_id'] != user.profile_id or request['role'] != user.role):
        db_enforce_assignable_profile(session, tid, user_session, request['profile_id'], request['role'])

    old_role = user.role
    old_profile_id = user.profile_id
    old_enabled = user.enabled

    if ((user.id == user.profile_id and request['profile_id'] != user.id) or (user.role != request['role'])):
        # Delete profiles when:
        # - the user configuration passes from using a standard role to a custom profile
        # - the user uses a standard role but the role changes
        db_del(session, models.UserProfile, models.UserProfile.id == user.id)

    if ((user.id != user.profile_id and request['profile_id'] == user.id) or (user.role != request['role'])):
        # Recreate the profile when:
        # - the user configuration passes from using a custom profile to using a standard role
        # - the user user changes from a standard role to one other
        profile = {
          'id': user.id,
          'role': request['role'],
          'roles':  [request['role']],
          'permissions':  db_default_profile_permissions(request['role'], user_session)
        }

        db_create_user_profile(session, tid, profile)

    if request['mail_address'] != user.mail_address:
        user.change_email_token = None
        user.change_email_address = ''
        user.change_email_date = datetime_null()

    # Prevent administrators to reset password change needed status
    if user.password_change_needed:
        request['password_change_needed'] = True

    # The various options related in manage PGP keys are used here.
    parse_pgp_options(user, request)

    user.update(request)
    session.flush()
    session.expire(user, ['profile'])

    # A change of profile realigns the channels the user receives on: the ones
    # of the profile left are detached and the ones of the profile taken are
    # attached
    if old_profile_id != user.profile_id:
        old_profile = session.query(models.UserProfile) \
                             .filter(models.UserProfile.id == old_profile_id).one_or_none()
        if old_profile is not None:
            db_detach_user_from_profile_contexts(session, user, old_profile)

        if user.profile_id != user.id:
            new_profile = session.query(models.UserProfile) \
                                 .filter(models.UserProfile.id == user.profile_id).one_or_none()
            if new_profile is not None:
                db_attach_user_to_profile_contexts(session, user, new_profile)

    permissions_changed = db_update_user_permissions(session, user, request)

    revoke_session = old_role != user.role or \
        old_profile_id != user.profile_id or \
        old_enabled != user.enabled or \
        permissions_changed
    return serialize_user(session, user, language), revoke_session


def db_get_users(session, tid, role=None, language=None):
    """
    Transaction for retrieving the list of users defined on a tenant

    :param session: An ORM session
    :param tid: A tenant ID
    :param role: The role of the users to be retriven
    :param language: The language to be used during serialization
    :return: A list of serialized descriptors of the users defined on the specified tenant
    """
    if role is None:
        users = session.query(models.User).filter(models.User.tid == tid)
    else:
        users = session.query(models.User).filter(models.User.tid == tid,
                                                  models.User.role == role)

    language = language or State.tenants[tid].cache.default_language

    return [serialize_user(session, user, language) for user in users]


def get_user(session, tid, id):
    """
    Return specific user.
    """
    user = session.query(models.User).filter(models.User.id == id, models.User.tid == tid).first()
    if user:
        return serialize_user(session, user, State.tenants[tid].cache.default_language)

    raise errors.ResourceNotFound


class UsersCollection(BaseHandler):
    check_roles = 'admin'
    require_permission = 'can_manage_users'
    invalidate_cache = True

    def get(self):
        """
        Return all the users.
        """
        return tw(db_get_users, self.request.tid, None, self.request.language)

    @inlineCallbacks
    def post(self):
        """
        Create a new user.
        """
        request = json.loads(self.request.content.read())

        request = yield self.validate_request(json.dumps(request), requests.AdminUserDesc)
        user = yield create_user(self.request.tid, self.session, request, self.request.language)
        return user


class UserInstance(BaseHandler):
    check_roles = 'admin'
    require_permission = 'can_manage_users'
    invalidate_cache = True

    def get(self, user_id):
        """
        Retrieve the specified user.
        """
        return tw(get_user, self.request.tid, user_id)

    @inlineCallbacks
    def put(self, user_id):
        """
        Update the specified user.
        """
        request = json.loads(self.request.content.read())
        request = self.validate_request(request, requests.AdminUserDesc)
        user, revoke_session = yield tw(
            db_update_user,
            self.request.tid,
            self.session,
            user_id,
            request,
            self.request.language
        )
        # Revoke the target user's active sessions so that the reconfiguration
        # (e.g. account disabling or role change) takes effect immediately rather
        # than after idle session expiration; never revoke the operator's own.
        if self.session.user_id != user_id:
            Sessions.revoke_user(self.request.tid, user_id)

        return user

    @inlineCallbacks
    def delete(self, user_id):
        """
        Delete the specified user.
        """
        self.check_confirmation()

        check = self.request.content.read()
        if check:
            check = self.validate_request(check,
                                          requests.AdminUserDeleteDesc)


        yield tw(db_delete_user,
                 self.request.tid,
                 self.session,
                 user_id,
                 check)
        Sessions.revoke_user(self.request.tid, user_id)


class UserStats(BaseHandler):
    check_roles = 'admin'
    require_permission = 'can_manage_users'

    def get(self, user_id):
        """
        Retrieve statistics about a user's report access.
        """
        return tw(db_get_user_stats, self.request.tid, user_id)
