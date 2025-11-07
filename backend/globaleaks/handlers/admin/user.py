import copy
import json
from nacl.encoding import Base64Encoder
from twisted.internet.defer import inlineCallbacks

from globaleaks import models
from globaleaks.handlers.admin.operation import set_tmp_key
from globaleaks.handlers.admin.user_profile import db_create_user_profile, db_update_user_profile
from globaleaks.handlers.base import BaseHandler
from globaleaks.handlers.user import parse_pgp_options, \
                                     serialize_user, \
                                     user_permissions
from globaleaks.handlers.user.reset_password import db_generate_password_reset_token
from globaleaks.models import config, Config, UserProfile, fill_localized_keys
from globaleaks.orm import db_del, db_get, db_log, transact, tw
from globaleaks.rest import errors, requests
from globaleaks.state import State
from globaleaks.transactions import db_get_user
from globaleaks.utils.crypto import GCE, generateRandomPassword, sha256
from globaleaks.utils.utility import datetime_null, uuid4


def db_create_user(session, tid, user_session, request, language):
    """
    Transaction for creating a new user

    :param session: An ORM session
    :param tid: A tenant ID
    :param user_session: The session of the user performing the operation
    :param request: The request data
    :param language: The language of the request
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
          'permissions':  copy.deepcopy(user_permissions)
        }

        db_create_user_profile(session, tid, profile)

    if not request['public_name']:
        request['public_name'] = request['name']

    user = models.User(request)
    user.salt = GCE.generate_salt(config.get_val('receipt_salt') + ":" + user.username)
    user.language = request['language']

    # The various options related in manage PGP keys are used here.
    parse_pgp_options(user, request)

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

    if encryption and crypto_escrow_pub_key_tenant_1 or crypto_escrow_pub_key_tenant_n:
        cc, user.crypto_pub_key = GCE.generate_keypair()
        user.crypto_prv_key = Base64Encoder.encode(GCE.symmetric_encrypt(key, cc))
        user.crypto_bkp_key, user.crypto_rec_key = GCE.generate_recovery_key(cc)

        if user_session:
            if token:
                set_tmp_key(user_session, user, token, cc)

            if any(role in user.profile.roles_list for role in ('admin', 'analyst')):
                current_user = db_get(session, models.User, models.User.id == user_session.user_id)
                if current_user.crypto_global_stat_prv_key:
                    crypto_global_stat_prv_key = GCE.asymmetric_decrypt(user_session.cc, Base64Encoder.decode(current_user.crypto_global_stat_prv_key))
                    user.crypto_global_stat_prv_key = Base64Encoder.encode(GCE.asymmetric_encrypt(user.crypto_pub_key, crypto_global_stat_prv_key))


    if not crypto_escrow_pub_key_tenant_1 and not crypto_escrow_pub_key_tenant_n:
        return user

    if crypto_escrow_pub_key_tenant_1:
        user.crypto_escrow_bkp1_key = Base64Encoder.encode(GCE.asymmetric_encrypt(crypto_escrow_pub_key_tenant_1, cc))

    if tid != 1 and crypto_escrow_pub_key_tenant_n:
        user.crypto_escrow_bkp2_key = Base64Encoder.encode(GCE.asymmetric_encrypt(crypto_escrow_pub_key_tenant_n, cc))

    return user


def db_delete_user(session, tid, user_session, user_id):
    db_get(session, models.User, models.User.id == user_session.user_id)

    user = db_get(session, models.User, models.User.id == user_id)

    if user_session.user_id == user_id:
        # Prevent users to delete themeselves
        raise errors.ForbiddenOperation
    elif user.crypto_escrow_prv_key and not user_session.ek:
        # Prevent users to delete privileged users when escrow keys could be invalidated
        raise errors.ForbiddenOperation

    db_del(session, models.User, (models.User.tid == tid, models.User.id == user_id))

    if user.id == user.profile_id:
        # in this condition we should delete the profile since it will become unused
        db_del(session, models.UserProfile, models.UserProfile.id == user.id)

    db_log(session, tid=tid, type='delete_user', user_id=user_session.user_id, object_id=user_id)


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
    user = db_create_user(session, tid, user_session, request, language)
    return serialize_user(session, user, language)


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

    user = db_get_user(session, tid, user_id)

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
          'permissions':  copy.deepcopy(user_permissions)
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

    return serialize_user(session, user, language)


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
    invalidate_cache = True

    def get(self, user_id):
        """
        Retrieve the specified user.
        """
        return tw(get_user, self.request.tid, user_id)

    def put(self, user_id):
        """
        Update the specified user.
        """
        request = json.loads(self.request.content.read())
        request = self.validate_request(request, requests.AdminUserDesc)
        return tw(db_update_user, self.request.tid, self.session, user_id, request, self.request.language)

    def delete(self, user_id):
        """
        Delete the specified user.
        """
        return tw(db_delete_user, self.request.tid, self.session, user_id)
