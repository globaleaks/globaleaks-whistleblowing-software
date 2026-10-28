"""
Test the migrations of the working directory.

For each version an empty and a populated working directory are stored in
data/workingdirs/empty/<version> and data/workingdirs/populated/<version>:
each holds the globaleaks.db of that version and whatever else of a working
directory (attachments, files, logs, ...) the migration to test needs, and
it is migrated whole.
"""
import hashlib
import io
import os
import shutil
import sqlite3
import zipfile

from nacl.encoding import Base64Encoder
from twisted.internet.defer import inlineCallbacks
from twisted.trial import unittest

from globaleaks import DATABASE_VERSION, FIRST_DATABASE_VERSION_SUPPORTED, db
from globaleaks.db import refresh_tenant_cache, sync_clean_untracked_files, update_db
from globaleaks.db.migrations.update_72 import MigrationScript
from globaleaks.handlers import file
from globaleaks.handlers.admin import tenant
from globaleaks.handlers.recipient import rtip
from globaleaks.jobs import cleaning
from globaleaks.settings import Settings
from globaleaks.tests import helpers
from globaleaks.utils import fs
from globaleaks.utils.crypto import GCE
from globaleaks.utils.fs import get_storage_path
from globaleaks.utils.log import Logger


class TestMigrationRoutines(unittest.TestCase):
    def _test(self, path, version):
        helpers.init_state()
        shutil.copytree(os.path.join(path, str(version)), Settings.working_path, dirs_exist_ok=True)

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

        # The change of a temporary redaction names the one it replaced by its correct key
        with sqlite3.connect(dbpath) as conn:
            data = conn.execute("SELECT data FROM auditlog WHERE type = 'update_redaction'").fetchone()[0]

        self.assertIn('old_temporary_redaction', data)
        self.assertNotIn('old_remporary_redaction', data)


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

    def preconditions_71(self):
        dbpath = os.path.join(Settings.working_path, 'globaleaks.db')
        self.storage_files = {}
        with sqlite3.connect(dbpath) as conn:
            queries = [('files', 'SELECT tid, id FROM file')]
            for table in ('internalfile', 'receiverfile'):
                queries.append(('attachments', f"SELECT internaltip.tid, {table}.id FROM {table} "
                                               f"JOIN internaltip ON {table}.internaltip_id = internaltip.id"))
            queries.append(('attachments', "SELECT internaltip.tid, whistleblowerfile.id FROM whistleblowerfile "
                                           "JOIN internalfile ON whistleblowerfile.internalfile_id = internalfile.id "
                                           "JOIN internaltip ON internalfile.internaltip_id = internaltip.id"))
            for kind, query in queries:
                for tid, file_id in conn.execute(query):
                    source = os.path.join(Settings.working_path, kind, file_id)
                    # Delivered whistleblower files can use the shared internal file.
                    if not os.path.isfile(source):
                        self.assertEqual(kind, 'attachments')
                        self.assertIsNotNone(conn.execute("SELECT id FROM whistleblowerfile WHERE id = ?",
                                                         (file_id,)).fetchone())
                        continue
                    with open(source, 'rb') as f:
                        self.storage_files[tid, kind, file_id] = hashlib.sha256(f.read()).hexdigest()

        for tid in (1, 2, 3):
            for kind in ('files', 'attachments'):
                self.assertTrue(any(key[:2] == (tid, kind) for key in self.storage_files))

        tid, kind, file_id = next(key for key in self.storage_files if key[:2] == (2, 'attachments'))
        source = os.path.join(Settings.working_path, kind, file_id)
        mode = getattr(self, 'storage_migration_mode', None)
        if mode in ('partial', 'conflict', 'destination_symlink'):
            destination = get_storage_path(tid, kind, file_id, create=True)
            if mode == 'partial':
                os.rename(source, destination)
            elif mode == 'conflict':
                shutil.copyfile(source, destination)
            else:
                self.storage_symlink_target = destination + '.target'
                with open(self.storage_symlink_target, 'wb') as f:
                    f.write(b'keep')
                os.symlink(self.storage_symlink_target, destination)
        elif mode in ('source_symlink', 'directory'):
            os.unlink(source)
            if mode == 'source_symlink':
                self.storage_symlink_target = source + '.target'
                with open(self.storage_symlink_target, 'wb') as f:
                    f.write(b'keep')
                os.symlink(self.storage_symlink_target, source)
            else:
                os.mkdir(source)

    def postconditions_71(self):
        expected = set()
        for (tid, kind, file_id), digest in self.storage_files.items():
            source = os.path.join(Settings.working_path, kind, file_id)
            destination = os.path.join(Settings.tenants_path, str(tid), kind, file_id)
            self.assertFalse(os.path.exists(source))
            self.assertTrue(os.path.isfile(destination))
            with open(destination, 'rb') as f:
                self.assertEqual(hashlib.sha256(f.read()).hexdigest(), digest)
            expected.add(os.path.relpath(destination, Settings.tenants_path))

        actual = set()
        for root, directories, files in os.walk(Settings.tenants_path):
            for file_id in files:
                actual.add(os.path.relpath(os.path.join(root, file_id), Settings.tenants_path))
        self.assertEqual(actual, expected)
        self.assertFalse(os.path.exists(Settings.files_path))
        self.assertFalse(os.path.exists(Settings.attachments_path))

    def test_db_migration_71_after_partial_move(self):
        self.storage_migration_mode = 'partial'
        self._test(path, 71)

    def check_storage_migration_failure(self, mode, message):
        helpers.init_state()
        shutil.copytree(os.path.join(path, '71'), Settings.working_path, dirs_exist_ok=True)
        self.storage_migration_mode = mode
        self.preconditions_71()
        move_storage_file = MigrationScript.move_storage_file
        failures = []

        def move(script, tid, kind, file_id):
            try:
                return move_storage_file(script, tid, kind, file_id)
            except RuntimeError as exception:
                failures.append(str(exception))
                raise

        self.patch(MigrationScript, 'move_storage_file', move)
        self.assertEqual(update_db(), -1)
        self.assertTrue(failures)
        self.assertIn(message, failures[0])
        if mode in ('source_symlink', 'destination_symlink'):
            with open(self.storage_symlink_target, 'rb') as f:
                self.assertEqual(f.read(), b'keep')
        self.assertTrue(os.path.isdir(Settings.files_path))
        self.assertTrue(os.path.isdir(Settings.attachments_path))

    def test_db_migration_71_rejects_existing_destination(self):
        self.check_storage_migration_failure('conflict', 'destination already exists')

    def test_db_migration_71_rejects_source_symlink(self):
        self.check_storage_migration_failure('source_symlink', 'storage symlink')

    def test_db_migration_71_rejects_destination_symlink(self):
        self.check_storage_migration_failure('destination_symlink', 'storage symlink')

    def test_db_migration_71_rejects_non_regular_source(self):
        self.check_storage_migration_failure('directory', 'not a regular file')


