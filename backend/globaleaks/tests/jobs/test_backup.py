import os
import shutil
import sqlite3
import tempfile

from datetime import datetime
from unittest.mock import patch

from twisted.internet.defer import fail, inlineCallbacks, succeed
from twisted.trial import unittest

import globaleaks.jobs.backup as backup_job

from globaleaks import models
from globaleaks.jobs.backup import Backup, BackupList
from globaleaks.models import config
from globaleaks.orm import transact, tw
from globaleaks.rest import errors
from globaleaks.settings import Settings
from globaleaks.tests import helpers


class BackupJob(Backup):
    operation_called = 0

    def operation(self):
        self.operation_called += 1
        return succeed(None)


class TestBackupGrid(unittest.TestCase):
    """
    The runs are laid on a grid anchored at the hour that has been chosen and
    stepped by the period: what the next run waits for is the next free slot
    of that grid, which is not necessarily the hour of tomorrow.
    """
    def delay_at(self, hour, minute=0, backup_time="02:00", period=2):
        return backup_job.next_run(datetime(2026, 1, 1, hour, minute), backup_time, period)

    def test_the_first_run_waits_for_the_hour_of_today_when_it_is_still_to_come(self):
        self.assertEqual(self.delay_at(1), 3600)

    def test_the_first_run_lands_on_the_next_slot_of_the_grid(self):
        # 02:00 has passed and the period is two hours: the next slot is 04:00,
        # not tomorrow's 02:00
        self.assertEqual(self.delay_at(3), 3600)

    def test_a_run_falling_on_a_slot_that_is_now_is_pushed_to_the_next(self):
        self.assertEqual(self.delay_at(4), 7200)


class TestBackupSchedule(helpers.TestGL):
    """
    The backup runs on the hour it is given, as often as it is given; where it
    has been given neither, it falls back to a run a day rather than to no run
    at all.
    """
    def test_the_job_runs_on_the_configured_period(self):
        with patch.object(backup_job, 'wrap_get_backups_parameter',
                          lambda: (True, "02:00", 2, 7)):
            job = BackupJob()
            self.assertEqual(job.operation_called, 0)

            self.test_reactor.advance(job.get_delay())
            self.assertEqual(job.operation_called, 1)
            self.assertEqual(job.interval, 7200)

            self.test_reactor.advance(job.interval)
            self.assertEqual(job.operation_called, 2)

    def test_without_an_hour_and_a_period_the_job_falls_back_to_once_a_day(self):
        # Not "it does not run": it runs, once a day, on the fallback interval.
        # Nothing is lost while the site has not chosen when to back up.
        with patch.object(backup_job, 'wrap_get_backups_parameter',
                          lambda: (True, None, None, None)):
            job = BackupJob()

            self.assertEqual(job.get_delay(), 24 * 3600)
            self.assertEqual(job.interval, 24 * 3600)

            self.test_reactor.advance(3600)
            self.assertEqual(job.operation_called, 0)

    @inlineCallbacks
    def test_the_job_runs_the_backup(self):
        with patch.object(backup_job, 'wrap_get_backups_parameter',
                          lambda: (True, "02:00", 2, 7)), \
             patch.object(backup_job, 'do_backup', return_value=succeed(None)) as do_backup:
            yield Backup().operation()

        do_backup.assert_called_once()


