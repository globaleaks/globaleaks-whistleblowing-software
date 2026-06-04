# -*- coding: UTF-8
import json
import os
from nacl.encoding import Base64Encoder
from sqlalchemy import func
from twisted.internet.defer import inlineCallbacks

from globaleaks import LANGUAGES_SUPPORTED_CODES, models
from globaleaks.db.appdata import load_appdata, db_load_defaults
from globaleaks.handlers.admin.context import admin_serialize_context, db_create_context
from globaleaks.handlers.admin.node import db_update_enabled_languages
from globaleaks.handlers.admin.questionnaire import db_create_questionnaire, db_get_questionnaires, import_questionnaires
from globaleaks.handlers.admin.user import db_create_user
from globaleaks.handlers.base import BaseHandler
from globaleaks.handlers.user import user_permissions
from globaleaks.models import Config, EnabledLanguage, config, serializers
from globaleaks.models.config import db_get_configs, \
    db_get_config_variable, db_set_config_variable
from globaleaks.orm import db_del, db_get, db_log, transact, tw
from globaleaks.rest import errors, requests
from globaleaks.settings import Settings
from globaleaks.utils.crypto import GCE
from globaleaks.utils.fs import read_json_file
from globaleaks.utils.log import log
from globaleaks.utils.sock import isIPAddress
from globaleaks.utils.tls import gen_selfsigned_certificate
from globaleaks.utils.utility import datetime_null, uuid4

DEFAULT_PROFILE_ID = 1000001
FORWARD_QUESTIONNAIRE_ID = 'forward'
FORWARD_REQUEST_QUESTIONNAIRE_ID = 'forward_request'
FORWARD_REQUEST_CHANNEL_NAME = 'Forward Request'


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


def db_ensure_forward_questionnaire(session):
    root_tenant_node = config.ConfigFactory(session, 1)
    config_rows = list(session.query(models.Config)
                       .filter(models.Config.var_name == 'forward_questionnaire'))
    old_config_questionnaire_ids = {cfg.value for cfg in config_rows
                                    if cfg.value and cfg.value != FORWARD_QUESTIONNAIRE_ID}
    old_questionnaire_ids = set()
    if old_config_questionnaire_ids:
        old_questionnaire_ids = {
            questionnaire.id for questionnaire in session.query(models.Questionnaire)
                                                   .filter(models.Questionnaire.id.in_(old_config_questionnaire_ids),
                                                           models.Questionnaire.tid == 1,
                                                           models.Questionnaire.name == 'Forward')
        }

    forward_questionnaire = session.query(models.Questionnaire) \
                                   .filter(models.Questionnaire.id == FORWARD_QUESTIONNAIRE_ID,
                                           models.Questionnaire.tid == 1) \
                                   .one_or_none()

    if forward_questionnaire is None:
        qfile = os.path.join(Settings.questionnaires_path, 'forward.json')
        if not os.path.exists(qfile):
            raise errors.InternalServerError('Missing bundled forward questionnaire')

        forward_questionnaire = db_create_questionnaire(session,
                                                        1,
                                                        None,
                                                        read_json_file(qfile),
                                                        None)

    root_tenant_node.set_val('forward_questionnaire', FORWARD_QUESTIONNAIRE_ID)

    for cfg in config_rows:
        cfg.value = FORWARD_QUESTIONNAIRE_ID

    if old_questionnaire_ids:
        for context in session.query(models.Context).filter(models.Context.questionnaire_id.in_(old_questionnaire_ids)):
            context.questionnaire_id = FORWARD_QUESTIONNAIRE_ID
            context.hidden = True
            context.additional_questionnaire_id = ''

        for context in session.query(models.Context).filter(models.Context.additional_questionnaire_id.in_(old_questionnaire_ids)):
            context.additional_questionnaire_id = ''

        db_del(session,
               models.Questionnaire,
               (models.Questionnaire.id.in_(old_questionnaire_ids),
                models.Questionnaire.tid == 1))

    return forward_questionnaire


def db_ensure_forward_request_questionnaire(session):
    forward_request_questionnaire = session.query(models.Questionnaire) \
                                           .filter(models.Questionnaire.id == FORWARD_REQUEST_QUESTIONNAIRE_ID,
                                                   models.Questionnaire.tid == 1) \
                                           .one_or_none()
    if forward_request_questionnaire is not None:
        return forward_request_questionnaire

    qfile = os.path.join(Settings.questionnaires_path, 'forward_request.json')
    if not os.path.exists(qfile):
        raise errors.InternalServerError('Missing bundled forward request questionnaire')

    return db_create_questionnaire(session, 1, None, read_json_file(qfile), None)


def db_has_forward_permission(session, user):
    if user is None:
        return False

    return session.query(models.UserProfilePermission) \
                  .filter(models.UserProfilePermission.profile_id == user.profile_id,
                          models.UserProfilePermission.permission == 'can_forward_reports') \
                  .count() > 0


