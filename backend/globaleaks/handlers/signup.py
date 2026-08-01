import json
from datetime import timedelta

from globaleaks import models
from globaleaks.db import db_refresh_tenant_cache
from globaleaks.handlers.admin.node import db_admin_serialize_node
from globaleaks.handlers.admin.notification import db_get_notification
from globaleaks.handlers.admin.tenant import db_create as db_create_tenant, db_wizard
from globaleaks.handlers.admin.user import db_get_users
from globaleaks.handlers.base import BaseHandler
from globaleaks.models import serializers
from globaleaks.models.config import ConfigFactory, db_get_signup_idp_config, db_get_signup_profile, db_set_config_variable
from globaleaks.models.enums import EnumSubscriberStatus
from globaleaks.orm import db_del, transact
from globaleaks.rest import requests, errors
from globaleaks.state import State
from globaleaks.utils.crypto import generateRandomKey, generateRandomPassword, GCE
from globaleaks.utils.oidc import extract_bearer_token
from globaleaks.utils.utility import datetime_now


def db_verify_signup_token(session, tid, bearer_token):
    """
    Verify the OIDC access token carried by a signup request

    The token is validated against the IdP inherited from the profile
    configured for the tenants created via signup.

    :param session: An ORM session
    :param tid: The tenant ID of the tenant handling the signups
    :param bearer_token: The OIDC access token carried by the request
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
    :param bearer_token: The OIDC access token carried by the request
    """
    config = ConfigFactory(session, 1)

    if not config.get_val('enable_signup'):
        raise errors.ForbiddenOperation

    oidc_token = db_verify_signup_token(session, 1, bearer_token)

    invite = None
    invited_tenant = None
    invite_token = request['token']

    if invite_token:
        ret = session.query(models.Subscriber, models.Tenant) \
            .filter(models.Subscriber.activation_token == invite_token,
                    models.Subscriber.state == EnumSubscriberStatus.invited.value,
                    models.Tenant.id == models.Subscriber.tid).one_or_none()

        if ret is None:
            raise errors.ForbiddenOperation

        invite, invited_tenant = ret

        if invite.registration_date < datetime_now() - timedelta(hours=24):
            db_del(session, models.Tenant, models.Tenant.id == invited_tenant.id)
            raise errors.ForbiddenOperation

        request['subdomain'] = ''
        request['organization_name'] = invite.organization_name
        request['organization_tax_code'] = ''
        request['organization_vat_code'] = ''
        request['organization_location'] = ''
    elif config.get_val('signup_invite_only'):
        raise errors.ForbiddenOperation
    elif not request['subdomain']:
        raise errors.InputValidationError

    if request['subdomain'] and request['subdomain'] + "." + config.get_val('rootdomain') == config.get_val('hostname'):
        raise errors.ForbiddenOperation

    request['activation_token'] = generateRandomKey()
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

    db_del(session, models.Tenant, models.Tenant.id.in_(tids))

    active = invite is not None or config.get_val('signup_auto_authorize')
    if invite is not None:
        tenant = invited_tenant
        tenant.active = active

        signup = invite
        for key in request:
            if key != 'subdomain' and hasattr(signup, key):
                setattr(signup, key, request[key])
        db_set_config_variable(session, tenant.id, 'subdomain', request['subdomain'])
        signup.state = EnumSubscriberStatus.invited.value
    else:
        tenant = db_create_tenant(session, {'active': active,
                                            'name': request['organization_name'] or request['subdomain'],
                                            'subdomain': request['subdomain'],
                                            'profile': db_get_signup_profile(session, 1)})

        signup = models.Subscriber(request)

        signup.tid = tenant.id

        session.add(signup)

    session.flush()

    if active:
        db_signup_activation(session, request['activation_token'], '', language, oidc_token)
        return

    # Notify instance administrators that a new platform is waiting for approval.

    signup_dict = serializers.serialize_signup(signup)

    for user_desc in db_get_users(session, 1, 'admin'):
        template_vars = {
            'type': 'admin_signup_alert',
            'node': db_admin_serialize_node(session, 1, user_desc['language']),
            'notification': db_get_notification(session, 1, user_desc['language']),
            'user': user_desc,
            'signup': signup_dict
        }

        State.format_and_send_mail(session, 1, user_desc['mail_address'], template_vars)


