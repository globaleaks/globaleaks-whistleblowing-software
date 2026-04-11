"""
Tests for gl-admin backup and restore functionality.

These tests verify that the backup/restore logic correctly handles
directory recreation after shutil.rmtree().
"""
import os
import shutil
import tarfile
import tempfile

from twisted.trial import unittest


class TestGLAdminBackupRestore(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.backup_file = os.path.join(tempfile.gettempdir(), 'test_backup.tar.gz')

    def tearDown(self):
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)

        if os.path.exists(self.backup_file):
            os.remove(self.backup_file)

    def _create_test_directory_structure(self):
        """Create a directory structure similar to /var/globaleaks"""
        os.makedirs(os.path.join(self.test_dir, 'files'), exist_ok=True)
        os.makedirs(os.path.join(self.test_dir, 'attachments'), exist_ok=True)
        os.makedirs(os.path.join(self.test_dir, 'log'), exist_ok=True)
        os.makedirs(os.path.join(self.test_dir, 'tmp'), exist_ok=True)

        # Create test files
        with open(os.path.join(self.test_dir, 'globaleaks.db'), 'w') as f:
            f.write('test database content')

        with open(os.path.join(self.test_dir, 'files', 'file1.txt'), 'w') as f:
            f.write('test file content')

        with open(os.path.join(self.test_dir, 'attachments', 'attach1.bin'), 'w') as f:
            f.write('test attachment content')

    def _perform_backup(self, workdir, backuppath):
        """Simulate gl-admin backup logic using tarfile"""
        with tarfile.open(backuppath, "w:gz") as tar:
            for item in os.listdir(workdir):
                if item != 'backups':
                    tar.add(os.path.join(workdir, item), arcname=item)

    def _perform_restore(self, workdir, backuppath):
        """Simulate gl-admin restore logic (fixed version with os.makedirs)"""
        shutil.rmtree(workdir)
        os.makedirs(workdir)

        with tarfile.open(backuppath, "r:gz") as tar:
            tar.extractall(path=workdir, filter='data')

    def test_rmtree_removes_directory(self):
        """Test that shutil.rmtree removes the entire directory including root"""
        self._create_test_directory_structure()

        # Verify directory exists before rmtree
        self.assertTrue(os.path.isdir(self.test_dir))

        shutil.rmtree(self.test_dir)

        # Verify directory no longer exists after rmtree
        self.assertFalse(os.path.exists(self.test_dir))

    def test_makedirs_recreates_directory(self):
        """Test that os.makedirs recreates the directory after rmtree"""
        self._create_test_directory_structure()

        shutil.rmtree(self.test_dir)
        self.assertFalse(os.path.exists(self.test_dir))

        os.makedirs(self.test_dir)
        self.assertTrue(os.path.isdir(self.test_dir))

    def test_restore_succeeds_with_makedirs(self):
        """Test that restore succeeds when directory is recreated after rmtree"""
        self._create_test_directory_structure()
        self._perform_backup(self.test_dir, self.backup_file)

        self._perform_restore(self.test_dir, self.backup_file)

        # Verify directory exists
        self.assertTrue(os.path.isdir(self.test_dir))

        # Verify files were restored
        self.assertTrue(os.path.isfile(os.path.join(self.test_dir, 'globaleaks.db')))
        self.assertTrue(os.path.isfile(os.path.join(self.test_dir, 'files', 'file1.txt')))
        self.assertTrue(os.path.isfile(os.path.join(self.test_dir, 'attachments', 'attach1.bin')))

    def test_restore_preserves_file_content(self):
        """Test that restore preserves the original file content"""
        self._create_test_directory_structure()

        # Store original content
        original_db_content = 'test database content'
        original_file_content = 'test file content'

        self._perform_backup(self.test_dir, self.backup_file)
        self._perform_restore(self.test_dir, self.backup_file)

        # Verify content
        with open(os.path.join(self.test_dir, 'globaleaks.db'), 'r') as f:
            self.assertEqual(f.read(), original_db_content)

        with open(os.path.join(self.test_dir, 'files', 'file1.txt'), 'r') as f:
            self.assertEqual(f.read(), original_file_content)

    def test_restore_preserves_directory_structure(self):
        """Test that restore preserves the original directory structure"""
        self._create_test_directory_structure()
        self._perform_backup(self.test_dir, self.backup_file)
        self._perform_restore(self.test_dir, self.backup_file)

        # Verify directory structure
        self.assertTrue(os.path.isdir(os.path.join(self.test_dir, 'files')))
        self.assertTrue(os.path.isdir(os.path.join(self.test_dir, 'attachments')))
        self.assertTrue(os.path.isdir(os.path.join(self.test_dir, 'log')))
        self.assertTrue(os.path.isdir(os.path.join(self.test_dir, 'tmp')))

