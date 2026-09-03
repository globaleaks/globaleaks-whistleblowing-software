"""
Test database migrations.

for each version one an empty and a populated db must be sessiond in directories:
 - db/empty
 - db/populated
"""
import os
import shutil
import sqlite3

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

    def preconditions_68(self):
        # An analyst still to activate holds no key to encrypt the statistical key to
        dbpath = os.path.join(Settings.working_path, 'globaleaks.db')
        with sqlite3.connect(dbpath) as conn:
            conn.execute("UPDATE user SET crypto_pub_key = '' WHERE id = '68411d07-2e28-4d16-a213-21879ee5e14d'")

    def postconditions_68(self):
        dbpath = os.path.join(Settings.working_path, 'globaleaks.db')
        with sqlite3.connect(dbpath) as conn:
            keys = dict(conn.execute("SELECT id, crypto_global_stat_prv_key FROM user WHERE id IN "
                                     "('68411d07-2e28-4d16-a213-21879ee5e14d', '7ec773d3-f1dd-4ed6-9c1f-eba508725b08')"))

        self.assertEqual(keys['68411d07-2e28-4d16-a213-21879ee5e14d'], '')
        self.assertNotEqual(keys['7ec773d3-f1dd-4ed6-9c1f-eba508725b08'], '')


    def preconditions_69(self):
        # A text question and a choice the fork let be statistical alike
        dbpath = os.path.join(Settings.working_path, 'globaleaks.db')
        with sqlite3.connect(dbpath) as conn:
            for field_id, field_type in (('statistical-text', 'inputbox'), ('statistical-choice', 'selectbox')):
                conn.execute("INSERT INTO field (id, tid, x, y, width, label, description, hint, placeholder, "
                             "required, multi_entry, triggered_by_score, type, instance, statistical) "
                             "VALUES (?, 1, 0, 0, 0, '{}', '{}', '{}', '{}', 0, 0, 0, ?, 1, 1)", (field_id, field_type))

    def postconditions_69(self):
        dbpath = os.path.join(Settings.working_path, 'globaleaks.db')
        with sqlite3.connect(dbpath) as conn:
            statistical = dict(conn.execute("SELECT id, statistical FROM field WHERE id IN ('statistical-text', 'statistical-choice')"))

        self.assertFalse(statistical['statistical-text'])
        self.assertTrue(statistical['statistical-choice'])

def test(path, version):
    return lambda self: self._test(path, version)


path = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'db', 'populated')


for i in range(FIRST_DATABASE_VERSION_SUPPORTED, DATABASE_VERSION + 1):
    setattr(TestMigrationRoutines, f"test_db_migration_{i}", test(path, i))
