# -*- coding: utf-8 -*-
from sqlalchemy import not_
from sqlalchemy import or_
from globaleaks.models import Config, ConfigL10N, EnabledLanguage
from globaleaks.models.properties import *
from globaleaks.models.config_desc import ConfigDescriptor, ConfigFilters, ConfigL10NFilters
from globaleaks.utils.onion import generate_onion_service_v3


from globaleaks.utils.utility import datetime_null


import copy
# List of variables that on creation are set with the value
# they have on the root tenant
inherit_from_root_tenant = ['default_questionnaire']
default_tenant_keys = ["subdomain", "tor_onion_key", "onionservice", "https_admin", "https_analyst", "https_cert", "wizard_done", "uuid", "mode", "name", "encryption", "https_whistleblower", "receipt_salt", "crypto_escrow_pub_key", "counter_submissions"]


def get_default(default):
    if callable(default):
        return default()

    return default

def process_items(combined_values, default_profile_id, tid, pid):
    result = {}
    default_tenant_result = {}
    t_result = {}
    p_result = {}
    for item in combined_values:
        if item.tid == default_profile_id:
            default_tenant_result[item.var_name] = item
            if item.var_name not in result:
                result[item.var_name] = item
        if item.tid == pid:
            p_result[item.var_name] = item
            if item.var_name not in result or item.var_name not in t_result:
                result[item.var_name] = item
        if item.tid == tid:
            t_result[item.var_name] = item
            result[item.var_name] = item

    return result, default_tenant_result, t_result, p_result

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
        self.default_profile_id = 1000001
        self.tid = tid
        self.parent_profile = None
        self.init_default_profile_id()

    def init_default_profile_id(self):
        default_profile = self.session.query(Config.value).filter(
            Config.tid == self.tid,
            Config.var_name == 'default_profile',
        ).scalar()

        if default_profile is not None and default_profile != "default":
            self.parent_profile = int(default_profile)

    def get_all(self, filter_name):
        filters = [Config.var_name.in_(ConfigFilters[filter_name]), or_(
          Config.tid == self.default_profile_id,
          Config.tid == self.tid,
          Config.tid == self.parent_profile
        )]

        combined_values = self.session.query(Config).filter(*filters).all()
        return process_items(combined_values, self.default_profile_id, self.tid, self.parent_profile)

    def update(self, filter_name, data):
        result, default_tenant_result, t_result, p_result = self.get_all(filter_name)
        for k, v in result.items():
            if k in data:
                if self.tid != self.default_profile_id and self.tid != 1:
                    if k in t_result:
                        if (k in p_result and data[k] == p_result[k].value) or (k not in p_result and data[k] == default_tenant_result[k].value):
                            if k not in default_tenant_keys:
                                self.remove_val(k, self.tid)
                                del t_result[k]
                        else:
                            v.set_v(data[k])
                            t_result[k] = data[k]
                    elif (k in p_result and data[k] != p_result[k].value) or (k not in p_result and data[k] != default_tenant_result[k].value):
                        self.session.add(Config({'tid': self.tid, 'var_name': k, 'value': data[k]}))
                else:
                    t_result[k] = data[k]
                    v.set_v(data[k])

        if self.tid > self.default_profile_id:
            self.sync_profile(default_tenant_result, t_result)

    def sync_profile(self, default_tenant_result, t_result):
        result = self.session.query(Config).filter(Config.var_name == 'default_profile', Config.value == str(self.tid)).all()
        tid_list = [config.tid for config in result]

        for entry in self.session.query(Config).filter(Config.tid.in_(tid_list)).all():
            if entry.var_name not in default_tenant_keys and entry.var_name in t_result and t_result[entry.var_name] == entry.value or entry.var_name not in t_result and entry.var_name in default_tenant_result and default_tenant_result[entry.var_name].value == entry.value:
                self.remove_val(entry.var_name, entry.tid)

    def get_cfg(self, var_name):
        configurations = self.session.query(Config).filter(Config.var_name == var_name).filter(
            Config.tid.in_([self.tid, self.parent_profile, self.default_profile_id])
        ).all()

        config_map = {config.tid: config for config in configurations}

        return (
                config_map.get(self.tid) or
                config_map.get(self.parent_profile) or
                config_map.get(self.default_profile_id)
        )

    def get_val(self, var_name):
        config = self.get_cfg(var_name)
        if config is None:
            return get_default(ConfigDescriptor[var_name].default)

        new_config = copy.deepcopy(config)
        new_config.tid = self.tid
        return new_config.value

    def set_val(self, var_name, value):
        v = self.get_cfg(var_name)
        if v:
            v.set_v(value)

    def remove_val(self, var_name, tid):
        v = self.session.query(Config).filter(Config.tid == tid, Config.var_name == var_name).one_or_none()

        if v:
            self.session.delete(v)
            self.session.commit()

    def serialize(self, filter_name):
        values, _, _, _ = self.get_all(filter_name)
        return {k: v.value for k, v in values.items()}

    def update_defaults(self):
        actual = set([c[0] for c in self.session.query(Config.var_name).filter(Config.tid == self.tid)])
        allowed = set(ConfigDescriptor.keys())
        extra = list(actual - allowed)

        if extra:
            self.session.query(Config).filter(Config.tid == self.tid, Config.var_name.in_(extra)).delete(synchronize_session=False)

        missing = list(allowed - actual)
        for key in missing:
            self.session.add(Config({'tid': self.tid, 'var_name': key, 'value': get_default(ConfigDescriptor[key].default)}))


