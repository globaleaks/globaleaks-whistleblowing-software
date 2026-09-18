import os
import sqlalchemy
import sys
import traceback
from collections import defaultdict

from globaleaks.rest.cache import Cache

from sqlalchemy import and_, or_
from globaleaks import models, DATABASE_VERSION
from globaleaks.handlers.admin.https import db_load_tls_configs
from globaleaks.handlers.public import MAX_SERIALIZATION_DEPTH
from globaleaks.models import Base, Config
from globaleaks.models.config import DEFAULT_PROFILE_ID, db_get_pid, db_get_profile_children, db_get_signup_idp_config
from globaleaks.models.config_desc import ConfigFilters
from globaleaks.orm import get_engine, get_session, make_db_uri, transact, transact_sync
from globaleaks.settings import Settings
from globaleaks.state import State, TenantState
from globaleaks.utils import fs
from globaleaks.utils.crypto import generateRandomKey
from globaleaks.utils.log import log
from globaleaks.utils.objectdict import ObjectDict
from globaleaks.handlers.admin import tenant


def get_db_file(db_path):
    """
    Utility function to retrieve the database file path
    :param db_path: The path where to look for the database file
    :return: The version and the path of the existing database file
    """
    path = os.path.join(db_path, 'globaleaks.db')
    if os.path.exists(path):
        session = get_session(make_db_uri(path))
        version_db = session.query(models.Config.value).filter(Config.tid == 1,
                                                               Config.var_name == 'version_db').one()[0]
        session.close()
        return version_db, path

    for i in reversed(range(DATABASE_VERSION + 1)):
        file_name = f'glbackend-{i}.db'
        db_file_path = os.path.join(db_path, 'db', file_name)
        if os.path.exists(db_file_path):
            return i, db_file_path

    return 0, ''


def create_db():
    """
    Utility function to create a new database
    """
    engine = get_engine(orm_lockdown=False)

    conn = engine.connect()
    try:
        conn.execute(sqlalchemy.text('PRAGMA foreign_keys = ON'))
        conn.execute(sqlalchemy.text('PRAGMA secure_delete = ON'))
        conn.execute(sqlalchemy.text('PRAGMA auto_vacuum = FULL'))
        conn.execute(sqlalchemy.text('PRAGMA automatic_index = ON'))
    finally:
        conn.close()

    Base.metadata.create_all(engine)


def compact_db():
    """
    Execute VACUUM command to deallocate database space
    """
    engine = get_engine(orm_lockdown=False)
    conn = engine.connect()
    try:
        conn.execute(sqlalchemy.text('VACUUM'))
    finally:
        conn.close()


@transact_sync
def initialize_db(session):
    """
    Transaction for initializing the application database
    :param session: An ORM session
    """
    tenant.db_create(session, {'active': True, 'profile': 'default', 'name': 'GLOBALEAKS', 'subdomain': ''})
    tenant.db_create(session, {'active': True, 'profile': 'default', 'name': 'GLOBALEAKS', 'subdomain': ''}, False)


def update_db():
    """
    This function handles the update of an existing database
    :return: The database version
    """
    db_version, db_file_path = get_db_file(Settings.working_path)
    if db_version == 0:
        return 0

    try:
        from globaleaks.db import migration  # noqa: PLC0415
        log.err('Found an already initialized database version: %d', db_version)

        if db_version != DATABASE_VERSION:
            log.err('Performing schema migration from version %d to version %d',
                    db_version, DATABASE_VERSION)

            migration.perform_migration(db_version)
        else:
            migration.perform_data_update(db_file_path)
            compact_db()

        sync_clean_untracked_files()

        sync_fix_receipt_auth_downgrade()

    except Exception as exception:
        log.err('Failure: %s', exception)
        log.err('Verbose exception traceback:')
        etype, value, tback = sys.exc_info()
        log.info('\n'.join(traceback.format_exception(etype, value, tback)))
        return -1

    return DATABASE_VERSION


def db_get_tracked_files(session):
    """
    Transaction for retrieving the list of files tracked by the application database
    :param session: An ORM session
    :return: The list of filenames of the files
    """
    return [x[0] for x in session.query(models.File.id)]


