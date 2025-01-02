# -*- coding: utf-8 -*
import os
import shutil

from tempfile import mkdtemp

from twisted.trial import unittest

from globaleaks.utils.securetempfile import SecureTemporaryFile

TEST_DATA = b"Hello, world! This is a test data for writing, seeking and reading operations."

class TestSecureTemporaryFiles(unittest.TestCase):
    def setUp(self):
        self.storage_dir = mkdtemp()
        self.ephemeral_file = SecureTemporaryFile(self.storage_dir)

    def tearDown(self):
        shutil.rmtree(self.storage_dir)

    def test_create_and_write_file(self):
        with self.ephemeral_file.open('w') as file:
            for x in range(10):
                self.assertEqual(self.ephemeral_file.size, x * len(TEST_DATA))
                file.write(TEST_DATA)

        self.assertTrue(os.path.exists(self.ephemeral_file.filepath))
        self.assertEqual(self.ephemeral_file.size, len(TEST_DATA) * 10)

    def test_encryption_and_decryption(self):
        with self.ephemeral_file.open('w') as file:
            file.write(TEST_DATA)

        # Define test cases: each case is a tuple (seek_position, read_size, expected_data)
        seek_tests = [
            (0, 1, TEST_DATA[:1]),  # Seek at the start read 1 byte
            (5, 5, TEST_DATA[5:10]),  # Seek forward, read 5 bytes
            (10, 2, TEST_DATA[10:12]),  # Seek forward, read 2 bytes
            (0, 3, TEST_DATA[:3]),  # Seek backward, read 3 bytes
        ]

        # Test forward and backward seeking with different offsets
        with self.ephemeral_file.open('r') as file:
            for seek_pos, read_size, expected in seek_tests:
                file.seek(seek_pos)  # Seek to the given position
                self.assertEqual(file.tell(), seek_pos)  # Check position after seeking forward
                read_data = file.read(read_size)  # Read the specified number of bytes
                self.assertEqual(read_data, expected)  # Verify the data matches the expected value

    def test_file_cleanup(self):
        path_copy = self.ephemeral_file.filepath
        del self.ephemeral_file
        self.assertFalse(os.path.exists(path_copy))
