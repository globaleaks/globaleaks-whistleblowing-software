"""
Test database migrations.

for each version one an empty and a populated db must be sessiond in directories:
 - db/empty
 - db/populated
"""
import os
import shutil

from twisted.trial import unittest

from globaleaks import DATABASE_VERSION, FIRST_DATABASE_VERSION_SUPPORTED
from globaleaks.db import update_db
from globaleaks.settings import Settings
from globaleaks.tests import helpers


class TestMigrationRoutines(unittest.TestCase):
    def _test(self, path, version):
        helpers.init_state()
        srcpath = os.path.join(path, f'globaleaks-{version}.db')
        dstpath = os.path.join(Settings.working_path, 'globaleaks.db')
        shutil.copyfile(srcpath, dstpath)

        # TESTS PRECONDITIONS
        # Run preconditions if they exist, otherwise, run a no-op function
        getattr(self, f'preconditions_{version}', lambda: None)()

        ret = update_db()

        # TESTS POSTCONDITIONS
        # Run postconditions if they exist, otherwise, run a no-op function
        getattr(self, f'postconditions_{version}', lambda: None)()

        self.assertNotEqual(ret, -1)


def test(path, version):
    return lambda self: self._test(path, version)


path = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'db', 'populated')


for i in range(FIRST_DATABASE_VERSION_SUPPORTED, DATABASE_VERSION + 1):
    setattr(TestMigrationRoutines, f"test_db_migration_{i}", test(path, i))