def db_get_tracked_attachments(session):
    """
    Transaction for retrieving the list of attachment files tracked by the application database
    :param session: An ORM session
    :return: The list of filenames of the attachment files
    """
    ifiles = session.query(models.InternalFile.id).all()
    wbfiles = session.query(models.WhistleblowerFile.id).all()
    rfiles = session.query(models.ReceiverFile.id).all()

    return [x[0] for x in ifiles + wbfiles + rfiles]


@transact_sync
def sync_clean_untracked_files(session):
    """
    Transaction for removing files that are not tracked by the application database
    :param session: An ORM session
    """
    tracked_files = db_get_tracked_attachments(session)
    for filesystem_file in os.listdir(Settings.attachments_path):
        if filesystem_file not in tracked_files:
            file_to_remove = os.path.join(Settings.attachments_path, filesystem_file)
            log.debug('Removing untracked file: %s', file_to_remove)
            try:
                fs.srm(file_to_remove)
            except OSError:
                log.err('Failed to remove untracked file', file_to_remove)


def db_fix_receipt_auth_downgrade(session):
    """
    Normalize tenants with mixed receipt hash formats to the client-derived format

    :param session: An ORM session
    """
    mixed_tids = session.query(models.InternalTip.tid) \
                        .group_by(models.InternalTip.tid) \
                        .having(sqlalchemy.and_(sqlalchemy.func.max(sqlalchemy.func.length(models.InternalTip.receipt_hash)) >= 64,
                                                sqlalchemy.func.min(sqlalchemy.func.length(models.InternalTip.receipt_hash)) < 64)) \
                        .subquery()

    for itip in session.query(models.InternalTip) \
                       .filter(models.InternalTip.tid.in_(session.query(mixed_tids.c.tid)),
                               sqlalchemy.func.length(models.InternalTip.receipt_hash) < 64):
        log.err('Neutralizing receipt-auth downgrade report: tid=%d id=%s', itip.tid, itip.id)
        itip.receipt_hash = generateRandomKey()


@transact_sync
def sync_fix_receipt_auth_downgrade(session):
    db_fix_receipt_auth_downgrade(session)


@transact_sync
def sync_initialize_snimap(session):
    """
    Transaction for loading TLS certificates and initialize the SNI map
    :param session: An ORM session
    """
    for cfg in db_load_tls_configs(session):
        State.snimap.load(cfg['tid'], cfg)


def db_get_tenants_using_voice(session, tids):
    """
    Identify the tenants making use of questions of type voice.

    The evaluation spans every context of the tenant, hidden ones included:
    submissions are performed through hidden contexts as well and the
    microphone permission has therefore to be granted independently of the
    visibility of the context carrying the question.

    :param session: An ORM session
    :param tids: The tenant IDs to be evaluated
    :return: The subset of the tenant IDs using questions of type voice
    """
    # The questions of type voice are walked upwards up to the steps
    # referencing them, following at each level both the question nesting and
    # the questions inheriting the type from a template, as done in reverse by
    # the serialization. The walk is bounded by the same cap applied to the
    # serialization recursion.
    frontier = {f[0] for f in session.query(models.Field.id).filter(models.Field.type == 'voice')}

    seen = set()
    step_ids = set()
    depth = 0

    while frontier and depth < MAX_SERIALIZATION_DEPTH:
        frontier |= {f[0] for f in session.query(models.Field.id)
                                          .filter(or_(models.Field.template_override_id.in_(frontier),
                                                      and_(models.Field.template_override_id.is_(None),
                                                           models.Field.template_id.in_(frontier))))}

        frontier -= seen
        seen |= frontier

        parents = set()
        for step_id, fieldgroup_id in session.query(models.Field.step_id, models.Field.fieldgroup_id) \
                                             .filter(models.Field.id.in_(frontier)):
            if step_id is not None:
                step_ids.add(step_id)

            if fieldgroup_id is not None:
                parents.add(fieldgroup_id)

        frontier = parents
        depth += 1

    questionnaire_ids = {s[0] for s in session.query(models.Step.questionnaire_id)
                                              .filter(models.Step.id.in_(step_ids))}

    return {t[0] for t in session.query(models.Context.tid)
                                 .filter(models.Context.tid.in_(tids),
                                         or_(models.Context.questionnaire_id.in_(questionnaire_ids),
                                             models.Context.additional_questionnaire_id.in_(questionnaire_ids)))
                                 .distinct()}


