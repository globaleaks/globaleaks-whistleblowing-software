# -*- coding: utf-8
#
# Handlers implementing platform signup
from sqlalchemy import not_
from twisted.internet.threads import deferToThread
from globaleaks import models
from globaleaks.db import sync_refresh_tenant_cache
from globaleaks.handlers.admin.node import db_admin_serialize_node
from globaleaks.handlers.admin.notification import db_get_notification
from globaleaks.handlers.admin.tenant import db_create as db_create_tenant
from globaleaks.handlers.admin.user import db_get_users
from globaleaks.handlers.base import BaseHandler
from globaleaks.handlers.wizard import db_wizard
from globaleaks.models import serializers
from globaleaks.models.config import ConfigFactory
from globaleaks.orm import db_del, transact
from globaleaks.rest import requests, errors
from globaleaks.state import State
from globaleaks.utils.crypto import generateRandomKey, generateRandomPassword


@transact
def signup(session, request, language):
    """
    Transact handling the registration of a new signup

    :param session: An ORM session
    :param request: A user request
    :param language: A language of the request
    """
    config = ConfigFactory(session, 1)

    if not config.get_val('enable_signup'):
        raise errors.ForbiddenOperation

    if request['subdomain'] + "." + config.get_val('rootdomain') == config.get_val('hostname'):
        raise errors.ForbiddenOperation

    request['activation_token'] = generateRandomKey()
    request['language'] = language

    request['organization_tax_code'] = request['organization_tax_code'] or None
    request['organization_vat_code'] = request['organization_vat_code'] or None

    # Delete the tenants created for the same subdomain that have still not been activated
    # Ticket reference: https://github.com/globaleaks/globaleaks-whistleblowing-software/issues/2640
    subquery = session.query(models.Tenant.id) \
                      .filter(models.Subscriber.subdomain == request['subdomain'],
                              not_(models.Subscriber.activation_token.is_(None)),
                              models.Tenant.id == models.Subscriber.tid) \
                      .subquery()

    db_del(session, models.Tenant, models.Tenant.id.in_(subquery))

    tenant = db_create_tenant(session, {'active': False,
                                        'name': request['subdomain'],
                                        'subdomain': request['subdomain'],
                                        'mode': config.get_val('mode')})

    signup = models.Subscriber(request)

    signup.tid = tenant.id

    session.add(signup)

    session.flush()

    # We need to send two emails
    #
    # The first one is sent to the platform owner with the activation email.
    #
    # The second goes to the instance administrators notifying them that a new
    # platform has been added.

    signup_dict = serializers.serialize_signup(signup)

    # Email 1 - Activation Link
    template_vars = {
        'type': 'signup',
        'node': db_admin_serialize_node(session, 1, language),
        'notification': db_get_notification(session, 1, language),
        'signup': signup_dict
    }

    State.format_and_send_mail(session, 1, signup.email, template_vars)

    # Email 2 - Admin Notification
    for user_desc in db_get_users(session, 1, 'admin'):
        template_vars = {
            'type': 'admin_signup_alert',
            'node': db_admin_serialize_node(session, 1, user_desc['language']),
            'notification': db_get_notification(session, 1, user_desc['language']),
            'user': user_desc,
            'signup': signup_dict
        }

        State.format_and_send_mail(session, 1, user_desc['mail_address'], template_vars)


@transact
def signup_activation(session, token, hostname, language):
    """
    Transaction registering the activation of a platform registered via signup

    :param session: An ORM session
    :param token: A activation token
    :param hostname: The choosen hostname
    :param language: A language of the request
    """
    config = ConfigFactory(session, 1)

    if not config.get_val('enable_signup'):
        raise errors.ForbiddenOperation

    ret = session.query(models.Subscriber, models.Tenant) \
                 .filter(models.Subscriber.activation_token == token,
                         models.Tenant.id == models.Subscriber.tid).one_or_none()

    if ret is None:
        return {}

    signup, tenant = ret[0], ret[1]

    tenant.active = True

    signup.activation_token = None

    password_admin = generateRandomPassword(16)
    password_receiver = generateRandomPassword(16)

    node_name = signup.organization_name or signup.subdomain

    wizard = {
        'node_language': signup.language,
        'node_name': node_name,
        'admin_username': 'admin',
        'admin_name': signup.name + ' ' + signup.surname,
        'admin_password': password_admin,
        'admin_mail_address': signup.email,
        'admin_escrow': config.get_val('escrow'),
        'receiver_username': 'recipient',
        'receiver_name': signup.name + ' ' + signup.surname,
        'receiver_password': password_receiver,
        'receiver_mail_address': signup.email,
        'profile': 'default',
        'skip_admin_account_creation': False,
        'skip_recipient_account_creation': False,
        'enable_developers_exception_notification': True
    }

    db_wizard(session, signup.tid, hostname, wizard)

    template_vars = {
        'type': 'activation',
        'node': db_admin_serialize_node(session, 1, language),
        'notification': db_get_notification(session, 1, language),
        'signup': serializers.serialize_signup(signup),
        'password_admin': wizard['admin_password'],
        'password_recipient': wizard['receiver_password']
    }

    State.format_and_send_mail(session, 1, signup.email, template_vars)

    deferToThread(sync_refresh_tenant_cache, tenant)


class Signup(BaseHandler):
    """
    Signup handler responsible of registration
    """
    check_roles = 'any'
    root_tenant_only = True

    def post(self):
        request = self.validate_request(self.request.content.read(),
                                        requests.SignupDesc)

        request['client_ip_address'] = self.request.client_ip
        request['client_user_agent'] = self.request.client_ua

        return signup(request, self.request.language)


class SignupActivation(BaseHandler):
    """
    Signup handler responsible of activation
    """
    check_roles = 'any'
    root_tenant_only = True
    invalidate_cache = True

    def post(self, token):
        return signup_activation(token, self.request.hostname, self.request.language)
