import errno
import os
import shutil
import stat
import tempfile
import uuid

from tempfile import mkdtemp
from unittest.mock import patch, MagicMock

from twisted.trial import unittest

# Import fusepy as fuse when installed with pip
import importlib
fuse = importlib.import_module('fuse' if importlib.util.find_spec('fuse') else 'fusepy')

from globaleaks.utils.eph_fs import EphemeralFile, EphemeralOperations, main, mount, unmount_if_mounted

TEST_PATH = str(uuid.uuid4())
TEST_DATA = b"Hello, world! This is a test data for writing, seeking and reading operations."

ORIGINAL_SIZE = len(TEST_DATA)
EXTENDED_SIZE = ORIGINAL_SIZE*2
REDUCED_SIZE = ORIGINAL_SIZE//2

class TestEphemeralFile(unittest.TestCase):
    def setUp(self):
        self.storage_dir = mkdtemp()
        self.ephemeral_file = EphemeralFile(self.storage_dir)

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

class TestEphemeralOperations(unittest.TestCase):
    def setUp(self):
        self.storage_dir = mkdtemp()
        self.fs = EphemeralOperations(self.storage_dir)

        # Get current user's UID and GID
        self.current_uid = os.getuid()
        self.current_gid = os.getgid()

    def tearDown(self):
        for file in self.fs.files.values():
            os.remove(file.filepath)
        os.rmdir(self.storage_dir)

    def test_create_file(self):
        self.fs.create(TEST_PATH, 0o660)
        self.assertIn(TEST_PATH, self.fs.files)

    def test_create_file_with_arbitrary_name(self):
        with self.assertRaises(fuse.FuseOSError) as context:
            self.fs.create('/arbitraryname', os.O_RDONLY)
        self.assertEqual(context.exception.errno, errno.ENOENT)

    def test_open_existing_file(self):
        self.fs.create(TEST_PATH, 0o660)
        self.fs.open(TEST_PATH, os.O_RDONLY)

    def test_write_and_read_file(self):
        self.fs.create(TEST_PATH, 0o660)

        self.fs.open(TEST_PATH, os.O_RDWR)
        self.fs.write(TEST_PATH, TEST_DATA, 0, None)

        self.fs.release(TEST_PATH, None)

        self.fs.open(TEST_PATH, os.O_RDONLY)

        read_data = self.fs.read(TEST_PATH, len(TEST_DATA), 0, None)

        self.assertEqual(read_data, TEST_DATA)

        self.fs.release(TEST_PATH, None)

    def test_unlink_file(self):
        self.fs.create(TEST_PATH, 0o660)
        self.assertIn(TEST_PATH, self.fs.files)

        self.fs.unlink(TEST_PATH)
        self.assertNotIn(TEST_PATH, self.fs.files)

    def test_file_not_found(self):
        with self.assertRaises(fuse.FuseOSError) as context:
            self.fs.open('/nonexistentfile', os.O_RDONLY)
        self.assertEqual(context.exception.errno, errno.ENOENT)

    def test_getattr_root(self):
        attr = self.fs.getattr('/')
        self.assertEqual(stat.S_IFMT(attr['st_mode']), stat.S_IFDIR)
        self.assertEqual(attr['st_mode'] & 0o777, 0o750)
        self.assertEqual(attr['st_nlink'], 2)

    def test_getattr_file(self):
        self.fs.create(TEST_PATH, mode=0o660)

        attr = self.fs.getattr(TEST_PATH)

        self.assertEqual(stat.S_IFMT(attr['st_mode']), stat.S_IFREG)
        self.assertEqual(attr['st_mode'] & 0o777, 0o660)
        self.assertEqual(attr['st_size'], 0)
        self.assertEqual(attr['st_nlink'], 1)
        self.assertEqual(attr['st_uid'], os.getuid())
        self.assertEqual(attr['st_gid'], os.getgid())
        self.assertIn('st_atime', attr)
        self.assertIn('st_mtime', attr)
        self.assertIn('st_ctime', attr)

    def test_getattr_nonexistent(self):
        with self.assertRaises(OSError) as _:
            self.fs.getattr('/nonexistent')

    def test_truncate(self):
        self.fs.create(TEST_PATH, 0o660)
        self.fs.write(TEST_PATH, TEST_DATA, 0, None)

        self.fs.truncate(TEST_PATH, REDUCED_SIZE, None)
        file_content = self.fs.read(TEST_PATH, ORIGINAL_SIZE, 0, None)
        self.assertEqual(len(file_content), REDUCED_SIZE)
        self.assertEqual(file_content, TEST_DATA[:REDUCED_SIZE])

    def test_extend(self):
        self.fs.create(TEST_PATH, 0o660)
        self.fs.write(TEST_PATH, TEST_DATA, 0, None)

        self.fs.truncate(TEST_PATH, EXTENDED_SIZE, None)
        file_content = self.fs.read(TEST_PATH, EXTENDED_SIZE * 2, 0, None)
        self.assertEqual(file_content[:ORIGINAL_SIZE], TEST_DATA)
        self.assertEqual(len(file_content), EXTENDED_SIZE)
        self.assertTrue(all(byte == 0 for byte in file_content[ORIGINAL_SIZE:]))

    def test_readdir(self):
        file_names = []
        for _ in range(3):
            file_names.append(str(uuid.uuid4()))
            self.fs.create(file_names[-1], 0o660)

        directory_contents = self.fs.readdir('/', None)
        self.assertEqual(set(directory_contents), {'.', '..', file_names[0], file_names[1], file_names[2]})

        self.fs.unlink(file_names[1])
        directory_contents = self.fs.readdir('/', None)
        self.assertEqual(set(directory_contents), {'.', '..', file_names[0], file_names[2]})

    @patch("os.chmod")
    def test_chmod_success(self, mock_chmod):
        self.fs.create(TEST_PATH, 0o660)
        mock_chmod.assert_called_with(self.fs.files[TEST_PATH].filepath, 0o660)
        self.fs.chmod(TEST_PATH, 0o640)
        mock_chmod.assert_called_with(self.fs.files[TEST_PATH].filepath, 0o640)

    def test_chmod_file_not_found(self):
        with self.assertRaises(fuse.FuseOSError) as context:
            self.fs.chmod("/nonexistent", 0o644)
        self.assertEqual(context.exception.errno, errno.ENOENT)

    @patch("os.chown")
    def test_chown_success(self, mock_chown):
        self.fs.create(TEST_PATH, 0o660)
        self.fs.chown(TEST_PATH, self.current_uid, self.current_gid)
        mock_chown.assert_called_once_with(self.fs.files[TEST_PATH].filepath, self.current_uid, self.current_gid)

    def test_chown_file_not_found(self):
        with self.assertRaises(fuse.FuseOSError) as context:
            self.fs.chown("/nonexistent", self.current_uid, self.current_gid)
        self.assertEqual(context.exception.errno, errno.ENOENT)

    @patch("os.chown", side_effect=PermissionError)
    def test_chown_permission_error(self, mock_chown):
        self.fs.create(TEST_PATH, 0o660)
        with self.assertRaises(PermissionError):
            self.fs.chown(TEST_PATH, self.current_uid, self.current_gid)

    @patch('atexit.register')
    @patch('argparse.ArgumentParser.parse_args')
    @patch('globaleaks.utils.eph_fs.subprocess.run')
    @patch('globaleaks.utils.eph_fs.mount')
    @patch('globaleaks.utils.eph_fs.fuse.FUSE')
    @patch('builtins.print')
    def test_main_mount_with_unspecified_storage_directory(self, mock_print, mock_FUSE, mock_mount, mock_subprocess, mock_parse_args, mock_atexit_register):
        with tempfile.TemporaryDirectory() as mount_point:
            mock_parse_args.return_value = MagicMock(
                mount_point=mount_point,
                storage_directory=None,
                unmount=False
            )

            original_mount_function = mount

            def side_effect_func(mount_point, storage_directory, flag):
                return original_mount_function(mount_point, storage_directory, False)

            mock_mount.side_effect = side_effect_func

            main()

            mock_mount.assert_called_once_with(mount_point, None, True)

            mock_atexit_register.assert_called_once_with(unmount_if_mounted, mount_point)

            mock_subprocess.assert_called_once_with(['mount'], capture_output=True, text=True)

    @patch('atexit.register')
    @patch('argparse.ArgumentParser.parse_args')
    @patch('globaleaks.utils.eph_fs.subprocess.run')
    @patch('globaleaks.utils.eph_fs.mount')
    @patch('globaleaks.utils.eph_fs.fuse.FUSE')
    @patch('builtins.print')
    def test_main_mount_with_specified_storage_directory(self, mock_print, mock_FUSE, mock_mount, mock_subprocess, mock_parse_args, mock_atexit_register):
        with tempfile.TemporaryDirectory() as mount_point, tempfile.TemporaryDirectory() as storage_directory:
            mock_parse_args.return_value = MagicMock(
                mount_point=mount_point,
                storage_directory=storage_directory
            )

            original_mount_function = mount

            def side_effect_func(mount_point, storage_directory, flag):
                return original_mount_function(mount_point, storage_directory, False)

            mock_mount.side_effect = side_effect_func

            main()

            mock_mount.assert_called_once_with(mount_point, storage_directory, True)

            mock_atexit_register.assert_called_once_with(unmount_if_mounted, mount_point)

            mock_subprocess.assert_called_once_with(['mount'], capture_output=True, text=True)

    @patch('atexit.register')
    @patch('argparse.ArgumentParser.parse_args')
    @patch('globaleaks.utils.eph_fs.subprocess.run')
    @patch('globaleaks.utils.eph_fs.mount')
    @patch('globaleaks.utils.eph_fs.is_mount_point')
    @patch('globaleaks.utils.eph_fs.fuse.FUSE')
    @patch('builtins.print')
    def test_main_with_mount_point_check(self, mock_print, mock_FUSE, mock_is_mount_point, mock_mount, mock_subprocess, mock_parse_args, mock_atexit_register):
        with tempfile.TemporaryDirectory() as mount_point:
            mock_parse_args.return_value = MagicMock(
                mount_point=mount_point,
                storage_directory=None
            )

            mock_is_mount_point.return_value = True

            original_mount_function = mount

            def side_effect_func(mount_point, storage_directory, flag):
                return original_mount_function(mount_point, storage_directory, False)

            mock_mount.side_effect = side_effect_func

            main()

            mock_mount.assert_called_once_with(mount_point, None, True)

            mock_atexit_register.assert_called_once_with(unmount_if_mounted, mount_point)

            mock_subprocess.assert_called_once_with(['fusermount', '-u', mount_point])

    @patch('atexit.register')
    @patch('argparse.ArgumentParser.parse_args')
    @patch('globaleaks.utils.eph_fs.subprocess.run')
    @patch('globaleaks.utils.eph_fs.mount')
    @patch('globaleaks.utils.eph_fs.is_mount_point')
    @patch('globaleaks.utils.eph_fs.fuse.FUSE')
    @patch('builtins.print')
    def test_main_keyboard_interrupt(self, mock_print, mock_FUSE, mock_is_mount_point, mock_mount, mock_subprocess, mock_parse_args, mock_atexit_register):
        with tempfile.TemporaryDirectory() as mount_point:
            mock_parse_args.return_value = MagicMock(
                mount_point=mount_point,
                storage_directory=None
            )

            mock_is_mount_point.return_value = False

            mock_mount.side_effect = KeyboardInterrupt

            with self.assertRaises(SystemExit):
                main()

            mock_mount.assert_called_once_with(mount_point, None, True)

            mock_subprocess.assert_not_called()

    @patch('atexit.register')
    @patch('argparse.ArgumentParser.parse_args')
    @patch('globaleaks.utils.eph_fs.subprocess.run')
    @patch('globaleaks.utils.eph_fs.mount')
    @patch('globaleaks.utils.eph_fs.is_mount_point')
    @patch('globaleaks.utils.eph_fs.fuse.FUSE')
    @patch('builtins.print')
    def test_main_other_exception(self, mock_print, mock_FUSE, mock_is_mount_point, mock_mount, mock_subprocess, mock_parse_args, mock_atexit_register):
        with tempfile.TemporaryDirectory() as mount_point:
            mock_parse_args.return_value = MagicMock(
                mount_point=mount_point,
                storage_directory=None
            )

            mock_is_mount_point.return_value = False

            mock_mount.side_effect = Exception("Some unexpected error")

            with self.assertRaises(SystemExit):
                main()

            mock_mount.assert_called_once_with(mount_point, None, True)

            mock_atexit_register.assert_not_called()

            mock_subprocess.assert_not_called()

if __name__ == '__main__':
    unittest.main()
