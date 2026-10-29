import hashlib
import json
import os
import re
import shutil
import sqlite3
import tarfile
import tempfile

from html import escape

from twisted.internet import reactor
from twisted.internet.defer import inlineCallbacks
from twisted.internet.threads import deferToThreadPool

from globaleaks import DATABASE_VERSION
from globaleaks.handlers.base import BaseHandler
from globaleaks.models.config import get_default
from globaleaks.models.config_desc import ConfigDescriptor
from globaleaks.models.enums import EnumUserRole
from globaleaks.orm import db_log, get_thread_pool, transact, tw
from globaleaks.rest import errors
from globaleaks.settings import Settings
from globaleaks.utils.fs import get_storage_path
from globaleaks.utils.log import log


BACKUP_FORMAT = 'globaleaks-tenant-backup'
BACKUP_DATABASE = 'tenant.db'
BACKUP_MANIFEST = 'manifest.json'
BACKUP_REPORT = 'backup.html'
MAX_BACKUP_SIZE = 10 * 1024 * 1024 * 1024
DEFAULT_PROFILE_ID = 1000001
FILE_TABLES = {
    'file': 'files',
    'internalfile': 'attachments',
    'receiverfile': 'attachments',
    'whistleblowerfile': 'attachments',
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
    columns = {table: get_columns(connection, table) for table in tables}
    foreign_keys = {table: get_foreign_keys(connection, table) for table in tables}
    selected = {table: set() for table in tables}
    tenant_ids = {tid}

    for table in tables:
        if table == 'tenant':
            for tenant_id in tenant_ids:
                selected[table].update(row[0] for row in connection.execute(
                    'SELECT rowid FROM %s WHERE id = ?' % quote_identifier(table), (tenant_id,)))
        elif 'tid' in columns[table]:
            for tenant_id in tenant_ids:
                selected[table].update(row[0] for row in connection.execute(
                    'SELECT rowid FROM %s WHERE tid = ?' % quote_identifier(table), (tenant_id,)))

    changed = True
    while changed:
        changed = False
        for child in tables:
            for foreign_key in foreign_keys[child]:
                parent = foreign_key['table']
                # Reports own their files and accesses, including cross-site exchanges.
                if 'internaltip_id' in columns[child] and parent != 'internaltip':
                    continue
                if 'internalfile_id' in columns[child] and parent != 'internalfile':
                    continue
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
                if 'tid' in columns[child]:
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


def storage_file_tenant(connection, table, file_id):
    if table == 'file':
        query = 'SELECT tid FROM file WHERE id = ?'
    elif table == 'whistleblowerfile':
        query = ('SELECT t.tid FROM whistleblowerfile f JOIN internalfile i '
                 'ON f.internalfile_id = i.id JOIN internaltip t ON i.internaltip_id = t.id WHERE f.id = ?')
    else:
        query = ('SELECT t.tid FROM %s f JOIN internaltip t '
                 'ON f.internaltip_id = t.id WHERE f.id = ?') % quote_identifier(table)
    return connection.execute(query, (file_id,)).fetchone()[0]


def copy_tracked_files(connection, staging_path, tenants_path=None):
    files = []
    copied = set()
    tables = set(get_tables(connection))
    for table, archive_directory in FILE_TABLES.items():
        if table not in tables:
            continue
        for file_id, in connection.execute('SELECT id FROM %s' % quote_identifier(table)):
            key = (archive_directory, file_id)
            if key in copied:
                continue
            copied.add(key)
            tid = storage_file_tenant(connection, table, file_id)
            source = get_storage_path(tid, archive_directory, file_id, tenants_path=tenants_path)
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


def is_tenant_log_name(name):
    return isinstance(name, str) and re.fullmatch(r'globaleaks\.log(?:\.[1-9][0-9]*)?', name) is not None


def copy_tenant_logs(tid, staging_path, tenants_path=None):
    files = []
    with log._tenant_log_lock:
        directory = get_storage_path(tid, 'log', tenants_path=tenants_path)
        if not os.path.isdir(directory):
            return files
        for name in sorted(os.listdir(directory)):
            if not is_tenant_log_name(name):
                continue
            source = get_storage_path(tid, 'log', name, tenants_path=tenants_path)
            if os.path.islink(source) or not os.path.isfile(source):
                raise errors.InputValidationError('Invalid tenant log file')
            destination = safe_path(staging_path, 'log', name)
            os.makedirs(os.path.dirname(destination), mode=0o700, exist_ok=True)
            shutil.copy2(source, destination)
            files.append({
                'directory': 'log',
                'id': name,
                'size': os.path.getsize(destination),
                'sha256': calculate_sha256(destination)
            })
    return files


def decode_config_value(value):
    try:
        decoded = json.loads(value)
        return str(decoded)
    except (TypeError, ValueError):
        return str(value)


def format_file_size(size):
    value = float(size)
    for unit in ('B', 'KB', 'MB', 'GB'):
        if value < 1024 or unit == 'GB':
            return '%d %s' % (value, unit) if unit == 'B' else '%.1f %s' % (value, unit)
        value /= 1024


def get_backup_report_details(connection, tid):
    keys = ('profile', 'hostname', 'subdomain', 'rootdomain', 'disable_submissions',
            'enable_scoring_system', 'default_language', 'default_tip_timetolive',
            'maximum_filesize')
    profile_row = connection.execute(
        "SELECT value FROM config WHERE tid = ? AND var_name = 'profile'",
        (tid,)).fetchone()
    profile = json.loads(profile_row[0]) if profile_row else 'default'
    profile_id = DEFAULT_PROFILE_ID
    if profile != 'default':
        row = connection.execute(
            "SELECT tid FROM config WHERE var_name = 'uuid' AND value = ?",
            (json.dumps(profile),)).fetchone()
        if row:
            profile_id = row[0]

    tenant_ids = (tid, profile_id, DEFAULT_PROFILE_ID, 1)
    rows = connection.execute(
        'SELECT tid, var_name, value FROM config WHERE tid IN (%s) AND var_name IN (%s)' %
        (','.join('?' for _ in tenant_ids), ','.join('?' for _ in keys)),
        tenant_ids + keys)
    config = {(tenant_id, key): json.loads(value) for tenant_id, key, value in rows}

    def setting(key):
        for tenant_id in (tid, profile_id, DEFAULT_PROFILE_ID):
            if (tenant_id, key) in config:
                return config[(tenant_id, key)]
        return get_default(ConfigDescriptor[key].default)

    hostname = setting('hostname')
    subdomain = setting('subdomain')
    rootdomain = config.get((1, 'rootdomain'), '')
    if not hostname and subdomain and rootdomain:
        hostname = '%s.%s' % (subdomain, rootdomain)

    tenant = connection.execute('SELECT active FROM tenant WHERE id = ?', (tid,)).fetchone()
    users = dict(connection.execute(
        'SELECT enabled, COUNT(*) FROM user WHERE tid = ? GROUP BY enabled', (tid,)))
    admin = connection.execute(
        'SELECT public_name, enabled FROM user WHERE tid = ? AND role IN (?, ?) '
        'ORDER BY creation_date, id LIMIT 1',
        (tid, EnumUserRole.admin.value, EnumUserRole.admin.name)).fetchone()

    return {
        'url': 'https://%s' % hostname if hostname else 'Not configured',
        'subdomain': subdomain or 'Not configured',
        'site_status': 'Enabled' if tenant[0] else 'Disabled',
        'submissions': 'Disabled' if setting('disable_submissions') else 'Enabled',
        'scoring': 'Enabled' if setting('enable_scoring_system') else 'Disabled',
        'language': setting('default_language'),
        'retention_days': setting('default_tip_timetolive'),
        'maximum_filesize': setting('maximum_filesize'),
        'active_users': users.get(1, 0),
        'disabled_users': users.get(0, 0),
        'admin_name': (admin[0] or 'Name not shared') if admin else 'Not configured',
        'admin_status': ('Enabled' if admin[1] else 'Disabled') if admin else '',
    }


def build_backup_inventory(manifest):
    summary = manifest['summary']

    return {
        'tenant_name': decode_config_value(manifest['tenant_name']),
        'tenant_id': manifest['tenant_id'],
        'details': manifest['report_details'],
        'tenants': summary['tenants'],
        'total_users': summary['total_users'],
        'administrators': summary['administrators'],
        'recipients': summary['recipients'],
        'custodians': summary['custodians'],
        'analysts': summary['analysts'],
        'auditors': summary['auditors'],
        'transmitters': summary['transmitters'],
        'channels': summary['channels'],
        'questionnaires': summary['questionnaires'],
        'reports': summary['reports'],
        'comments': summary['comments'],
        'total_files': len(manifest['files']),
        'uploaded_files': sum(item['directory'] == 'files' for item in manifest['files']),
        'attachments': sum(item['directory'] == 'attachments' for item in manifest['files']),
        'logs': sum(item['directory'] == 'log' for item in manifest['files']),
        'total_file_size': format_file_size(sum(item['size'] for item in manifest['files'])),
    }


def render_tenant_backup_report(manifest):
    inventory = build_backup_inventory(manifest)
    details = inventory['details']
    return '''<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Tenant backup summary</title>
<style>
:root {{ color-scheme: light; --primary: #175cd3; --text: #101828; --muted: #667085;
  --border: #e4e7ec; --surface: #fff; --background: #f2f4f7; }}
* {{ box-sizing: border-box; }}
body {{ margin: 0; background: var(--background); color: var(--text);
  font: 14px/1.5 system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; }}
.page {{ width: min(1080px, calc(100% - 32px)); margin: 40px auto; }}
.header {{ padding: 30px 32px; border-radius: 14px 14px 0 0;
  background: linear-gradient(135deg, #1849a9, #1570ef); color: #fff; }}
.header h1 {{ margin: 0 0 6px; font-size: 26px; }}
.header p {{ margin: 0; color: #d1e9ff; }}
.content {{ padding: 28px 32px 36px; border: 1px solid var(--border); border-top: 0;
  border-radius: 0 0 14px 14px; background: var(--surface); box-shadow: 0 8px 24px #10182812; }}
.cards {{ display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 14px; margin-bottom: 28px; }}
.card {{ padding: 18px; border: 1px solid var(--border); border-radius: 10px; background: #fcfcfd; }}
.card span {{ display: block; color: var(--muted); font-size: 12px; font-weight: 600;
  letter-spacing: .04em; text-transform: uppercase; }}
.card strong {{ display: block; margin-top: 5px; font-size: 22px; }}
h2 {{ margin: 30px 0 12px; font-size: 18px; }}
.metrics {{ display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 12px; }}
.metric {{ display: flex; align-items: center; justify-content: space-between; padding: 14px 16px;
  border: 1px solid var(--border); border-radius: 10px; background: #fcfcfd; }}
.metric span {{ color: #344054; }}
.metric strong {{ color: var(--primary); font-size: 18px; }}
.details {{ margin-top: 30px; padding: 18px 20px; border-radius: 10px; background: #f9fafb; }}
.details strong {{ margin-right: 8px; }}
.details p {{ margin: 4px 0; overflow-wrap: anywhere; }}
.note {{ margin: 14px 0 0; color: var(--muted); font-size: 12px; }}
@media (max-width: 640px) {{ .page {{ width: 100%; margin: 0; }}
  .header, .content {{ border-radius: 0; }} .content {{ padding: 22px 18px; }}
  .cards, .metrics {{ grid-template-columns: 1fr; }} }}
</style>
</head>
<body>
<main class="page">
<header class="header"><h1>Tenant backup summary</h1><p>{name}</p></header>
<section class="content">
<div class="cards">
<div class="card"><span>Tenants</span><strong>{tenants}</strong></div>
<div class="card"><span>Users</span><strong>{total_users}</strong></div>
<div class="card"><span>Reports</span><strong>{reports}</strong></div>
<div class="card"><span>Files</span><strong>{total_files}</strong></div>
</div>
<h2>Site and access</h2>
<div class="details">
<p><strong>Website URL:</strong> {url}</p>
<p><strong>Subdomain:</strong> {subdomain}</p>
<p><strong>Site status:</strong> {site_status}</p>
</div>
<h2>Main settings</h2>
<div class="metrics">
<div class="metric"><span>Submissions</span><strong>{submissions}</strong></div>
<div class="metric"><span>Scoring</span><strong>{scoring}</strong></div>
<div class="metric"><span>Default language</span><strong>{language}</strong></div>
<div class="metric"><span>Report retention</span><strong>{retention_days} days</strong></div>
<div class="metric"><span>Maximum file size</span><strong>{maximum_filesize} MB</strong></div>
</div>
<p class="note">Settings and website address reflect this installation when the backup was created.</p>
<h2>People</h2>
<div class="details">
<p><strong>First administrator:</strong> {admin_name} {admin_status}</p>
<p><strong>Enabled users:</strong> {active_users}</p>
<p><strong>Disabled users:</strong> {disabled_users}</p>
</div>
<p class="note">Only the administrator's public display name is shown.</p>
<div class="metrics">
<div class="metric"><span>Administrators</span><strong>{administrators}</strong></div>
<div class="metric"><span>Recipients</span><strong>{recipients}</strong></div>
<div class="metric"><span>Custodians</span><strong>{custodians}</strong></div>
<div class="metric"><span>Analysts</span><strong>{analysts}</strong></div>
<div class="metric"><span>Auditors</span><strong>{auditors}</strong></div>
<div class="metric"><span>Transmitters</span><strong>{transmitters}</strong></div>
</div>
<h2>Content</h2>
<div class="metrics">
<div class="metric"><span>Channels</span><strong>{channels}</strong></div>
<div class="metric"><span>Questionnaires</span><strong>{questionnaires}</strong></div>
<div class="metric"><span>Reports</span><strong>{reports}</strong></div>
<div class="metric"><span>Comments</span><strong>{comments}</strong></div>
<div class="metric"><span>Uploaded files</span><strong>{uploaded_files}</strong></div>
<div class="metric"><span>Attachments</span><strong>{attachments}</strong></div>
<div class="metric"><span>Log files</span><strong>{logs}</strong></div>
</div>
<div class="details">
<p><strong>Tenant name:</strong> {name}</p>
<p><strong>Tenant ID:</strong> {tenant_id}</p>
<p><strong>Total file size:</strong> {total_file_size}</p>
</div>
</section>
</main>
</body>
</html>
'''.format(name=escape(inventory['tenant_name']),
           tenant_id=inventory['tenant_id'],
           url=escape(details['url']),
           subdomain=escape(details['subdomain']),
           site_status=details['site_status'],
           submissions=details['submissions'],
           scoring=details['scoring'],
           language=escape(details['language']),
           retention_days=details['retention_days'],
           maximum_filesize=details['maximum_filesize'],
           admin_name=escape(details['admin_name']),
           admin_status=details['admin_status'],
           active_users=details['active_users'],
           disabled_users=details['disabled_users'],
           tenants=inventory['tenants'],
           total_users=inventory['total_users'],
           administrators=inventory['administrators'],
           recipients=inventory['recipients'],
           custodians=inventory['custodians'],
           analysts=inventory['analysts'],
           auditors=inventory['auditors'],
           transmitters=inventory['transmitters'],
           channels=inventory['channels'],
           questionnaires=inventory['questionnaires'],
           reports=inventory['reports'],
           comments=inventory['comments'],
           uploaded_files=inventory['uploaded_files'],
           attachments=inventory['attachments'],
           logs=inventory['logs'],
           total_files=inventory['total_files'],
           total_file_size=inventory['total_file_size'])


def create_tenant_backup(tid, output_path, source_database_path=None, source_tenants_path=None):
    from globaleaks.jobs.backup import backup_sqlite_database

    os.makedirs(Settings.backups_tmp_path, exist_ok=True)
    staging_path = tempfile.mkdtemp(prefix='tenant-backup-', dir=Settings.backups_tmp_path)
    database_path = os.path.join(staging_path, BACKUP_DATABASE)
    if source_database_path is None:
        backup_sqlite_database(database_path)
    else:
        backup_sqlite_database(database_path, source_database_path)
    destination = sqlite3.connect(database_path)
    try:
        selected = select_tenant_rows(destination, tid)
        if not selected.get('tenant'):
            raise errors.ResourceNotFound
        report_details = get_backup_report_details(destination, tid)
        prune_snapshot(destination, selected)

        uuid_row = destination.execute(
            "SELECT value FROM config WHERE tid = ? AND var_name = 'uuid'", (tid,)).fetchone()
        name_row = destination.execute(
            "SELECT value FROM config WHERE tid = ? AND var_name = 'name'", (tid,)).fetchone()
        files = copy_tracked_files(destination, staging_path, source_tenants_path)
        files.extend(copy_tenant_logs(tid, staging_path, source_tenants_path))
        tables = {table: destination.execute(
            'SELECT COUNT(*) FROM %s' % quote_identifier(table)).fetchone()[0]
            for table in get_tables(destination)}
        role_counts = dict(destination.execute(
            'SELECT role, COUNT(*) FROM user GROUP BY role'))
        roles = {
            role.name: role_counts.get(role.value, role_counts.get(role.name, 0))
            for role in EnumUserRole
        }
        manifest = {
            'format': BACKUP_FORMAT,
            'database_version': DATABASE_VERSION,
            'tenant_id': tid,
            'tenant_uuid': uuid_row[0] if uuid_row else '',
            'tenant_name': name_row[0] if name_row else '',
            'database_sha256': calculate_sha256(database_path),
            'report_details': report_details,
            'summary': {
                'tenants': tables.get('tenant', 0),
                'total_users': tables.get('user', 0),
                'administrators': roles['admin'],
                'recipients': roles['receiver'],
                'custodians': roles['custodian'],
                'analysts': roles['analyst'],
                'auditors': roles['auditor'],
                'transmitters': roles['transmitter'],
                'channels': tables.get('context', 0),
                'questionnaires': tables.get('questionnaire', 0),
                'reports': tables.get('internaltip', 0),
                'comments': tables.get('comment', 0),
            },
            'tables': tables,
            'files': files,
        }
        with open(os.path.join(staging_path, BACKUP_MANIFEST), 'w', encoding='utf-8') as stream:
            json.dump(manifest, stream, sort_keys=True)
        report = render_tenant_backup_report(manifest)
        with open(os.path.join(staging_path, BACKUP_REPORT), 'w', encoding='utf-8') as stream:
            stream.write(report)

        with tarfile.open(output_path, 'w:gz') as archive:
            archive.add(os.path.join(staging_path, BACKUP_MANIFEST), arcname=BACKUP_MANIFEST)
            archive.add(os.path.join(staging_path, BACKUP_REPORT), arcname=BACKUP_REPORT)
            archive.add(database_path, arcname=BACKUP_DATABASE)
            for item in files:
                archive.add(os.path.join(staging_path, item['directory'], item['id']),
                            arcname=os.path.join(item['directory'], item['id']))
    finally:
        destination.close()
        shutil.rmtree(staging_path, ignore_errors=True)


def create_tenant_backup_file(tid, source_database_path=None, source_tenants_path=None):
    os.makedirs(Settings.tenant_backups_path, exist_ok=True)
    archive_path = os.path.join(Settings.tenant_backups_path, 'tenant-%d.tar.gz' % tid)
    descriptor, temporary_archive = tempfile.mkstemp(prefix='tenant-%d-' % tid,
                                                      suffix='.incomplete',
                                                      dir=Settings.tenant_backups_path)
    os.close(descriptor)
    try:
        create_tenant_backup(tid, temporary_archive, source_database_path, source_tenants_path)
        os.replace(temporary_archive, archive_path)
    finally:
        try:
            os.remove(temporary_archive)
        except OSError:
            pass
    return archive_path


def create_tenant_backup_files(source_database_path, source_tenants_path=None):
    os.makedirs(Settings.tenant_backups_path, exist_ok=True)
    connection = sqlite3.connect(source_database_path)
    try:
        tenant_ids = [row[0] for row in connection.execute(
            'SELECT id FROM tenant WHERE id > 1 AND id < ? ORDER BY id',
            (DEFAULT_PROFILE_ID,))]
    finally:
        connection.close()

    expected_files = set()
    for tid in tenant_ids:
        create_tenant_backup_file(tid, source_database_path, source_tenants_path)
        expected_files.add('tenant-%d.tar.gz' % tid)

    for filename in os.listdir(Settings.tenant_backups_path):
        is_tenant_file = filename.startswith('tenant-') and \
                         (filename.endswith('.tar.gz') or filename.endswith('.html'))
        if is_tenant_file and filename not in expected_files:
            os.remove(os.path.join(Settings.tenant_backups_path, filename))


def ensure_tenant_backup_file(tid):
    archive_path = os.path.join(Settings.tenant_backups_path, 'tenant-%d.tar.gz' % tid)
    if os.path.isfile(archive_path):
        try:
            read_backup_inventory(archive_path)
            return archive_path
        except errors.InputValidationError:
            pass

    create_tenant_backup_file(tid, source_tenants_path=Settings.tenants_path)
    if not os.path.isfile(archive_path):
        raise errors.ResourceNotFound
    return archive_path


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


def read_backup_inventory(archive_path):
    try:
        with tarfile.open(archive_path, 'r:gz') as archive:
            member = archive.getmember(BACKUP_MANIFEST)
            source = archive.extractfile(member)
            with source:
                manifest = json.load(source)

        return build_backup_inventory(manifest)
    except (AttributeError, KeyError, OSError, TypeError, UnicodeDecodeError, ValueError, tarfile.TarError):
        raise errors.InputValidationError('Invalid tenant backup inventory')


def load_and_validate_backup(archive_path, staging_path):
    try:
        extract_archive(archive_path, staging_path)
        with open(os.path.join(staging_path, BACKUP_MANIFEST), encoding='utf-8') as stream:
            manifest = json.load(stream)
    except (OSError, ValueError, tarfile.TarError) as exc:
        raise errors.InputValidationError('Invalid tenant backup: %s' % exc)

    if not isinstance(manifest, dict):
        raise errors.InputValidationError('Invalid tenant backup manifest')
    if manifest.get('format') != BACKUP_FORMAT:
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
        if not isinstance(item, dict) or item.get('directory') not in ('files', 'attachments', 'log') or \
           not isinstance(item.get('id'), str):
            raise errors.InputValidationError('Invalid tenant backup file descriptor')
        if not item['id'] or os.path.basename(item['id']) != item['id'] or item['id'] in ('.', '..'):
            raise errors.InputValidationError('Invalid tenant backup filename')
        if item['directory'] == 'log' and not is_tenant_log_name(item['id']):
            raise errors.InputValidationError('Invalid tenant backup log filename')
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

    tables = get_tables(connection)
    for table in tables:
        if 'tid' not in get_columns(connection, table):
            continue
        tenant_ids = {row[0] for row in connection.execute(
            'SELECT DISTINCT tid FROM %s WHERE tid IS NOT NULL' % quote_identifier(table))}
        if not tenant_ids.issubset(allowed_tenant_ids):
            raise errors.InputValidationError(
                'Tenant backup contains unrelated rows in table %s' % table)

    expected_files = set()
    for table, directory in FILE_TABLES.items():
        if table in tables:
            expected_files.update((directory, row[0]) for row in connection.execute(
                'SELECT id FROM %s' % quote_identifier(table)))
    manifest_files = {(item.get('directory'), item.get('id')) for item in manifest['files']
                      if item.get('directory') != 'log'}
    if not manifest_files.issubset(expected_files):
        raise errors.InputValidationError('Tenant backup file inventory mismatch')


def normalize_database_scope(connection, manifest):
    selected = select_tenant_rows(connection, manifest['tenant_id'])
    prune_snapshot(connection, selected)

    tracked_files = set()
    tables = set(get_tables(connection))
    for table, directory in FILE_TABLES.items():
        if table in tables:
            tracked_files.update((directory, row[0]) for row in connection.execute(
                'SELECT id FROM %s' % quote_identifier(table)))
    manifest['files'] = [item for item in manifest['files']
                         if item.get('directory') == 'log' or (item.get('directory'), item.get('id')) in tracked_files]


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
    for table in TRACKED_FILE_TABLES.get(directory, ()):
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
    destinations = {}
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
            if item['directory'] == 'log':
                tid = manifest['tenant_id']
            else:
                table = next(table for table, kind in FILE_TABLES.items()
                             if kind == item['directory'] and backup.execute(
                                 'SELECT 1 FROM %s WHERE id = ?' % quote_identifier(table), (item['id'],)).fetchone())
                tid = storage_file_tenant(backup, table, item['id'])
            get_storage_path(tid, item['directory'], create=True)
            destination = get_storage_path(tid, item['directory'], item['id'])
            destinations[(item['directory'], item['id'])] = destination
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
            source = os.path.join(staging_path, item['directory'], item['id'])
            destination = destinations[(item['directory'], item['id'])]
            copied_files.append(destination)
            shutil.copy2(source, destination)
            if item['directory'] == 'log':
                os.chmod(destination, 0o600)

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
    require_permission = 'can_manage_sites'
    root_tenant_only = True

    @inlineCallbacks
    def get(self, tid):
        tid = int(tid)
        if tid == 1 or tid >= DEFAULT_PROFILE_ID:
            raise errors.ForbiddenOperation
        output_path = yield deferToThreadPool(reactor, get_thread_pool(),
                                               ensure_tenant_backup_file, tid)
        yield log_tenant_backup(tid, self.session.user_id, 'export_tenant')
        with open(output_path, 'rb') as stream:
            yield self.write_file_as_download('tenant-%d.tar.gz' % tid, stream)


class TenantBackupReport(BaseHandler):
    check_roles = 'admin'
    require_permission = 'can_manage_sites'
    root_tenant_only = True

    @inlineCallbacks
    def get(self, tid):
        tid = int(tid)
        if tid == 1 or tid >= DEFAULT_PROFILE_ID:
            raise errors.ForbiddenOperation
        archive_path = yield deferToThreadPool(reactor, get_thread_pool(),
                                                ensure_tenant_backup_file, tid)
        return (yield deferToThreadPool(reactor, get_thread_pool(), read_backup_inventory, archive_path))


class TenantBackupImport(BaseHandler):
    check_roles = 'admin'
    require_permission = 'can_manage_sites'
    root_tenant_only = True
    invalidate_cache = True
    upload_handler = True
    allowed_mimetypes = ['application/gzip', 'application/x-gzip', 'application/x-tar', 'application/octet-stream']

    @inlineCallbacks
    def post(self):
        from globaleaks.db import db_refresh_tenant_cache

        if self.uploaded_file['type'] not in self.allowed_mimetypes:
            raise errors.InputValidationError('Invalid tenant backup content type')
        descriptor, archive_path = tempfile.mkstemp(prefix='tenant-upload-', suffix='.tar.gz', dir=Settings.tmp_path)
        os.close(descriptor)
        try:
            yield self.write_upload_plaintext_to_disk(archive_path)
            manifest = yield deferToThreadPool(reactor, get_thread_pool(), restore_tenant_backup, archive_path)
            yield log_tenant_backup(manifest['tenant_id'], self.session.user_id, 'import_tenant')
            yield tw(db_refresh_tenant_cache, manifest['tenant_id'])
            return {'id': manifest['tenant_id'], 'uuid': manifest['tenant_uuid']}
        finally:
            try:
                os.remove(archive_path)
            except OSError:
                pass
