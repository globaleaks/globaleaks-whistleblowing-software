import io

from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

from twisted.internet import defer
from twisted.trial import unittest

from globaleaks.models.enums import EnumStateFile
from globaleaks.utils import antivirus
from globaleaks.utils.antivirus import FileAnalysis


# The file every antivirus recognizes, by agreement and not by signature: it is
# the only harmless way of asking a scanner to say "unsafe".
EICAR = br'X5O!P%@AP[4\PZX54(P^)7CC)7}$EICAR-STANDARD-ANTIVIRUS-TEST-FILE!$H+H*'


class TestFileAnalysis(unittest.TestCase):
    """
    What the scanner answers, and what the platform makes of it. The daemon is
    """
    @defer.inlineCallbacks
    def scanned(self, answer, content=b'a file', endpoint=None):
        clamd = MagicMock()
        clamd.scan_stream.return_value = answer

        with patch('globaleaks.utils.antivirus.pyclamd.ClamdNetworkSocket',
                   return_value=clamd):
            analysis = FileAnalysis(endpoint) if endpoint else FileAnalysis()
            result = yield analysis.scan_file(io.BytesIO(content))

        return result

    @defer.inlineCallbacks
    def test_the_answer_of_the_scanner_is_read(self):
        cases = [
            ("a file the scanner passes", None, b'a harmless file', 'safe'),
            ("the file every scanner recognizes",
             {'stream': ('FOUND', 'Eicar-Test-Signature')}, EICAR, 'unsafe')
        ]

        for reason, answer, content, expected in cases:
            self.assertEqual((yield self.scanned(answer, content)), expected,
                             f"{reason} is not reported as {expected}")

    @defer.inlineCallbacks
    def test_a_scanner_that_does_not_answer_leaves_the_file_unjudged(self):
        # Neither safe nor unsafe: an error is its own outcome, and the platform
        # keeps the file pending rather than letting it through as clean
        with patch('globaleaks.utils.antivirus.pyclamd.ClamdNetworkSocket',
                   side_effect=Exception("connection refused")):
            result = yield FileAnalysis().scan_file(io.BytesIO(b'a file'))

        self.assertEqual(result, 'error')

    @defer.inlineCallbacks
    def test_the_scanner_is_reached_at_the_endpoint_it_is_configured_on(self):
        clamd = MagicMock()
        clamd.scan_stream.return_value = None

        with patch('globaleaks.utils.antivirus.pyclamd.ClamdNetworkSocket',
                   return_value=clamd) as socket:
            yield FileAnalysis('tcp://192.0.2.10:3310').scan_file(io.BytesIO(b'a file'))

        socket.assert_called_once_with('192.0.2.10', 3310)

    @defer.inlineCallbacks
    def test_a_transport_other_than_tcp_scans_nothing(self):
        result = yield FileAnalysis('unix:///var/run/clamd.sock').scan_file(io.BytesIO(b'a file'))

        self.assertEqual(result, 'error')

    def test_the_endpoint_is_composed_of_the_address_and_the_port(self):
        self.assertEqual(antivirus.get_clamd_endpoint('192.0.2.10', 3311),
                         'tcp://192.0.2.10:3311')


class TestFileState(unittest.TestCase):
    """
    A file is scanned again while its verdict is missing or stale: the answer
    """
    def test_the_file_is_scanned_again(self):
        recent = datetime.now(timezone.utc) - timedelta(days=1)
        stale = datetime.now(timezone.utc) - timedelta(days=antivirus.ANTIVIRUS_RECHECK_DAYS + 1)

        cases = [
            ("a file still pending", EnumStateFile.pending.name, recent, True),
            ("a file never verified", EnumStateFile.verified.name, None, True),
            ("a verdict older than the platform accepts", EnumStateFile.verified.name, stale, True),
            ("a verdict of yesterday", EnumStateFile.verified.name, recent, False)
        ]

        for reason, state, date, expected in cases:
            self.assertEqual(antivirus.needs_antivirus_recheck(state, date), expected,
                             "{}: the file {} scanned again".format(reason, "is not" if expected else "is"))

    def test_a_verdict_without_a_timezone_is_read_as_universal_time(self):
        # The dates the database gives back carry no timezone: read as local
        # time they would move by hours, and a verdict could age or rejuvenate
        naive = datetime.now(timezone.utc).replace(tzinfo=None)

        self.assertFalse(antivirus.needs_antivirus_recheck(EnumStateFile.verified.name, naive))

    def test_the_state_of_a_file_is_reported_to_whoever_downloads_it(self):
        cases = [(EnumStateFile.infected.name, 'UNSAFE'),
                 (EnumStateFile.pending.name, 'PENDING'),
                 (EnumStateFile.verified.name, 'SAFE')]

        for state, expected in cases:
            self.assertEqual(antivirus.get_av_result(state), expected)


class TestCsvSanitization(unittest.TestCase):
    """
    The metadata of the files are exported as a spreadsheet, and the name of a
    """
    def test_a_cell_that_would_be_executed_is_quoted(self):
        for trigger in ['=', '+', '-', '@', '\t', '\r']:
            value = trigger + 'cmd|/c calc'

            self.assertEqual(antivirus.csv_sanitize_cell(value), "'" + value,
                             f"a cell opening with {trigger!r} is not neutralized")

    def test_an_ordinary_cell_is_left_as_it_is(self):
        for value in ['report.pdf', 'a name with spaces.txt', '2026-08-31', '']:
            self.assertEqual(antivirus.csv_sanitize_cell(value), value)

    def test_a_cell_that_is_not_there_becomes_an_empty_one(self):
        self.assertEqual(antivirus.csv_sanitize_cell(None), '')
