import os
import shutil

from tempfile import mkdtemp
from twisted.trial import unittest

from globaleaks.utils.securetempfile import SecureTemporaryFile

class TestSecureTemporaryFiles(unittest.TestCase):
    def setUp(self):
        self.storage_dir = mkdtemp()
        self.ephemeral_file = SecureTemporaryFile(self.storage_dir)
        self.chunk_size = 4096  # Define chunk size (4KB)
        self.total_size = 1024 * 1024  # 1MB
        self.test_data = os.urandom(self.total_size)

    def tearDown(self):
        shutil.rmtree(self.storage_dir)

    def test_encryption_and_decryption(self):
        # Write 1MB of data in 4KB chunks
        for i in range(0, self.total_size, self.chunk_size):
            with self.ephemeral_file.open('w') as file:
                chunk = self.test_data[i:i + self.chunk_size]
                file.write(chunk)

        # Define test cases with various seek/read ranges
        seek_tests = [
            (0, 1024, self.test_data[:1024]),  # Seek at the start read 1024 byte
            (1024, 1024, self.test_data[1024:2048]),  # Seek forward, read 1024 bytes
            (4096, 1024, self.test_data[4096:5120]),  # Seek forward, read 1024 bytes
            (3072, 1024, self.test_data[3072:4096]),  # Seek backward, read 1024 bytes
        ]

        for seek_pos, read_size, expected in seek_tests:
            with self.ephemeral_file.open('r') as file:
                file.seek(seek_pos)
                self.assertEqual(file.tell(), seek_pos)
                read_data = file.read(read_size)
                self.assertEqual(read_data, expected)

    def test_file_cleanup(self):
        path_copy = self.ephemeral_file.filepath
        del self.ephemeral_file
        self.assertFalse(os.path.exists(path_copy))
