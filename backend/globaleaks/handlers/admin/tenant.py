# -*- coding: UTF-8
from nacl.encoding import Base64Encoder
from sqlalchemy import and_, func, or_

from globaleaks import models
from globaleaks.db.appdata import load_appdata, db_load_defaults
from globaleaks.handlers.admin.context import db_create_context
from globaleaks.handlers.admin.node import db_update_enabled_languages
from globaleaks.handlers.admin.user import db_create_user
from globaleaks.handlers.base import BaseHandler
from globaleaks.models import config, profiles, serializers
from globaleaks.models.config import db_get_configs, \
    db_get_config_variable, db_set_config_variable
from globaleaks.orm import db_del, db_get, transact, tw
from globaleaks.rest import errors, requests
from globaleaks.utils.crypto import GCE
from globaleaks.utils.log import log
from globaleaks.utils.sock import isIPAddress
from globaleaks.utils.tls import gen_selfsigned_certificate


def db_initialize_tenant_submission_statuses(session, tid):
    """
    Transaction for initializing the submission statuses of a tenant

    :param session: An ORM session
    :param tid: A tenant ID
    """
    for s in [{'tid': tid, 'id': 'new', 'label': {'en': 'New'}, 'tip_timetolive': 0},
              {'tid': tid, 'id': 'opened', 'label': {'en': 'Opened'}, 'tip_timetolive': 0},
              {'tid': tid, 'id': 'closed', 'label': {'en': 'Closed'}, 'tip_timetolive': 0}]:
        session.add(models.SubmissionStatus(s))


def db_subdomain_in_use(session, subdomain, excluded_tids=None):
    """
    Return whether the given subdomain is already taken by an existing tenant,
    either as its configured subdomain or as the leading label of its hostname.

    :param session: An ORM session
    :param subdomain: The subdomain to look up
    :param excluded_tids: An optional iterable of tenant ids to ignore
    :return: True if the subdomain is already in use, False otherwise
    """
    if not subdomain:
        return False

    # Config.value stores JSON, so string values are quoted; substr is used
    # because the ORM SQL authorizer does not permit LIKE
    hostname_prefix = '"' + subdomain + '.'

    query = session.query(models.Config.tid).filter(
        or_(and_(models.Config.var_name == 'subdomain',
                 models.Config.value == subdomain),
            and_(models.Config.var_name == 'hostname',
                 func.substr(models.Config.value, 1, len(hostname_prefix)) == hostname_prefix)))

    if excluded_tids:
        query = query.filter(models.Config.tid.notin_(list(excluded_tids)))

    return session.query(query.exists()).scalar()


def db_set_tenant_config(session, tid, desc):
    """
    Set the tenant settings shared by the creation and update paths,
    enforcing global subdomain uniqueness.

    :param session: An ORM session
    :param tid: The tenant ID being configured
    :param desc: A descriptor providing 'mode', 'name' and 'subdomain'
    """
    if db_subdomain_in_use(session, desc['subdomain'], excluded_tids=[tid]):
        raise errors.ForbiddenOperation

    for var in ['mode', 'name', 'subdomain']:
        db_set_config_variable(session, tid, var, desc[var])


def db_create(session, desc):
    t = models.Tenant()

    t.active = desc['active']

    session.add(t)

    # required to generate the tenant id
    session.flush()

    appdata = load_appdata()

    if t.id == 1:
        language = 'en'
        db_load_defaults(session)
    else:
        language = db_get_config_variable(session, 1, 'default_language')

    models.config.initialize_config(session, t.id, desc['mode'])

    if t.id == 1:
        key, cert = gen_selfsigned_certificate()
        db_set_config_variable(session, 1, 'https_selfsigned_key', key)
        db_set_config_variable(session, 1, 'https_selfsigned_cert', cert)

    db_set_tenant_config(session, t.id, desc)

    models.config.add_new_lang(session, t.id, language, appdata)

    db_initialize_tenant_submission_statuses(session, t.id)

    return t


@transact
def create(session, desc, *args, **kwargs):
    t = db_create(session, desc, *args, **kwargs)

    return serializers.serialize_tenant(session, t)


@transact
def create_and_initialize(session, desc, *args, **kwargs):
    t = db_create(session, desc, *args, **kwargs)

    wizard = {
        'node_language': 'en',
        'node_name': desc['name'],
        'profile': 'default',
        'skip_admin_account_creation': True,
        'skip_recipient_account_creation': True,
        'enable_developers_exception_notification': True
    }

    db_wizard(session, t.id, '', wizard)

    return serializers.serialize_tenant(session, t)


def db_get_tenant_list(session):
    ret = []

    configs = db_get_configs(session, 'tenant')

    for t, s in session.query(models.Tenant, models.Subscriber).join(models.Subscriber, models.Subscriber.tid == models.Tenant.id, isouter=True):
        tenant_dict = serializers.serialize_tenant(session, t, configs[t.id])
        if s:
            tenant_dict['signup'] = serializers.serialize_signup(s)

        ret.append(tenant_dict)

    return ret


@transact
def get_tenant_list(session):
    return db_get_tenant_list(session)


@transact
def get(session, tid):
    return serializers.serialize_tenant(session, db_get(session, models.Tenant, models.Tenant.id == tid))