def update_cache(tid, cfg):
    tenant_cache = State.tenants[tid].cache
    if cfg.var_name in ['https_cert', 'tor_onion_key'] or cfg.var_name in ConfigFilters['node']:
        tenant_cache[cfg.var_name] = cfg.value
    elif cfg.var_name in ConfigFilters['notification']:
        tenant_cache.setdefault('notification', {})[cfg.var_name] = cfg.value


def db_unload_tenants(tids):
    """
    Remove from the state the tenants that have been disabled

    :param tids: The tenants disabled
    """
    for tid in tids:
        if tid not in State.tenants:
            continue

        tenant_cache = State.tenants[tid].cache

        State.tenant_uuid_id_map.pop(tenant_cache.uuid, None)
        State.tenant_subdomain_id_map.pop(tenant_cache.subdomain, None)

        for h in tenant_cache.hostnames + tenant_cache.onionnames:
            State.tenant_hostname_id_map.pop(h, None)

        State.snimap.unload(tid)

        if State.tor:
            State.tor.unload_onion_service(tid)

        del State.tenants[tid]


def db_get_tids_to_refresh(session, to_refresh, active_tids):
    """
    Return the tenants a change touches the cache of: every tenant, the tenant changed with its
    profile, or the profile changed with the tenants using it

    :param session: An ORM session
    :param to_refresh: The tenant changed, None for every tenant
    :param active_tids: The tenants that exist
    :return: The tenants to refresh
    """
    if to_refresh is None or to_refresh == 1:
        return active_tids

    if to_refresh not in active_tids:
        return []

    tids = [to_refresh]

    if to_refresh < DEFAULT_PROFILE_ID:
        pid = db_get_pid(session, to_refresh)
        if pid is not None and pid != to_refresh:
            tids.append(pid)

        return tids

    matching_tids = [tid for tid in db_get_profile_children(session, to_refresh)
                     if tid in active_tids and tid != to_refresh]

    tids.extend(matching_tids)

    # Invalidate every tenant using the updated profile
    for tid in matching_tids:
        Cache.invalidate(tid)

    return tids


def db_reset_tenant_cache(session, tid):
    """
    Give a tenant a blank cache

    :param session: An ORM session
    :param tid: A tenant ID
    :return: The profile of the tenant
    """
    if tid not in State.tenants:
        State.tenants[tid] = TenantState()

    pid = db_get_pid(session, tid) or DEFAULT_PROFILE_ID

    tenant_cache = State.tenants[tid].cache
    tenant_cache['ptid'] = pid

    tenant_cache['redirects'] = {}
    tenant_cache['custodian'] = False
    tenant_cache['microphone'] = False
    tenant_cache['notification'] = ObjectDict()
    tenant_cache['notification'].admin_list = []
    tenant_cache['hostnames'] = []
    tenant_cache['onionnames'] = []
    tenant_cache['languages_enabled'] = []

    return pid


def db_load_tenant_configs(session, tids, pids):
    """
    Load the configuration of some tenants; every configuration variable is resolved following
    the inheritance chain default profile < tenant profile < tenant

    :param session: An ORM session
    :param tids: The tenants
    :param pids: The profile of each tenant
    """
    configs = defaultdict(dict)

    lookup_tids = set(tids) | set(pids.values()) | {DEFAULT_PROFILE_ID}

    for cfg in session.query(Config).filter(Config.tid.in_(lookup_tids)):
        configs[cfg.tid][cfg.var_name] = cfg

    for tid in tids:
        resolved = dict(configs[DEFAULT_PROFILE_ID])
        resolved.update(configs[pids[tid]])
        resolved.update(configs[tid])

        for cfg in resolved.values():
            update_cache(tid, cfg)