class TestScheduledBackup(helpers.TestGL):
    """
    The scheduled run reads its parameters from the configuration of the
    platform, and records the outcome it reached in the audit log.
    """
    @inlineCallbacks
    def configure(self, enabled=True, backup_time="02:00", period=2, retention=3):
        yield tw(config.db_set_config_variable, 1, 'backup_enabled', enabled)
        yield tw(config.db_set_config_variable, 1, 'backup_time', backup_time)
        yield tw(config.db_set_config_variable, 1, 'backup_period', period)
        yield tw(config.db_set_config_variable, 1, 'backup_retention', retention)

    @transact
    def outcomes_logged(self, session):
        return [entry.data for entry in session.query(models.AuditLog)
                                               .filter(models.AuditLog.type == 'backup')]

    @inlineCallbacks
    def run_with(self, outcome):
        with patch.object(backup_job, 'backup_sqlite_database_and_files', **outcome) as run:
            yield backup_job.do_backup()

        return run

    @inlineCallbacks
    def test_the_period_is_kept_between_an_hour_and_a_day(self):
        for period, expected in [(0, 1), (2, 2), (48, 24)]:
            yield self.configure(period=period)

            self.assertEqual(backup_job.wrap_get_backups_parameter()[2], expected)

    @inlineCallbacks
    def test_a_backup_that_is_off_runs_nothing(self):
        yield self.configure(enabled=False)

        run = yield self.run_with({'return_value': succeed(None)})

        run.assert_not_called()
        self.assertEqual((yield self.outcomes_logged()), [])

    @inlineCallbacks
    def test_a_backup_that_succeeds_is_logged(self):
        yield self.configure(retention=5)

        run = yield self.run_with({'return_value': succeed(None)})

        run.assert_called_once_with(Settings.backups_path, 5)
        self.assertEqual((yield self.outcomes_logged()), ['OK'])

    @inlineCallbacks
    def test_a_backup_that_fails_is_logged_with_its_reason(self):
        yield self.configure()

        yield self.run_with({'return_value': fail(Exception('the disk is full'))})

        self.assertEqual((yield self.outcomes_logged()), ['KO: the disk is full'])


class TestTransferToRsync(unittest.TestCase):
    """
    The files are moved by rsync, told what to leave out and what to link
    against; what rsync reports as a failure is a failed transfer.
    """
    @inlineCallbacks
    def test_the_transfer_is_handed_to_rsync_with_its_options(self):
        with patch.object(backup_job, 'getProcessOutputAndValue',
                          return_value=succeed((b'', b'', 0))) as process:
            yield backup_job.launch_rsync('/source/', '/destination/',
                                          ['globaleaks.db*'], '/previous')

        executable, args = process.call_args[0][:2]
        self.assertEqual(executable, 'rsync')
        self.assertEqual(args, ['-a', '--exclude', 'globaleaks.db*',
                                '--link-dest', '/previous', '/source/', '/destination/'])
        # rsync is looked up on the PATH, which the process has to inherit
        self.assertIn('PATH', process.call_args[1]['env'])

    @inlineCallbacks
    def test_a_transfer_rsync_fails_is_a_failed_transfer(self):
        with patch.object(backup_job, 'getProcessOutputAndValue',
                          return_value=succeed((b'', b'some files vanished', 24))):
            failure = yield self.assertFailure(backup_job.launch_rsync('/source/', '/destination/'),
                                               Exception)

        self.assertIn('24', str(failure))
        self.assertIn('some files vanished', str(failure))

    def test_a_filesystem_without_fsync_does_not_stop_the_backup(self):
        with patch.object(backup_job.os, 'fsync', side_effect=OSError('not supported')):
            backup_job.fsync_path(tempfile.gettempdir())


