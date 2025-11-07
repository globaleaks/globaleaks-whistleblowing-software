# -*- coding: UTF-8
import json
from nacl.encoding import Base64Encoder
from twisted.internet.defer import inlineCallbacks

from globaleaks import LANGUAGES_SUPPORTED_CODES, models
from globaleaks.db.appdata import load_appdata, db_load_defaults
from globaleaks.handlers.admin.context import db_create_context
from globaleaks.handlers.admin.node import db_update_enabled_languages
from globaleaks.handlers.admin.questionnaire import db_get_questionnaires, import_questionnaires
from globaleaks.handlers.admin.user import db_create_user
from globaleaks.handlers.base import BaseHandler
from globaleaks.handlers.user import user_permissions
from globaleaks.models import Config, EnabledLanguage, config, serializers
from globaleaks.models.config import db_get_configs, \
    db_get_config_variable, db_set_config_variable
from globaleaks.orm import db_del, db_get, transact, tw
from globaleaks.rest import errors, requests
from globaleaks.utils.crypto import GCE
from globaleaks.utils.log import log
from globaleaks.utils.sock import isIPAddress
from globaleaks.utils.tls import gen_selfsigned_certificate
from globaleaks.utils.utility import uuid4

DEFAULT_PROFILE_ID = 1000001


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


def get_tenant_id(session, isTenant, is_profile):
    id_key = 'counter_tenants' if isTenant and not is_profile else 'counter_profiles'
    tid = db_get_config_variable(session, 1, id_key)
    return id_key, tid


def calculate_tenant_id(tid, is_profile):
    return tid + 1


def db_create(session, desc, isTenant = True, **kwargs):
    is_profile = kwargs.get('is_profile', False)

    id_key, tid = get_tenant_id(session, isTenant, is_profile)

    tenant_id = calculate_tenant_id(tid, is_profile)

    t = models.Tenant()
    t.id = tenant_id
    t.active = desc['active']

    session.add(t)

    # required to generate the tenant id
    session.flush()

    language = db_get_config_variable(session, 1, 'default_language')

    if t.id < DEFAULT_PROFILE_ID: # ignore profiles
        session.add(EnabledLanguage({'tid': t.id, 'name': language}))

        models.config.initialize_config(session, t.id, desc)

        if t.id == 1:
            db_set_config_variable(session, 1, id_key, t.id)
            db_load_defaults(session)
            key, cert = gen_selfsigned_certificate()
            db_set_config_variable(session, 1, 'https_selfsigned_key', key)
            db_set_config_variable(session, 1, 'https_selfsigned_cert', cert)

        for var in ['mode', 'profile', 'subdomain']:
            db_set_config_variable(session, t.id, var, desc[var])

    elif t.id == DEFAULT_PROFILE_ID:
        appdata = load_appdata()
        for language in LANGUAGES_SUPPORTED_CODES:
            session.add(EnabledLanguage({'tid': t.id, 'name': language}))

        models.config.load_defaults(session, appdata)

    else:
        db_set_config_variable(session, t.id, 'uuid', uuid4())

    db_initialize_tenant_submission_statuses(session, t.id)

    db_set_config_variable(session, 1, id_key, t.id)
    db_set_config_variable(session, t.id, 'name', desc['name'])

    return t


@transact
def create(session, desc, *args, **kwargs):
    t = db_create(session, desc, *args, **kwargs)

    return serializers.serialize_tenant(session, t)


@transact
def is_profile_mapped(session, tid):
    if int(tid) > 1000001:
        return session.query(Config).filter_by(value=tid, var_name='profile').first() is not None
    else:
        return False

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

    for t, s in session.query(models.Tenant, models.Subscriber).join(models.Subscriber, models.Subscriber.tid == models.Tenant.id, isouter=True).filter(models.Tenant.id != DEFAULT_PROFILE_ID):
        tenant_dict = serializers.serialize_tenant(session, t, configs[t.id])
        if s:
            tenant_dict['signup'] = serializers.serialize_signup(s)

        ret.append(tenant_dict)

    return ret


@transact
def get_tenant_list(session):
    return db_get_tenant_list(session)


@transact
def get(session, self, tid):
    tenant = db_get(session, models.Tenant, models.Tenant.id == tid)
    configs = session.query(models.Config).filter(models.Config.tid == tid).all()
    config_langs = session.query(models.ConfigL10N).filter(models.ConfigL10N.tid == tid).all()
    user_profiles = session.query(models.UserProfile).filter(models.UserProfile.tid == tid).all()
    questionnaires = db_get_questionnaires(session, tid, self.request.language)
    editable_questionnaires = [q for q in questionnaires if q.get('editable', True)]

    return {
        "tenant": serializers.serialize_tenant(session, tenant),
        "config_vars": {
            "configs": [{col.name: getattr(config, col.name) for col in config.__table__.columns} for config in configs],
            "config_langs": [{col.name: getattr(config_lang, col.name) for col in config_lang.__table__.columns} for config_lang in config_langs],
        },
        "user_profiles": [{col.name: getattr(profile, col.name) for col in profile.__table__.columns} for profile in user_profiles],
        "questionnaires": editable_questionnaires
    }


