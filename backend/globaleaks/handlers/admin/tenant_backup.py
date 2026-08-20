import hashlib
import json
import os
import shutil
import sqlite3
import tarfile
import tempfile

from twisted.internet import reactor
from twisted.internet.defer import inlineCallbacks, returnValue
from twisted.internet.threads import deferToThreadPool

from globaleaks import DATABASE_VERSION
from globaleaks.db import db_refresh_tenant_cache
from globaleaks.handlers.base import BaseHandler
from globaleaks.orm import db_log, get_thread_pool, transact, tw
from globaleaks.rest import errors
from globaleaks.settings import Settings


BACKUP_FORMAT = 'globaleaks-tenant-backup'
BACKUP_FORMAT_VERSION = 1
BACKUP_DATABASE = 'tenant.db'
BACKUP_MANIFEST = 'manifest.json'
MAX_BACKUP_SIZE = 10 * 1024 * 1024 * 1024
DEFAULT_PROFILE_ID = 1000001
FILE_TABLES = {
    'file': ('files', 'files_path'),
    'internalfile': ('attachments', 'attachments_path'),
    'receiverfile': ('attachments', 'attachments_path'),
    'whistleblowerfile': ('attachments', 'attachments_path'),
}
TRACKED_FILE_TABLES = {
    'files': ('file',),
    'attachments': ('internalfile', 'receiverfile', 'whistleblowerfile'),
}


def quote_identifier(identifier):
    return '"%s"' % identifier.replace('"', '""')


def safe_path(root, *parts):
    root = os.path.abspath(root)
    path = os.path.abspath(os.path.join(root, *parts))
    if os.path.commonpath((root, path)) != root:
        raise errors.InputValidationError('Invalid path in tenant backup')
    return path


def get_tables(connection):
    return [row[0] for row in connection.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
    )]


def get_columns(connection, table):
    return [row[1] for row in connection.execute('PRAGMA table_info(%s)' % quote_identifier(table))]


def get_foreign_keys(connection, table):
    grouped = {}
    for row in connection.execute('PRAGMA foreign_key_list(%s)' % quote_identifier(table)):
        grouped.setdefault(row[0], {'table': row[2], 'columns': []})['columns'].append((row[3], row[4]))
    return list(grouped.values())


def select_tenant_rows(connection, tid):
    tables = get_tables(connection)
    selected = {table: set() for table in tables}
    tenant_ids = {tid}

    for table in tables:
        columns = get_columns(connection, table)
        if table == 'tenant':
            for tenant_id in tenant_ids:
                selected[table].update(row[0] for row in connection.execute(
                    'SELECT rowid FROM %s WHERE id = ?' % quote_identifier(table), (tenant_id,)))
        elif 'tid' in columns:
            for tenant_id in tenant_ids:
                selected[table].update(row[0] for row in connection.execute(
                    'SELECT rowid FROM %s WHERE tid = ?' % quote_identifier(table), (tenant_id,)))

    changed = True
    while changed:
        changed = False
        for child in tables:
            for foreign_key in get_foreign_keys(connection, child):
                parent = foreign_key['table']
                if parent not in selected or not selected[parent]:
                    continue

                parent_rowids = sorted(selected[parent])
                parent_columns = [pair[1] for pair in foreign_key['columns']]
                child_columns = [pair[0] for pair in foreign_key['columns']]
                query = 'SELECT %s FROM %s WHERE rowid = ?' % (
                    ', '.join(quote_identifier(column) for column in parent_columns), quote_identifier(parent))
                child_query = 'SELECT rowid FROM %s WHERE %s' % (
                    quote_identifier(child), ' AND '.join('%s IS ?' % quote_identifier(column) for column in child_columns))
                child_parameters = []
                if 'tid' in get_columns(connection, child):
                    child_query += ' AND tid IN (%s)' % ','.join('?' for _ in tenant_ids)
                    child_parameters = sorted(tenant_ids)

                for parent_rowid in parent_rowids:
                    values = connection.execute(query, (parent_rowid,)).fetchone()
                    if values is None or any(value is None for value in values):
                        continue
                    before = len(selected[child])
                    selected[child].update(row[0] for row in connection.execute(
                        child_query, tuple(values) + tuple(child_parameters)))
                    changed = changed or len(selected[child]) != before

    return selected


