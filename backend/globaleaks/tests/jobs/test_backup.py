import os
import shutil
import tempfile
from unittest.mock import patch

from twisted.internet.defer import inlineCallbacks, fail, succeed

import globaleaks.jobs.backup as backup_job
from globaleaks.jobs.backup import Backup, do_backup
from globaleaks.rest import errors
from globaleaks.settings import Settings
from globaleaks.state import State
from globaleaks.tests import helpers

class BackupJob(Backup):
    operation_called = 0

    def operation(self):
        self.operation_called += 1
        return succeed(None)

class TestBackupJob(helpers.TestGL):
    def test_run_with_params(self):
        def mock_params():
            return (True, "02:00", 2, 7)

        with patch.object(backup_job, 'wrap_get_backups_parameter', mock_params):
            job = BackupJob()
            self.assertEqual(job.operation_called, 0)

            self.test_reactor.advance(job.get_delay())
            self.assertEqual(job.operation_called, 1)
            self.assertEqual(job.interval, 7200)

            self.test_reactor.advance(job.interval)
            self.assertEqual(job.operation_called, 2)

    def test_no_run_without_params(self):
        def mock_params():
            return (True, None, None, None)

        with patch.object(backup_job, 'wrap_get_backups_parameter', mock_params):
            job = BackupJob()
            self.assertEqual(job.operation_called, 0)

            self.test_reactor.advance(3600)
            self.assertEqual(job.operation_called, 0)

    @inlineCallbacks
    def test_backup_files_flow(self):
        calls = []
        backup_path = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, backup_path, ignore_errors=True)

        def launch_rsync(source, destination, excludes=None, link_dest=None):
            calls.append(('rsync', source, destination, excludes, link_dest))
            return succeed(None)

        def backup_sqlite_database_threaded(path):
            calls.append(('sqlite', path))
            return succeed(None)

        def remove_staging_database_threaded(path):
            calls.append(('remove', path))
            return succeed(None)

        def publish_snapshot_threaded(bp, snapshots_path, incomplete_path, final_path, keep):
            calls.append(('publish', incomplete_path, final_path, keep))
            return succeed(None)

        with patch.object(backup_job, 'launch_rsync', launch_rsync), \
             patch.object(backup_job, 'backup_sqlite_database_threaded', backup_sqlite_database_threaded), \
             patch.object(backup_job, 'remove_staging_database_threaded', remove_staging_database_threaded), \
             patch.object(backup_job, 'publish_snapshot_threaded', publish_snapshot_threaded):
            yield backup_job.backup_sqlite_database_and_files(backup_path, 5)

        source_path = os.path.join(Settings.working_path, '')
        snapshots_path = os.path.join(backup_path, 'snapshots')

        # two file passes around a local database snapshot, the snapshot shipped
        # into the generation, the local copy wiped, then publish
        self.assertEqual([c[0] for c in calls],
                         ['rsync', 'sqlite', 'rsync', 'rsync', 'remove', 'publish'])

        rsync1, sqlite_call, rsync2, rsync_db, remove, publish = calls
        incomplete_path = publish[1]
        name = os.path.basename(incomplete_path)[:-len('.incomplete')]
        staging_db = os.path.join(backup_path, 'tmp', name + '.db')

        # both file passes target the same generation dir, from the working dir
        self.assertEqual(rsync1[1], source_path)
        self.assertEqual(rsync1[2], rsync2[2])
        self.assertEqual(rsync1[2], os.path.join(incomplete_path, ''))
        self.assertEqual(rsync1[3], backup_job.DB_RSYNC_EXCLUDES)

        # the database is snapshotted onto local staging, not over the network
        self.assertEqual(sqlite_call[1], staging_db)

        # the local snapshot is shipped into the generation as globaleaks.db,
        # with no excludes/link-dest, then securely removed
        self.assertEqual(rsync_db[1], staging_db)
        self.assertEqual(rsync_db[2], os.path.join(incomplete_path, 'globaleaks.db'))
        self.assertIsNone(rsync_db[3])
        self.assertIsNone(rsync_db[4])
        self.assertEqual(remove[1], staging_db)

        # staging lives under snapshots/ and is published via atomic rename
        self.assertTrue(incomplete_path.endswith('.incomplete'))
        self.assertEqual(os.path.dirname(incomplete_path), snapshots_path)
        self.assertEqual(publish[2], incomplete_path[:-len('.incomplete')])
        # the retention count is propagated through to the publish step
        self.assertEqual(publish[3], 5)

    @inlineCallbacks
    def test_backup_wipes_local_staging_even_on_failure(self):
        backup_path = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, backup_path, ignore_errors=True)

        removed = []

        def launch_rsync(source, destination, excludes=None, link_dest=None):
            # fail on the database transfer (source is the staging .db)
            if source.endswith('.db'):
                return fail(Exception("transfer boom"))
            return succeed(None)

        def remove_staging_database_threaded(path):
            removed.append(path)
            return succeed(None)

        with patch.object(backup_job, 'launch_rsync', launch_rsync), \
             patch.object(backup_job, 'backup_sqlite_database_threaded', lambda p: succeed(None)), \
             patch.object(backup_job, 'remove_staging_database_threaded', remove_staging_database_threaded), \
             patch.object(backup_job, 'publish_snapshot_threaded', lambda *a: succeed(None)):
            yield self.assertFailure(backup_job.backup_sqlite_database_and_files(backup_path, 5), Exception)

        # the local plaintext snapshot is wiped despite the failure
        self.assertEqual(len(removed), 1)
        self.assertEqual(os.path.dirname(removed[0]), os.path.join(backup_path, 'tmp'))
        self.assertTrue(removed[0].endswith('.db'))

    def test_cleanup_staging_securely_removes_leftovers(self):
        tmp_path = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, tmp_path, ignore_errors=True)
        with open(os.path.join(tmp_path, '20260101-000000-000000.db'), 'wb') as f:
            f.write(b'leftover plaintext database')

        backup_job.cleanup_staging(tmp_path)

        self.assertEqual(os.listdir(tmp_path), [])

    def test_publish_snapshot_is_atomic(self):
        backup_path = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, backup_path, ignore_errors=True)
        snapshots_path = os.path.join(backup_path, 'snapshots')
        incomplete_path = os.path.join(snapshots_path, '20260101-000000-000000.incomplete')
        final_path = os.path.join(snapshots_path, '20260101-000000-000000')
        os.makedirs(incomplete_path)
        open(os.path.join(incomplete_path, 'globaleaks.db'), 'w').close()

        backup_job.publish_snapshot(backup_path, snapshots_path, incomplete_path, final_path, 7)

        # the staging dir has been renamed in place to the final generation
        self.assertFalse(os.path.exists(incomplete_path))
        self.assertTrue(os.path.isdir(final_path))
        self.assertTrue(os.path.isfile(os.path.join(final_path, 'globaleaks.db')))
        # the latest generation is resolved by name, no symlink required
        self.assertEqual(backup_job.get_latest_snapshot(snapshots_path), final_path)

    def test_get_latest_snapshot_ignores_incomplete(self):
        snapshots_path = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, snapshots_path, ignore_errors=True)
        os.makedirs(os.path.join(snapshots_path, '20260101-000000-000000'))
        os.makedirs(os.path.join(snapshots_path, '20260102-000000-000000'))
        os.makedirs(os.path.join(snapshots_path, '20260103-000000-000000.incomplete'))

        self.assertEqual(backup_job.get_latest_snapshot(snapshots_path),
                         os.path.join(snapshots_path, '20260102-000000-000000'))

    def test_prune_snapshots_keeps_latest_generations(self):
        snapshots_path = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, snapshots_path, ignore_errors=True)
        names = ['2026010%d-000000-000000' % i for i in range(1, 9)]
        for name in names:
            os.makedirs(os.path.join(snapshots_path, name))

        backup_job.prune_snapshots(snapshots_path, 7)

        self.assertEqual(sorted(os.listdir(snapshots_path)), names[1:])

    def test_prune_snapshots_always_keeps_at_least_one(self):
        snapshots_path = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, snapshots_path, ignore_errors=True)
        names = ['2026010%d-000000-000000' % i for i in range(1, 4)]
        for name in names:
            os.makedirs(os.path.join(snapshots_path, name))

        # keep < 1 must not wipe every generation (snapshots[:-0] == snapshots[:0])
        backup_job.prune_snapshots(snapshots_path, 0)

        self.assertEqual(sorted(os.listdir(snapshots_path)), names[-1:])

    def test_get_rsync_excludes_excludes_internal_backup_dir(self):
        inside = os.path.join(Settings.working_path, 'backup')
        excludes = backup_job.get_rsync_excludes(inside)
        self.assertIn('/backup', excludes)
        for pattern in backup_job.DB_RSYNC_EXCLUDES:
            self.assertIn(pattern, excludes)

    def test_get_rsync_excludes_external_path(self):
        outside = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, outside, ignore_errors=True)
        self.assertEqual(backup_job.get_rsync_excludes(outside), backup_job.DB_RSYNC_EXCLUDES)

    def test_get_rsync_excludes_rejects_working_dir(self):
        self.assertRaises(Exception, backup_job.get_rsync_excludes, Settings.working_path)

    @inlineCallbacks
    def test_do_backup_logs_failure_once(self):
        errors = []

        def wrap_get_backups_parameter():
            return succeed((True, "02:00", 1, 7))

        def backup_sqlite_database_and_files(*args):
            return fail(Exception("boom"))

        def db_backup_log(exception):
            errors.append(exception)
            return succeed(None)

        with patch.object(backup_job, 'wrap_get_backups_parameter', wrap_get_backups_parameter), \
             patch.object(backup_job.os, 'makedirs'), \
             patch.object(backup_job, 'backup_sqlite_database_and_files', backup_sqlite_database_and_files), \
             patch.object(backup_job, 'db_backup_log', db_backup_log):
            yield do_backup()

        self.assertEqual(len(errors), 1)
        self.assertEqual(str(errors[0]), "boom")

    def test_list_backups_parses_names_and_skips_incomplete(self):
        snapshots_path = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, snapshots_path, ignore_errors=True)
        os.makedirs(os.path.join(snapshots_path, '20260101-000000-000000'))
        os.makedirs(os.path.join(snapshots_path, '20260102-030405-000000'))
        os.makedirs(os.path.join(snapshots_path, '20260103-000000-000000.incomplete'))

        backups = backup_job.list_backups(snapshots_path)

        # oldest-first, incomplete generations excluded, timestamp derived from name
        self.assertEqual([b['id'] for b in backups],
                         ['20260101-000000-000000', '20260102-030405-000000'])
        self.assertEqual(backups[1]['creation_date'], '2026-01-02T03:04:05')

    def test_list_backups_missing_dir_returns_empty(self):
        missing = os.path.join(tempfile.mkdtemp(), 'snapshots')
        self.addCleanup(shutil.rmtree, os.path.dirname(missing), ignore_errors=True)
        self.assertEqual(backup_job.list_backups(missing), [])


class TestBackupList(helpers.TestHandler):
    _handler = backup_job.BackupList

    @inlineCallbacks
    def test_get_lists_published_generations(self):
        snapshots_path = os.path.join(Settings.backups_path, 'snapshots')
        os.makedirs(snapshots_path, exist_ok=True)
        self.addCleanup(shutil.rmtree, Settings.backups_path, ignore_errors=True)
        os.makedirs(os.path.join(snapshots_path, '20260101-000000-000000'))
        os.makedirs(os.path.join(snapshots_path, '20260102-000000-000000.incomplete'))

        handler = self.request(role='admin')
        response = yield handler.get()

        self.assertEqual([b['id'] for b in response], ['20260101-000000-000000'])

    @inlineCallbacks
    def test_get_forbidden_on_non_root_tenant(self):
        # The connection policy is evaluated before the root-tenant requirement
        # and needs the tenant to be present in the runtime state
        self.state.tenants[2] = self.state.tenants[1]

        handler = self.request(role='admin', tid=2)
        yield self.assertFailure(handler.get(), errors.ForbiddenOperation)