def db_get_first_forward_receiver(session, tid):
    return session.query(models.User) \
                  .join(models.UserProfilePermission,
                        models.UserProfilePermission.profile_id == models.User.profile_id) \
                  .filter(models.User.tid == tid,
                          models.User.role == 'receiver',
                          models.User.enabled == True,
                          models.UserProfilePermission.permission == 'can_forward_reports') \
                  .order_by(models.User.creation_date) \
                  .first()


def db_initialize_default_forward(session, tid, language, default_context, receiver_user=None):
    tenant_node = config.ConfigFactory(session, tid)
    forward_questionnaire = db_ensure_forward_questionnaire(session)
    receiver_user = receiver_user if db_has_forward_permission(session, receiver_user) else None

    forward_channel = session.query(models.Context) \
                             .filter(models.Context.id == tenant_node.get_val('forward_channel'),
                                     models.Context.tid == tid) \
                             .one_or_none()

    if forward_channel is None:
        context_desc = admin_serialize_context(session, default_context, language)
        context_desc['id'] = uuid4()
        context_desc['name'] = 'Forward'
        context_desc['hidden'] = True
        context_desc['questionnaire_id'] = forward_questionnaire.id
        context_desc['additional_questionnaire_id'] = ''
        context_desc['allow_recipients_selection'] = False
        context_desc['select_all_receivers'] = True
        context_desc['receivers'] = [receiver_user.id] if receiver_user and receiver_user.tid == tid else []
        forward_channel = db_create_context(session, tid, None, context_desc, language)
    else:
        forward_channel.hidden = True
        forward_channel.additional_questionnaire_id = ''
        forward_channel.allow_recipients_selection = False
        forward_channel.select_all_receivers = True
        if forward_channel.questionnaire_id != forward_questionnaire.id:
            forward_channel.questionnaire_id = forward_questionnaire.id

    tenant_node.set_val('forward_questionnaire', forward_questionnaire.id)
    tenant_node.set_val('forward_channel', forward_channel.id)

    if receiver_user is not None:
        session.merge(models.ReceiverContext({
            'context_id': forward_channel.id,
            'receiver_id': receiver_user.id,
            'order': 0
        }))


def db_ensure_forward_channel(session, tid, language=None):
    tenant_node = config.ConfigFactory(session, tid)
    forward_channel = session.query(models.Context) \
                             .filter(models.Context.id == tenant_node.get_val('forward_channel'),
                                     models.Context.tid == tid) \
                             .one_or_none()
    if forward_channel is not None:
        return forward_channel

    excluded_context_ids = {
        tenant_node.get_val('forward_channel'),
        tenant_node.get_val('forward_request_channel')
    }
    default_context = session.query(models.Context) \
                             .filter(models.Context.tid == tid,
                                     ~models.Context.id.in_(excluded_context_ids)) \
                             .order_by(models.Context.order) \
                             .first()
    if default_context is None:
        raise errors.InternalServerError('Unable to initialize forward channel')

    receiver_user = db_get_first_forward_receiver(session, tid)

    db_initialize_default_forward(session, tid, language, default_context, receiver_user)

    return session.query(models.Context) \
                  .filter(models.Context.id == tenant_node.get_val('forward_channel'),
                          models.Context.tid == tid) \
                  .one()


def db_initialize_forward_request_channel(session, tid, language, default_context, receiver_user=None):
    if tid != 1:
        return

    tenant_node = config.ConfigFactory(session, tid)
    forward_request_questionnaire = db_ensure_forward_request_questionnaire(session)
    receiver_user = receiver_user if db_has_forward_permission(session, receiver_user) else None

    request_channel = session.query(models.Context) \
                             .filter(models.Context.id == tenant_node.get_val('forward_request_channel'),
                                     models.Context.tid == tid) \
                             .one_or_none()

    if request_channel is None:
        context_desc = admin_serialize_context(session, default_context, language)
        context_desc['id'] = uuid4()
        context_desc['name'] = FORWARD_REQUEST_CHANNEL_NAME
        context_desc['hidden'] = True
        context_desc['questionnaire_id'] = forward_request_questionnaire.id
        context_desc['additional_questionnaire_id'] = ''
        context_desc['allow_recipients_selection'] = False
        context_desc['select_all_receivers'] = True
        context_desc['receivers'] = [receiver_user.id] if receiver_user and receiver_user.tid == tid else []
        request_channel = db_create_context(session, tid, None, context_desc, language)
    else:
        request_channel.hidden = True
        request_channel.additional_questionnaire_id = ''
        request_channel.allow_recipients_selection = False
        request_channel.select_all_receivers = True
        if request_channel.questionnaire_id != forward_request_questionnaire.id:
            request_channel.questionnaire_id = forward_request_questionnaire.id

    tenant_node.set_val('forward_request_channel', request_channel.id)