def prune_snapshot(connection, selected):
    connection.execute('PRAGMA foreign_keys=OFF')
    for table, rowids in selected.items():
        if rowids:
            placeholders = ','.join('?' for _ in rowids)
            connection.execute('DELETE FROM %s WHERE rowid NOT IN (%s)' % (quote_identifier(table), placeholders), tuple(rowids))
        else:
            connection.execute('DELETE FROM %s' % quote_identifier(table))
    connection.commit()
    connection.execute('VACUUM')


def calculate_sha256(path):
    digest = hashlib.sha256()
    with open(path, 'rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def copy_tracked_files(connection, staging_path):
    files = []
    copied = set()
    for table, (archive_directory, source_attribute) in FILE_TABLES.items():
        if table not in get_tables(connection):
            continue
        for file_id, in connection.execute('SELECT id FROM %s' % quote_identifier(table)):
            key = (archive_directory, file_id)
            if key in copied:
                continue
            copied.add(key)
            source_directory = getattr(Settings, source_attribute)
            source = safe_path(source_directory, file_id)
            if not os.path.isfile(source):
                continue
            destination_directory = os.path.join(staging_path, archive_directory)
            os.makedirs(destination_directory, exist_ok=True)
            destination = os.path.join(destination_directory, file_id)
            shutil.copy2(source, destination)
            files.append({
                'directory': archive_directory,
                'id': file_id,
                'size': os.path.getsize(destination),
                'sha256': calculate_sha256(destination)
            })
    return files


def create_tenant_backup(tid, output_path):
    staging_path = tempfile.mkdtemp(prefix='tenant-backup-', dir=Settings.tmp_path)
    database_path = os.path.join(staging_path, BACKUP_DATABASE)
    source = sqlite3.connect(Settings.db_file_path)
    destination = sqlite3.connect(database_path)
    try:
        source.backup(destination, pages=-1)
        selected = select_tenant_rows(destination, tid)
        if not selected.get('tenant'):
            raise errors.ResourceNotFound
        prune_snapshot(destination, selected)

        uuid_row = destination.execute(
            "SELECT value FROM config WHERE tid = ? AND var_name = 'uuid'", (tid,)).fetchone()
        files = copy_tracked_files(destination, staging_path)
        manifest = {
            'format': BACKUP_FORMAT,
            'format_version': BACKUP_FORMAT_VERSION,
            'database_version': DATABASE_VERSION,
            'tenant_id': tid,
            'tenant_uuid': uuid_row[0] if uuid_row else '',
            'database_sha256': calculate_sha256(database_path),
            'files': files,
        }
        with open(os.path.join(staging_path, BACKUP_MANIFEST), 'w', encoding='utf-8') as stream:
            json.dump(manifest, stream, sort_keys=True)

        with tarfile.open(output_path, 'w:gz') as archive:
            archive.add(os.path.join(staging_path, BACKUP_MANIFEST), arcname=BACKUP_MANIFEST)
            archive.add(database_path, arcname=BACKUP_DATABASE)
            for item in files:
                archive.add(os.path.join(staging_path, item['directory'], item['id']),
                            arcname=os.path.join(item['directory'], item['id']))
    finally:
        source.close()
        destination.close()
        shutil.rmtree(staging_path, ignore_errors=True)


def extract_archive(archive_path, destination):
    with tarfile.open(archive_path, 'r:gz') as archive:
        total_size = 0
        seen = set()
        for member in archive.getmembers():
            if member.name in seen:
                raise errors.InputValidationError('Duplicate tenant backup member')
            seen.add(member.name)
            total_size += member.size
            if total_size > MAX_BACKUP_SIZE:
                raise errors.FileTooBig(MAX_BACKUP_SIZE // (1024 * 1024))
            target = safe_path(destination, member.name)
            if not member.isfile():
                raise errors.InputValidationError('Invalid tenant backup member')
            source = archive.extractfile(member)
            if source is None:
                raise errors.InputValidationError('Invalid tenant backup member')
            os.makedirs(os.path.dirname(target), exist_ok=True)
            with source, open(target, 'wb') as output:
                shutil.copyfileobj(source, output)


def load_and_validate_backup(archive_path, staging_path):
    try:
        extract_archive(archive_path, staging_path)
        with open(os.path.join(staging_path, BACKUP_MANIFEST), encoding='utf-8') as stream:
            manifest = json.load(stream)
    except (OSError, ValueError, tarfile.TarError) as exc:
        raise errors.InputValidationError('Invalid tenant backup: %s' % exc)

    if manifest.get('format') != BACKUP_FORMAT or manifest.get('format_version') != BACKUP_FORMAT_VERSION:
        raise errors.InputValidationError('Unsupported tenant backup format')
    if manifest.get('database_version') != DATABASE_VERSION:
        raise errors.InputValidationError('Tenant backup database version mismatch')
    if not isinstance(manifest.get('tenant_id'), int) or manifest['tenant_id'] <= 1 or \
       manifest['tenant_id'] >= DEFAULT_PROFILE_ID or not isinstance(manifest.get('tenant_uuid'), str) or \
       not manifest['tenant_uuid'] or not isinstance(manifest.get('files'), list):
        raise errors.InputValidationError('Invalid tenant backup identity')

    database_path = os.path.join(staging_path, BACKUP_DATABASE)
    if calculate_sha256(database_path) != manifest.get('database_sha256'):
        raise errors.InputValidationError('Tenant backup database checksum mismatch')
    file_descriptors = set()
    for item in manifest.get('files', []):
        if item.get('directory') not in ('files', 'attachments') or not isinstance(item.get('id'), str):
            raise errors.InputValidationError('Invalid tenant backup file descriptor')
        descriptor = (item['directory'], item['id'])
        if descriptor in file_descriptors:
            raise errors.InputValidationError('Duplicate tenant backup file descriptor')
        file_descriptors.add(descriptor)
        path = safe_path(staging_path, item['directory'], item['id'])
        if not os.path.isfile(path) or os.path.getsize(path) != item.get('size') or calculate_sha256(path) != item.get('sha256'):
            raise errors.InputValidationError('Tenant backup file checksum mismatch')
    return manifest, database_path


def validate_database_scope(connection, manifest):
    tenant = connection.execute('SELECT id FROM tenant WHERE id = ?', (manifest['tenant_id'],)).fetchone()
    uuid_row = connection.execute(
        "SELECT value FROM config WHERE tid = ? AND var_name = 'uuid'", (manifest['tenant_id'],)).fetchone()
    if tenant is None or uuid_row is None or uuid_row[0] != manifest['tenant_uuid']:
        raise errors.InputValidationError('Tenant backup identity mismatch')

    allowed_tenant_ids = {manifest['tenant_id']}

    archived_tenant_ids = {row[0] for row in connection.execute('SELECT id FROM tenant')}
    if archived_tenant_ids != allowed_tenant_ids:
        raise errors.InputValidationError('Tenant backup contains unrelated tenants')

    for table in get_tables(connection):
        if 'tid' not in get_columns(connection, table):
            continue
        tenant_ids = {row[0] for row in connection.execute(
            'SELECT DISTINCT tid FROM %s WHERE tid IS NOT NULL' % quote_identifier(table))}
        if not tenant_ids.issubset(allowed_tenant_ids):
            raise errors.InputValidationError(
                'Tenant backup contains unrelated rows in table %s' % table)

    expected_files = set()
    for table, (directory, _) in FILE_TABLES.items():
        if table in get_tables(connection):
            expected_files.update((directory, row[0]) for row in connection.execute(
                'SELECT id FROM %s' % quote_identifier(table)))
    manifest_files = {(item.get('directory'), item.get('id')) for item in manifest['files']}
    if not manifest_files.issubset(expected_files):
        raise errors.InputValidationError('Tenant backup file inventory mismatch')


def normalize_database_scope(connection, manifest):
    selected = select_tenant_rows(connection, manifest['tenant_id'])
    prune_snapshot(connection, selected)

    tracked_files = set()
    for table, (directory, _) in FILE_TABLES.items():
        if table in get_tables(connection):
            tracked_files.update((directory, row[0]) for row in connection.execute(
                'SELECT id FROM %s' % quote_identifier(table)))
    manifest['files'] = [item for item in manifest['files']
                         if (item.get('directory'), item.get('id')) in tracked_files]


def get_table_order(connection, tables):
    dependencies = {table: set() for table in tables}
    for table in tables:
        dependencies[table].update(fk['table'] for fk in get_foreign_keys(connection, table) if fk['table'] in dependencies)
    ordered = []
    remaining = set(tables)
    while remaining:
        ready = sorted(table for table in remaining if not (dependencies[table] & remaining))
        if not ready:
            ready = sorted(remaining)
        ordered.extend(ready)
        remaining.difference_update(ready)
    return ordered


def check_database_collisions(live, backup, manifest):
    tenant_id = manifest['tenant_id']
    if live.execute('SELECT 1 FROM tenant WHERE id = ?', (tenant_id,)).fetchone():
        raise errors.InputValidationError('Tenant ID already exists')
    if live.execute("SELECT 1 FROM config WHERE var_name = 'uuid' AND value = ?", (manifest['tenant_uuid'],)).fetchone():
        raise errors.InputValidationError('Tenant UUID already exists')

    live_tables = set(get_tables(live))
    for table in get_tables(backup):
        if table not in live_tables or get_columns(live, table) != get_columns(backup, table):
            raise errors.InputValidationError('Tenant backup schema mismatch')


def file_is_tracked(connection, directory, file_id):
    live_tables = set(get_tables(connection))
    for table in TRACKED_FILE_TABLES[directory]:
        if table in live_tables and connection.execute(
                'SELECT 1 FROM %s WHERE id = ? LIMIT 1' % quote_identifier(table),
                (file_id,)).fetchone():
            return True
    return False


def restore_tenant_backup(archive_path):
    staging_path = tempfile.mkdtemp(prefix='tenant-restore-', dir=Settings.tmp_path)
    copied_files = []
    preserved_files = []
    reusable_files = set()
    live = sqlite3.connect(Settings.db_file_path, timeout=30)
    backup = None
    try:
        manifest, database_path = load_and_validate_backup(archive_path, staging_path)
        backup = sqlite3.connect(database_path)
        normalize_database_scope(backup, manifest)
        validate_database_scope(backup, manifest)
        live.execute('PRAGMA foreign_keys=ON')
        check_database_collisions(live, backup, manifest)

        for item in manifest.get('files', []):
            destination_root = Settings.files_path if item['directory'] == 'files' else Settings.attachments_path
            destination = safe_path(destination_root, item['id'])
            if os.path.exists(destination):
                if not os.path.isfile(destination) or file_is_tracked(live, item['directory'], item['id']):
                    raise errors.InputValidationError('Backup file already exists: %s' % item['id'])
                if os.path.getsize(destination) == item['size'] and calculate_sha256(destination) == item['sha256']:
                    reusable_files.add((item['directory'], item['id']))
                    continue

                preserved = safe_path(staging_path, 'preserved', item['directory'], item['id'])
                os.makedirs(os.path.dirname(preserved), exist_ok=True)
                shutil.move(destination, preserved)
                preserved_files.append((destination, preserved))

        live.execute('BEGIN IMMEDIATE')
        live.execute('PRAGMA defer_foreign_keys=ON')
        for table in get_table_order(backup, get_tables(backup)):
            columns = get_columns(backup, table)
            if table == 'auditlog':
                columns.remove('id')
            rows = backup.execute('SELECT %s FROM %s' % (
                ', '.join(quote_identifier(column) for column in columns), quote_identifier(table))).fetchall()
            if not rows:
                continue
            insert = 'INSERT INTO %s (%s) VALUES (%s)' % (
                quote_identifier(table), ', '.join(quote_identifier(column) for column in columns), ', '.join('?' for _ in columns))
            live.executemany(insert, rows)

        for item in manifest.get('files', []):
            if (item['directory'], item['id']) in reusable_files:
                continue
            destination_root = Settings.files_path if item['directory'] == 'files' else Settings.attachments_path
            source = os.path.join(staging_path, item['directory'], item['id'])
            destination = os.path.join(destination_root, item['id'])
            shutil.copy2(source, destination)
            copied_files.append(destination)

        counter = live.execute("SELECT value FROM config WHERE tid = 1 AND var_name = 'counter_tenants'").fetchone()
        if counter and int(counter[0]) < int(manifest['tenant_id']):
            live.execute("UPDATE config SET value = ? WHERE tid = 1 AND var_name = 'counter_tenants'",
                         (manifest['tenant_id'],))
        live.commit()
        for _, preserved in preserved_files:
            try:
                os.remove(preserved)
            except OSError:
                pass
        return manifest
    except Exception as exception:
        live.rollback()
        for path in copied_files:
            try:
                os.remove(path)
            except OSError:
                pass
        for destination, preserved in preserved_files:
            try:
                if os.path.exists(destination):
                    os.remove(destination)
                shutil.move(preserved, destination)
            except OSError:
                pass
        if isinstance(exception, sqlite3.IntegrityError):
            raise errors.InputValidationError('Tenant backup data conflicts with existing data')
        raise
    finally:
        if backup is not None:
            backup.close()
        live.close()
        shutil.rmtree(staging_path, ignore_errors=True)


@transact
def log_tenant_backup(session, tid, user_id, operation):
    db_log(session, tid=1, type=operation, user_id=user_id, object_id=str(tid))


class TenantBackupExport(BaseHandler):
    check_roles = 'admin'
    root_tenant_only = True
    allowed_mimetypes = ['application/gzip', 'application/x-tar', 'application/octet-stream']

    @inlineCallbacks
    def get(self, tid):
        tid = int(tid)
        if tid == 1 or tid >= DEFAULT_PROFILE_ID:
            raise errors.ForbiddenOperation
        descriptor, output_path = tempfile.mkstemp(prefix='tenant-', suffix='.tar.gz', dir=Settings.tmp_path)
        os.close(descriptor)
        try:
            yield deferToThreadPool(reactor, get_thread_pool(), create_tenant_backup, tid, output_path)
            yield log_tenant_backup(tid, self.session.user_id, 'export_tenant')
            with open(output_path, 'rb') as stream:
                yield self.write_file_as_download('tenant-%d.tar.gz' % tid, stream)
        finally:
            try:
                os.remove(output_path)
            except OSError:
                pass


class TenantBackupImport(BaseHandler):
    check_roles = 'admin'
    root_tenant_only = True
    invalidate_cache = True
    upload_handler = True
    allowed_mimetypes = ['application/gzip', 'application/x-gzip', 'application/x-tar', 'application/octet-stream']

    @inlineCallbacks
    def post(self):
        if self.uploaded_file['type'] not in self.allowed_mimetypes:
            raise errors.InputValidationError('Invalid tenant backup content type')
        descriptor, archive_path = tempfile.mkstemp(prefix='tenant-upload-', suffix='.tar.gz', dir=Settings.tmp_path)
        os.close(descriptor)
        try:
            yield self.write_upload_plaintext_to_disk(archive_path)
            manifest = yield deferToThreadPool(reactor, get_thread_pool(), restore_tenant_backup, archive_path)
            yield log_tenant_backup(manifest['tenant_id'], self.session.user_id, 'import_tenant')
            yield tw(db_refresh_tenant_cache, manifest['tenant_id'])
            returnValue({'id': manifest['tenant_id'], 'uuid': manifest['tenant_uuid']})
        finally:
            try:
                os.remove(archive_path)
            except OSError:
                pass