class ConfigL10NFactory(object):
    def __init__(self, session, tid):
        self.session = session
        self.default_profile_id = 1000001
        self.tid = tid

    def initialize(self, keys, lang, data):
        if self.tid == self.default_profile_id or self.tid == 1:
            for key in keys:
                value = data[key][lang] if key in data else ''
                self.session.add(ConfigL10N({'tid': self.tid, 'lang': lang, 'var_name': key, 'value': value}))

    def get_all(self, filter_name, lang):

        default_profile_value = None
        filters = [ConfigL10N.lang == lang,ConfigL10N.var_name.in_(ConfigL10NFilters[filter_name])]

        default_profile = self.session.query(Config.value).filter(
            Config.tid == self.tid,
            Config.var_name == 'default_profile',
        ).scalar()

        if default_profile is not None and default_profile != "default":
            default_profile_value = int(default_profile)

        filters.append(
            or_(
                ConfigL10N.tid == self.default_profile_id,
                ConfigL10N.tid == self.tid,
                ConfigL10N.tid == default_profile_value
            )
        )

        combined_values = self.session.query(ConfigL10N).filter(*filters).all()
        result, default_tenant_result, t_result ,p_result = process_items(combined_values, self.default_profile_id, self.tid, default_profile_value)
        return list(result.values()), default_tenant_result, t_result,p_result

    def serialize(self, filter_name, lang):
        rows, _, _ ,_= self.get_all(filter_name, lang)
        return {c.var_name: c.value for c in rows if c.var_name in ConfigL10NFilters[filter_name]}

    def update(self, filter_name, data, lang):
        result, default_tenant_result, t_result, p_result = self.get_all(filter_name, lang)
        c_map = {c.var_name: c for c in result}

        for key in (x for x in ConfigL10NFilters[filter_name] if x in data):
            if key in c_map:
                if self.tid != self.default_profile_id and self.tid != 1:
                    if key in t_result:
                        if (key in p_result and data[key] == p_result[key].value) or (key not in p_result and data[key] == default_tenant_result[key].value):
                            if key not in default_tenant_keys:
                                self.remove_val(key, lang, self.tid)
                                del t_result[key]
                        else:
                            c_map[key].set_v(data[key])
                            t_result[key] = data[key]
                    elif (key in p_result and data[key] != p_result[key].value) or (key not in p_result and data[key] != default_tenant_result[key].value):
                        self.session.add(ConfigL10N({'tid': self.tid, 'lang': lang, 'var_name': key, 'value': data[key]}))
                else:
                    c_map[key].set_v(data[key])
                    t_result[key] = data[key]
        if self.tid > self.default_profile_id:
            self.sync_profile(lang, default_tenant_result, t_result)

    def sync_profile(self, lang, default_tenant_result, t_result):
        result = self.session.query(Config).filter(Config.var_name == 'default_profile', Config.value == str(self.tid)).all()
        tid_list = [config.tid for config in result]

        for entry in self.session.query(ConfigL10N).filter(ConfigL10N.tid.in_(tid_list)).all():
            if entry.var_name not in default_tenant_keys and entry.var_name in t_result and t_result[entry.var_name] == entry.value or entry.var_name not in t_result and entry.var_name in default_tenant_result and default_tenant_result[entry.var_name] == entry.value:
                self.remove_val(entry.var_name, lang,entry.tid)

    def update_defaults(self, filter_name, langs, data, reset=False):
        null = datetime_null()
        templates = data.get('templates', {})

        for lang in langs:
            old_keys = []

            values, _, _, _ = self.get_all(filter_name, lang)
            for cfg in values:
                old_keys.append(cfg.var_name)
                if (cfg.update_date == null or reset) and cfg.var_name in templates:
                    cfg.value = templates[cfg.var_name][lang]

            ConfigL10NFactory.initialize(self, list(set(ConfigL10NFilters[filter_name]) - set(old_keys)), lang, data)

    def get_val(self, var_name, lang):
        v = self.session.query(ConfigL10N.value).filter(ConfigL10N.tid == self.tid, ConfigL10N.lang == lang, ConfigL10N.var_name == var_name).one_or_none()
        if v is None:
            return ''

        return v.value

    def remove_val(self, var_name, lang, tid):
        v = self.session.query(ConfigL10N).filter(ConfigL10N.tid == tid, ConfigL10N.lang == lang, ConfigL10N.var_name == var_name).one_or_none()
        if v:
            self.session.delete(v)
            self.session.commit()

    def set_val(self, var_name, lang, value):
        v = self.session.query(ConfigL10N).filter(ConfigL10N.tid == self.tid, ConfigL10N.lang == lang, ConfigL10N.var_name == var_name).one_or_none()
        if v:
            v.set_v(value)

    def reset(self, filter_name, data):
        langs = [x[0] for x in self.session.query(EnabledLanguage.name).filter(EnabledLanguage.tid == self.tid)]
        self.update_defaults(filter_name, langs, data, reset=True)


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

    if data['mode'] == 'default':
        variables['onionservice'], variables['tor_onion_key'] = generate_onion_service_v3()

    if data['mode'] == 'wbpa':
        root_tenant_node = ConfigFactory(session, 1).serialize('node')
        for name in inherit_from_root_tenant:
            variables[name] = root_tenant_node[name]

    if tid in (1, 1000001):
        variables.pop('default_profile', None)

    for name, value in variables.items():
        if tid in (1, 1000001) or name in default_tenant_keys:
            session.add(Config({'tid': tid, 'var_name': name, 'value': value}))

    default_profile = data.get('default_profile')
    if default_profile and default_profile != 'default':
        variables['default_profile'] = default_profile
        session.add(Config({'tid': tid, 'var_name': 'default_profile', 'value': default_profile}))

def add_new_lang(session, tid, lang, appdata_dict):
    l = EnabledLanguage()
    l.tid = tid
    l.name = lang
    session.add(l)

    ConfigL10NFactory(session, tid).initialize(ConfigL10NFilters['node'], lang, appdata_dict['node'])
    ConfigL10NFactory(session, tid).initialize(ConfigL10NFilters['notification'], lang, appdata_dict['templates'])


def update_defaults(session, tid, appdata):
    ConfigFactory(session, tid).update_defaults()

    langs = [x[0] for x in session.query(EnabledLanguage.name).filter(EnabledLanguage.tid == tid)]

    session.query(ConfigL10N).filter(ConfigL10N.tid == tid, not_(ConfigL10N.var_name.in_(list(set(ConfigL10NFilters['node']).union(ConfigL10NFilters['notification']))))).delete(synchronize_session=False)

    ConfigL10NFactory(session, tid).update_defaults('node', langs, appdata['node'])
    ConfigL10NFactory(session, tid).update_defaults('notification', langs, appdata['templates'])