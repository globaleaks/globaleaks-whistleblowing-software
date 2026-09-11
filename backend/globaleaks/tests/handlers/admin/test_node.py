from twisted.internet.defer import inlineCallbacks

from globaleaks import __version__, models
from globaleaks.handlers.admin import node, tenant
from globaleaks.models.config import db_get_config_variable, db_set_config_variable
from globaleaks.orm import transact, tw
from globaleaks.rest.errors import InputValidationError
from globaleaks.state import State
from globaleaks.tests import helpers
from globaleaks.utils.utility import datetime_now


class FakeBackupJob:
    name = "Backup"
    interval = 24 * 3600
    last_executions = []

    def __init__(self):
        self.running = False
        self.scheduled = False

    def get_delay(self):
        return 0

    def schedule(self):
        self.scheduled = True
        self.running = True
        State.jobs_status["Backup"] = {"status": "running", "execution_time": 0}

    def stop(self):
        self.running = False
        State.jobs_status["Backup"]["status"] = "stopped"


class TestNodeInstance(helpers.TestHandlerWithPopulatedDB):
    _handler = node.NodeInstance

    @transact
    def set_antivirus_file_state(self, session, enabled):
        db_set_config_variable(session, 1, 'antivirus_enabled', enabled)
        ifile = session.query(models.InternalFile).first()
        ifile.state = 'verified'
        ifile.verification_date = datetime_now()
        return ifile.id

    @transact
    def get_antivirus_file_state(self, session, file_id):
        ifile = session.query(models.InternalFile).filter_by(id=file_id).one()
        return ifile.state, ifile.verification_date

    @inlineCallbacks
    def test_get(self):
        handler = self.request(role='admin')
        response = yield handler.get()

        self.assertTrue(response['version'], __version__)

    @inlineCallbacks
    def test_put_update_node(self):
        self.dummy_node['custom_support_url'] = 'https://globaleaks.org'

        handler = self.request(self.dummy_node, role='admin')
        response = yield handler.put()
        self.assertTrue(isinstance(response, dict))
        self.assertTrue(response['version'], __version__)
        self.assertEqual(response['custom_support_url'], 'https://globaleaks.org')


    @inlineCallbacks
    def test_put_update_node_invalid_lang(self):
        self.dummy_node['languages_enabled'] = ["en", "shit"]
        handler = self.request(self.dummy_node, role='admin')

        yield self.assertFailure(handler.put(), InputValidationError)

    @inlineCallbacks
    def test_put_update_node_languages(self):
        # this tests start setting en as the only enabled language and
        # ends keeping enabled only french.
        self.dummy_node['languages_enabled'] = ["en"]
        self.dummy_node['default_language'] = "en"
        handler = self.request(self.dummy_node, role='admin')
        yield handler.put()

        self.dummy_node['languages_enabled'] = ["fr"]
        self.dummy_node['default_language'] = "fr"
        handler = self.request(self.dummy_node, role='admin')
        yield handler.put()


    @inlineCallbacks
    def test_update_ignored_fields(self):
        self.dummy_node['version'] = 'xxx'

        handler = self.request(self.dummy_node, role='admin')

        resp = yield handler.put()

        self.assertNotEqual('version', resp['version'])


@transact
def languages_of(session, tid):
    return sorted(x[0] for x in session.query(models.EnabledLanguage.name)
                                       .filter(models.EnabledLanguage.tid == tid))


@transact
def update_node(session, tid, request):
    return node.db_update_node(session, tid, None, request, 'en')


class TestProfileLanguages(helpers.TestGLWithPopulatedDB):
    """
    A site naming a profile speaks the languages of the profile, and those alone
    """
    @inlineCallbacks
    def setUp(self):
        yield helpers.TestGLWithPopulatedDB.setUp(self)

        profile = yield tenant.create({'name': 'A profile',
                                       'active': True,
                                       'subdomain': '',
                                       'profile': 'default'}, is_profile=True)

        self.pid = profile['id']

        uuid = yield tw(db_get_config_variable, self.pid, 'uuid')
        yield tw(db_set_config_variable, 2, 'profile', uuid)

    @inlineCallbacks
    def test_a_site_naming_a_profile_does_not_change_its_languages(self):
        spoken = yield languages_of(2)

        yield update_node(2, {'languages_enabled': ['fr'], 'default_language': 'fr'})

        self.assertEqual((yield languages_of(2)), spoken)

    @inlineCallbacks
    def test_a_language_the_profile_adds_reaches_the_sites_naming_it(self):
        yield update_node(self.pid, {'languages_enabled': ['en', 'fr'], 'default_language': 'en'})

        self.assertEqual((yield languages_of(2)), ['en', 'fr'])

    @inlineCallbacks
    def test_a_language_the_profile_drops_leaves_the_sites_naming_it(self):
        yield update_node(self.pid, {'languages_enabled': ['en', 'fr'], 'default_language': 'en'})
        yield update_node(self.pid, {'languages_enabled': ['fr'], 'default_language': 'fr'})

        self.assertEqual((yield languages_of(2)), ['fr'])
        self.assertEqual((yield tw(db_get_config_variable, 2, 'default_language')), 'fr')

    @inlineCallbacks
    def test_a_site_naming_no_profile_changes_its_languages(self):
        yield tw(db_set_config_variable, 2, 'profile', 'default')

        yield update_node(2, {'languages_enabled': ['en', 'fr'], 'default_language': 'en'})

        self.assertEqual((yield languages_of(2)), ['en', 'fr'])
