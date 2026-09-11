from twisted.internet.defer import inlineCallbacks
import os
import re

import globaleaks
from globaleaks import models
from globaleaks.models import config
from globaleaks.handlers.admin import tenant
from globaleaks.models.config_desc import ConfigDescriptor
from globaleaks.orm import transact, tw
from globaleaks.tests import helpers


class TestModels(helpers.TestGL):
    initialize_test_database_using_archived_db = False

    def test_threshold_config_references_are_consistent(self):
        # Every threshold_* knob declared in ConfigDescriptor must be read from
        # the tenant cache somewhere in the backend, and every threshold_*
        # attribute read from the cache must be declared. This catches typos in
        # cache attribute names (a wrong name would only fail at runtime when
        # the endpoint is hit) and configuration knobs left as dead code.
        declared = {k for k in ConfigDescriptor if k.startswith('threshold_')}

        referenced = set()
        pattern = re.compile(r'\.(threshold_[a-z0-9_]+)')
        root = os.path.dirname(globaleaks.__file__)
        for dirpath, _, filenames in os.walk(root):
            if 'tests' in dirpath.split(os.sep):
                continue
            for filename in filenames:
                if not filename.endswith('.py'):
                    continue
                with open(os.path.join(dirpath, filename), encoding='utf-8') as fd:
                    referenced.update(pattern.findall(fd.read()))

        self.assertEqual(referenced - declared, set(),
                         'threshold(s) read from cache but missing from ConfigDescriptor')
        self.assertEqual(declared - referenced, set(),
                         'threshold(s) declared in ConfigDescriptor but never read')

    def test_initialize_config(self):
        @transact
        def transaction(session):
            session.query(models.Config).filter(models.Config.tid == 1).delete()
            config.initialize_config(session, 1, {})

        return transaction()


@transact
def own_rows(session, tid, var_name):
    return session.query(models.Config).filter(models.Config.tid == tid, models.Config.var_name == var_name).count()


@transact
def own_l10n_rows(session, tid, lang, var_name):
    return session.query(models.ConfigL10N).filter(models.ConfigL10N.tid == tid,
                                                   models.ConfigL10N.lang == lang,
                                                   models.ConfigL10N.var_name == var_name).count()


@transact
def read(session, tid, var_name):
    return config.ConfigFactory(session, tid).get_val(var_name)


@transact
def write(session, tid, var_name, value):
    config.ConfigFactory(session, tid).set_val(var_name, value)


@transact
def read_l10n(session, tid, lang, var_name):
    return config.ConfigL10NFactory(session, tid).get_val(lang, var_name)


@transact
def write_l10n(session, tid, lang, var_name, value):
    config.ConfigL10NFactory(session, tid).set_val(lang, var_name, value)


@transact
def update_profile(session, filter_name, data):
    config.ConfigFactory(session, config.DEFAULT_PROFILE_ID).update(filter_name, data)


@transact
def update_node_l10n(session, tid, lang, data):
    config.ConfigL10NFactory(session, tid).update('node', data, lang)