def db_load_tenant_users(session, tids):
    """
    Note on some tenants the administrators to notify, the presence of a custodian and the use of
    the voice

    :param session: An ORM session
    :param tids: The tenants
    """
    query = (session.query(models.User.tid, models.User.mail_address, models.User.pgp_key_public)
            .join(models.UserProfileRole, models.User.profile_id == models.UserProfileRole.profile_id)
            .filter(models.UserProfileRole.role == 'admin',
                    models.User.enabled.is_(True),
                    models.User.notification.is_(True),
                    models.User.tid.in_(tids))
            .distinct())
    results = query.all()

    for tid, mail, pub_key in results:
        State.tenants[tid].cache.notification.admin_list.extend([(mail, pub_key)])

    for (tid,) in session.query(models.User.tid) \
                         .filter(models.User.role == 'custodian',
                                 models.User.enabled.is_(True),
                                 models.User.tid.in_(tids)) \
                         .distinct():
        State.tenants[tid].cache['custodian'] = True

    for tid in db_get_tenants_using_voice(session, tids):
        State.tenants[tid].cache['microphone'] = True


def load_tenant_names(tid, root_tenant_cache):
    """
    Register the names a tenant is reached by: its hostname and its onion service, and the ones
    derived from its subdomain

    :param tid: A tenant ID
    :param root_tenant_cache: The cache of the root tenant
    """
    tenant_cache = State.tenants[tid].cache

    State.tenant_uuid_id_map[tenant_cache.uuid] = tid

    if tenant_cache.hostname and tenant_cache.reachable_via_web:
        tenant_cache.hostnames.append(tenant_cache.hostname.encode())

    if tenant_cache.onionservice:
        tenant_cache.onionnames.append(tenant_cache.onionservice.encode())

    if tenant_cache.subdomain:
        State.tenant_subdomain_id_map[tenant_cache.subdomain] = tid

        if not tenant_cache.onionservice and root_tenant_cache.onionservice:
            tenant_cache.onionservice = tenant_cache.subdomain + '.' + root_tenant_cache.onionservice

        if root_tenant_cache.rootdomain and tenant_cache.reachable_via_web:
            tenant_cache.hostnames.append(f'{tenant_cache.subdomain}.{root_tenant_cache.rootdomain}'.encode())

        if root_tenant_cache.onionservice:
            tenant_cache.onionnames.append(f'{tenant_cache.subdomain}.{root_tenant_cache.onionservice}'.encode())

    State.tenant_hostname_id_map.update({h: tid for h in tenant_cache.hostnames + tenant_cache.onionnames})


def db_refresh_tenant_cache(session, to_refresh=None):
    active_tids = set([tid[0] for tid in session.query(models.Tenant.id)])#.filter(models.Tenant.active.is_(True))])

    cached_tids = set(State.tenants.keys())

    # Remove tenants that have been disabled
    db_unload_tenants(cached_tids - active_tids)

    tids = db_get_tids_to_refresh(session, to_refresh, active_tids)
    if not tids:
        return

    tids = sorted(tids)

    pids = {tid: db_reset_tenant_cache(session, tid) for tid in tids}

    root_tenant_cache = State.tenants[1].cache

    for tid, lang in session.query(models.EnabledLanguage.tid, models.EnabledLanguage.name)\
                            .filter(models.EnabledLanguage.tid.in_(tids)):
        State.tenants[tid].cache['languages_enabled'].append(lang)

    db_load_tenant_configs(session, tids, pids)

    db_load_tenant_users(session, tids)

    for redirect in session.query(models.Redirect).filter(models.Redirect.tid.in_(tids)):
        State.tenants[redirect.tid].cache['redirects'][redirect.path1] = redirect.path2

    for tid in tids:
        load_tenant_names(tid, root_tenant_cache)

    if State.tor:
        State.tor.load_all_onion_services()

    # The IdP of the signups is inherited from the signup profile and resolved separately
    if 1 in State.tenants:
        signup_idp_config = db_get_signup_idp_config(session, 1)
        if any(State.tenants[1].cache.get(k) != v for k, v in signup_idp_config.items()):
            State.tenants[1].cache.update(signup_idp_config)
            Cache.invalidate(1)

    if 1 in tids:
        log.setloglevel(State.tenants[1].cache.log_level)


@transact
def refresh_tenant_cache(session, tid=None):
    return db_refresh_tenant_cache(session, tid)


@transact_sync
def sync_refresh_tenant_cache(session, tid=None):
    return db_refresh_tenant_cache(session, tid)