def db_wizard(session, tid, hostname, request):
    """
    Transaction for the handling of wizard request

    :param session: An ORM session
    :param tid: A tenant ID
    :param hostname: The hostname to be configured
    :param request: A user request
    """
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

    crypto_stat_prv_key = ""
    if encryption:
        crypto_stat_prv_key, crypto_stat_pub_key = GCE.generate_keypair()
        node.set_val('crypto_stat_pub_key', crypto_stat_pub_key)

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
        admin_desc = admin_desc | user_permissions

        admin_user = db_create_user(session, tid, None, admin_desc, language)
        admin_user.password_change_needed = (tid != 1)

        if encryption and escrow:
            node.set_val('crypto_escrow_pub_key', crypto_escrow_pub_key)
            admin_user.crypto_escrow_prv_key = Base64Encoder.encode(GCE.asymmetric_encrypt(admin_user.crypto_pub_key, crypto_escrow_prv_key))
            admin_user.crypto_global_stat_prv_key = Base64Encoder.encode(GCE.asymmetric_encrypt(admin_user.crypto_pub_key, crypto_stat_prv_key))

    if not request['skip_recipient_account_creation']:
        receiver_desc = models.User().dict(language)
        receiver_desc['username'] = request['receiver_username']
        receiver_desc['password'] = request['receiver_password']
        receiver_desc['name'] = request['receiver_name']
        receiver_desc['mail_address'] = request['receiver_mail_address']
        receiver_desc['language'] = language
        receiver_desc['role'] = 'receiver'
        receiver_desc['pgp_key_remove'] = False
        receiver_desc = receiver_desc | user_permissions

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

    for var in ['mode', 'name', 'subdomain']:
        db_set_config_variable(session, tid, var, request[var])

    return serializers.serialize_tenant(session, t)


@transact
def add_user_profiles(session, model, data):
    session.bulk_insert_mappings(model, data)
    session.commit()


@transact
def add_or_update_configs(session, model, data):
    for config_data in data:
        filters = {'tid': config_data['tid'], 'var_name': config_data['var_name']}
        if model == models.ConfigL10N:
            filters['lang'] = config_data['lang']

        existing_record = session.query(model).filter_by(**filters).first()

        if existing_record:
            existing_record.set_v(config_data['value'])
        else:
            session.add(model(values=config_data))

    session.commit()


class TenantCollection(BaseHandler):
    check_roles = 'admin'
    root_tenant_only = True
    invalidate_cache = True

    def get(self):
        """
        Return the list of registered tenants
        """
        return get_tenant_list()

    @inlineCallbacks
    def post(self):
        """
        Create a new tenant
        """
        raw_content = self.request.content.read()
        content = json.loads(raw_content)
        tenant_profile = content.get('tenant')

        if tenant_profile:
            is_profile = True
            request = self.validate_request(tenant_profile, requests.AdminTenantDesc)
            t = yield create_and_initialize(request, is_profile=is_profile)

            if t:
                config_vars = content.get('config_vars', {})
                user_profiles = content.get('user_profiles', [])
                configs = config_vars.get('configs', [])
                config_langs = config_vars.get('config_langs', [])
                questionnaires = content.get('questionnaires', [])

                config_data = [
                    {"tid": t["id"], "var_name": config["var_name"], "value": config["value"]}
                    for config in configs if config["var_name"] != "uuid"
                ]

                config_lang_data = [{'tid': t['id'],'lang': lang.get("lang"),'var_name': lang.get("var_name"),'value': lang.get("value")}
                     for lang in config_langs]

                user_profiles_data = [{**{k: v for k, v in user_profile.items() if k not in ["id", "tid"]}, "tid": t["id"]}
                    for user_profile in user_profiles
                ]

                if config_data:
                    yield add_or_update_configs(models.Config, config_data)

                if config_lang_data:
                    yield add_or_update_configs(models.ConfigL10N, config_lang_data)

                if user_profiles_data:
                    yield add_user_profiles(models.UserProfile, user_profiles_data)

                if questionnaires:
                    # Duplicate each questionnaire for the new tenant
                    for q in questionnaires:
                        yield import_questionnaires(t['id'], q)

        else:
            request = self.validate_request(raw_content, requests.AdminTenantDesc)
            is_profile = content.get('is_profile', False)
            t = yield create_and_initialize(request, is_profile=is_profile)
            return t

class TenantInstance(BaseHandler):
    check_roles = 'admin'
    root_tenant_only = True
    invalidate_cache = True

    def get(self, tid):
        return get(self, int(tid))

    def put(self, tid):
        """
        Update the specified tenant.
        """
        request = self.validate_request(self.request.content.read(),
                                        requests.AdminTenantDesc)

        return update(int(tid), request)

    @inlineCallbacks
    def delete(self, tid):
        """
        Delete the specified tenant.
        """

        profile_mapped_status = yield is_profile_mapped(tid)
        if profile_mapped_status:
            raise errors.ForbiddenOperation

        tid = int(tid)
        tw(db_del, models.Tenant, models.Tenant.id == tid)
