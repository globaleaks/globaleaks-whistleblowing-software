import io
from unittest.mock import patch, MagicMock

from twisted.internet import defer
from twisted.trial import unittest as twisted_unittest

from globaleaks.utils.antivirus import FileAnalysis


class FileAnalysisMockedTests(twisted_unittest.TestCase):
    @defer.inlineCallbacks
    def test_scan_file_safe(self):
        mock_clamd = MagicMock()
        mock_clamd.scan_stream.return_value = None  # Safe file

        with patch('globaleaks.utils.antivirus.pyclamd.ClamdNetworkSocket', return_value=mock_clamd):
            fa = FileAnalysis()
            result = yield fa.scan_file(io.BytesIO(b"This is a safe file"))
            self.assertEqual(result, 'safe')

    @defer.inlineCallbacks
    def test_scan_file_unsafe(self):
        mock_clamd = MagicMock()
        mock_clamd.scan_stream.return_value = {'stream': ('FOUND', 'Eicar-Test-Signature')}  # Unsafe file

        with patch('globaleaks.utils.antivirus.pyclamd.ClamdNetworkSocket', return_value=mock_clamd):
            fa = FileAnalysis()
            result = yield fa.scan_file(io.BytesIO(b"EICAR"))
            self.assertEqual(result, 'unsafe')

    @defer.inlineCallbacks
    def test_scan_file_error(self):
        with patch('globaleaks.utils.antivirus.pyclamd.ClamdNetworkSocket', side_effect=Exception("Connection failed")):
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