class TestConfigInheritance(helpers.TestGLWithPopulatedDB):
    """
    A site resolves what it does not set from its profile; what it sets equal to the profile is
    not kept
    """
    VAR = 'threshold_logins_per_minute_per_ip'

    @inlineCallbacks
    def test_a_value_not_set_on_the_site_is_inherited(self):
        inherited = yield read(config.DEFAULT_PROFILE_ID, self.VAR)

        self.assertEqual((yield read(2, self.VAR)), inherited)
        self.assertEqual((yield own_rows(2, self.VAR)), 0)

    @inlineCallbacks
    def test_setting_the_inherited_value_leaves_no_override(self):
        inherited = yield read(config.DEFAULT_PROFILE_ID, self.VAR)

        yield write(2, self.VAR, inherited)

        self.assertEqual((yield own_rows(2, self.VAR)), 0)

    @inlineCallbacks
    def test_an_override_is_kept_until_it_equals_the_profile_again(self):
        inherited = yield read(config.DEFAULT_PROFILE_ID, self.VAR)

        yield write(2, self.VAR, inherited + 10)
        self.assertEqual((yield read(2, self.VAR)), inherited + 10)
        self.assertEqual((yield own_rows(2, self.VAR)), 1)
        # the other sites are untouched
        self.assertEqual((yield read(3, self.VAR)), inherited)

        yield write(2, self.VAR, inherited)
        self.assertEqual((yield read(2, self.VAR)), inherited)
        self.assertEqual((yield own_rows(2, self.VAR)), 0)

    @inlineCallbacks
    def test_a_profile_update_drops_the_overrides_it_makes_redundant(self):
        inherited = yield read(config.DEFAULT_PROFILE_ID, self.VAR)

        yield write(2, self.VAR, inherited + 10)
        yield update_profile('node', {self.VAR: inherited + 10})

        self.assertEqual((yield read(config.DEFAULT_PROFILE_ID, self.VAR)), inherited + 10)
        self.assertEqual((yield read(2, self.VAR)), inherited + 10)
        self.assertEqual((yield own_rows(2, self.VAR)), 0)

    @inlineCallbacks
    def test_a_protected_key_stays_on_the_site_even_when_equal_to_the_profile(self):
        # the state of the encryption is read on the row of the site itself
        inherited = yield read(config.DEFAULT_PROFILE_ID, 'encryption')

        yield write(2, 'encryption', inherited)

        self.assertEqual((yield own_rows(2, 'encryption')), 1)

    @inlineCallbacks
    def test_a_text_follows_the_same_rule(self):
        # the profile holds the text the sites inherit
        yield write_l10n(config.DEFAULT_PROFILE_ID, 'en', 'header_title_homepage', 'The title of the profile')
        self.assertEqual((yield read_l10n(2, 'en', 'header_title_homepage')), 'The title of the profile')
        self.assertEqual((yield own_l10n_rows(2, 'en', 'header_title_homepage')), 0)

        yield write_l10n(2, 'en', 'header_title_homepage', 'A title of the site')
        self.assertEqual((yield read_l10n(2, 'en', 'header_title_homepage')), 'A title of the site')
        self.assertEqual((yield own_l10n_rows(2, 'en', 'header_title_homepage')), 1)

        yield write_l10n(2, 'en', 'header_title_homepage', 'The title of the profile')
        self.assertEqual((yield read_l10n(2, 'en', 'header_title_homepage')), 'The title of the profile')
        self.assertEqual((yield own_l10n_rows(2, 'en', 'header_title_homepage')), 0)

    @inlineCallbacks
    def test_saving_the_form_holds_the_text_that_changed_and_no_other(self):
        # the form sends every text it shows, and the ones left empty have no row of their own
        # anywhere: saving must not turn them into values the site holds
        texts = ['presentation', 'header_title_homepage', 'whistleblowing_question', 'footer']
        before = {}
        for var_name in texts:
            before[var_name] = yield own_l10n_rows(3, 'en', var_name)

        yield update_node_l10n(3, 'en', {'presentation': 'What this site is for',
                                         'header_title_homepage': '',
                                         'whistleblowing_question': '',
                                         'footer': ''})

        self.assertEqual((yield own_l10n_rows(3, 'en', 'presentation')), 1)
        for var_name in texts[1:]:
            self.assertLessEqual((yield own_l10n_rows(3, 'en', var_name)), before[var_name])


@transact
def held_keys(session, tid):
    return config.db_get_held_keys(session, tid)


@transact
def update_node(session, tid, data):
    config.ConfigFactory(session, tid).update('node', data)