class TestBackupRun(helpers.TestGL):
    """
    A run of the backup, with the transfer done by hand in place of rsync:
    what a generation holds, what the next one links against, and what is left
    behind when a transfer fails halfway.
    """
    @inlineCallbacks
    def setUp(self):
        yield super().setUp()

        self.backup_path = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.backup_path, True)
        self.snapshots = os.path.join(self.backup_path, 'snapshots')

        self.transfers = []

    def rsync(self, source, destination, excludes=None, link_dest=None):
        self.transfers.append((source, destination, excludes, link_dest))

        if os.path.isdir(source):
            ignored = shutil.ignore_patterns(*(exclude.strip('/') for exclude in excludes or []))
            shutil.copytree(source, destination, ignore=ignored, dirs_exist_ok=True)
        else:
            shutil.copy(source, destination)

        return succeed(None)

    def rsync_failing_on_the_database(self, source, destination, excludes=None, link_dest=None):
        if source.endswith('.db'):
            return fail(Exception('rsync exited with 23'))

        return self.rsync(source, destination, excludes, link_dest)

    @inlineCallbacks
    def backup(self, transfer=None):
        with patch.object(backup_job, 'launch_rsync', transfer or self.rsync):
            yield backup_job.backup_sqlite_database_and_files(self.backup_path, 3)

    @inlineCallbacks
    def test_a_run_publishes_a_generation_holding_a_copy_of_the_database(self):
        yield self.backup()

        generations = backup_job.list_snapshots(self.snapshots)
        self.assertEqual(len(generations), 1)

        copy = os.path.join(self.snapshots, generations[0], 'globaleaks.db')
        connection = sqlite3.connect(copy)
        try:
            self.assertEqual(connection.execute("PRAGMA integrity_check").fetchone()[0], 'ok')
        finally:
            connection.close()

        # the files went before and after the snapshot of the database, which
        # was then shipped from the staging, now empty
        self.assertEqual(len(self.transfers), 3)
        self.assertTrue(self.transfers[2][0].endswith('.db'))
        self.assertEqual(os.listdir(os.path.join(self.backup_path, 'tmp')), [])

        self.assertEqual(os.readlink(os.path.join(self.backup_path, 'latest')),
                         os.path.join('snapshots', generations[0]))

    @inlineCallbacks
    def test_a_further_run_links_against_the_previous_generation(self):
        yield self.backup()
        previous = backup_job.get_latest_snapshot(self.snapshots)

        yield self.backup()

        self.assertIsNone(self.transfers[0][3])
        self.assertEqual(self.transfers[3][3], previous)
        self.assertEqual(len(backup_job.list_snapshots(self.snapshots)), 2)

    @inlineCallbacks
    def test_a_transfer_that_fails_publishes_nothing_and_leaves_no_database_in_the_clear(self):
        yield self.assertFailure(self.backup(self.rsync_failing_on_the_database), Exception)

        self.assertEqual(backup_job.list_snapshots(self.snapshots), [])
        self.assertEqual(os.listdir(os.path.join(self.backup_path, 'tmp')), [])
        # what was half written stays until the next run sweeps it
        self.assertTrue(any(entry.endswith('.incomplete') for entry in os.listdir(self.snapshots)))

        yield self.backup()

        self.assertFalse(any(entry.endswith('.incomplete') for entry in os.listdir(self.snapshots)))
        self.assertEqual(len(backup_job.list_snapshots(self.snapshots)), 1)

    @inlineCallbacks
    def test_without_rsync_installed_the_backup_is_refused(self):
        with patch.object(backup_job.shutil, 'which', return_value=None):
            failure = yield self.assertFailure(
                backup_job.backup_sqlite_database_and_files(self.backup_path, 3), Exception)

        self.assertIn('rsync', str(failure))


class TestDatabaseSnapshot(helpers.TestGL):
    """
    The copy of the database is the part of a backup that has to be restorable:
    it is taken on the local disk, carries the data of the platform, and is
    wiped from the staging whether the run reached its end or not.
    """
    @inlineCallbacks
    def test_the_copy_of_the_database_is_a_database_that_answers(self):
        staging = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, staging, True)

        copy = os.path.join(staging, 'globaleaks.db')

        yield backup_job.backup_sqlite_database_threaded(copy)

        self.assertTrue(os.path.exists(copy))

        connection = sqlite3.connect(copy)
        try:
            # It opens, and what it holds is coherent
            self.assertEqual(connection.execute("PRAGMA integrity_check").fetchone()[0],
                             'ok')

            # and it carries the data of the platform, not an empty shell: the
            # configuration of the first site is in there and can be read back
            copied = connection.execute(
                "SELECT COUNT(*) FROM config WHERE tid = 1").fetchone()[0]
        finally:
            connection.close()

        source = sqlite3.connect(Settings.db_file_path)
        try:
            original = source.execute(
                "SELECT COUNT(*) FROM config WHERE tid = 1").fetchone()[0]
        finally:
            source.close()

        self.assertGreater(copied, 0)
        self.assertEqual(copied, original)

    def test_the_staging_is_wiped_of_whatever_is_left_in_it(self):
        # A snapshot of the database sits in the staging in the clear until it
        # is transferred: what is left behind is removed, run or no run
        staging = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, staging, True)

        leftover = os.path.join(staging, 'globaleaks.db')
        with open(leftover, 'wb') as f:
            f.write(b'a leftover snapshot')

        backup_job.cleanup_staging(staging)

        self.assertFalse(os.path.exists(leftover))


