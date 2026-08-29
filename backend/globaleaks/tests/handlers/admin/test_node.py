from twisted.internet.defer import inlineCallbacks

from globaleaks import __version__, models
from globaleaks.handlers.admin import node
from globaleaks.jobs.delivery import Delivery
from globaleaks.models.config import db_set_config_variable
from globaleaks.orm import transact
from globaleaks.rest.errors import InputValidationError
from globaleaks.state import State
from globaleaks.tests import helpers
from globaleaks.utils.utility import datetime_now


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
        self.dummyNode['custom_support_url'] = 'https://globaleaks.org'

        handler = self.request(self.dummyNode, role='admin')
        response = yield handler.put()
        self.assertTrue(isinstance(response, dict))
        self.assertTrue(response['version'], __version__)
        self.assertEqual(response['custom_support_url'], 'https://globaleaks.org')

    @inlineCallbacks
    def test_put_update_antivirus_clamd_endpoint(self):
        self.dummyNode['antivirus_enabled'] = True
        self.dummyNode['antivirus_clamd_ip'] = '192.0.2.10'
        self.dummyNode['antivirus_clamd_port'] = 3311

        handler = self.request(self.dummyNode, role='admin')
        response = yield handler.put()

        self.assertEqual(response['antivirus_clamd_ip'], '192.0.2.10')
        self.assertEqual(response['antivirus_clamd_port'], 3311)

    @inlineCallbacks
    def test_put_updates_antivirus_runtime_cache(self):
        self.dummyNode['antivirus_enabled'] = True
        self.dummyNode['antivirus_clamd_ip'] = '192.0.2.20'
        self.dummyNode['antivirus_clamd_port'] = 3320

        handler = self.request(self.dummyNode, role='admin')
        yield handler.put()

        tenant_cache = self.state.tenants[1].cache
        self.assertTrue(tenant_cache.antivirus_enabled)
        self.assertEqual(tenant_cache.antivirus_clamd_ip, '192.0.2.20')
        self.assertEqual(tenant_cache.antivirus_clamd_port, 3320)

    @inlineCallbacks
    def test_put_disable_antivirus_resets_file_verification(self):
        yield self.perform_minimal_submission_actions()
        yield Delivery().run()
        file_id = yield self.set_antivirus_file_state(True)

        self.dummyNode['antivirus_enabled'] = False
        handler = self.request(self.dummyNode, role='admin')
        yield handler.put()

        state, verification_date = yield self.get_antivirus_file_state(file_id)
        self.assertEqual(state, 'pending')
        self.assertIsNone(verification_date)

    @inlineCallbacks
    def test_put_update_antivirus_clamd_endpoint(self):
        self.dummyNode['antivirus_enabled'] = True
        self.dummyNode['antivirus_clamd_ip'] = '192.0.2.10'
        self.dummyNode['antivirus_clamd_port'] = 3311

        handler = self.request(self.dummyNode, role='admin')
        response = yield handler.put()

        self.assertEqual(response['antivirus_clamd_ip'], '192.0.2.10')
        self.assertEqual(response['antivirus_clamd_port'], 3311)

    @inlineCallbacks
    def test_put_updates_antivirus_runtime_cache(self):
        self.dummyNode['antivirus_enabled'] = True
        self.dummyNode['antivirus_clamd_ip'] = '192.0.2.20'
        self.dummyNode['antivirus_clamd_port'] = 3320

        handler = self.request(self.dummyNode, role='admin')
        yield handler.put()

        tenant_cache = self.state.tenants[1].cache
        self.assertTrue(tenant_cache.antivirus_enabled)
        self.assertEqual(tenant_cache.antivirus_clamd_ip, '192.0.2.20')
        self.assertEqual(tenant_cache.antivirus_clamd_port, 3320)

    @inlineCallbacks
    def test_put_disable_antivirus_resets_file_verification(self):
        yield self.perform_minimal_submission_actions()
        yield Delivery().run()
        file_id = yield self.set_antivirus_file_state(True)

        self.dummyNode['antivirus_enabled'] = False
        handler = self.request(self.dummyNode, role='admin')
        yield handler.put()

        state, verification_date = yield self.get_antivirus_file_state(file_id)
        self.assertEqual(state, 'pending')
        self.assertIsNone(verification_date)

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
    def test_put_antivirus_and_backup_ignored_on_secondary_tenant(self):
        self.dummyNode['antivirus_enabled'] = True
        self.dummyNode['antivirus_clamd_ip'] = '192.0.2.30'
        self.dummyNode['antivirus_clamd_port'] = 3330
        self.dummyNode['backup_enabled'] = True

        handler = self.request(self.dummyNode, role='admin', tid=2)
        response = yield handler.put()

        self.assertFalse(response['antivirus_enabled'])
        self.assertEqual(response['antivirus_clamd_ip'], 'localhost')
        self.assertEqual(response['antivirus_clamd_port'], 3310)
        self.assertFalse(response['backup_enabled'])

    @inlineCallbacks
    def test_update_ignored_fields(self):
        self.dummyNode['version'] = 'xxx'

        handler = self.request(self.dummyNode, role='admin')

        resp = yield handler.put()

        self.assertNotEqual('version', resp['version'])
