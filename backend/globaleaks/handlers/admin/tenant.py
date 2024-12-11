# -*- coding: UTF-8
from globaleaks import models
from globaleaks.db.appdata import load_appdata, db_load_defaults
from globaleaks.handlers.base import BaseHandler
from globaleaks.handlers.wizard import db_wizard
from globaleaks.models import Config, config, serializers
from globaleaks.models.config import db_get_configs, \
    db_get_config_variable, db_set_config_variable
from globaleaks.orm import db_del, db_get, transact, tw
from globaleaks.rest import errors, requests
from globaleaks.utils.tls import gen_selfsigned_certificate
import json
from twisted.internet.defer import inlineCallbacks

default_profile_id = 1000001

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
    id_key = 'tenant_counter' if isTenant and not is_profile else 'profile_counter'
    tid = db_get_config_variable(session, 1, id_key)
    return id_key, tid

def calculate_tenant_id(tid, is_profile):
    if tid == 1000000 and is_profile:
        return tid + 2
    else:
        return tid + 1
    
def db_create(session, desc, isTenant = True, **kwargs):
    is_profile = kwargs.get('is_profile', False)
    
    id_key, tid = get_tenant_id(session, isTenant, is_profile)
    
    tenant_id = calculate_tenant_id(tid, is_profile)
    
    t = models.Tenant()
    t.id = tenant_id
    t.active = desc['active']

    session.add(t)

    session.flush()

    appdata = load_appdata()

    if t.id == 1:
        language = 'en'
        db_load_defaults(session)
    else:
        language = db_get_config_variable(session, 1, 'default_language')
    models.config.initialize_config(session, t.id, desc)

    if t.id == 1:
        key, cert = gen_selfsigned_certificate()
        db_set_config_variable(session, 1, 'https_selfsigned_key', key)
        db_set_config_variable(session, 1, 'https_selfsigned_cert', cert)

    db_set_config_variable(session, 1, id_key, t.id)
    for var in ['mode', 'name', 'subdomain']:
        db_set_config_variable(session, t.id, var, desc[var])

    models.config.add_new_lang(session, t.id, language, appdata)

    db_initialize_tenant_submission_statuses(session, t.id)

    return t


@transact
def create(session, desc, *args, **kwargs):
    t = db_create(session, desc, *args, **kwargs)

    return serializers.serialize_tenant(session, t)

@transact
def is_profile_mapped(session, tid):
    if int(tid) > 1000001:
        return session.query(Config).filter_by(value=tid, var_name='default_profile').first() is not None
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

    for t, s in session.query(models.Tenant, models.Subscriber).join(models.Subscriber, models.Subscriber.tid == models.Tenant.id, isouter=True).filter(models.Tenant.id != default_profile_id):
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
        raw_content = self.request.content.read()
        request = self.validate_request(raw_content, requests.AdminTenantDesc)
        content = json.loads(raw_content)
        is_profile = content.get('is_profile', False)

        return create_and_initialize(request, is_profile=is_profile)


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