def db_ensure_channel_receiver(session, tid, context):
    has_receiver = session.query(models.ReceiverContext) \
                          .filter(models.ReceiverContext.context_id == context.id) \
                          .count()
    if has_receiver:
        return

    receiver_user = db_get_first_forward_receiver(session, tid)
    if receiver_user is None:
        return

    session.merge(models.ReceiverContext({
        'context_id': context.id,
        'receiver_id': receiver_user.id,
        'order': 0
    }))


def db_ensure_forward_request_channel(session, language=None):
    tenant_node = config.ConfigFactory(session, 1)
    request_channel = session.query(models.Context) \
                             .filter(models.Context.id == tenant_node.get_val('forward_request_channel'),
                                     models.Context.tid == 1) \
                             .one_or_none()
    if request_channel is not None:
        db_ensure_channel_receiver(session, 1, request_channel)
        return request_channel

    excluded_context_ids = {
        tenant_node.get_val('forward_channel'),
        tenant_node.get_val('forward_request_channel')
    }
    default_context = session.query(models.Context) \
                             .filter(models.Context.tid == 1,
                                     ~models.Context.id.in_(excluded_context_ids)) \
                             .order_by(models.Context.order) \
                             .first()
    if default_context is None:
        raise errors.InternalServerError('Unable to initialize forward request channel')

    receiver_user = db_get_first_forward_receiver(session, 1)

    db_initialize_forward_request_channel(session, 1, language, default_context, receiver_user)

    return session.query(models.Context) \
                  .filter(models.Context.id == tenant_node.get_val('forward_request_channel'),
                          models.Context.tid == 1) \
                  .one()


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
            db_set_config_variable(session, 1, 'accept_forwarding', True)
            db_set_config_variable(session, 1, 'accept_forwarding_from', ['*'])
            db_set_config_variable(session, 1, 'accepts_requests_of_forward_from', ['*'])
            db_set_config_variable(session, 1, 'send_forwarding', ['*'])
            db_set_config_variable(session, 1, 'send_forwarding_request', [])
        else:
            db_set_config_variable(session, t.id, 'accept_forwarding', True)
            db_set_config_variable(session, t.id, 'accept_forwarding_from', [1])
            db_set_config_variable(session, t.id, 'send_forwarding', [1])
            db_set_config_variable(session, t.id, 'send_forwarding_request', [1])

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


def db_get_tenant_stats(session, tid):
    """
    Get statistics about a tenant's reports.

    :param session: An ORM session
    :param tid: A tenant ID
    :return: Dictionary with tenant statistics
    """
    total_reports = session.query(models.InternalTip).filter(
        models.InternalTip.tid == tid
    ).count()

    open_reports = session.query(models.InternalTip).filter(
        models.InternalTip.tid == tid,
        models.InternalTip.status != 'closed'
    ).count()

    last_update = session.query(func.max(models.InternalTip.update_date)).filter(
        models.InternalTip.tid == tid
    ).scalar()

    if not last_update:
        last_update = datetime_null()

    return {
        'total_reports': total_reports,
        'open_reports': open_reports,
        'last_update': last_update.isoformat()
    }


@transact
def get_tenant_stats(session, tid):
    return db_get_tenant_stats(session, tid)


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
    else:
        receiver_user = None

    context_desc = models.Context().dict(language)
    context_desc['name'] = 'Default'
    context_desc['status'] = 'enabled'

    if not request['skip_recipient_account_creation']:
        context_desc['receivers'] = [receiver_user.id]

    context = db_create_context(session, tid, None, context_desc, language)
    db_initialize_default_forward(session, tid, language, context, receiver_user)
    db_initialize_forward_request_channel(session, tid, language, context, receiver_user)

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
                        'default_questionnaire',
                        'forward_questionnaire']:
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

        check = self.request.content.read()
        if check:
            check = self.validate_request(check,
                                          requests.AdminTenantDeleteDesc)

        yield tw(db_delete_tenant,
                 self.request.tid,
                 self.session,
                 tid,
                 check)


def db_delete_tenant(session, request_tid, user_session, tid, check):
    """
    Delete a tenant after validating stats.

    :param session: An ORM session
    :param request_tid: The requesting tenant ID
    :param user_session: The user session
    :param tid: The tenant ID to delete
    :param check: deletion checks
    """
    stats = db_get_tenant_stats(session, tid)

    if check:
        stats_changed = (
            stats['total_reports'] != check['total_reports'] or
            stats['open_reports'] != check['open_reports'] or
            stats['last_update'] != check['last_update']
        )

        if stats_changed:
            raise errors.ForbiddenOperation

    db_del(session, models.Tenant, models.Tenant.id == tid)

    db_log(session, tid=request_tid, type='delete_tenant', user_id=user_session.user_id, object_id=str(tid), data=stats)


class TenantStats(BaseHandler):
    check_roles = 'admin'
    root_tenant_only = True

    def get(self, tid):
        """
        Retrieve statistics about a tenant's reports.
        """
        return get_tenant_stats(int(tid))
