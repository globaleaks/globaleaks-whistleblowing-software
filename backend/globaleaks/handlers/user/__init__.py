# Handlers dealing with user preferences
from globaleaks import models
from globaleaks.handlers.base import BaseHandler
from globaleaks.models import get_localized_values
from globaleaks.orm import db_get, transact
from globaleaks.rest import requests
from globaleaks.state import State
from globaleaks.transactions import db_get_user
from globaleaks.utils.crypto import generateRandomKey
from globaleaks.utils.objectdict import ObjectDict
from globaleaks.utils.pgp import PGPContext
from globaleaks.utils.utility import datetime_now, datetime_null

import globaleaks.handlers.user.validate_email

user_permissions = ObjectDict({
    'can_edit_general_settings': False,
    'can_delete_submission': False,
    'can_postpone_expiration': True,
    'can_grant_access_to_reports': False,
    'can_mask_information': True,
    'can_redact_information': False,
    'can_transfer_access_to_reports': False
})


def serialize_user_profile(session, profile):
    """
    Serialize a user profile object into a dictionary format.

    :param user: The user profile object to serialize.
    :return: A dictionary containing user profile data.
    """
    user_profile = {
        'id': profile.id,
        'tid': profile.tid,
        'name': profile.name,
        'role': profile.role,
        'roles': sorted(profile.roles_list),
        'permissions': {}
    }

    for r in user_permissions:
        user_profile['permissions'][r] = r in profile.permissions_list

    return user_profile


def serialize_user(session, user, language):
    """
    Serialize user model

    :param user: the user object
    :param language: the language of the data
    :param session: the session on which perform queries.
    :return: a serialization of the object
    """
    picture = session.query(models.File).filter(models.File.name == user.id).one_or_none() is not None

    # take only contexts for the current tenant
    contexts = [x[0] for x in session.query(models.ReceiverContext.context_id)
                                     .filter(models.ReceiverContext.receiver_id == user.id)]

    profile = session.query(models.UserProfile).filter(models.UserProfile.id == user.profile_id).first()

    ret = {
        'id': user.id,
        'creation_date': user.creation_date,
        'username': user.username,
        'role': user.role,
        'enabled': user.enabled,
        'last_login': user.last_login,
        'name': user.name,
        'description': user.description,
        'public_name': user.public_name,
        'mail_address': user.mail_address,
        'change_email_address': user.change_email_address,
        'language': user.language,
        'password_change_needed': user.password_change_needed,
        'password_change_date': user.password_change_date,
        'pgp_key_fingerprint': user.pgp_key_fingerprint,
        'pgp_key_public': user.pgp_key_public,
        'pgp_key_expiration': user.pgp_key_expiration,
        'pgp_key_remove': False,
        'picture': picture,
        'tid': user.tid,
        'notification': user.notification,
        'encryption': user.crypto_pub_key != '',
        'salt': user.salt,
        'escrow': user.crypto_escrow_prv_key != '',
        'two_factor': user.two_factor_secret != '',
        'clicked_recovery_key': user.clicked_recovery_key,
        'accepted_privacy_policy': user.accepted_privacy_policy,
        'contexts': contexts,
        'send_activation_link': False,
        'forcefully_selected': False,
        'profile_id': user.profile_id,
        'profile': serialize_user_profile(session, profile)
    }

    if State.tenants[user.tid].cache.two_factor and \
      user.two_factor_secret == '':
        ret['require_two_factor'] = True

    return get_localized_values(ret, user, user.localized_keys, language)



def parse_pgp_options(user, request):
    """
    Used for parsing PGP key infos and fill related user configurations.

    :param user: A user model
    :param request: A request to be parsed
    """
    pgp_key_public = request['pgp_key_public']
    remove_key = request['pgp_key_remove']

    if not remove_key and pgp_key_public:
        pgpctx = PGPContext(pgp_key_public)
        user.pgp_key_public = pgp_key_public
        user.pgp_key_fingerprint = pgpctx.fingerprint
        user.pgp_key_expiration = pgpctx.expiration
    else:
        user.pgp_key_public = ''
        user.pgp_key_fingerprint = ''
        user.pgp_key_expiration = datetime_null()


@transact
def get_user(session, tid, user_id, language):
    """
    Transaction for retrieving a user model given an id

    :param session: An ORM session
    :param tid: A tenant ID
    :param user_id: A id of the user to retrieve
    :param language: The language to be used in the serialization
    :return: A serialization of the retrieved user
    """
    user = db_get_user(session, tid, user_id)

    return serialize_user(session, user, language)


def db_user_update_user(session, tid, user_session, request):
    """
    Transaction for updating an existing user

    :param session: An ORM session
    :param tid: A tenant ID
    :param user_session: A session of the user invoking the transaction
    :param request: A user request data
    :return: A user model
    """
    from globaleaks.handlers.admin.notification import db_get_notification
    from globaleaks.handlers.admin.node import db_admin_serialize_node

    user = db_get(session,
                  models.User,
                  models.User.id == user_session.user_id)

    user.language = request.get('language', State.tenants[tid].cache.default_language)
    user.name = request['name']
    user.role = request['role']
    user.public_name = request['public_name'] or request['name']
    user.notification = request['notification']

    # If the email address changed, send a validation email
    if request['mail_address'] != user.mail_address:
        user.change_email_address = request['mail_address']
        user.change_email_date = datetime_now()
        user.change_email_token = generateRandomKey()

        user_desc = serialize_user(session, user, user.language)

        user_desc['mail_address'] = request['mail_address']

        template_vars = {
            'type': 'email_validation',
            'user': user_desc,
            'new_email_address': request['mail_address'],
            'validation_token': user.change_email_token,
            'node': db_admin_serialize_node(session, tid, user.language),
            'notification': db_get_notification(session, tid, user.language)
        }

        State.format_and_send_mail(session, tid, user_desc['mail_address'], template_vars)

    parse_pgp_options(user, request)

    return user


@transact
def update_user_settings(session, tid, user_session, request, language):
    """
    Transaction for updating an existing user

    :param session: An ORM session
    :param tid: A tenant ID
    :param user_session: A session of the user invoking the transaction
    :param request: A user request data
    :param language: A language to be used when serializing the user
    :return: A serialization of user model
    """
    user = db_user_update_user(session, tid, user_session, request)

    return serialize_user(session, user, language)


class UserInstance(BaseHandler):
    """
    Handler that enables users to update their own setings
    """
    check_roles = 'user'
    invalidate_cache = True

    def get(self):
        return get_user(self.session.user_tid,
                        self.session.user_id,
                        self.request.language)

    def put(self):
        request = self.validate_request(self.request.content.read(), requests.UserUserDesc)

        return update_user_settings(self.session.user_tid,
                                    self.session,
                                    request,
                                    self.request.language)