def test(path, version):
    return lambda self: self._test(path, version)


path = os.path.join(helpers.DATA_DIR, 'workingdirs', 'populated')


for i in range(FIRST_DATABASE_VERSION_SUPPORTED, DATABASE_VERSION + 1):
    setattr(TestMigrationRoutines, f"test_db_migration_{i}", test(path, i))


class TestMigratedTenantStorage(helpers.TestHandler):
    @inlineCallbacks
    def setUp(self):
        yield helpers.TestHandler.setUp(self)
        fixture = os.path.join(helpers.DATA_DIR, 'workingdirs', 'populated', '71')
        shutil.copytree(fixture, Settings.working_path, dirs_exist_ok=True)
        self.assertEqual(update_db(), DATABASE_VERSION)
        yield refresh_tenant_cache()
        self.user_keys = {}

    def get_user_key(self, conn, user_id):
        if user_id not in self.user_keys:
            salt, private_key = conn.execute("SELECT salt, crypto_prv_key FROM user WHERE id = ?",
                                             (user_id,)).fetchone()
            # These are the password and browser KDF parameters used by Cypress.
            key = GCE.argon2id('ACollectionOfDiplomaticHistorySince_1966_ToThe_Pr esentDay#', salt, 16, 1 << 27)
            self.user_keys[user_id] = GCE.symmetric_decrypt(Base64Encoder.decode(key),
                                                          Base64Encoder.decode(private_key))
        return self.user_keys[user_id]

    @inlineCallbacks
    def check_downloads(self, cross_site=False):
        fixture = os.path.join(helpers.DATA_DIR, 'workingdirs', 'populated', '71', 'attachments')
        checked = set()
        recipients = {1: 'Recipient',
                      2: 'Platform A Storage Recipient',
                      3: 'Platform B Storage Recipient'}
        with sqlite3.connect(Settings.db_file_path) as conn:
            queries = (
                (rtip.WhistleblowerFileDownload,
                 "SELECT user.tid, user.id, user.username, internaltip.tid, whistleblowerfile.id, internalfile.id, "
                 "receivertip.crypto_tip_prv_key FROM whistleblowerfile "
                 "JOIN internalfile ON internalfile.id = whistleblowerfile.internalfile_id "
                 "JOIN internaltip ON internaltip.id = internalfile.internaltip_id "
                 "JOIN receivertip ON receivertip.id = whistleblowerfile.receivertip_id "
                 "JOIN user ON user.id = receivertip.receiver_id"),
                (rtip.ReceiverFileDownload,
                 "SELECT user.tid, user.id, user.username, internaltip.tid, receiverfile.id, receiverfile.id, "
                 "receivertip.crypto_tip_prv_key FROM receiverfile "
                 "JOIN internaltip ON internaltip.id = receiverfile.internaltip_id "
                 "JOIN receivertip ON receivertip.internaltip_id = internaltip.id "
                 "JOIN user ON user.id = receivertip.receiver_id "
                 "WHERE receiverfile.visibility = 0 OR receiverfile.author_id = user.id"))
            for handler_cls, query in queries:
                for tid, user_id, username, storage_tid, file_id, internal_id, encrypted_key in conn.execute(query).fetchall():
                    if cross_site:
                        if tid == storage_tid:
                            continue
                    elif tid != storage_tid or username != recipients.get(tid):
                        continue

                    user_key = self.get_user_key(conn, user_id)
                    tip_key = GCE.asymmetric_decrypt(user_key, Base64Encoder.decode(encrypted_key))
                    source = os.path.join(fixture, file_id)
                    if not os.path.isfile(source):
                        source = os.path.join(fixture, internal_id)
                    with GCE.streaming_encryption_open('DECRYPT', tip_key, source) as f:
                        expected = b''.join(iter(lambda: f.read(65536), b''))

                    handler = self.request(tid=tid, user_id=user_id, role='receiver', handler_cls=handler_cls)
                    handler.session.cc = user_key
                    yield handler.get(file_id)
                    with zipfile.ZipFile(io.BytesIO(handler.request.getResponseBody())) as archive:
                        contents = [archive.read(name) for name in archive.namelist()
                                    if name.upper() not in ('METADATA.CSV', 'README.TXT')]
                    self.assertEqual(contents, [expected])
                    checked.add((tid, handler_cls))
                    if cross_site:
                        self.assertFalse(os.path.exists(get_storage_path(tid, 'attachments', file_id)))

        if cross_site:
            self.assertTrue(checked)
        else:
            self.assertEqual(checked, {(tid, handler_cls) for tid in (1, 2, 3)
                                      for handler_cls in (rtip.WhistleblowerFileDownload, rtip.ReceiverFileDownload)})

    def test_recipients_download_migrated_files(self):
        return self.check_downloads()

    def test_cross_site_exchange_downloads_from_report_site(self):
        return self.check_downloads(cross_site=True)

    @inlineCallbacks
    def test_site_without_logo_downloads_root_logo(self):
        with sqlite3.connect(Settings.db_file_path) as conn:
            file_id = conn.execute("SELECT id FROM file WHERE tid = 1 AND name = 'logo'").fetchone()[0]
            tid = conn.execute("SELECT id FROM tenant WHERE id > 1 AND id NOT IN "
                               "(SELECT tid FROM file WHERE name = 'logo') ORDER BY id").fetchone()[0]
        handler = self.request(tid=tid, handler_cls=file.FileHandler)
        yield handler.get('logo')
        with open(get_storage_path(1, 'files', file_id), 'rb') as f:
            self.assertEqual(handler.request.getResponseBody(), f.read())

    @inlineCallbacks
    def test_delete_site_removes_migrated_storage(self):
        self.assertTrue(os.listdir(get_storage_path(3, 'files')))
        self.assertTrue(os.listdir(get_storage_path(3, 'attachments')))
        with open(get_storage_path(2, 'files', os.listdir(get_storage_path(2, 'files'))[0]), 'rb') as f:
            expected = f.read()
        yield self.request(role='admin', handler_cls=tenant.TenantInstance).delete(3)
        self.assertFalse(os.path.exists(os.path.join(Settings.tenants_path, '3')))
        with open(get_storage_path(2, 'files', os.listdir(get_storage_path(2, 'files'))[0]), 'rb') as f:
            self.assertEqual(f.read(), expected)

    @inlineCallbacks
    def test_cleaning_keeps_misplaced_migrated_file(self):
        file_id = os.listdir(get_storage_path(2, 'attachments'))[0]
        source = get_storage_path(2, 'attachments', file_id)
        destination = get_storage_path(3, 'attachments', file_id)
        shutil.copyfile(source, destination)
        os.utime(destination, (0, 0))
        yield cleaning.Cleaning().run()
        with open(source, 'rb') as original, open(destination, 'rb') as misplaced:
            self.assertEqual(original.read(), misplaced.read())

    @inlineCallbacks
    def test_cleaning_handles_unexpected_migrated_storage(self):
        target = os.path.join(Settings.working_path, 'outside-storage')
        os.mkdir(target)
        with open(os.path.join(target, 'file'), 'wb') as f:
            f.write(b'keep')
        link = get_storage_path(2, 'attachments', 'untracked-link')
        os.symlink(target, link)
        orphan = get_storage_path(999, 'attachments', 'untracked', create=True)
        with open(orphan, 'wb') as f:
            f.write(b'remove')
        unexpected = os.path.join(Settings.tenants_path, 'unexpected')
        os.mkdir(unexpected)
        with open(os.path.join(unexpected, 'file'), 'wb') as f:
            f.write(b'keep')

        yield cleaning.Cleaning().run()

        self.assertFalse(os.path.lexists(link))
        self.assertFalse(os.path.exists(os.path.join(Settings.tenants_path, '999')))
        for path in (target, unexpected):
            with open(os.path.join(path, 'file'), 'rb') as f:
                self.assertEqual(f.read(), b'keep')

    def test_startup_keeps_misplaced_migrated_file(self):
        file_id = os.listdir(get_storage_path(2, 'attachments'))[0]
        source = get_storage_path(2, 'attachments', file_id)
        destination = get_storage_path(3, 'attachments', file_id)
        with open(source, 'rb') as f:
            expected = f.read()
        os.rename(source, destination)

        sync_clean_untracked_files()

        self.assertFalse(os.path.exists(source))
        with open(destination, 'rb') as f:
            self.assertEqual(f.read(), expected)

    def test_startup_unlinks_symlinks_without_following_them(self):
        file_id = os.listdir(get_storage_path(2, 'attachments'))[0]
        tracked = get_storage_path(2, 'attachments', file_id)
        with open(tracked, 'rb') as f:
            expected = f.read()
        target = os.path.join(Settings.working_path, 'outside-storage')
        os.mkdir(target)
        target_file = os.path.join(target, 'file')
        with open(target_file, 'wb') as f:
            f.write(b'keep')
        targets = (tracked, target_file, target, os.path.join(target, 'missing'))
        links = []
        for index, destination in enumerate(targets):
            link = get_storage_path(2, 'attachments', 'untracked-link-%d' % index)
            os.symlink(destination, link)
            links.append(link)

        sync_clean_untracked_files()

        for link in links:
            self.assertFalse(os.path.lexists(link))
        with open(tracked, 'rb') as f:
            self.assertEqual(f.read(), expected)
        with open(target_file, 'rb') as f:
            self.assertEqual(f.read(), b'keep')
        self.assertFalse(os.path.lexists(targets[-1]))

    def test_startup_continues_after_file_removal_failure(self):
        # Use the real logger: test helpers otherwise silence its formatting.
        self.patch(db, 'log', Logger())
        paths = []
        for index in range(2):
            path = get_storage_path(2, 'attachments', 'untracked-file-%d' % index)
            with open(path, 'wb') as f:
                f.write(b'untracked')
            paths.append(path)
        attempted = []
        srm = fs.srm

        def remove(path):
            attempted.append(path)
            if len(attempted) == 1:
                raise OSError('Removal failed')
            srm(path)

        self.patch(fs, 'srm', remove)

        sync_clean_untracked_files()

        self.assertEqual(set(attempted), set(paths))
        self.assertEqual(len(attempted), 2)
        self.assertTrue(os.path.isfile(attempted[0]))
        self.assertFalse(os.path.exists(attempted[1]))