class TestSnapshots(unittest.TestCase):
    """
    A generation is published by a single rename onto a name that does not yet
    exist, so until the rename succeeds the generation published before it
    remains the latest one and a crash never destroys a good backup.
    """
    def setUp(self):
        self.backup_path = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.backup_path, True)

        self.snapshots = os.path.join(self.backup_path, 'snapshots')
        os.makedirs(self.snapshots)

    def generation(self, name):
        path = os.path.join(self.snapshots, name)
        os.makedirs(path)
        return path

    def test_only_the_complete_generations_are_published_ones(self):
        self.generation('20260101-000000-000000')
        self.generation('20260102-000000-000000')
        self.generation('20260103-000000-000000.incomplete')

        self.assertEqual(backup_job.list_snapshots(self.snapshots),
                         ['20260101-000000-000000', '20260102-000000-000000'])

        self.assertEqual(backup_job.get_latest_snapshot(self.snapshots),
                         os.path.join(self.snapshots, '20260102-000000-000000'))

    def test_the_latest_of_no_generation_is_nothing(self):
        self.assertIsNone(backup_job.get_latest_snapshot(self.snapshots))

    def test_the_generations_kept_are_the_most_recent_ones(self):
        cases = [("keeping two of four", 2, 2),
                 ("keeping more than there are", 10, 4),
                 # keep < 1 would slice nothing away and silently prune
                 # everything or nothing depending on the reading: one is kept
                 ("keeping none", 0, 1)]

        for reason, keep, expected in cases:
            shutil.rmtree(self.snapshots, ignore_errors=True)
            os.makedirs(self.snapshots)
            for day in range(1, 5):
                self.generation(f'2026010{day}-000000-000000')

            backup_job.prune_snapshots(self.snapshots, keep)

            self.assertEqual(len(backup_job.list_snapshots(self.snapshots)), expected,
                             f"{reason} leaves the wrong number of generations")

    def test_the_publication_replaces_nothing_until_it_succeeds(self):
        previous = self.generation('20260101-000000-000000')
        incomplete = self.generation('20260102-000000-000000.incomplete')
        final = os.path.join(self.snapshots, '20260102-000000-000000')

        backup_job.publish_snapshot(self.backup_path, self.snapshots,
                                    incomplete, final, keep=2)

        self.assertTrue(os.path.isdir(final))
        self.assertFalse(os.path.exists(incomplete))
        # the one that was there is still there: the publication adds, it does
        # not overwrite
        self.assertTrue(os.path.isdir(previous))

    def test_the_generations_left_half_written_are_swept_away(self):
        self.generation('20260101-000000-000000')
        self.generation('20260102-000000-000000.incomplete')

        backup_job.cleanup_incomplete_snapshots(self.snapshots)

        self.assertEqual(os.listdir(self.snapshots), ['20260101-000000-000000'])

    def test_the_inventory_reads_the_date_out_of_the_name(self):
        self.generation('20260102-030405-000000')
        self.generation('not-a-generation')

        inventory = backup_job.list_backups(self.snapshots)

        self.assertEqual([entry['id'] for entry in inventory],
                         ['20260102-030405-000000', 'not-a-generation'])
        self.assertEqual(inventory[0]['creation_date'], '2026-01-02T03:04:05')
        # a name the platform did not write says nothing about when it was made
        self.assertEqual(inventory[1]['creation_date'], '')

    def test_the_inventory_of_a_place_that_does_not_exist_is_empty(self):
        self.assertEqual(backup_job.list_backups(os.path.join(self.backup_path, 'nowhere')), [])

    def test_resetting_drops_every_generation_and_leaves_the_place_ready(self):
        self.generation('20260101-000000-000000')

        backup_job.reset_backups(self.snapshots)

        self.assertTrue(os.path.isdir(self.snapshots))
        self.assertEqual(os.listdir(self.snapshots), [])

    def test_the_pointer_to_the_latest_generation_follows_the_publication(self):
        latest = os.path.join(self.backup_path, 'latest')
        # a pointer left half-made by an earlier run is not in the way
        os.symlink('nowhere', latest + '.tmp')

        backup_job.update_latest_pointer(self.backup_path, self.generation('20260101-000000-000000'))

        self.assertEqual(os.readlink(latest), os.path.join('snapshots', '20260101-000000-000000'))
        self.assertFalse(os.path.lexists(latest + '.tmp'))

    def test_a_filesystem_without_symlinks_gets_no_pointer_and_no_failure(self):
        with patch.object(backup_job.os, 'symlink', side_effect=OSError('not supported')):
            backup_job.update_latest_pointer(self.backup_path, self.generation('20260101-000000-000000'))

        self.assertFalse(os.path.lexists(os.path.join(self.backup_path, 'latest')))


