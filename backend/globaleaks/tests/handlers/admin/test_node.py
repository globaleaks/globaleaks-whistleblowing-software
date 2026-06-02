from twisted.internet.defer import inlineCallbacks

from globaleaks import __version__
from globaleaks.handlers.admin import node
from globaleaks.rest.errors import InputValidationError
from globaleaks.state import State
from globaleaks.tests import helpers


class FakeBackupJob:
    name = "Backup"
    interval = 24 * 3600

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

    @inlineCallbacks
    def test_get(self):
        handler = self.request(role='admin')
        response = yield handler.get()

        self.assertTrue(response['version'], __version__)

    @inlineCallbacks
    def test_put_update_node(self):
        self.dummyNode['custom_support_url'] = 'https://www.globaleaks.org'

        handler = self.request(self.dummyNode, role='admin')
        response = yield handler.put()
        self.assertTrue(isinstance(response, dict))
        self.assertTrue(response['version'], __version__)
        self.assertEqual(response['custom_support_url'], 'https://www.globaleaks.org')

    @inlineCallbacks
    def test_put_update_node_invalid_lang(self):
        self.dummyNode['languages_enabled'] = ["en", "shit"]
        handler = self.request(self.dummyNode, role='admin')

        yield self.assertFailure(handler.put(), InputValidationError)

    @inlineCallbacks
    def test_put_update_node_languages(self):
        # this tests start setting en as the only enabled language and
        # ends keeping enabled only french.
        self.dummyNode['languages_enabled'] = ["en"]
        self.dummyNode['default_language'] = "en"
        handler = self.request(self.dummyNode, role='admin')
        yield handler.put()

        self.dummyNode['languages_enabled'] = ["fr"]
        self.dummyNode['default_language'] = "fr"
        handler = self.request(self.dummyNode, role='admin')
        yield handler.put()

    @inlineCallbacks
    def test_put_backup_enabled_reschedules_and_stops_job(self):
        job = FakeBackupJob()
        State.jobs = [job]
        State.jobs_status["Backup"] = {"status": "stopped", "execution_time": 0}

        self.dummyNode['backup_enabled'] = True
        handler = self.request(self.dummyNode, role='admin')
        yield handler.put()
        self.assertTrue(job.scheduled)
        self.assertTrue(job.running)
        self.assertEqual(State.jobs_status["Backup"]["status"], "running")

        self.dummyNode['backup_enabled'] = False
        handler = self.request(self.dummyNode, role='admin')
        yield handler.put()
        self.assertFalse(job.running)
        self.assertEqual(State.jobs_status["Backup"]["status"], "stopped")

    @inlineCallbacks
    def test_update_ignored_fields(self):
        self.dummyNode['version'] = 'xxx'

        handler = self.request(self.dummyNode, role='admin')

        resp = yield handler.put()

        self.assertNotEqual('version', resp['version'])
