import os
import shutil
import tempfile

from unittest.mock import MagicMock, patch

from twisted.internet.defer import inlineCallbacks, succeed
from twisted.trial import unittest

from globaleaks import models
from globaleaks.jobs.antivirus_decryptor import AntivirusDecryptor, decrypt_file, \
    update_verification_status, verdict_to_state
from globaleaks.models import config
from globaleaks.models.enums import EnumStateFile
from globaleaks.orm import transact, tw
from globaleaks.settings import Settings
from globaleaks.state import State
from globaleaks.tests import helpers
from globaleaks.utils.crypto import GCE

CONTENT = b'the content of a file attached to a report'


def encrypt(path, content=CONTENT):
    """
    Write the file on disk as the platform does, and give back the key
    """
    prv_key, pub_key = GCE.generate_keypair()

    with GCE.streaming_encryption_open('ENCRYPT', pub_key, path) as seo:
        seo.encrypt_chunk(content, 1)

    return prv_key


class TestVerdict(unittest.TestCase):
    """
    A file the scanner has judged takes the state of that judgement; anything
    else it may answer - an error, a silence, a verdict withheld because the
    antivirus is off - leaves the file pending.
    """
    def test_the_verdicts_of_the_scanner_are_the_states_of_the_file(self):
        self.assertEqual(verdict_to_state('safe'), EnumStateFile.verified.name)
        self.assertEqual(verdict_to_state('unsafe'), EnumStateFile.infected.name)

    def test_anything_that_is_not_a_verdict_leaves_the_file_pending(self):
        for answer in ['error', '', None, 'something else']:
            self.assertEqual(verdict_to_state(answer), EnumStateFile.pending.name,
                             f"{answer!r} is read as a verdict")


class TestDecryption(unittest.TestCase):
    """
    A file is stored encrypted: what reaches the scanner is the content in the
    clear, read back whole however many chunks it was written in.
    """
    def setUp(self):
        self.attachments = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.attachments, True)

    def path(self, name='a-file'):
        return os.path.join(self.attachments, name)

    def test_the_file_is_read_back_as_it_was_written(self):
        path = self.path()

        self.assertEqual(decrypt_file(path, encrypt(path)), CONTENT)

    def test_a_file_written_in_several_chunks_is_read_back_whole(self):
        path = self.path()
        prv_key, pub_key = GCE.generate_keypair()

        with GCE.streaming_encryption_open('ENCRYPT', pub_key, path) as seo:
            seo.encrypt_chunk(b'a' * 16384, 0)
            seo.encrypt_chunk(b'b' * 16384, 1)

        self.assertEqual(decrypt_file(path, prv_key), b'a' * 16384 + b'b' * 16384)

    def test_an_empty_file_is_read_back_empty(self):
        path = self.path()

        self.assertEqual(decrypt_file(path, encrypt(path, b'')), b'')


class TestQueue(unittest.TestCase):
    """
    The queue is walked one file at a time, and a file that cannot be handed
    over - queued without its key, gone from the disk, or empty - leaves the
    queue without ever reaching the scanner.
    """
    def setUp(self):
        self.attachments = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.attachments, True)

        attachments = patch.object(Settings, 'attachments_path', self.attachments)
        attachments.start()
        self.addCleanup(attachments.stop)

        State.antivirus_files = []
        State.antivirus_file_ids = set()

        self.scanner = MagicMock()
        self.scanner.scan_file.return_value = succeed('safe')

        self.job = AntivirusDecryptor()
        self.job.scanner_factory = lambda: self.scanner

    def enqueue(self, name, key):
        State.antivirus_files.append((name, key))
        State.antivirus_file_ids.add(name)

    @inlineCallbacks
    def test_an_empty_queue_is_nothing_to_do(self):
        yield self.job.operation()

        self.scanner.scan_file.assert_not_called()

    @inlineCallbacks
    def test_a_file_queued_without_its_key_is_dropped(self):
        self.enqueue('a-file', None)

        yield self.job.operation()

        self.scanner.scan_file.assert_not_called()
        self.assertNotIn('a-file', State.antivirus_file_ids)

    @inlineCallbacks
    def test_a_file_missing_from_the_disk_is_skipped(self):
        prv_key, _ = GCE.generate_keypair()
        self.enqueue('a-file-that-was-never-written', prv_key)

        yield self.job.operation()

        self.scanner.scan_file.assert_not_called()

    @inlineCallbacks
    def test_an_empty_file_is_not_sent_to_the_scanner(self):
        path = os.path.join(self.attachments, 'an-empty-file')
        self.enqueue('an-empty-file', encrypt(path, b''))

        yield self.job.operation()

        self.scanner.scan_file.assert_not_called()


class TestAntivirusDecryptor(helpers.TestGLWithPopulatedDB):
    """
    A file attached to a report is stored encrypted: to be scanned it is
    decrypted in memory, handed over in the clear, and marked with the verdict
    the scanner gave - unless the antivirus has been turned off in between.
    """
    @inlineCallbacks
    def setUp(self):
        yield super().setUp()

        yield self.perform_full_submission_actions()

        wbtips = yield self.get_wbtips()
        ifiles = yield self.get_ifiles_by_wbtip_id(wbtips[0]['id'])
        self.file_id = ifiles[0]

        yield tw(config.db_set_config_variable, 1, 'antivirus_enabled', True)

        State.antivirus_files = []
        State.antivirus_file_ids = set()

        self.scanner = MagicMock()

        self.job = AntivirusDecryptor()
        self.job.scanner_factory = lambda: self.scanner

    @transact
    def get_file(self, session, file_id):
        ifile = session.query(models.InternalFile).filter_by(id=file_id).one()
        return ifile.state, ifile.verification_date

    @inlineCallbacks
    def scan(self, verdict):
        key = encrypt(os.path.join(Settings.attachments_path, self.file_id))
        State.antivirus_files.append((self.file_id, key))
        State.antivirus_file_ids.add(self.file_id)

        self.scanner.scan_file.return_value = succeed(verdict)

        yield self.job.operation()

        state, verification_date = yield self.get_file(self.file_id)
        return state, verification_date

    @inlineCallbacks
    def test_a_file_the_scanner_passes_is_marked_verified(self):
        state, verification_date = yield self.scan('safe')

        # what the scanner saw is the file in the clear
        self.assertEqual(self.scanner.scan_file.call_args[0][0], CONTENT)
        self.assertEqual(state, EnumStateFile.verified.name)
        self.assertIsNotNone(verification_date)
        # and the file has left the queue
        self.assertEqual(State.antivirus_files, [])
        self.assertNotIn(self.file_id, State.antivirus_file_ids)

    @inlineCallbacks
    def test_a_file_the_scanner_flags_is_marked_infected(self):
        state, verification_date = yield self.scan('unsafe')

        self.assertEqual(state, EnumStateFile.infected.name)
        self.assertIsNotNone(verification_date)

    @inlineCallbacks
    def test_the_verdict_is_discarded_where_the_antivirus_is_off(self):
        yield tw(config.db_set_config_variable, 1, 'antivirus_enabled', False)

        state, verification_date = yield self.scan('safe')

        self.assertEqual(state, EnumStateFile.pending.name)
        self.assertIsNone(verification_date)

    @inlineCallbacks
    def test_a_verdict_on_a_file_unknown_to_the_platform_leaves_no_trace(self):
        yield update_verification_status('not-a-file', 'safe')

        state, _ = yield self.get_file(self.file_id)
        self.assertEqual(state, EnumStateFile.pending.name)
