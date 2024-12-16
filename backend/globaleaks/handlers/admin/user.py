# -*- coding: utf-8
import json
from twisted.internet.defer import inlineCallbacks

from globaleaks import models
from globaleaks.handlers.base import BaseHandler
from globaleaks.handlers.user import parse_pgp_options, \
                                     user_serialize_user
from globaleaks.models import UserProfile, fill_localized_keys
from globaleaks.orm import db_del, db_get, db_log, transact, tw
from globaleaks.rest import errors, requests
from globaleaks.state import State
from globaleaks.transactions import db_get_user
from globaleaks.utils.crypto import GCE, Base64Encoder, generateRandomPassword
from globaleaks.utils.utility import datetime_now, datetime_null, uuid4

def serialize_user_profile(user):
    """
    Serialize a user profile object into a dictionary format.

    :param user: The user profile object to serialize.
    :return: A dictionary containing user profile data.
    """
    user_profile = {
        'id': user.id,
        'name': user.name,
        'role': user.role,
        'enabled': user.enabled,
        'language': user.language,
        'pgp_key_remove': False,
        'pgp_key_fingerprint': user.pgp_key_fingerprint,
        'pgp_key_public': user.pgp_key_public,
        'notification': user.notification,
        'can_edit_general_settings': user.can_edit_general_settings,
        'can_delete_submission': user.can_delete_submission,
        'can_postpone_expiration': user.can_postpone_expiration,
        'can_grant_access_to_reports': user.can_grant_access_to_reports,
        'can_redact_information': user.can_redact_information,
        'can_mask_information': user.can_mask_information,
        'can_reopen_reports': user.can_reopen_reports,
        'can_transfer_access_to_reports': user.can_transfer_access_to_reports,
        'forcefully_selected': user.forcefully_selected,
    }

    return user_profile

def db_create_user_profile(session, request):
    """
    Transaction for creating a new user

    :param user_session: The session of the user performing the operation
    :param request: The request data
    :return: The serialized descriptor of the created object
    """

    user = models.UserProfile(request)

    for key, value in request.items():
        setattr(user, key, value)
    
    parse_pgp_options(user, request)

    existing_user = session.query(models.UserProfile).filter(models.UserProfile.name == user.name).first()
    if existing_user:
        raise errors.DuplicateUserError

    session.add(user)

    session.flush()

    return serialize_user_profile(user)

@transact
def db_delete_user_profile(session, user_id):
    protected_profiles = {'admin': 'Admin', 'receiver': 'Receiver', 'analyst': 'Analyst', 'custodian': 'Custodian'}

    user = session.query(models.UserProfile).filter(models.UserProfile.id == user_id).first()

    if not user:
        raise ValueError

    if user.role in protected_profiles and user.name == protected_profiles[user.role]:
        raise errors.ForbiddenOperation

    if session.query(models.User).filter(models.User.profile_id == user_id).first():
        raise errors.ForbiddenOperation

    session.delete(user)
    session.commit()

@transact
def create_user_profile(session, request):
    """
    Transaction for creating a new user

    :param session: An ORM session
    :param request: The request data
    :return: The serialized descriptor of the created object
    """
    return db_create_user_profile(session, request)

@transact
def db_admin_update_user_profile(session, user_id, request):
    """
    Update the user profile in the database.
    
    :param session: An ORM session
    :param user_id: The ID of the user to update
    :param request: The new data for updating the user profile
    :return: The updated user object
    """
    user = session.query(models.UserProfile).filter(models.UserProfile.id == user_id).first()
    
    parse_pgp_options(user, request)
    
    for key, value in request.items():
        if hasattr(user, key):
            setattr(user, key, value) 

    session.commit()

    return serialize_user_profile(user)

@transact
def db_get_user_profiles(session):
    """
    Retrieve all user profiles from the database.
    
    :param session: ORM session
    :return: List of user profiles in serialized form
    """
    users = session.query(models.UserProfile).all()

    user_profiles = []
    for user in users:
        user_data = serialize_user_profile(user)
        user_profiles.append(user_data)

    return user_profiles

