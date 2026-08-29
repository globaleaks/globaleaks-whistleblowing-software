import json
from datetime import timedelta

from globaleaks import models
from globaleaks.db import db_refresh_tenant_cache
from globaleaks.handlers.admin.node import db_admin_serialize_node
from globaleaks.handlers.admin.notification import db_get_notification
from globaleaks.handlers.admin.tenant import db_create as db_create_tenant, db_wizard
from globaleaks.handlers.admin.user import db_get_users
from globaleaks.handlers.admin.user_profile import db_resolve_default_user_profile
from globaleaks.handlers.base import BaseHandler
from globaleaks.models import serializers
from globaleaks.models.config import ConfigFactory, db_get_signup_idp_config, db_get_signup_profile, db_set_config_variable
from globaleaks.models.enums import EnumSubscriberStatus
from globaleaks.models.exchanges import db_forget_exchanges
from globaleaks.orm import db_del, db_log, transact
from globaleaks.rest import requests, errors
from globaleaks.state import State
from globaleaks.utils.crypto import generateRandomKey, generateRandomPassword, sha256, GCE
from globaleaks.utils.log import log
from globaleaks.utils.oidc import extract_bearer_token
from globaleaks.utils.utility import datetime_now


def db_verify_signup_token(session, tid, bearer_token):
    """
    Verify the OIDC ID token carried by a signup request

    :param session: An ORM session
    :param tid: The tenant ID of the tenant handling the signups
    :param bearer_token: The OIDC ID token carried by the request
    :return: The claims of the verified token or None if no IdP is configured
    """
    idp_config = db_get_signup_idp_config(session, tid)

    if not idp_config['signup_idp']:
        return None

    if not bearer_token:
        raise errors.ForbiddenOperation

    try:
        return State.oidcauth.verify_token(bearer_token,
                                           idp_config['signup_idp_issuer'],
                                           idp_config['signup_idp_client_id'])
    except:
        raise errors.ForbiddenOperation


