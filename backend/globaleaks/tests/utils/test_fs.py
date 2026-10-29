import os

from globaleaks.rest import errors
from globaleaks.settings import Settings
from globaleaks.tests import helpers
from globaleaks.utils import fs


class TestFilesystemUtilities(helpers.TestGL):
    def test_directory_traversal_failure_on_relative_trusted_path_must_fail(self):
        self.assertRaises(errors.DirectoryTraversalError, fs.directory_traversal_check, 'invalid/relative/trusted/path', "valid.txt")

    def test_directory_traversal_check_blocked(self):
        self.assertRaises(errors.DirectoryTraversalError, fs.directory_traversal_check, Settings.files_path,
                          "/etc/passwd")

    def test_directory_traversal_check_allowed(self):
        valid_access = os.path.join(Settings.files_path, "valid.txt")
        fs.directory_traversal_check(Settings.files_path, valid_access)

    def test_directory_traversal_check_sibling_suffix_blocked(self):
        # /…/files vs /…/files-evil/x: the classic commonprefix bug case.
        evil = Settings.files_path + "-evil/x"
        self.assertRaises(errors.DirectoryTraversalError,
                          fs.directory_traversal_check, Settings.files_path, evil)

    def test_directory_traversal_check_sibling_no_separator_blocked(self):
        # /…/files vs /…/filesomething: variants without a separator character.
        evil = Settings.files_path + "something"
        self.assertRaises(errors.DirectoryTraversalError,
                          fs.directory_traversal_check, Settings.files_path, evil)

    def test_directory_traversal_check_nested_sibling_blocked(self):
        # /a/b as trusted, /a/bc/x as untrusted: a sibling with a partial prefix
        # on a deeper path component.
        base = os.path.join(Settings.files_path, "sub")
        evil = os.path.join(Settings.files_path, "subother", "x")
        self.assertRaises(errors.DirectoryTraversalError,
                          fs.directory_traversal_check, base, evil)

    def test_get_storage_path_rejects_invalid_tenant_ids(self):
        for tid in (True, 0, -1):
            self.assertRaises(errors.DirectoryTraversalError, fs.get_storage_path, tid, 'files')

    def test_get_storage_path_rejects_unknown_kind(self):
        self.assertRaises(errors.DirectoryTraversalError, fs.get_storage_path, 1, 'unknown')

    def test_get_storage_path_rejects_invalid_file_ids(self):
        for file_id in ('..', '.', 'a/b', '', '/etc/passwd'):
            self.assertRaises(errors.DirectoryTraversalError, fs.get_storage_path, 1, 'files', file_id)

    def test_get_storage_path_rejects_symlinked_tenant_root(self):
        os.symlink(Settings.tmp_path, os.path.join(Settings.tenants_path, '3'))
        self.assertRaises(errors.DirectoryTraversalError, fs.get_storage_path, 3, 'files', create=True)
        self.assertFalse(os.path.exists(os.path.join(Settings.tmp_path, 'files')))

    def test_get_storage_path_creates_tenant_directories(self):
        path = fs.get_storage_path(3, 'attachments', 'file-id', create=True)
        self.assertEqual(path, os.path.join(Settings.tenants_path, '3', 'attachments', 'file-id'))
        self.assertTrue(os.path.isdir(os.path.dirname(path)))
        self.assertFalse(os.path.exists(path))

    def test_get_storage_path_uses_the_snapshot_tenant_root(self):
        root = os.path.join(Settings.tmp_path, 'snapshot', 'tenants')
        path = fs.get_storage_path(2, 'attachments', 'file-id', create=True, tenants_path=root)
        self.assertEqual(path, os.path.join(root, '2', 'attachments', 'file-id'))
        self.assertTrue(os.path.isdir(os.path.dirname(path)))
        os.symlink(Settings.tmp_path, os.path.join(root, '3'))
        self.assertRaises(errors.DirectoryTraversalError, fs.get_storage_path,
                          3, 'attachments', 'file-id', tenants_path=root)

    def test_srm(self):
        path = os.path.join(Settings.working_path, "antani.txt")

        with open(path, "wb") as f:
            f.seek((10 * 1024 * 1024) - 1)
            f.write(b"\0")

        self.assertTrue(os.path.isfile(path))

        fs.srm(path, 10)

        self.assertFalse(os.path.isfile(path))
