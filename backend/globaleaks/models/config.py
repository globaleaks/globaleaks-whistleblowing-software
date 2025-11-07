from sqlalchemy import and_, delete, or_, tuple_
from sqlalchemy.orm import aliased

from globaleaks import LANGUAGES_SUPPORTED_CODES
from globaleaks.models import Config, ConfigL10N
from globaleaks.models.properties import *
from globaleaks.models.config_desc import ConfigDescriptor, ConfigFilters, ConfigL10NFilters
from globaleaks.utils.onion import generate_onion_service_v3


# List of variables that on creation are set with the value
# they have on the root tenant
inherit_from_root_tenant = ['default_questionnaire']

root_tenant_keys = ["version", "version_db", "latest_version", "profile", "default_language", "subdomain", "tor_onion_key", "onionservice", "https_admin", "https_analyst", "https_cert", "wizard_done", "uuid", "mode", "name", "encryption", "https_whistleblower", "receipt_salt", "crypto_escrow_pub_key", "crypto_stat_pub_key", "counter_profiles", "counter_submissions", "counter_tenants"]

secondary_tenant_keys = ["profile", "default_language", "subdomain", "tor_onion_key", "onionservice", "https_admin", "https_analyst", "https_cert", "wizard_done", "uuid", "mode", "name", "encryption", "https_whistleblower", "receipt_salt", "crypto_escrow_pub_key", "crypto_stat_pub_key", "counter_profiles", "counter_submissions", "counter_tenants"]

protected_keys = ["version", "version_db", "latest_version", "profile", "default_language", "subdomain", "tor_onion_key", "onionservice", "https_admin", "https_analyst", "https_cert", "wizard_done", "uuid", "mode", "name", "encryption", "https_whistleblower", "receipt_salt", "crypto_escrow_pub_key", "crypto_stat_pub_key", "counter_profiles", "counter_submissions", "counter_tenants"]


DEFAULT_PROFILE_ID = 1000001


def db_get_pid(session, tid):
    profile_value = session.query(Config.value).filter(
        Config.tid == tid,
        Config.var_name == 'profile',
    ).scalar()

    if not profile_value:
        return None

    if profile_value == 'default':
        return DEFAULT_PROFILE_ID

    config_profile = aliased(Config)
    config_uuid4 = aliased(Config)

    result_tid = session.query(config_uuid4.tid).join(
        config_profile,
        config_uuid4.value == config_profile.value
    ).filter(
        config_profile.var_name == 'profile',
        config_profile.value == profile_value,
        config_uuid4.var_name == 'uuid'
    ).scalar()

    return result_tid


def get_default(default):
    if callable(default):
        return default()

    return default


def process_items(combined_values, tid, pid):
    # Step 1: Split by tid
    by_tid = {DEFAULT_PROFILE_ID: {}, pid: {}, tid: {}}

    for item in combined_values:
        if item.tid in by_tid:
            by_tid[item.tid][item.var_name] = item

    # Step 2: Merge in priority order: default < profile < tenant
    result = {**by_tid[DEFAULT_PROFILE_ID], **by_tid[pid], **by_tid[tid]}

    return result, by_tid[tid], by_tid[pid], by_tid[DEFAULT_PROFILE_ID]


def db_get_configs(session, filter_name):
    configs = {}
    _configs = session.query(Config).filter(Config.var_name.in_(ConfigFilters[filter_name]))

    for c in _configs:
        if c.tid not in configs:
            configs[c.tid] = {}

        configs[c.tid][c.var_name] = c.value

    return configs


