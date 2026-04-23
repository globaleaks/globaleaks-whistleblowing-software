from unittest.mock import patch

from twisted.internet.defer import inlineCallbacks, succeed

from globaleaks import __version__, models
from globaleaks.handlers.admin import node
from globaleaks.jobs.delivery import Delivery
from globaleaks.models.config import db_set_config_variable
from globaleaks.orm import transact
from globaleaks.rest.errors import InputValidationError
from globaleaks.tests import helpers
from globaleaks.utils.utility import datetime_now


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
        self.dummyNode['custom_support_url'] = 'https://www.globaleaks.org'

        handler = self.request(self.dummyNode, role='admin')
        response = yield handler.put()
        self.assertTrue(isinstance(response, dict))
        self.assertTrue(response['version'], __version__)
        self.assertEqual(response['custom_support_url'], 'https://www.globaleaks.org')

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
    def test_put_syncs_antivirus_runtime_with_updated_cache(self):
        self.dummyNode['antivirus_enabled'] = True
        self.dummyNode['antivirus_clamd_ip'] = '192.0.2.20'
        self.dummyNode['antivirus_clamd_port'] = 3320

        def assert_runtime_sync():
            tenant_cache = self.state.tenants[1].cache
            self.assertTrue(tenant_cache.antivirus_enabled)
            self.assertEqual(tenant_cache.antivirus_clamd_ip, '192.0.2.20')
            self.assertEqual(tenant_cache.antivirus_clamd_port, 3320)
            return succeed(None)

        with patch('globaleaks.handlers.admin.node.antivirus_service.sync_antivirus_runtime',
                   side_effect=assert_runtime_sync) as sync_runtime:
            handler = self.request(self.dummyNode, role='admin')
            yield handler.put()

        sync_runtime.assert_called_once_with()

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
    def test_update_ignored_fields(self):
        self.dummyNode['version'] = 'xxx'

        handler = self.request(self.dummyNode, role='admin')

        resp = yield handler.put()

        self.assertNotEqual('version', resp['version'])
