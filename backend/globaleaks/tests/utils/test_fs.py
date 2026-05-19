import os

from globaleaks.rest import errors
from globaleaks.settings import Settings
from globaleaks.tests import helpers
from globaleaks.utils import fs


class TestFilesystemUtilities(helpers.TestGL):
    def test_directory_traversal_failure_on_relative_trusted_path_must_fail(self):
        self.assertRaises(Exception, fs.directory_traversal_check, 'invalid/relative/trusted/path', "valid.txt")

    def test_directory_traversal_check_blocked(self):
        self.assertRaises(errors.DirectoryTraversalError, fs.directory_traversal_check, Settings.files_path,
                          "/etc/passwd")

    def test_directory_traversal_check_allowed(self):
        valid_access = os.path.join(Settings.files_path, "valid.txt")
        fs.directory_traversal_check(Settings.files_path, valid_access)

    def test_directory_traversal_check_sibling_suffix_blocked(self):
        # /…/files vs /…/files-evil/x — il caso classico del bug commonprefix.
        evil = Settings.files_path + "-evil/x"
        self.assertRaises(errors.DirectoryTraversalError,
                          fs.directory_traversal_check, Settings.files_path, evil)

    def test_directory_traversal_check_sibling_no_separator_blocked(self):
        # /…/files vs /…/filesomething — varianti senza un carattere separatore.
        evil = Settings.files_path + "something"
        self.assertRaises(errors.DirectoryTraversalError,
                          fs.directory_traversal_check, Settings.files_path, evil)

    def test_directory_traversal_check_nested_sibling_blocked(self):
        # /a/b come trusted, /a/bc/x come untrusted: sibling con prefisso parziale
        # su un componente più profondo.
        base = os.path.join(Settings.files_path, "sub")
        evil = os.path.join(Settings.files_path, "subother", "x")
        self.assertRaises(errors.DirectoryTraversalError,
                          fs.directory_traversal_check, base, evil)

    def test_srm(self):
        path = os.path.join(Settings.working_path, "antani.txt")

        f = open(path, "wb")
        f.seek((10 * 1024 * 1024) - 1)
        f.write(b"\0")
        f.close()

        self.assertTrue(os.path.isfile(path))

        fs.srm(path, 10)

        self.assertFalse(os.path.isfile(path))
