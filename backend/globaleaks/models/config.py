# -*- coding: utf-8 -*-
from sqlalchemy import not_
from globaleaks.models import Config, ConfigL10N, EnabledLanguage
from globaleaks.models.config_desc import ConfigDescriptor, ConfigFilters, ConfigL10NFilters
from globaleaks.utils.onion import generate_onion_service_v3


from globaleaks.utils.utility import datetime_null


# List of variables that on creation are set with the value
# they have on the root tenant
inherit_from_root_tenant = [
    'default_questionnaire'
]


def get_default(default):
    if callable(default):
        return default()

    return default


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

    def get_all(self, filter_name):
        return {c.var_name: c for c in self.session.query(Config).filter(Config.tid == self.tid, Config.var_name.in_(ConfigFilters[filter_name]))}

    def update(self, filter_name, data):
        for k, v in self.get_all(filter_name).items():
            if k in data:
                v.set_v(data[k])

    def get_cfg(self, var_name):
        return self.session.query(Config).filter(Config.tid == self.tid, Config.var_name == var_name).one_or_none()

    def get_val(self, var_name):
        v = self.get_cfg(var_name)
        if v is None:
            return get_default(ConfigDescriptor[var_name].default)

        return v.value

    def set_val(self, var_name, value):
        v = self.get_cfg(var_name)
        if v:
            v.set_v(value)

    def serialize(self, filter_name):
        return {k: v.value for k, v in self.get_all(filter_name).items()}

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
        self.tid = tid

    def initialize(self, keys, lang, data):
        for key in keys:
            value = data[key][lang] if key in data else ''
            self.session.add(ConfigL10N({'tid': self.tid, 'lang': lang, 'var_name': key, 'value': value}))

    def get_all(self, filter_name, lang):
        return list(self.session.query(ConfigL10N).filter(ConfigL10N.tid == self.tid, ConfigL10N.lang == lang, ConfigL10N.var_name.in_(ConfigL10NFilters[filter_name])))

    def serialize(self, filter_name, lang):
        rows = self.get_all(filter_name, lang)
        return {c.var_name: c.value for c in rows if c.var_name in ConfigL10NFilters[filter_name]}

    def update(self, filter_name, data, lang):
        c_map = {c.var_name: c for c in self.get_all(filter_name, lang)}

        for key in (x for x in ConfigL10NFilters[filter_name] if x in data):
            c_map[key].set_v(data[key])

    def update_defaults(self, filter_name, langs, data, reset=False):
        null = datetime_null()
        templates = data.get('templates', {})

        for lang in langs:
            old_keys = []

            for cfg in self.get_all(filter_name, lang):
                old_keys.append(cfg.var_name)
                if (cfg.update_date == null or reset) and cfg.var_name in templates:
                    cfg.value = templates[cfg.var_name][lang]

            ConfigL10NFactory.initialize(self, list(set(ConfigL10NFilters[filter_name]) - set(old_keys)), lang, data)

    def get_val(self, var_name, lang):
        v = self.session.query(ConfigL10N.value).filter(ConfigL10N.tid == self.tid, ConfigL10N.lang == lang, ConfigL10N.var_name == var_name).one_or_none()
        if v is None:
            return ''

        return v.value

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


def initialize_config(session, tid, mode):
    variables = {}

    # Initialization valid for any tenant
    for name, desc in ConfigDescriptor.items():
        variables[name] = get_default(desc.default)

    if tid != 1:
        # Initialization valid for secondary tenants
        variables['mode'] = mode

    if mode == 'default':
        variables['onionservice'], variables['tor_onion_key'] = generate_onion_service_v3()

    if mode == 'wbpa':
        root_tenant_node = ConfigFactory(session, 1).serialize('node')
        for name in inherit_from_root_tenant:
            variables[name] = root_tenant_node[name]

    variables['max_msg_external_to_whistle'] = 1
    variables['max_msg_external_to_whistle_not_aff'] = 1
    variables['external_organization_activation'] = True
    variables['url_file_analysis'] = 'http://localhost:3000/api/v1/scan'
    variables['global_stat_pub_key'] = ''

    for name, value in variables.items():
        session.add(Config({'tid': tid, 'var_name': name, 'value': value}))


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