class TestSnapshotsOffTheMainThread(helpers.TestGL):
    """
    The generations are read and dropped from the thread pool, so a snapshots
    directory that lives on a slow remote mount never blocks the reactor.
    """
    def setUp(self):
        helpers.TestGL.setUp(self)

        self.snapshots = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.snapshots, True)

    @inlineCallbacks
    def test_resetting_off_the_main_thread_is_the_same_reset(self):
        os.makedirs(os.path.join(self.snapshots, '20260101-000000-000000'))

        yield backup_job.reset_backups_threaded(self.snapshots)

        self.assertEqual(os.listdir(self.snapshots), [])

    @inlineCallbacks
    def test_the_inventory_off_the_main_thread_is_the_same_inventory(self):
        os.makedirs(os.path.join(self.snapshots, '20260102-030405-000000'))

        inventory = yield backup_job.list_backups_threaded(self.snapshots)

        self.assertEqual([entry['id'] for entry in inventory], ['20260102-030405-000000'])


class TestTransfer(helpers.TestGL):
    """
    What is transferred is the working directory, and never the backup itself:
    a destination that sits inside it is excluded from its own transfer.
    """
    def test_the_backup_is_not_copied_into_itself(self):
        inside = os.path.join(Settings.working_path, 'backups')

        excludes = backup_job.get_rsync_excludes(inside)

        self.assertIn('/backups', excludes)

    def test_a_destination_outside_the_working_directory_excludes_nothing_of_its_own(self):
        outside = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, outside, True)

        excludes = backup_job.get_rsync_excludes(outside)

        self.assertEqual(excludes, list(backup_job.DB_RSYNC_EXCLUDES))

    def test_the_working_directory_is_not_a_destination(self):
        self.assertRaises(ValueError, backup_job.get_rsync_excludes,
                          Settings.working_path)


class TestBackupList(helpers.TestHandlerWithPopulatedDB):
    """
    The generations are listed to the administrators of the platform: a site
    other than the first owns no backups and is refused the inventory.
    """
    _handler = BackupList

    @inlineCallbacks
    def test_get(self):
        handler = self.request(role='admin')

        self.assertIsInstance((yield handler.get()), list)

    @inlineCallbacks
    def test_get_is_refused_to_a_site_that_is_not_the_first(self):
        handler = self.request(role='admin', tid=2)

        yield self.assertFailure(handler.get(), errors.ForbiddenOperation)