@transact
def signup(session, request, language, bearer_token=None):
    """
    Transact handling the registration of a new signup

    :param session: An ORM session
    :param request: A user request
    :param language: A language of the request
    :param bearer_token: The OIDC ID token carried by the request
    """
    config = ConfigFactory(session, 1)

    if not config.get_val('enable_signup'):
        raise errors.ForbiddenOperation

    oidc_token = db_verify_signup_token(session, 1, bearer_token)

    # The user data always come from the registration; with an identity provider they come from its
    # claims, validated as any other input
    if oidc_token:
        for claim, key in [('given_name', 'name'),
                           ('family_name', 'surname')]:
            value = oidc_token.get(claim)
            if isinstance(value, str) and BaseHandler.validate_regexp(value, requests.SignupDesc[key]):
                request[key] = value

    if not config.get_val('signup_request_subdomain'):
        request['subdomain'] = ''

    invite = None
    invited_tenant = None
    invite_token = request['token']

    if invite_token:
        ret = session.query(models.Subscriber, models.Tenant) \
            .filter(models.Subscriber.activation_token == sha256(invite_token).decode(),
                    models.Subscriber.state == EnumSubscriberStatus.invited.value,
                    models.Tenant.id == models.Subscriber.tid).one_or_none()

        if ret is None:
            raise errors.ForbiddenOperation

        invite, invited_tenant = ret

        if invite.registration_date < datetime_now() - timedelta(hours=24):
            db_forget_exchanges(session, [invited_tenant.id])
            db_del(session, models.Tenant, models.Tenant.id == invited_tenant.id)
            raise errors.ForbiddenOperation

        # The organization is the invited one: taken from the invitation, never from the request
        request['subdomain'] = ''
        request['organization_name'] = invite.organization_name
        request['organization_email'] = invite.organization_email
    elif config.get_val('signup_invite_only'):
        raise errors.ForbiddenOperation
    elif config.get_val('signup_request_subdomain') and not request['subdomain']:
        raise errors.InputValidationError

    # The organization name is mandatory; on an invited registration it is the invited one
    if not request['organization_name']:
        raise errors.InputValidationError

    # The organization email is known only through the invitation
    if invite is None:
        request['organization_email'] = ''

    # Details not asked for are dropped, so a client cannot plant them
    for var, key in [('signup_request_location', 'organization_location'),
                     ('signup_request_phone', 'phone'),
                     ('signup_request_tax_code', 'organization_tax_code'),
                     ('signup_request_vat_code', 'organization_vat_code')]:
        if not config.get_val(var):
            request[key] = ''
        elif not request[key]:
            raise errors.InputValidationError

    if request['subdomain'] and request['subdomain'] + "." + config.get_val('rootdomain') == config.get_val('hostname'):
        raise errors.ForbiddenOperation

    activation_token = generateRandomKey()
    request['activation_token'] = sha256(activation_token).decode()
    request['language'] = language

    request['organization_tax_code'] = request['organization_tax_code'] or None
    request['organization_vat_code'] = request['organization_vat_code'] or None

    # Delete the tenants created for the same subdomain that have still not been activated
    # Ticket reference: https://github.com/globaleaks/globaleaks-whistleblowing-software/issues/2640
    tids = []
    if request['subdomain']:
        tids = [tid for (tid,) in session.query(models.Tenant.id).filter(
            models.Subscriber.subdomain == request['subdomain'],
            models.Subscriber.activation_token.isnot(None),
            models.Tenant.id == models.Subscriber.tid
        ).all()]

    db_forget_exchanges(session, tids)
    db_del(session, models.Tenant, models.Tenant.id.in_(tids))

    # The tenant is created now; it is activated at once only with the automatic authorization,
    # otherwise when an administrator authorizes it
    active = config.get_val('signup_auto_authorize')

    if invite is not None:
        tenant = invited_tenant

        signup = invite
        for key in request:
            if key != 'subdomain' and hasattr(signup, key):
                setattr(signup, key, request[key])
        db_set_config_variable(session, tenant.id, 'subdomain', request['subdomain'])
        signup.state = EnumSubscriberStatus.invited.value
    else:
        tenant = db_create_tenant(session, {'active': False,
                                            'name': request['organization_name'] or request['subdomain'] or request['email'],
                                            'subdomain': request['subdomain'],
                                            'profile': db_get_signup_profile(session, 1)})

        signup = models.Subscriber(request)

        # The subdomain column is unique: a placeholder when none is asked for
        signup.subdomain = request['subdomain'] or generateRandomKey()

        signup.tid = tenant.id

        session.add(signup)

    session.flush()

    # Logged on the root tenant, which holds the events of the accreditation
    db_log(session, tid=1, type='signup', object_id=signup.id, data={'tid': tenant.id})

    if active:
        db_signup_activation(session, activation_token, language, oidc_token)
    else:
        # The notification carries the raw token; the database stores its hash
        signup_dict = serializers.serialize_signup(signup)
        signup_dict['activation_token'] = activation_token

        notif = State.tenants[1].cache.notification
        if not notif or notif.enable_admin_notification_emails:
            for user_desc in db_get_users(session, 1, 'admin'):
                # Do not generate emails if the user has disabled notifications
                if not user_desc['notification']:
                    log.debug("Discarding emails for %s due to user's preference.", user_desc['id'])
                    continue

                template_vars = {
                    'type': 'admin_signup_alert',
                    'node': db_admin_serialize_node(session, 1, user_desc['language']),
                    'notification': db_get_notification(session, 1, user_desc['language']),
                    'user': user_desc,
                    'signup': signup_dict
                }

                State.format_and_send_mail(session, 1, user_desc['mail_address'], template_vars)

        # Confirmed on its own unless activated at once, when the confirmation of the activation is
        # the only one sent
        signup_dict = serializers.serialize_signup(signup)
        signup_dict['activation_token'] = ''

        for address in signup_notification_addresses(signup):
            template_vars = {
                'type': 'signup',
                'node': db_admin_serialize_node(session, 1, language),
                'notification': db_get_notification(session, 1, language),
                'signup': signup_dict
            }

            State.format_and_send_mail(session, 1, address, template_vars)


def signup_notification_addresses(signup):
    """
    Return the addresses to be notified about a registration: the user and,

    :param signup: The subscriber of the registration
    :return: The list of the addresses to be notified
    """
    addresses = [signup.email]

    if signup.state is not None and signup.organization_email and signup.organization_email != signup.email:
        addresses.append(signup.organization_email)

    return addresses