class ConfigFactory(object):
    def __init__(self, session, tid):
        self.session = session
        self.tid = tid
        self.pid = db_get_pid(session, tid)

    def get_all(self, filter_name):
        filters = [
          Config.tid.in_([self.tid, self.pid, DEFAULT_PROFILE_ID]),
          Config.var_name.in_(ConfigFilters[filter_name])
        ]

        combined_values = self.session.query(Config).filter(*filters).all()
        return process_items(combined_values, self.tid, self.pid)

    def get_cfg(self, var_name):
        configurations = self.session.query(Config).filter(Config.var_name == var_name).filter(
            Config.tid.in_([self.tid, self.pid, DEFAULT_PROFILE_ID])
        ).all()

        return {config.tid: config for config in configurations}

    def get_val(self, var_name):
        config = self.get_cfg(var_name)
        if not config:
            return get_default(ConfigDescriptor[var_name].default)

        if self.tid in config:
            return config.get(self.tid).value
        elif self.pid in config:
            return config.get(self.pid).value
        else:
            return config.get(DEFAULT_PROFILE_ID).value

    def set_val(self, var_name, value):
        config = self.get_cfg(var_name)
        if config:
            if self.tid in config:
                if self.pid in config:
                    if config[self.pid] == value:
                        self.session.remove(config[self.tid])
                        return

                elif DEFAULT_PROFILE_ID in config:
                    if config[DEFAULT_PROFILE_ID] == value:
                        self.session.remove(config[self.tid])
                        return
            else:
                if self.pid in config:
                    if config[self.pid] == value:
                        return

                elif DEFAULT_PROFILE_ID in config:
                    if config[DEFAULT_PROFILE_ID] == value:
                        return

        self.session.merge(Config({'tid': self.tid, 'var_name': var_name, 'value': value}))

    def remove_val(self, tid, var_name):
        self.session.query(Config).filter(Config.tid == tid, Config.var_name == var_name).delete(synchronize_session=False)

    def sync_profile(self, t_result, d_result):
        result = self.session.query(Config).filter(Config.var_name == 'profile', Config.value == str(self.tid)).all()
        tid_list = [config.tid for config in result]

        for entry in self.session.query(Config).filter(Config.tid.in_(tid_list)).all():
            if entry.var_name not in protected_keys and entry.var_name in t_result and t_result[entry.var_name] == entry.value or entry.var_name not in t_result and entry.var_name in d_result and d_result[entry.var_name].value == entry.value:
                self.remove_val(entry.tid, entry.var_name)

    def update(self, filter_name, data):
        result, t_result, p_result, d_result = self.get_all(filter_name)
        for k, v in result.items():
            if k in data:
                if self.tid != DEFAULT_PROFILE_ID and self.tid != 1:
                    if k in t_result:
                        if not data[k] or (k in p_result and data[k] == p_result[k].value) or (k not in p_result and k in d_result and data[k] == d_result[k].value):
                            if k not in protected_keys:
                                self.remove_val(self.tid, k)
                                del t_result[k]
                        else:
                            v.set_v(data[k])
                            t_result[k] = data[k]
                    elif data[k] and ((k in p_result and data[k] != p_result[k].value) or (k not in p_result and data[k] != d_result[k].value)):
                        self.session.add(Config({'tid': self.tid, 'var_name': k, 'value': data[k]}))
                else:
                    t_result[k] = data[k]
                    v.set_v(data[k])

        if self.tid > DEFAULT_PROFILE_ID:
            self.sync_profile(t_result, d_result)

    def serialize(self, filter_name):
        values, _, _, _ = self.get_all(filter_name)
        return {k: v.value for k, v in values.items()}


class ConfigL10NFactory(object):
    def __init__(self, session, tid):
        self.session = session
        self.tid = tid
        self.pid = db_get_pid(session, tid)

    def get_all(self, filter_name, lang):
        filters = [
          ConfigL10N.tid.in_([self.tid, self.pid, DEFAULT_PROFILE_ID]),
          ConfigL10N.lang == lang,
          ConfigL10N.var_name.in_(ConfigL10NFilters[filter_name])
        ]

        combined_values = self.session.query(ConfigL10N).filter(*filters).all()
        result, t_result, p_result, d_result = process_items(combined_values, self.tid, self.pid)
        return list(result.values()), t_result, p_result, d_result

    def get_cfg(self, lang, var_name):
        configurations = self.session.query(ConfigL10N).filter(ConfigL10N.lang == lang, ConfigL10N.var_name == var_name).filter(
            ConfigL10N.tid.in_([self.tid, self.pid, DEFAULT_PROFILE_ID])
        ).all()

        return {config.tid: config for config in configurations}

    def get_val(self, lang, var_name):
        config = self.get_cfg(lang, var_name)
        if not config:
            return ""

        if self.tid in config:
            return config.get(self.tid).value
        elif self.pid in config:
            return config.get(self.pid).value
        else:
            return config.get(DEFAULT_PROFILE_ID).value

    def set_val(self, lang, var_name, value):
        config = self.get_cfg(lang, var_name)
        if config:
            if self.tid in config:
                if self.pid in config:
                    if config[self.pid] == value:
                        self.session.remove(config[self.tid])
                        return

                elif DEFAULT_PROFILE_ID in config:
                    if config[DEFAULT_PROFILE_ID] == value:
                        self.session.remove(config[self.tid])
                        return
            else:
                if self.pid in config:
                    if config[self.pid] == value:
                        return

                elif DEFAULT_PROFILE_ID in config:
                    if config[DEFAULT_PROFILE_ID] == value:
                        return

        self.session.merge(ConfigL10N({'tid': self.tid, 'lang': lang, 'var_name': var_name, 'value': value}))

    def remove_val(self, tid, lang, var_name):
        self.session.query(ConfigL10N).filter(ConfigL10N.tid == tid, ConfigL10N.lang == lang, ConfigL10N.var_name == var_name).delete(synchronize_session=False)

    def reset(self, filter_name):
        self.session.query(ConfigL10N).filter(ConfigL10N.tid == self.tid, ConfigL10N.var_name.in_(ConfigFilters[filter_name]))

    def sync_profile(self, lang, t_result, d_result):
        result = self.session.query(Config).filter(Config.var_name == 'profile', Config.value == str(self.tid)).all()
        tid_list = [config.tid for config in result]

        for entry in self.session.query(ConfigL10N).filter(ConfigL10N.tid.in_(tid_list)).all():
            if (entry.var_name not in protected_keys and entry.var_name in t_result and t_result[entry.var_name] == entry.value) or (entry.var_name not in t_result and entry.var_name in d_result and d_result[entry.var_name] == entry.value):
                self.remove_val(entry.tid, lang, entry.var_name)

    def update(self, filter_name, data, lang):
        result, t_result, p_result, d_result = self.get_all(filter_name, lang)
        c_map = {c.var_name: c for c in result}

        for k in (x for x in ConfigL10NFilters[filter_name] if x in data):
            if k in c_map:
                if self.tid != self.pid:
                    if k in t_result:
                        if not data[k] or (k in p_result and data[k] == p_result[k].value) or (k not in p_result and k in d_result and data[k] == d_result[k].value):
                            self.remove_val(self.tid, lang, k)
                            del t_result[k]
                        else:
                            c_map[k].set_v(data[k])
                            t_result[k] = data[k]
                    elif (k in p_result and data[k] != p_result[k].value) or (k not in p_result and data[k] != d_result[k].value):
                        self.session.add(ConfigL10N({'tid': self.tid, 'lang': lang, 'var_name': k, 'value': data[k]}))
                else:
                    c_map[k].set_v(data[k])
                    t_result[k] = data[k]
            else:
                self.session.add(ConfigL10N({'tid': self.tid, 'lang': lang, 'var_name': k, 'value': data[k]}))

        if self.tid > DEFAULT_PROFILE_ID:
            self.sync_profile(lang, t_result, d_result)

    def serialize(self, filter_name, lang):
        rows, _, _, _ = self.get_all(filter_name, lang)

        ret = {var_name: "" for var_name in ConfigL10NFilters[filter_name]}

        for c in rows:
            if c.var_name in ConfigL10NFilters[filter_name]:
                ret[c.var_name] = c.value

        return ret


