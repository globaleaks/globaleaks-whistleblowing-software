# -*- coding: utf-8
import base64
import json
import logging

from twisted.internet.defer import inlineCallbacks

from globaleaks.handlers.admin.notification import db_get_notification
from globaleaks.handlers.admin.node import db_admin_serialize_node
from globaleaks import models
from globaleaks.handlers.base import BaseHandler
from globaleaks.handlers.user import parse_pgp_options, \
                                     user_serialize_user
from globaleaks.models import fill_localized_keys, EnumUserRole
from globaleaks.models.config import ConfigFactory
from globaleaks.orm import db_del, db_get, db_log, transact, tw
from globaleaks.rest import errors, requests
from globaleaks.state import State
from globaleaks.transactions import db_get_user
from globaleaks.utils.crypto import GCE, Base64Encoder, generateRandomPassword
from globaleaks.utils.utility import datetime_now, datetime_null, uuid4

def send_email_delete_eo_user(session, tid, user, eo_name):
    """
    Send deleted user email to the user.

    Args:
        session: The database session.
        username: The username that has been deleted
        eo_name: The external organization's name.
    """
    language = ConfigFactory(session, tid).get_val('default_language')
    node = db_admin_serialize_node(session, tid, language)
    notification = db_get_notification(session, 1, language)
    template_vars = {
        'type': 'delete_user_external_organization',
        'node': node,
        'notification': notification,
        'username': user.public_name,
        'eo_name': eo_name
    }

    State.format_and_send_mail(session, tid, user.mail_address, template_vars)


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

def share_analyst_key_pair(session, user, user_session):
    if user.role not in [EnumUserRole.analyst.name, EnumUserRole.admin.name]:
        return
    try:
        global_stat_prv_key, global_stat_pub_key = GCE.generate_keypair()

        global_stat_pub_key_config = session.query(models.Config).filter(
            models.Config.tid == user.tid,
            models.Config.var_name == 'global_stat_pub_key'
        ).first()

        if not global_stat_pub_key_config:
            raise ValueError("Config not found")

        if not global_stat_pub_key_config.value:
            global_stat_pub_key_config.value = global_stat_pub_key
        else:
            user_admin = session.query(models.User).filter(
                models.User.id == user_session.attrs.get('user_id'),
                models.User.tid == user.tid
            ).one_or_none()

            if not user_admin:
                raise ValueError("Admin user for decryption not found")

            sts_prv_key = base64.b64decode(user_admin.crypto_global_stat_prv_key)
            global_stat_prv_key = GCE.asymmetric_decrypt(user_session.cc, sts_prv_key)
        encrypted_global_stat_prv_key = GCE.asymmetric_encrypt(
            user.crypto_pub_key, global_stat_prv_key
        )
        crypto_stat_key_encoded = Base64Encoder.encode(encrypted_global_stat_prv_key).decode()
        session.query(models.User).filter(
            models.User.id == user.id
        ).update(
            {'crypto_global_stat_prv_key': crypto_stat_key_encoded}
        )
    except ValueError as e:
        logging.error(e)
        raise errors.ForbiddenOperation
    except Exception as e:
        logging.error(e)
        session.rollback()
        raise errors.InternalServerError


def db_create_user(session, tid, user_session, request, language, wizard: bool = False):
    """
    Transaction for creating a new user

    :param session: An ORM session
    :param tid: A tenant ID
    :param user_session: The session of the user performing the operation
    :param request: The request data
    :param language: The language of the request
    :param wizard: Creation of first admin
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

    user.language = request['language']

    # The various options related in manage PGP keys are used here.
    parse_pgp_options(user, request)

    if user_session and user_session.ek:
        db_set_user_password(session, tid, user, generateRandomPassword(16))

    session.add(user)
    session.flush()
    if not wizard and tid == 1:
        share_analyst_key_pair(session, user, user_session)

    if user_session:
        db_log(session, tid=tid, type='create_user', user_id=user_session.user_id, object_id=user.id)

    return user


def db_delete_user(session, tid, user_session, user_id):
    db_get(session, models.User, models.User.id == user_session.user_id)
    user_to_be_deleted = db_get(session, models.User, models.User.id == user_id)


    if user_session.user_id == user_id:
        # Prevent users to delete themeselves
        raise errors.ForbiddenOperation

    if user_to_be_deleted.crypto_escrow_prv_key and not user_session.ek:
        # Prevent users to delete privileged users when escrow keys could be invalidated
        raise errors.ForbiddenOperation

    tenant = db_get(session, models.Tenant, models.Tenant.id == tid)
    if tenant.external:
        eo_name = ConfigFactory(session, tid).get_val('name')
        send_email_delete_eo_user(session, tid, user_to_be_deleted, eo_name)

    db_del(session, models.User, (models.User.tid == tid, models.User.id == user_id))
    db_log(session, tid=tid, type='delete_user', user_id=user_session.user_id, object_id=user_id)


@transact
def create_user(session, tid, user_session, request, language, wizard:bool = False):
    """
    Transaction for creating a new user

    :param session: An ORM session
    :param tid: A tenant ID
    :param user_session: A user session
    :param request: The request data
    :param language: The language of the request
    :param wizard: IS not wizard?
    :return: The serialized descriptor of the created object
    """
    accreditation_mode = ConfigFactory(session, 1).get_val('mode') == 'accreditation'
    if accreditation_mode and request['idp_id'] is None:
        raise errors.InputValidationError("Key (idp_id) type validation failure")
    return user_serialize_user(session, db_create_user(session, tid, user_session, request, language, wizard), language)


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
    user.can_redact_information = request['can_redact_information']
    user.can_mask_information = request['can_mask_information']
    user.can_download_infected = request['can_download_infected']
    if request['mail_address'] != user.mail_address:
        user.change_email_token = None
        user.change_email_address = ''
        user.change_email_date = datetime_null()

    # Prevent administrators to reset password change needed status
    if user.password_change_needed:
        request['password_change_needed'] = True

    # The various options related in manage PGP keys are used here.
    parse_pgp_options(user, request)
    if user.role != request['role'] and tid == 1:
        share_analyst_key_pair(session, user, user_session)
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

    def get(self):
        """
        Return all the users.
        """
        return tw(db_get_users, self.request.tid, None, self.request.language)

    @inlineCallbacks
    def post(self):
        """
        Create a new user
        """
        body = self.request.content.read()
        request = self.validate_request(body, requests.AdminUserDesc)
        try:
            request['idp_id'] = json.loads(body).get('idp_id')
        except Exception as e:
            logging.debug(e)
            request['idp_id'] = None

        try:
            wizard = json.loads(body).get('wizard')
        except Exception as e:
            logging.debug(e)
            wizard = False

        user = yield create_user(self.request.tid, self.session, request, self.request.language, wizard)

        return user


class UserInstance(BaseHandler):
    check_roles = 'admin'
    invalidate_cache = True

    def put(self, user_id):
        """
        Update the specified user.
        """
        request = self.validate_request(self.request.content.read(), requests.AdminUserDesc)

        return tw(db_admin_update_user,
                  self.request.tid,
                  self.session,
                  user_id,
                  request,
                  self.request.language)

    def delete(self, user_id):
        """
        Delete the specified user.
        """
        return tw(db_delete_user, self.request.tid, self.session, user_id)
