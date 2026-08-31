import os
import shutil
import sqlite3
import tempfile

from unittest.mock import patch

from twisted.internet.defer import inlineCallbacks, succeed

import globaleaks.jobs.backup as backup_job

from globaleaks.jobs.backup import Backup, BackupList
from globaleaks.rest import errors
from globaleaks.settings import Settings
from globaleaks.tests import helpers


class BackupJob(Backup):
    operation_called = 0

    def operation(self):
        self.operation_called += 1
        return succeed(None)


class TestBackupSchedule(helpers.TestGL):
    """
    The backup runs on the hour it is given, as often as it is given; where it
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


class TestDatabaseSnapshot(helpers.TestGL):
    """
    The copy of the database is the part of a backup that has to be restorable:
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


class TestSnapshots(helpers.TestGL):
    """
    A generation is published by a single rename onto a name that does not yet
    """
    def setUp(self):
        helpers.TestGL.setUp(self)

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
                self.generation('2026010%d-000000-000000' % day)

            backup_job.prune_snapshots(self.snapshots, keep)

            self.assertEqual(len(backup_job.list_snapshots(self.snapshots)), expected,
                             "%s leaves the wrong number of generations" % reason)

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


class TestTransfer(helpers.TestGL):
    """
    What is transferred is the working directory, and never the backup itself:
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
        self.assertRaises(Exception, backup_job.get_rsync_excludes,
                          Settings.working_path)


class TestBackupList(helpers.TestHandlerWithPopulatedDB):
    """
    The generations are listed to the administrators of the platform: a site
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