class TestProfileLock(helpers.TestGLWithPopulatedDB):
    """
    A site naming a profile writes only the variables the profile unlocks
    """
    @inlineCallbacks
    def setUp(self):
        yield helpers.TestGLWithPopulatedDB.setUp(self)

        profile = yield tenant.create({'name': 'A profile',
                                       'active': True,
                                       'subdomain': '',
                                       'profile': 'default'}, is_profile=True)

        self.pid = profile['id']

        # the site names the profile by the UUID the profile holds
        uuid = yield read(self.pid, 'uuid')
        yield tw(config.db_set_config_variable, 2, 'profile', uuid)

    @inlineCallbacks
    def unlock(self, keys):
        yield tw(config.db_set_config_variable, self.pid, 'unlocked_keys', keys)

    @inlineCallbacks
    def test_a_locked_variable_is_not_written(self):
        inherited = yield read(2, 'custom_support_url')

        yield update_node(2, {'custom_support_url': 'https://support.example.org'})

        self.assertEqual((yield read(2, 'custom_support_url')), inherited)
        self.assertEqual((yield own_rows(2, 'custom_support_url')), 0)

    @inlineCallbacks
    def test_an_unlocked_variable_is_written(self):
        yield self.unlock(['custom_support_url'])

        yield update_node(2, {'custom_support_url': 'https://support.example.org'})

        self.assertEqual((yield read(2, 'custom_support_url')), 'https://support.example.org')
        self.assertEqual((yield own_rows(2, 'custom_support_url')), 1)

    @inlineCallbacks
    def test_a_variable_the_application_never_unlocks_stays_locked(self):
        # the profile names it, but it is not among the ones that can be unlocked at all
        yield self.unlock(['encryption', 'custom_support_url'])
        inherited = yield read(2, 'enable_signup')

        yield update_node(2, {'enable_signup': not inherited})

        self.assertEqual((yield read(2, 'enable_signup')), inherited)

    @inlineCallbacks
    def test_a_variable_the_site_owns_stays_writable(self):
        # the name of a site is its own: no profile hands it, so none withholds it
        yield update_node(2, {'name': 'The name of the site'})

        self.assertEqual((yield read(2, 'name')), 'The name of the site')

    @inlineCallbacks
    def test_a_locked_text_is_not_written(self):
        yield write_l10n(self.pid, 'en', 'header_title_homepage', 'The title of the profile')

        yield update_node_l10n(2, 'en', {'header_title_homepage': 'A title of the site'})

        self.assertEqual((yield read_l10n(2, 'en', 'header_title_homepage')), 'The title of the profile')
        self.assertEqual((yield own_l10n_rows(2, 'en', 'header_title_homepage')), 0)

    @inlineCallbacks
    def test_an_unlocked_text_is_written(self):
        yield write_l10n(self.pid, 'en', 'header_title_homepage', 'The title of the profile')
        yield self.unlock(['header_title_homepage'])

        yield update_node_l10n(2, 'en', {'header_title_homepage': 'A title of the site'})

        self.assertEqual((yield read_l10n(2, 'en', 'header_title_homepage')), 'A title of the site')
        self.assertEqual((yield own_l10n_rows(2, 'en', 'header_title_homepage')), 1)

    @inlineCallbacks
    def test_what_the_site_holds_is_what_it_wrote_differently(self):
        yield self.unlock(['custom_support_url'])

        self.assertNotIn('custom_support_url', (yield held_keys(2)))

        yield update_node(2, {'custom_support_url': 'https://support.example.org'})

        self.assertIn('custom_support_url', (yield held_keys(2)))

    @inlineCallbacks
    def test_a_value_written_back_to_the_inherited_one_is_not_held(self):
        yield self.unlock(['custom_support_url'])
        inherited = yield read(2, 'custom_support_url')

        yield update_node(2, {'custom_support_url': 'https://support.example.org'})
        yield update_node(2, {'custom_support_url': inherited})

        self.assertNotIn('custom_support_url', (yield held_keys(2)))

    @inlineCallbacks
    def test_what_no_form_configures_is_not_held(self):
        # the keys and the counters a site keeps for itself are not a configuration of the site
        held = yield held_keys(1)

        self.assertNotIn('crypto_stat_prv_key', held)
        self.assertNotIn('https_selfsigned_key', held)

    @inlineCallbacks
    def test_the_variables_a_site_owns_in_any_case_are_not_held(self):
        # the name and the subdomain tell one site from another: they are not a customization
        held = yield held_keys(2)

        self.assertNotIn('name', held)
        self.assertNotIn('subdomain', held)

    @inlineCallbacks
    def test_a_site_naming_no_profile_writes_what_it_likes(self):
        yield update_node(3, {'custom_support_url': 'https://support.example.org'})

        self.assertEqual((yield read(3, 'custom_support_url')), 'https://support.example.org')
