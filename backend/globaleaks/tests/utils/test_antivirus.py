import io
import unittest
from unittest.mock import patch, MagicMock

from twisted.internet import defer
from twisted.trial import unittest as twisted_unittest

from globaleaks.services import antivirus as antivirus_service
from globaleaks.state import State, TenantState
from globaleaks.utils.antivirus import FileAnalysis


class FileAnalysisMockedTests(twisted_unittest.TestCase):
    @defer.inlineCallbacks
    def test_scan_file_safe(self):
        mock_clamd = MagicMock()
        mock_clamd.scan_stream.return_value = None  # Safe file

        with patch('globaleaks.utils.antivirus.pyclamd.ClamdUnixSocket', return_value=mock_clamd):
            fa = FileAnalysis()
            result = yield fa.scan_file(io.BytesIO(b"This is a safe file"))
            self.assertEqual(result, 'safe')

    @defer.inlineCallbacks
    def test_scan_file_unsafe(self):
        mock_clamd = MagicMock()
        mock_clamd.scan_stream.return_value = {'stream': ('FOUND', 'Eicar-Test-Signature')}  # Unsafe file

        with patch('globaleaks.utils.antivirus.pyclamd.ClamdUnixSocket', return_value=mock_clamd):
            fa = FileAnalysis()
            result = yield fa.scan_file(io.BytesIO(b"EICAR"))
            self.assertEqual(result, 'unsafe')

    @defer.inlineCallbacks
    def test_scan_file_error(self):
        with patch('globaleaks.utils.antivirus.pyclamd.ClamdUnixSocket', side_effect=Exception("Connection failed")):
            fa = FileAnalysis()
            result = yield fa.scan_file(io.BytesIO(b"whatever"))
            self.assertEqual(result, 'error')

    @defer.inlineCallbacks
    def test_scan_file_tcp_endpoint(self):
        mock_clamd = MagicMock()
        mock_clamd.scan_stream.return_value = None

        with patch('globaleaks.utils.antivirus.pyclamd.ClamdNetworkSocket', return_value=mock_clamd) as clamd_socket:
            fa = FileAnalysis('tcp://192.0.2.10:3310')
            result = yield fa.scan_file(io.BytesIO(b"This is a safe file"))

            self.assertEqual(result, 'safe')
            clamd_socket.assert_called_once_with('192.0.2.10', 3310)


class AntivirusRuntimeTests(twisted_unittest.TestCase):
    def setUp(self):
        self._state_snapshot = {
            'tenants': State.tenants,
            'jobs': State.jobs,
            'services': State.services,
            'antivirus': getattr(State, 'antivirus', None)
        }

        State.tenants = {}
        State.jobs = []
        State.services = []
        State.antivirus = None

        root_tenant = TenantState()
        root_tenant.cache.antivirus_enabled = False
        root_tenant.cache.antivirus_clamd_ip = 'localhost'
        root_tenant.cache.antivirus_clamd_port = 3310
        State.tenants[1] = root_tenant

    def tearDown(self):
        State.tenants = self._state_snapshot['tenants']
        State.jobs = self._state_snapshot['jobs']
        State.services = self._state_snapshot['services']
        State.antivirus = self._state_snapshot['antivirus']

    @defer.inlineCallbacks
    def test_sync_runtime_starts_local_antivirus_components_when_enabled(self):
        State.tenants[1].cache.antivirus_enabled = True

        with patch('globaleaks.services.antivirus.ensure_antivirus_decryptor_running') as ensure_decryptor, \
             patch('globaleaks.services.antivirus.ensure_antivirus_updater_running') as ensure_updater, \
             patch('globaleaks.services.antivirus.ensure_local_clamd_running') as ensure_clamd, \
             patch('globaleaks.services.antivirus.stop_antivirus_updater', return_value=defer.succeed(None)) as stop_updater, \
             patch('globaleaks.services.antivirus.stop_local_clamd', return_value=defer.succeed(None)) as stop_clamd:
            yield antivirus_service.sync_antivirus_runtime()

        ensure_decryptor.assert_called_once_with()
        ensure_updater.assert_called_once_with()
        ensure_clamd.assert_called_once_with()
        stop_updater.assert_not_called()
        stop_clamd.assert_not_called()

    @defer.inlineCallbacks
    def test_sync_runtime_keeps_decryptor_and_stops_local_processes_for_remote_clamd(self):
        State.tenants[1].cache.antivirus_enabled = True
        State.tenants[1].cache.antivirus_clamd_ip = '192.0.2.10'
        State.tenants[1].cache.antivirus_clamd_port = 3311

        with patch('globaleaks.services.antivirus.ensure_antivirus_decryptor_running') as ensure_decryptor, \
             patch('globaleaks.services.antivirus.ensure_antivirus_updater_running') as ensure_updater, \
             patch('globaleaks.services.antivirus.ensure_local_clamd_running') as ensure_clamd, \
             patch('globaleaks.services.antivirus.stop_antivirus_updater', return_value=defer.succeed(None)) as stop_updater, \
             patch('globaleaks.services.antivirus.stop_local_clamd', return_value=defer.succeed(None)) as stop_clamd:
            yield antivirus_service.sync_antivirus_runtime()

        ensure_decryptor.assert_called_once_with()
        ensure_updater.assert_not_called()
        ensure_clamd.assert_not_called()
        stop_updater.assert_called_once_with()
        stop_clamd.assert_called_once_with()

    @defer.inlineCallbacks
    def test_sync_runtime_stops_all_components_when_disabled_everywhere(self):
        with patch('globaleaks.services.antivirus.stop_antivirus_decryptor', return_value=defer.succeed(None)) as stop_decryptor, \
             patch('globaleaks.services.antivirus.stop_antivirus_updater', return_value=defer.succeed(None)) as stop_updater, \
             patch('globaleaks.services.antivirus.stop_local_clamd', return_value=defer.succeed(None)) as stop_clamd:
            yield antivirus_service.sync_antivirus_runtime()

        stop_decryptor.assert_called_once_with()
        stop_updater.assert_called_once_with()
        stop_clamd.assert_called_once_with()

    @defer.inlineCallbacks
    def test_sync_runtime_starts_when_any_tenant_has_antivirus_enabled(self):
        tenant = TenantState()
        tenant.cache.antivirus_enabled = True
        State.tenants[2] = tenant

        with patch('globaleaks.services.antivirus.ensure_antivirus_decryptor_running') as ensure_decryptor, \
             patch('globaleaks.services.antivirus.ensure_antivirus_updater_running') as ensure_updater, \
             patch('globaleaks.services.antivirus.ensure_local_clamd_running') as ensure_clamd:
            yield antivirus_service.sync_antivirus_runtime()

        ensure_decryptor.assert_called_once_with()
        ensure_updater.assert_called_once_with()
        ensure_clamd.assert_called_once_with()