def db_wizard(session, tid, hostname, request):
    """
    Transaction for the handling of wizard request

    :param session: An ORM session
    :param tid: A tenant ID
    :param hostname: The hostname to be configured
    :param request: A user request
    """
    admin_password = receiver_password = ''

    language = request['node_language']

    root_tenant_node = config.ConfigFactory(session, 1)

    if tid == 1:
        node = root_tenant_node
        encryption = True
        escrow = request['admin_escrow']
    else:
        node = config.ConfigFactory(session, tid)
        encryption = root_tenant_node.get_val('encryption')
        escrow = root_tenant_node.get_val('crypto_escrow_pub_key') != ''

    if node.get_val('wizard_done'):
        log.err("DANGER: Wizard already initialized!", tid=tid)
        raise errors.ForbiddenOperation

    db_update_enabled_languages(session, tid, [language], language)

    node.set_val('encryption', encryption)

    node.set_val('name', request['node_name'])
    node.set_val('default_language', language)
    node.set_val('wizard_done', True)
    node.set_val('enable_developers_exception_notification', request['enable_developers_exception_notification'])

    if tid == 1 and not isIPAddress(hostname):
       node.set_val('hostname', hostname)

    profiles.load_profile(session, tid, request['profile'])

    if encryption and escrow:
        crypto_escrow_prv_key, crypto_escrow_pub_key = GCE.generate_keypair()

        node.set_val('crypto_escrow_pub_key', crypto_escrow_pub_key)

        if  tid != 1 and root_tenant_node.get_val('crypto_escrow_pub_key'):
            node.set_val('crypto_escrow_prv_key', Base64Encoder.encode(GCE.asymmetric_encrypt(root_tenant_node.get_val('crypto_escrow_pub_key'), crypto_escrow_prv_key)))

    if not request['skip_admin_account_creation']:
        admin_desc = models.User().dict(language)
        admin_desc['username'] = request['admin_username']
        admin_desc['name'] = request['admin_name']
        admin_desc['password'] = request['admin_password']
        admin_desc['mail_address'] = request['admin_mail_address']
        admin_desc['language'] = language
        admin_desc['role'] = 'admin'
        admin_desc['pgp_key_remove'] = False
        admin_user = db_create_user(session, tid, None, admin_desc, language)
        admin_user.password_change_needed = (tid != 1)

        if encryption and escrow:
            node.set_val('crypto_escrow_pub_key', crypto_escrow_pub_key)
            admin_user.crypto_escrow_prv_key = Base64Encoder.encode(GCE.asymmetric_encrypt(admin_user.crypto_pub_key, crypto_escrow_prv_key))

    if not request['skip_recipient_account_creation']:
        receiver_desc = models.User().dict(language)
        receiver_desc['username'] = request['receiver_username']
        receiver_desc['password'] = request['receiver_password']
        receiver_desc['name'] = request['receiver_name']
        receiver_desc['mail_address'] = request['receiver_mail_address']
        receiver_desc['language'] = language
        receiver_desc['role'] = 'receiver'
        receiver_desc['pgp_key_remove'] = False
        receiver_user = db_create_user(session, tid, None, receiver_desc, language)
        receiver_user.password_change_needed = (tid != 1)

    context_desc = models.Context().dict(language)
    context_desc['name'] = 'Default'
    context_desc['status'] = 'enabled'

    if not request['skip_recipient_account_creation']:
        context_desc['receivers'] = [receiver_user.id]

    context = db_create_context(session, tid, None, context_desc, language)

    # Root tenants initialization terminates here

    if tid == 1:
        return

    # Secondary tenants initialization starts here
    subdomain = node.get_val('subdomain')
    rootdomain = root_tenant_node.get_val('rootdomain')
    if subdomain and rootdomain:
        node.set_val('hostname', subdomain + "." + rootdomain)

    mode = node.get_val('mode')

    if mode != 'default':
        node.set_val('tor', False)

    if mode in ['wbpa']:
        node.set_val('simplified_login', True)

        for varname in ['anonymize_outgoing_connections',
                        'password_change_period',
                        'default_questionnaire']:
            node.set_val(varname, root_tenant_node.get_val(varname))

        context.questionnaire_id = root_tenant_node.get_val('default_questionnaire')

        # Set data retention policy to 12 months
        context.tip_timetolive = 365

        if not request['skip_recipient_account_creation']:
            receiver_user.can_edit_general_settings = True
            receiver_user.can_mask_information = False

            # Set the recipient name equal to the node name
            receiver_user.name = receiver_user.public_name = request['node_name']

@transact
def wizard(session, tid, hostname, request):
    return db_wizard(session, tid, hostname, request)


@transact
def update(session, tid, request):
    root_tenant_config = config.ConfigFactory(session, 1)

    t = db_get(session, models.Tenant, models.Tenant.id == tid)

    t.active = request['active']

    if request['subdomain'] + "." + root_tenant_config.get_val('rootdomain') == root_tenant_config.get_val('hostname'):
        raise errors.ForbiddenOperation

    db_set_tenant_config(session, tid, request)

    return serializers.serialize_tenant(session, t)


class TenantCollection(BaseHandler):
    check_roles = 'admin'
    root_tenant_only = True
    invalidate_cache = True

    def get(self):
        """
        Return the list of registered tenants
        """
        return get_tenant_list()

    def post(self):
        """
        Create a new tenant
        """
        request = self.validate_request(self.request.content.read(),
                                        requests.AdminTenantDesc)

        return create_and_initialize(request)


class TenantInstance(BaseHandler):
    check_roles = 'admin'
    root_tenant_only = True
    invalidate_cache = True

    def get(self, tid):
        return get(int(tid))

    def put(self, tid):
        """
        Update the specified tenant.
        """
        request = self.validate_request(self.request.content.read(),
                                        requests.AdminTenantDesc)

        return update(int(tid), request)

    def delete(self, tid):
        """
        Delete the specified tenant.
        """
        return tw(db_del, models.Tenant, models.Tenant.id == int(tid))
