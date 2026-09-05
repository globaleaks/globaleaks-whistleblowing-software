import copy
import json
from nacl.encoding import Base64Encoder
from sqlalchemy import func
from twisted.internet.defer import inlineCallbacks

from globaleaks import models
from globaleaks.handlers.admin.operation import set_tmp_key
from globaleaks.handlers.admin.user_profile import db_attach_user_to_profile_contexts, db_create_user_profile, db_detach_user_from_profile_contexts, db_enforce_administrable, db_enforce_assignable_profile, db_enforce_grantable, sync_permissions
from globaleaks.handlers.base import BaseHandler
from globaleaks.handlers.support import db_reconcile_support_user_access, \
                                         decrypt_tenant_support_private_key, \
                                         is_support_admin
from globaleaks.handlers.user import db_reconcile_statistical_key, \
                                     parse_pgp_options, \
                                     serialize_user, \
                                     user_permissions
from globaleaks.handlers.user.reset_password import db_generate_password_reset_token
from globaleaks.models import fill_localized_keys
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

    :param role: The role of the user the profile belongs to
    :param user_session: The session of the operator, or None for a system op
    :return: The default permissions map for the profile
    """
    permissions = copy.deepcopy(user_permissions)

    if role == 'admin':
        for permission in models.admin_permissions:
            permissions[permission] = user_session is None or user_session.has_permission(permission)

    return permissions


def db_new_user_profile(session, tid, request, user_session):
    """
    Give an account bound to no shared profile a profile of its own, of its role

    :param session: An ORM session
    :param tid: A tenant ID
    :param request: The request data
    :param user_session: The session of the user performing the operation
    """
    request['profile_id'] = request['id']

    profile = {
      'id': request['id'],
      'role': request['role'],
      'roles':  [request['role']],
      'permissions':  db_default_profile_permissions(request['role'], user_session)
    }

    db_create_user_profile(session, tid, profile)


def db_user_key(user, request, defer_password_setup):
    """
    Set the hash of an account from its password, given or generated

    :param user: The account
    :param request: The request data
    :param defer_password_setup: Whether the account holds no password yet
    :return: The key derived from the password, None when the account holds no password
    """
    if defer_password_setup:
        # An empty hash marks an account authenticated elsewhere that must set a password
        user.hash = ''
        return None

    password = request.get('password', '')
    if not password:
        password = generateRandomPassword(16)
        key = Base64Encoder.decode(GCE.derive_key(password, user.salt).encode())
    else:
        key = Base64Encoder.decode(password)

    user.hash = sha256(key)

    return key


def db_attach_to_shared_profile(session, user):
    """
    A receiver bound to a shared profile is a recipient of the channels the profile is associated to

    :param session: An ORM session
    :param user: The account
    """
    if user.profile_id == user.id:
        return

    profile = session.query(models.UserProfile) \
                     .filter(models.UserProfile.id == user.profile_id).one_or_none()
    if profile is not None:
        db_attach_user_to_profile_contexts(session, user, profile)


def db_activation_token(session, tid, user, user_session, request):
    """
    Issue the token of the activation link of an account, when asked

    :param session: An ORM session
    :param tid: A tenant ID
    :param user: The account
    :param user_session: The session of the user performing the operation
    :param request: The request data
    :return: The token, None when no link is sent
    """
    if not request.get('send_activation_link', False):
        return None

    token = db_generate_password_reset_token(session, user)

    if user_session:
        db_log(session, tid=tid, type='send_password_reset_email', user_id=user_session.user_id, object_id=user.id)

    return token


def db_user_needs_keys(defer_password_setup, encryption, request, escrow_pub_key_1, escrow_pub_key_n, support_pub_key):
    """
    An account with a password on a site that encrypts, or that an escrow or the support has to
    reach, holds keys from its creation
    """
    if defer_password_setup:
        return False

    return (encryption and escrow_pub_key_1) or escrow_pub_key_n or support_pub_key or (encryption and request.get('password'))


def db_generate_user_keys(session, tid, user, user_session, key, token):
    """
    Generate the key pair of an account and its recovery key; the creating user keeps a copy for
    the activation link and reconciles the statistical key

    :param session: An ORM session
    :param tid: A tenant ID
    :param user: The account
    :param user_session: The session of the user performing the operation
    :param key: The key derived from the password
    :param token: The token of the activation link, if any
    :return: The private key of the account
    """
    cc, user.crypto_pub_key = GCE.generate_keypair()
    user.crypto_prv_key = Base64Encoder.encode(GCE.symmetric_encrypt(key, cc))
    user.crypto_bkp_key, user.crypto_rec_key = GCE.generate_recovery_key(cc)

    if user_session:
        if token:
            set_tmp_key(session, user_session, user, token, cc)

        current_user = db_get(session, models.User, models.User.id == user_session.user_id)
        db_reconcile_statistical_key(session, tid, current_user, user_session.cc)

    return cc


def db_escrow_user_key(user, tid, cc, escrow_pub_key_1, escrow_pub_key_n):
    """
    Keep copies of the key of an account encrypted to the escrow key of the root site and to the
    one of its site

    :param user: The account
    :param tid: A tenant ID
    :param cc: The private key of the account
    :param escrow_pub_key_1: The escrow key of the root site
    :param escrow_pub_key_n: The escrow key of the site
    """
    if escrow_pub_key_1:
        user.crypto_escrow_bkp1_key = Base64Encoder.encode(GCE.asymmetric_encrypt(escrow_pub_key_1, cc))

    if tid != 1 and escrow_pub_key_n:
        user.crypto_escrow_bkp2_key = Base64Encoder.encode(GCE.asymmetric_encrypt(escrow_pub_key_n, cc))


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
        db_new_user_profile(session, tid, request, user_session)

    if not request['public_name']:
        request['public_name'] = request['name']

    user = models.User(request)
    user.salt = GCE.generate_salt(config.get_val('receipt_salt') + ":" + user.username)
    user.language = request['language']

    # The various options related in manage PGP keys are used here.
    parse_pgp_options(user, request)

    key = db_user_key(user, request, defer_password_setup)

    session.add(user)

    session.flush()

    # After flush align date to user.creation_date
    user.password_change_date = user.creation_date

    db_attach_to_shared_profile(session, user)

    if user_session:
        db_log(session, tid=tid, type='create_user', user_id=user_session.user_id, object_id=user.id)

    token = db_activation_token(session, tid, user, user_session, request)

    crypto_escrow_pub_key_tenant_1 = models.config.ConfigFactory(session, 1).get_val('crypto_escrow_pub_key')
    crypto_escrow_pub_key_tenant_n = config.get_val('crypto_escrow_pub_key')
    crypto_support_pub_key = config.get_val('crypto_support_pub_key')

    cc = None
    if db_user_needs_keys(defer_password_setup, encryption, request,
                          crypto_escrow_pub_key_tenant_1, crypto_escrow_pub_key_tenant_n, crypto_support_pub_key):
        cc = db_generate_user_keys(session, tid, user, user_session, key, token)

    if crypto_support_pub_key and user_session:
        support_private_key = decrypt_tenant_support_private_key(user_session, tid, session)
        db_reconcile_support_user_access(
            session, tid, user, support_private_key
        )

    # No password, no encryption material yet: keys and escrow copies are generated on setup
    if defer_password_setup or (not crypto_escrow_pub_key_tenant_1 and not crypto_escrow_pub_key_tenant_n):
        return user

    db_escrow_user_key(user, tid, cc, crypto_escrow_pub_key_tenant_1, crypto_escrow_pub_key_tenant_n)

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


def db_switch_standard_profile(session, tid, user, request, user_session):
    """
    Delete the profile of an account when passing from a standard role to a custom profile, or
    when the standard role changes; recreate it when passing from a custom profile to a standard
    role, or between standard roles

    :param session: An ORM session
    :param tid: A tenant ID
    :param user: The account
    :param request: The request data
    :param user_session: The current user session
    """
    if ((user.id == user.profile_id and request['profile_id'] != user.id) or (user.role != request['role'])):
        db_del(session, models.UserProfile, models.UserProfile.id == user.id)

    if ((user.id != user.profile_id and request['profile_id'] == user.id) or (user.role != request['role'])):
        profile = {
          'id': user.id,
          'role': request['role'],
          'roles':  [request['role']],
          'permissions':  db_default_profile_permissions(request['role'], user_session)
        }

        db_create_user_profile(session, tid, profile)


def db_realign_profile_contexts(session, user, old_profile_id):
    """
    A change of profile realigns the channels of an account: detached from the old one, attached
    to the new one

    :param session: An ORM session
    :param user: The account
    :param old_profile_id: The profile the account was bound to
    """
    if old_profile_id == user.profile_id:
        return

    old_profile = session.query(models.UserProfile) \
                         .filter(models.UserProfile.id == old_profile_id).one_or_none()
    if old_profile is not None:
        db_detach_user_from_profile_contexts(session, user, old_profile)

    if user.profile_id != user.id:
        new_profile = session.query(models.UserProfile) \
                             .filter(models.UserProfile.id == user.profile_id).one_or_none()
        if new_profile is not None:
            db_attach_user_to_profile_contexts(session, user, new_profile)


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

    # A shared profile binding is validated when established or when the role changes: assignable by
    # the operator and compatible with the role
    if request['profile_id'] not in ('', 'none', user_id) and \
       (request['profile_id'] != user.profile_id or request['role'] != user.role):
        db_enforce_assignable_profile(session, tid, user_session, request['profile_id'], request['role'])

    old_role = user.role
    old_profile_id = user.profile_id
    old_enabled = user.enabled
    was_support_admin = is_support_admin(user)
    support_private_key = decrypt_tenant_support_private_key(user_session, tid, session)

    db_switch_standard_profile(session, tid, user, request, user_session)

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

    db_realign_profile_contexts(session, user, old_profile_id)

    permissions_changed = db_update_user_permissions(session, user, request)

    is_now_support_admin = is_support_admin(user)
    db_reconcile_support_user_access(session, tid, user, support_private_key, admin_capable=is_now_support_admin)

    revoke_session = old_role != user.role or \
        old_profile_id != user.profile_id or \
        old_enabled != user.enabled or \
        permissions_changed or \
        was_support_admin != is_now_support_admin
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
