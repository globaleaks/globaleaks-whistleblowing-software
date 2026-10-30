import io
import json
import os
import shutil
import sqlite3
import tarfile

from twisted.internet.defer import inlineCallbacks

from globaleaks import DATABASE_VERSION
from globaleaks.db import refresh_tenant_cache, update_db
from globaleaks.handlers.admin import tenant, tenant_backup
from globaleaks.jobs import backup
from globaleaks.rest import api, errors
from globaleaks.settings import Settings
from globaleaks.tests import helpers
from globaleaks.utils.fs import get_storage_path
from globaleaks.utils.log import Logger


class TestTenantBackup(helpers.TestHandler):
    @inlineCallbacks
    def setUp(self):
        yield super().setUp()
        fixture = os.path.join(helpers.DATA_DIR, 'workingdirs', 'populated', '71')
        shutil.copytree(fixture, Settings.working_path, dirs_exist_ok=True)
        self.assertEqual(update_db(), DATABASE_VERSION)
        yield refresh_tenant_cache()
        # Keep physical test files in this temporary working directory.
        with sqlite3.connect(Settings.db_file_path) as connection:
            queries = [('files', 'SELECT tid, id FROM file')]
            for table in ('internalfile', 'receiverfile'):
                queries.append(('attachments', 'SELECT internaltip.tid, %s.id FROM %s '
                                'JOIN internaltip ON %s.internaltip_id = internaltip.id' % (table, table, table)))
            for kind, query in queries:
                for tid, file_id in connection.execute(query):
                    with open(get_storage_path(tid, kind, file_id, create=True), 'wb') as stream:
                        stream.write(('Test content for %s' % file_id).encode())
        self.archive_path = os.path.join(Settings.tmp_path, 'tenant-2.tar.gz')

    def create_backup(self):
        tenant_backup.create_tenant_backup(2, self.archive_path)
        return self.archive_path

    def storage_contents(self, tid):
        contents = {}
        for kind in ('files', 'attachments', 'log'):
            root = get_storage_path(tid, kind)
            if not os.path.isdir(root):
                continue
            for name in os.listdir(root):
                with open(get_storage_path(tid, kind, name), 'rb') as stream:
                    contents[kind, name] = stream.read()
        return contents

    def test_export_contains_only_the_selected_tenant_and_its_files(self):
        self.create_backup()
        staging = os.path.join(Settings.tmp_path, 'inventory')
        os.mkdir(staging)
        manifest, database_path = tenant_backup.load_and_validate_backup(self.archive_path, staging)
        with sqlite3.connect(database_path) as connection:
            tenant_backup.validate_database_scope(connection, manifest)
            self.assertEqual(connection.execute('SELECT id FROM tenant').fetchall(), [(2,)])
            self.assertTrue(connection.execute('SELECT COUNT(*) FROM internaltip').fetchone()[0])
            self.assertTrue(connection.execute('SELECT 1 FROM internaltipanswers a JOIN archivedschema s '
                                               'ON a.questionnaire_hash = s.hash').fetchone())
        inventory = tenant_backup.read_backup_inventory(self.archive_path)
        self.assertEqual(inventory['tenant_id'], 2)
        self.assertTrue(inventory['uploaded_files'])
        self.assertTrue(inventory['attachments'])
        with tarfile.open(self.archive_path) as archive:
            self.assertIn(tenant_backup.BACKUP_REPORT, archive.getnames())
            for (kind, name), expected in self.storage_contents(2).items():
                self.assertEqual(archive.extractfile('%s/%s' % (kind, name)).read(), expected)

    @inlineCallbacks
    def test_restore_recovers_tenant_data_files_and_logs(self):
        Logger().write_tenant_log(2, 'Tenant backup test')
        expected = self.storage_contents(2)
        other = self.storage_contents(3)
        with sqlite3.connect(Settings.db_file_path) as connection:
            users = connection.execute('SELECT id FROM user WHERE tid = 2 ORDER BY id').fetchall()
            schemas = connection.execute('SELECT DISTINCT s.hash, s.schema FROM archivedschema s '
                                         'JOIN internaltipanswers a ON s.hash = a.questionnaire_hash '
                                         'JOIN internaltip t ON a.internaltip_id = t.id WHERE t.tid = 2').fetchall()
            self.assertTrue(schemas)
        self.create_backup()
        yield self.request(role='admin', handler_cls=tenant.TenantInstance).delete(2)
        self.assertFalse(os.path.exists(os.path.join(Settings.tenants_path, '2')))

        manifest = tenant_backup.restore_tenant_backup(self.archive_path)
        yield refresh_tenant_cache()

        self.assertEqual(manifest['tenant_id'], 2)
        self.assertEqual(self.storage_contents(2), expected)
        self.assertEqual(self.storage_contents(3), other)
        with sqlite3.connect(Settings.db_file_path) as connection:
            self.assertEqual(connection.execute('SELECT id FROM user WHERE tid = 2 ORDER BY id').fetchall(), users)
            self.assertEqual(connection.execute('SELECT DISTINCT s.hash, s.schema FROM archivedschema s '
                                                'JOIN internaltipanswers a ON s.hash = a.questionnaire_hash '
                                                'JOIN internaltip t ON a.internaltip_id = t.id WHERE t.tid = 2').fetchall(), schemas)
            self.assertEqual(connection.execute('PRAGMA foreign_key_check').fetchall(), [])

    def test_restore_rejects_an_existing_tenant(self):
        self.create_backup()
        expected = self.storage_contents(2)
        self.assertRaises(errors.InputValidationError, tenant_backup.restore_tenant_backup, self.archive_path)
        self.assertEqual(self.storage_contents(2), expected)

    def test_restore_rejects_a_modified_attachment(self):
        self.create_backup()
        staging = os.path.join(Settings.tmp_path, 'modified')
        os.mkdir(staging)
        tenant_backup.extract_archive(self.archive_path, staging)
        with open(os.path.join(staging, tenant_backup.BACKUP_MANIFEST)) as stream:
            manifest = json.load(stream)
        item = next(item for item in manifest['files'] if item['directory'] == 'attachments')
        with open(os.path.join(staging, item['directory'], item['id']), 'ab') as stream:
            stream.write(b'modified')
        with tarfile.open(self.archive_path, 'w:gz') as archive:
            for root, directories, files in os.walk(staging):
                for name in files:
                    path = os.path.join(root, name)
                    archive.add(path, arcname=os.path.relpath(path, staging))
        self.assertRaises(errors.InputValidationError, tenant_backup.restore_tenant_backup, self.archive_path)

    def test_archive_rejects_traversal_and_symlinks(self):
        for name, kind in (('../outside', tarfile.REGTYPE), ('link', tarfile.SYMTYPE)):
            with tarfile.open(self.archive_path, 'w:gz') as archive:
                member = tarfile.TarInfo(name)
                member.type = kind
                member.linkname = '/etc/passwd' if kind == tarfile.SYMTYPE else ''
                member.size = 0
                archive.addfile(member, io.BytesIO())
            self.assertRaises(errors.InputValidationError, tenant_backup.restore_tenant_backup, self.archive_path)
        self.assertFalse(os.path.exists(os.path.join(Settings.tmp_path, 'outside')))

    def test_backup_uses_files_from_the_database_snapshot(self):
        snapshot = os.path.join(Settings.tmp_path, 'snapshot')
        os.mkdir(snapshot)
        database_path = os.path.join(snapshot, 'globaleaks.db')
        backup.backup_sqlite_database(database_path)
        source_tenants = os.path.join(snapshot, 'tenants')
        shutil.copytree(Settings.tenants_path, source_tenants)
        expected = self.storage_contents(2)
        for kind, name in expected:
            with open(get_storage_path(2, kind, name), 'wb') as stream:
                stream.write(b'changed after snapshot')

        tenant_backup.create_tenant_backup(2, self.archive_path, database_path, source_tenants)

        with tarfile.open(self.archive_path) as archive:
            for (kind, name), contents in expected.items():
                self.assertEqual(archive.extractfile('%s/%s' % (kind, name)).read(), contents)

    @inlineCallbacks
    def test_report_and_export_handlers(self):
        handler = self.request(role='admin', handler_cls=tenant_backup.TenantBackupReport)
        report = yield handler.get(2)
        self.assertEqual(report['tenant_id'], 2)
        handler = self.request(role='admin', handler_cls=tenant_backup.TenantBackupExport)
        yield handler.get(2)
        with tarfile.open(fileobj=io.BytesIO(handler.request.getResponseBody())) as archive:
            self.assertIn(tenant_backup.BACKUP_DATABASE, archive.getnames())

    @inlineCallbacks
    def test_export_refuses_root_and_profile_tenants(self):
        for tid in (1, 1000001):
            handler = self.request(role='admin', handler_cls=tenant_backup.TenantBackupExport)
            yield self.assertFailure(handler.get(tid), errors.ForbiddenOperation)

    def test_automatic_archives_exclude_root_and_profiles_and_remove_stale_files(self):
        database_path = os.path.join(Settings.tmp_path, 'tenants.db')
        with sqlite3.connect(database_path) as connection:
            connection.execute('CREATE TABLE tenant (id INTEGER PRIMARY KEY)')
            connection.executemany('INSERT INTO tenant VALUES (?)', [(1,), (2,), (3,), (1000001,)])
        stale = os.path.join(Settings.tenant_backups_path, 'tenant-999.tar.gz')
        with open(stale, 'wb') as stream:
            stream.write(b'stale')
        created = []

        def create(tid, source_database_path, source_tenants_path):
            created.append((tid, source_database_path, source_tenants_path))

        self.patch(tenant_backup, 'create_tenant_backup_file', create)
        tenant_backup.create_tenant_backup_files(database_path, Settings.tenants_path)
        self.assertEqual(created, [(tid, database_path, Settings.tenants_path) for tid in (2, 3)])
        self.assertFalse(os.path.exists(stale))

    @inlineCallbacks
    def test_import_handler_restores_an_uploaded_archive(self):
        self.create_backup()
        with open(self.archive_path, 'rb') as stream:
            contents = stream.read()
        yield self.request(role='admin', handler_cls=tenant.TenantInstance).delete(2)
        handler = self.request(role='admin', handler_cls=tenant_backup.TenantBackupImport)
        handler.uploaded_file = {'type': 'application/gzip'}

        def write_upload(path):
            with open(path, 'wb') as stream:
                stream.write(contents)

        self.patch(handler, 'write_upload_plaintext_to_disk', write_upload)
        result = yield handler.post()
        self.assertEqual(result['id'], 2)
        self.assertTrue(self.storage_contents(2))

    def test_handlers_refuse_access_from_another_tenant(self):
        with sqlite3.connect(Settings.db_file_path) as connection:
            uuid = json.loads(connection.execute(
                "SELECT value FROM config WHERE tid = 2 AND var_name = 'uuid'").fetchone()[0])
        resource = api.APIResourceWrapper()
        for method, path in ((b'GET', '3/backup'), (b'GET', '3/backup/report'),
                             (b'POST', 'backup/import')):
            uri = ('https://localhost/t/%s/api/admin/tenants/%s' % (uuid, path)).encode()
            request = helpers.forge_request(uri=uri, method=method)
            resource.render(request)
            self.assertEqual(request.responseCode, 403)

    @inlineCallbacks
    def test_scheduled_backup_generates_tenant_archives(self):
        yield backup.backup_sqlite_database_and_files(Settings.backups_path, 2)
        archive_path = os.path.join(Settings.tenant_backups_path, 'tenant-2.tar.gz')
        inventory = tenant_backup.read_backup_inventory(archive_path)
        self.assertEqual(inventory['tenant_id'], 2)
        self.assertTrue(inventory['attachments'])
        self.assertFalse(os.path.exists(os.path.join(Settings.tenant_backups_path, 'tenant-1.tar.gz')))
        self.assertTrue(backup.list_snapshots(Settings.backups_snapshots_path))


    @inlineCallbacks
    def test_restore_keeps_report_ownership_for_a_site_using_exchanges(self):
        tenant_backup.create_tenant_backup(6, self.archive_path)
        yield self.request(role='admin', handler_cls=tenant.TenantInstance).delete(6)
        tenant_backup.restore_tenant_backup(self.archive_path)
        with sqlite3.connect(Settings.db_file_path) as connection:
            self.assertEqual(connection.execute('PRAGMA foreign_key_check').fetchall(), [])


    def test_first_export_prepares_all_tenant_archives(self):
        tenant_backup.ensure_tenant_backup_file(2)
        with sqlite3.connect(Settings.db_file_path) as connection:
            tids = [tid for tid, in connection.execute('SELECT id FROM tenant WHERE id > 1 AND id < 1000001')]
        self.assertEqual(set(os.listdir(Settings.tenant_backups_path)),
                         {'tenant-%d.tar.gz' % tid for tid in tids})

    def test_export_rejects_a_tracked_symlink(self):
        file_id = os.listdir(get_storage_path(2, 'files'))[0]
        source = get_storage_path(2, 'files', file_id)
        target = source + '.target'
        os.rename(source, target)
        os.symlink(target, source)
        self.assertRaises(errors.InputValidationError, self.create_backup)
        self.assertTrue(os.path.isfile(target))

    @inlineCallbacks
    def test_restore_rejects_a_destination_symlink(self):
        expected = self.storage_contents(3)
        file_id = os.listdir(get_storage_path(2, 'files'))[0]
        self.create_backup()
        yield self.request(role='admin', handler_cls=tenant.TenantInstance).delete(2)
        destination = get_storage_path(2, 'files', file_id, create=True)
        target = destination + '.target'
        with open(target, 'wb') as stream:
            stream.write(b'keep')
        os.symlink(target, destination)
        self.assertRaises(errors.InputValidationError, tenant_backup.restore_tenant_backup, self.archive_path)
        with open(target, 'rb') as stream:
            self.assertEqual(stream.read(), b'keep')
        self.assertEqual(self.storage_contents(3), expected)


    @inlineCallbacks
    def test_restore_rejects_a_conflicting_saved_report_schema(self):
        self.create_backup()
        with sqlite3.connect(Settings.db_file_path) as connection:
            schema_hash = connection.execute('SELECT a.questionnaire_hash FROM internaltipanswers a '
                                             'JOIN internaltip t ON a.internaltip_id = t.id WHERE t.tid = 2').fetchone()[0]
        yield self.request(role='admin', handler_cls=tenant.TenantInstance).delete(2)
        with sqlite3.connect(Settings.db_file_path) as connection:
            connection.execute("UPDATE archivedschema SET schema = '{}' WHERE hash = ?", (schema_hash,))
        self.assertRaises(errors.InputValidationError, tenant_backup.restore_tenant_backup, self.archive_path)
        with sqlite3.connect(Settings.db_file_path) as connection:
            self.assertIsNone(connection.execute('SELECT id FROM tenant WHERE id = 2').fetchone())
            self.assertEqual(connection.execute('SELECT schema FROM archivedschema WHERE hash = ?',
                                                 (schema_hash,)).fetchone()[0], '{}')