def db_get_config_variable(session, tid, var):
    return ConfigFactory(session, tid).get_val(var)


def db_set_config_variable(session, tid, var, val):
    ConfigFactory(session, tid).set_val(var, val)


def initialize_config(session, tid, data):
    variables = {}

    # Initialization valid for any tenant
    for name, desc in ConfigDescriptor.items():
        variables[name] = get_default(desc.default)

    if tid != 1:
        # Initialization valid for secondary tenants
        variables['mode'] = data['mode']
        variables['profile'] = data['profile']

    if data['mode'] == 'default':
        variables['onionservice'], variables['tor_onion_key'] = generate_onion_service_v3()

    if data['mode'] == 'wbpa':
        root_tenant_node = ConfigFactory(session, 1).serialize('node')
        for name in inherit_from_root_tenant:
            variables[name] = root_tenant_node[name]

    if tid == 1:
        for name in root_tenant_keys:
            session.add(Config({'tid': tid, 'var_name': name, 'value': variables[name]}))

    elif tid < 1000001:
        for name in secondary_tenant_keys:
            session.add(Config({'tid': tid, 'var_name': name, 'value': variables[name]}))

    elif tid == DEFAULT_PROFILE_ID:
        for name, value in variables.items():
            session.add(Config({'tid': tid, 'var_name': name, 'value': value}))


def load_defaults(session, appdata):
    session.query(Config).filter(Config.tid == DEFAULT_PROFILE_ID).delete(synchronize_session=False)
    session.query(ConfigL10N).filter(ConfigL10N.tid == DEFAULT_PROFILE_ID).delete(synchronize_session=False)

    keys = ConfigDescriptor.keys()
    for key in keys:
        session.add(Config({'tid': DEFAULT_PROFILE_ID, 'var_name': key, 'value': get_default(ConfigDescriptor[key].default)}))

    for lang in LANGUAGES_SUPPORTED_CODES:
        for d in ['node', 'notification']:
            keys = ConfigL10NFilters[d]

            if d == 'notification':
                data = appdata['templates']
            else:
                data = appdata[d]

            for k in keys:
                value = data[k][lang] if k in data else ''
                if value:
                    session.add(ConfigL10N({'tid': DEFAULT_PROFILE_ID, 'lang': lang, 'var_name': k, 'value': value}))

    session.flush()

    subquery = session.query(
        Config.var_name,
        Config.value
    ).filter(Config.tid == DEFAULT_PROFILE_ID, Config.var_name.notin_(protected_keys))

    stmt = delete(Config).where(
        and_(
            Config.tid != DEFAULT_PROFILE_ID,
            or_(
                tuple_(Config.var_name, Config.value).in_(subquery),
                Config.value == ''
            )
        )
    )

    session.execute(stmt.execution_options(synchronize_session=False))

    subquery = session.query(
        ConfigL10N.var_name,
        ConfigL10N.lang,
        ConfigL10N.value
    ).filter(ConfigL10N.tid == DEFAULT_PROFILE_ID)

    stmt = delete(ConfigL10N).where(
        and_(
            ConfigL10N.tid != DEFAULT_PROFILE_ID,
            or_(
                tuple_(ConfigL10N.var_name, ConfigL10N.lang, ConfigL10N.value).in_(subquery),
                ConfigL10N.value == ''
            )
        )
    )

    session.execute(stmt.execution_options(synchronize_session=False))
