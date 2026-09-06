from twisted.internet.defer import inlineCallbacks

from globaleaks import __version__, models
from globaleaks.handlers.admin import node
from globaleaks.models.config import db_set_config_variable
from globaleaks.orm import transact
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