def db_set_user_password(session, tid, user, password):
    config = models.config.ConfigFactory(session, tid)

    user.hash = GCE.hash_password(password, user.salt)
    user.password_change_date = datetime_now()

    if config.get_val('encryption'):
        root_config = models.config.ConfigFactory(session, 1)

        enc_key = GCE.derive_key(password.encode(), user.salt)
        cc, user.crypto_pub_key = GCE.generate_keypair()
        user.crypto_prv_key = Base64Encoder.encode(GCE.symmetric_encrypt(enc_key, cc))
        user.crypto_bkp_key, user.crypto_rec_key = GCE.generate_recovery_key(cc)

        crypto_escrow_pub_key_tenant_1 = root_config.get_val('crypto_escrow_pub_key')
        if crypto_escrow_pub_key_tenant_1:
            user.crypto_escrow_bkp1_key = Base64Encoder.encode(GCE.asymmetric_encrypt(crypto_escrow_pub_key_tenant_1, cc))

        if tid != 1:
            crypto_escrow_pub_key_tenant_n = config.get_val('crypto_escrow_pub_key')
            if crypto_escrow_pub_key_tenant_n:
                user.crypto_escrow_bkp2_key = Base64Encoder.encode(GCE.asymmetric_encrypt(crypto_escrow_pub_key_tenant_n, cc))



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
    request['tid'] = tid

    fill_localized_keys(request, models.User.localized_keys, language)

    if not request['public_name']:
        request['public_name'] = request['name']

    user = models.User(request)

    if not request['username']:
        user.username = user.id = uuid4()

    existing_user = session.query(models.User).filter(models.User.tid == user.tid, models.User.username == user.username).first()
    if existing_user:
        raise errors.DuplicateUserError

    user.salt = GCE.generate_salt()

    if user_session and user_session.ek:
        db_set_user_password(session, tid, user, generateRandomPassword(16))

    session.add(user)

    session.flush()
    
    if user_session:
        db_log(session, tid=tid, type='create_user', user_id=user_session.user_id, object_id=user.id)

    return user


def db_delete_user(session, tid, user_session, user_id):
    current_user = db_get(session, models.User, models.User.id == user_session.user_id)
    user_to_be_deleted = db_get(session, models.User, models.User.id == user_id)

    if user_session.user_id == user_id:
        # Prevent users to delete themeselves
        raise errors.ForbiddenOperation
    elif user_to_be_deleted.crypto_escrow_prv_key and not user_session.ek:
        # Prevent users to delete privileged users when escrow keys could be invalidated
        raise errors.ForbiddenOperation

    db_del(session, models.User, (models.User.tid == tid, models.User.id == user_id))
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
    return user_serialize_user(session, db_create_user(session, tid, user_session, request, language), language)


def db_admin_update_user(session, tid, user_session, user_id, request, language):
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
    profile = session.query(UserProfile).filter(UserProfile.id == request['profile_id']).first()
    request['role'] = profile.role
    if request['mail_address'] != user.mail_address:
        user.change_email_token = None
        user.change_email_address = ''
        user.change_email_date = datetime_null()

    # Prevent administrators to reset password change needed status
    if user.password_change_needed:
        request['password_change_needed'] = True

    user.update(request)

    return user_serialize_user(session, user, language)


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

    return [user_serialize_user(session, user, language) for user in users]


class UsersCollection(BaseHandler):
    check_roles = 'admin'
    invalidate_cache = True

    @inlineCallbacks
    def get(self):
        """
        Return all the users.
        """
        users = yield tw(db_get_users, self.request.tid, None, self.request.language)

        user_profiles = yield db_get_user_profiles()

        response = {"users": users, "user_profiles": user_profiles}
    
        return response
    
    @inlineCallbacks
    def post(self):
        """
        Create a new user or user profile.
        If 'profile_id' is in the request, create a User; otherwise, create a UserProfile.
        """
        content = self.request.content.read().decode('utf-8')
        content_data = json.loads(content)
        profile_id = content_data.get("profile_id", "").strip()
        is_profile_id_present = profile_id != ""        
        request_type = requests.AdminUserDesc if is_profile_id_present else requests.AdminUserProfileDesc
        request = yield self.validate_request(content, request_type)
        if "profile_id" in request:
            user = yield create_user(self.request.tid, self.session, request, self.request.language)
            return user
        else:
            profile = yield create_user_profile(request)
            return profile


class UserInstance(BaseHandler):
    check_roles = 'admin'
    invalidate_cache = True

    @inlineCallbacks
    def put(self, user_id):
        """
        Update the specified user or user profile.
        If 'profile_id' is in the request, update the user; otherwise, update the user profile.
        """
        content = self.request.content.read().decode('utf-8')
        is_profile_id = "profile_id" in content

        if is_profile_id:
            request = yield self.validate_request(content, requests.AdminUserDesc)
            user = yield tw(db_admin_update_user,
                self.request.tid,
                self.session,
                user_id,
                request,
                self.request.language)
            
            return user
        else:
            request = yield self.validate_request(content, requests.AdminUserProfileDesc)
    
            profile = yield db_admin_update_user_profile(user_id, request)

            return profile


    def delete(self, user_id):
        """
        Delete the specified user.
        """
        request_body = json.loads(self.request.content.read())
        is_profile = request_body.get("is_profile", False)
        
        if is_profile:
            return db_delete_user_profile(user_id)
        else:
            return tw(db_delete_user, self.request.tid, self.session, user_id)
