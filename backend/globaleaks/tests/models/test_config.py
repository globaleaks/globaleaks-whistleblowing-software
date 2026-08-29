from twisted.internet.defer import inlineCallbacks
import os
import re

import globaleaks
from globaleaks import models
from globaleaks.models import config
from globaleaks.models.config_desc import ConfigDescriptor
from globaleaks.orm import transact
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