def db_signup_activation(session, token, hostname, language, idp_claims=None):
    """
    Transaction registering the activation of a platform registered via signup

    :param session: An ORM session
    :param token: A activation token
    :param hostname: The choosen hostname
    :param language: A language of the request
    :param idp_claims: IDP user claims for autofilling data
    """
    config = ConfigFactory(session, 1)

    if not config.get_val('enable_signup'):
        raise errors.ForbiddenOperation

    if not token:
        # An empty token would match subscribers whose activation token has
        # been voided upon activation, reactivating them.
        return {}

    ret = session.query(models.Subscriber, models.Tenant) \
                 .filter(models.Subscriber.activation_token == token,
                         models.Tenant.id == models.Subscriber.tid).one_or_none()

    if ret is None:
        return {}

    signup, tenant = ret[0], ret[1]

    tenant.active = True

    signup.activation_token = None

    if idp_claims and not signup.name:
        signup.name = idp_claims['given_name'] if 'given_name' in idp_claims else signup.name or ''
    if idp_claims and not signup.surname:
        signup.surname = idp_claims['family_name'] if 'family_name' in idp_claims else signup.surname or ''

    node_name = signup.organization_name or signup.subdomain

    # The IdP configuration is not copied on the created tenant as it is
    # inherited from the profile assigned to the tenants created via signup
    node = ConfigFactory(session, tenant.id)

    salt = node.get_val('receipt_salt')

    # Read the tenant specific value (inherited from the tenant profile)
    # falling back on the root tenant configuration set via Settings/Advanced
    default_user_profile = node.get_val('default_user_profile') or config.get_val('default_user_profile')

    default_role = ''
    default_profile_id = ''
    if default_user_profile in ('admin', 'analyst', 'custodian', 'recipient'):
        # Role keyword: create the user with the given role and a
        # standard per-user profile
        default_role = 'receiver' if default_user_profile == 'recipient' else default_user_profile
    elif default_user_profile and default_user_profile != 'none':
        # Profile reference: create the user with the role and profile
        # of the referenced user profile
        default_profile = session.query(models.UserProfile).filter(models.UserProfile.id == default_user_profile).one_or_none()
        if default_profile is None:
            raise errors.InputValidationError

        default_role = default_profile.role
        default_profile_id = default_profile.id

    if not default_role:
        skip_admin_account_creation = True
        skip_recipient_account_creation = True
        skip_default_account_creation = True
        default_username = ''
        admin_password = admin_key = ''
        receiver_password = receiver_key = ''
        generic_password = ''
        default_key = ''
    else:
        default_username = 'recipient' if default_role == 'receiver' else default_role
        default_password = generateRandomPassword(16)
        default_salt = GCE.generate_salt(salt + ":" + default_username)
        default_key = GCE.derive_key(default_password, default_salt).encode()

        skip_admin_account_creation = default_role != 'admin'
        skip_recipient_account_creation = default_role != 'receiver'
        skip_default_account_creation = default_role in ('admin', 'receiver')

        admin_password = default_password if default_role == 'admin' else ''
        admin_key = default_key if default_role == 'admin' else ''
        receiver_password = default_password if default_role == 'receiver' else ''
        receiver_key = default_key if default_role == 'receiver' else ''
        generic_password = default_password if not skip_default_account_creation else ''

    wizard = {
        'node_language': signup.language,
        'node_name': node_name,
        'admin_username': 'admin',
        'admin_name': signup.name + ' ' + signup.surname,
        'admin_password': admin_key,
        'admin_mail_address': signup.email,
        'admin_profile_id': default_profile_id if default_role == 'admin' else '',
        'admin_escrow': config.get_val('escrow'),
        'receiver_username': 'recipient',
        'receiver_name': signup.name + ' ' + signup.surname,
        'receiver_password': receiver_key,
        'receiver_mail_address': signup.email,
        'receiver_profile_id': default_profile_id if default_role == 'receiver' else '',
        'default_username': default_username,
        'default_name': signup.name + ' ' + signup.surname,
        'default_password': generic_password and default_key or '',
        'default_mail_address': signup.email,
        'default_role': default_role,
        'default_profile_id': default_profile_id if not skip_default_account_creation else '',
        'profile': 'default',
        'skip_admin_account_creation': skip_admin_account_creation,
        'skip_recipient_account_creation': skip_recipient_account_creation,
        'skip_default_account_creation': skip_default_account_creation,
        'enable_developers_exception_notification': True
    }

    password_recipient = receiver_password or generic_password
    signup_user_role = 'recipient' if default_role == 'receiver' else default_role
    signup_user_username = default_username

    db_wizard(session, signup.tid, hostname, wizard)

    template_vars = {
        'type': 'activation',
        'node': db_admin_serialize_node(session, 1, language),
        'notification': db_get_notification(session, 1, language),
        'signup': serializers.serialize_signup(signup),
        'password_admin': admin_password,
        'password_recipient': password_recipient,
        'signup_user_role': signup_user_role,
        'signup_user_username': signup_user_username
    }

    State.format_and_send_mail(session, 1, signup.email, template_vars)

    db_refresh_tenant_cache(session, tenant.id)


@transact
def signup_activation(session, token, hostname, language):
    return db_signup_activation(session, token, hostname, language)


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
        return signup_activation(token, self.request.hostname, self.request.language)