def db_signup_provision(session, signup, language, username, password, idp_claims=None):
    """
    Transaction provisioning the accounts of a platform registered via signup

    :param session: An ORM session
    :param signup: The subscriber of the registration
    :param language: A language of the request
    :param username: The username to be assigned to the account
    :param password: The generated password protecting the account
    :param idp_claims: The claims of the identity that performed the registration
    :return: The role and the username of the provisioned account
    """
    config = ConfigFactory(session, 1)

    # The IdP configuration is inherited from the signup profile, not copied
    node = ConfigFactory(session, signup.tid)

    # The configured subdomain is empty when none is asked for; the subscriber holds a placeholder
    node_name = signup.organization_name or node.get_val('subdomain') or signup.email

    salt = node.get_val('receipt_salt')

    default_role, default_profile_id = db_resolve_default_user_profile(session, signup.tid)

    # Without a default user profile the user is the administrator of its own platform
    if not default_role:
        default_role = 'admin'
        default_profile_id = ''

    default_username = username
    default_salt = GCE.generate_salt(salt + ":" + default_username)

    default_key = GCE.derive_key(password, default_salt).encode()

    skip_admin_account_creation = default_role != 'admin'
    skip_recipient_account_creation = default_role != 'receiver'
    skip_default_account_creation = default_role in ('admin', 'receiver')

    admin_key = default_key if default_role == 'admin' else ''
    receiver_key = default_key if default_role == 'receiver' else ''

    wizard = {
        'node_language': signup.language,
        'node_name': node_name,
        'admin_username': default_username or 'admin',
        'admin_name': signup.name + ' ' + signup.surname,
        'admin_password': admin_key,
        'admin_mail_address': signup.email,
        'admin_profile_id': default_profile_id if default_role == 'admin' else '',
        'admin_escrow': config.get_val('escrow'),
        'receiver_username': default_username or 'recipient',
        'receiver_name': signup.name + ' ' + signup.surname,
        'receiver_password': receiver_key,
        'receiver_mail_address': signup.email,
        'receiver_profile_id': default_profile_id if default_role == 'receiver' else '',
        'default_username': default_username,
        'default_name': signup.name + ' ' + signup.surname,
        'default_password': default_key if not skip_default_account_creation else '',
        'default_mail_address': signup.email,
        'default_role': default_role,
        'default_profile_id': default_profile_id if not skip_default_account_creation else '',
        # The account is bound to the identity that performed the registration
        'idp_id': idp_claims.get('sub', '') if idp_claims else '',
        'profile': 'default',
        'skip_admin_account_creation': skip_admin_account_creation,
        'skip_recipient_account_creation': skip_recipient_account_creation,
        'skip_default_account_creation': skip_default_account_creation,
        'enable_developers_exception_notification': True
    }

    db_wizard(session, signup.tid, '', wizard)

    # Bound to the registration for the notifications; the provisioned password must be changed on
    # first login
    user = session.query(models.User) \
                  .filter(models.User.tid == signup.tid,
                          models.User.username == default_username).one_or_none()

    if user is not None:
        signup.user_id = user.id

    return default_role, default_username


def db_signup_activation(session, token, language, idp_claims=None):
    """
    Transaction registering the activation of a platform registered via signup

    :param session: An ORM session
    :param token: A activation token
    :param language: A language of the request
    """
    if not token:
        # An empty token would match subscribers whose activation token has
        # been voided upon activation, reactivating them.
        return {}

    return db_signup_activation_by_hash(session, sha256(token).decode(), language, idp_claims)


def db_signup_activation_by_hash(session, token_hash, language, idp_claims=None):
    """
    Transaction registering the activation of a platform via the hash of its
    """
    config = ConfigFactory(session, 1)

    if not config.get_val('enable_signup'):
        raise errors.ForbiddenOperation

    if not token_hash:
        return {}

    ret = session.query(models.Subscriber, models.Tenant) \
                 .filter(models.Subscriber.activation_token == token_hash,
                         models.Tenant.id == models.Subscriber.tid).one_or_none()

    if ret is None:
        return {}

    signup, tenant = ret[0], ret[1]

    tenant.active = True

    signup.activation_token = None

    # Provisioned on activation with a generated password and the email as username
    default_password = generateRandomPassword(16)
    default_role, default_username = db_signup_provision(session, signup, language, signup.email, default_password, idp_claims)

    signup_dict = serializers.serialize_signup(signup)

    # Confirmed to the user and, on an invited registration, to the invitation address; once when
    # they match
    for address in signup_notification_addresses(signup):
        template_vars = {
            'type': 'activation',
            'node': db_admin_serialize_node(session, 1, language),
            'notification': db_get_notification(session, 1, language),
            'signup': signup_dict,
            'password': default_password if address == signup.email else '',
            'password_admin': '',
            'password_recipient': '',
            'signup_user_role': default_role,
            'signup_user_username': default_username
        }

        State.format_and_send_mail(session, 1, address, template_vars)

    db_log(session, tid=1, type='activate_signup', object_id=signup.id, data={'tid': tenant.id})

    db_refresh_tenant_cache(session, tenant.id)


@transact
def signup_activation(session, token, language):
    return db_signup_activation(session, token, language)


class Signup(BaseHandler):
    """
    Signup handler responsible of registration
    """
    check_roles = 'any'
    root_tenant_only = True

    def post(self):
        raw_request = self.request.content.read()
        try:
            parsed_request = json.loads(raw_request)
        except:
            raise errors.InputValidationError

        token = ''
        if 'token' in parsed_request:
            token = parsed_request['token']
        request = self.validate_request(parsed_request, requests.SignupDesc)

        request['client_ip_address'] = self.request.client_ip
        request['client_user_agent'] = self.request.client_ua
        request['token'] = token

        return signup(request, self.request.language, extract_bearer_token(self.request))


class SignupActivation(BaseHandler):
    """
    Signup handler responsible of activation
    """
    check_roles = 'any'
    root_tenant_only = True
    invalidate_cache = True

    def post(self, token):
        return signup_activation(token, self.request.language)
