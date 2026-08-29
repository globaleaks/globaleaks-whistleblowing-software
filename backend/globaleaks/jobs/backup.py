from datetime import datetime, timedelta
import contextlib
import fnmatch
import os
import sqlite3
import shutil
import stat

from globaleaks.handlers.base import BaseHandler
from globaleaks.models.config import ConfigFactory
from globaleaks.orm import db_log, get_thread_pool, transact, transact_sync
from globaleaks.jobs.job import PeriodJob
from globaleaks.rest import errors
from globaleaks.settings import Settings
from globaleaks.utils.fs import srm
from globaleaks.utils.log import log
from twisted.internet import reactor, defer
from twisted.internet.defer import inlineCallbacks, returnValue
from twisted.internet.threads import deferToThreadPool

__all__ = ['Backup']

DB_EXCLUDES = ['globaleaks.db*']
SECONDS_IN_HOUR = 60 * 60


def is_excluded(path, patterns):
    """
    Whether a path, relative to the root of the copy, is left out.

    The two shapes of pattern in use carry the meaning rsync gave them, because
    that is what the callers were written against: a pattern that begins with a
    slash is anchored at the root of the copy, one that does not matches the
    name of any entry along the way.
    """
    name = os.path.basename(path)

    for pattern in patterns or []:
        if pattern.startswith('/'):
            anchored = pattern[1:]
            if path == anchored or path.startswith(anchored + os.sep):
                return True
        elif fnmatch.fnmatch(name, pattern):
            return True

    return False


NANOSECONDS_IN_SECOND = 1000000000


def is_unchanged(source, other):
    """
    The quick check: an entry of the same kind, size and modification time is
    taken for unchanged. Comparing the contents would mean reading every file of
    every generation, which is the very cost the hard links exist to avoid.

    Times are compared to the second, and to the fraction of a second only when
    both sides carry one. A destination that keeps times more coarsely than the
    source - FAT rounds them to two seconds, some network mounts to one - would
    otherwise make every entry look changed, and every generation a full copy
    with no hard link in it. Where the fraction is there on both sides it is
    worth using: two writes landing in the same second, on a file that keeps its
    size, would otherwise pass for one.
    """
    try:
        a = os.lstat(source)
        b = os.lstat(other)
    except OSError:
        return False

    if stat.S_IFMT(a.st_mode) != stat.S_IFMT(b.st_mode) or a.st_size != b.st_size:
        return False

    if a.st_mtime_ns // NANOSECONDS_IN_SECOND != b.st_mtime_ns // NANOSECONDS_IN_SECOND:
        return False

    fraction_a = a.st_mtime_ns % NANOSECONDS_IN_SECOND
    fraction_b = b.st_mtime_ns % NANOSECONDS_IN_SECOND

    if fraction_a and fraction_b:
        return fraction_a == fraction_b

    return True


def copy_entry(source, destination, previous=None):
    """
    One entry into its place, linking it against the previous generation when it
    has not changed.

    The destination may already hold the entry: the copy runs twice over the
    same generation (see backup_sqlite_database_and_files), and a second pass
    must leave alone what the first one already put there.
    """
    if os.path.islink(source):
        target = os.readlink(source)
        if os.path.islink(destination) and os.readlink(destination) == target:
            return

        if os.path.lexists(destination):
            os.remove(destination)

        os.symlink(target, destination)
        return

    if os.path.lexists(destination):
        if is_unchanged(source, destination):
            return

        os.remove(destination)

    if previous is not None and is_unchanged(source, previous):
        try:
            os.link(previous, destination)
            return
        except OSError:
            # Where the filesystem has no hard links the entry is copied
            # instead: the generation costs its own space and stays correct.
            pass

    shutil.copy2(source, destination)


def copy_tree(source, destination, excludes=None, link_dest=None):
    """
    The contents of source into destination, leaving out what is excluded and
    linking against link_dest whatever has not changed since that generation.

    A source that is not a directory is a single entry, copied to the
    destination as it is: that is how the snapshot of the database is shipped
    into the generation.
    """
    if not os.path.isdir(source):
        copy_entry(source, destination)
        return

    directories = []

    for root, dirs, files in os.walk(source):
        relative_root = os.path.relpath(root, source)
        relative_root = '' if relative_root == '.' else relative_root

        # A directory that is a symbolic link is copied as the link it is, and
        # not descended into: os.walk would otherwise list it as a directory.
        linked = [d for d in dirs if os.path.islink(os.path.join(root, d))]
        dirs[:] = [d for d in dirs
                   if d not in linked and not is_excluded(os.path.join(relative_root, d), excludes)]

        target_root = os.path.join(destination, relative_root)
        os.makedirs(target_root, exist_ok=True)
        directories.append((root, target_root))

        for name in files + linked:
            relative = os.path.join(relative_root, name)
            if is_excluded(relative, excludes):
                continue

            previous = os.path.join(link_dest, relative) if link_dest else None

            try:
                copy_entry(os.path.join(root, name), os.path.join(target_root, name), previous)
            except FileNotFoundError:
                # The application keeps writing while the copy runs: an entry
                # that goes away between the listing and the copy is skipped,
                # which is what rsync reports as files having vanished.
                continue

    # The times of a directory are settled once its contents are in place:
    # writing into a directory bumps the modification time of the directory
    # itself, so the deepest are settled first.
    for source_dir, target_dir in reversed(directories):
        with contextlib.suppress(OSError):
            shutil.copystat(source_dir, target_dir)


def copy_files(source, destination, excludes=None, link_dest=None):
    # The copy runs in a thread: it is a long walk over the filesystem, and the
    # reactor thread has an application to serve in the meanwhile.
    return deferToThreadPool(reactor, get_thread_pool(), copy_tree,
                             source, destination, excludes, link_dest)


def fsync_path(path):
    # Best-effort: several remote filesystems (CIFS, sshfs, some NFS setups)
    # do not support fsync on directories and may raise. Durability is a bonus
    # here; correctness relies on the atomic rename ordering, not on fsync.
    try:
        fd = os.open(path, os.O_RDONLY)
        try:
            os.fsync(fd)
        finally:
            os.close(fd)
    except OSError as e:
        log.debug("fsync not available on %s: %s", path, e)


def backup_sqlite_database(backup_db_path):
    # The snapshot is taken onto local disk (backup_db_path lives under
    # backups/tmp, which is always on the local working volume). pages=-1 copies
    # the whole database in a single step: against a fast local target the source
    # read lock is held only briefly, and a single step cannot be starved by the
    # restart-on-external-write behaviour of the incremental backup API.
    source_conn = sqlite3.connect(Settings.db_file_path)
    dest_conn = sqlite3.connect(backup_db_path)

    try:
        source_conn.backup(dest_conn, pages=-1)
    finally:
        source_conn.close()
        dest_conn.close()


def backup_sqlite_database_threaded(backup_db_path):
    return deferToThreadPool(reactor, get_thread_pool(), backup_sqlite_database, backup_db_path)


def cleanup_staging(tmp_path):
    # Securely wipe leftover database snapshots in the local staging directory.
    # A staging file is a full plaintext copy of the database, so a crash between
    # the snapshot and its removal must not leave it readable on disk.
    for entry in os.listdir(tmp_path):
        srm(os.path.join(tmp_path, entry))


def remove_staging_database_threaded(staging_db):
    return deferToThreadPool(reactor, get_thread_pool(), srm, staging_db)


def get_excludes(backup_path):
    # The backup directory is expected to live inside the working directory
    # (the AppArmor profile confines the backend's writes there). Exclude it
    # from the transfer, anchored to the working dir root, so it is never
    # copied into itself.
    excludes = list(DB_EXCLUDES)

    working_path = os.path.realpath(Settings.working_path)
    target_path = os.path.realpath(backup_path)

    if target_path == working_path:
        raise Exception("backup_path must not be the working directory itself")

    if target_path.startswith(working_path + os.sep):
        excludes.append('/' + os.path.relpath(target_path, working_path))

    return excludes


def list_snapshots(snapshots_path):
    # Published generations sorted oldest-first: complete directories only,
    # named with zero-padded timestamps so lexical order is chronological.
    return sorted(entry for entry in os.listdir(snapshots_path)
                  if not entry.endswith('.incomplete')
                  and os.path.isdir(os.path.join(snapshots_path, entry)))


def get_latest_snapshot(snapshots_path):
    # The most recently published generation is simply the highest-named
    # complete directory. This avoids relying on a symlink, which some remote
    # filesystems do not support.
    snapshots = list_snapshots(snapshots_path)
    if snapshots:
        return os.path.join(snapshots_path, snapshots[-1])
    return None


def list_backups(snapshots_path):
    # Read-only inventory of the published generations. The generation name
    # already encodes its creation timestamp (see the '%Y%m%d-%H%M%S-%f' naming
    # in backup_sqlite_database_and_files), so the listing is derived purely from
    # the directory names and needs no extra stat() calls against the (possibly
    # remote) snapshots filesystem.
    if not os.path.isdir(snapshots_path):
        return []

    backups = []
    for name in list_snapshots(snapshots_path):
        try:
            creation_date = datetime.strptime(name, '%Y%m%d-%H%M%S-%f').isoformat()
        except ValueError:
            creation_date = ''
        backups.append({'id': name, 'creation_date': creation_date})

    return backups


def list_backups_threaded(snapshots_path):
    return deferToThreadPool(reactor, get_thread_pool(), list_backups, snapshots_path)


def reset_backups(snapshots_path):
    # Drop every published generation. The snapshots directory is recreated empty
    # so the next scheduled run starts a fresh chain (no link-dest to inherit).
    if os.path.isdir(snapshots_path):
        shutil.rmtree(snapshots_path, ignore_errors=True)
        os.makedirs(snapshots_path, exist_ok=True)


def reset_backups_threaded(snapshots_path):
    return deferToThreadPool(reactor, get_thread_pool(), reset_backups, snapshots_path)


def update_latest_pointer(backup_path, final_path):
    # Convenience only: a 'latest' symlink to the newest generation. Best-effort
    # because symlinks are not available on every filesystem; correctness does
    # not depend on it (see get_latest_snapshot).
    latest = os.path.join(backup_path, 'latest')
    latest_tmp = os.path.join(backup_path, 'latest.tmp')
    target = os.path.join('snapshots', os.path.basename(final_path))

    try:
        if os.path.lexists(latest_tmp):
            os.remove(latest_tmp)
        os.symlink(target, latest_tmp)
        os.replace(latest_tmp, latest)
    except OSError as e:
        log.debug("Could not update 'latest' pointer on %s: %s", backup_path, e)


def cleanup_incomplete_snapshots(snapshots_path):
    for entry in os.listdir(snapshots_path):
        if entry.endswith('.incomplete'):
            shutil.rmtree(os.path.join(snapshots_path, entry), ignore_errors=True)


def prune_snapshots(snapshots_path, keep):
    # Always retain at least one generation: keep < 1 would make snapshots[:-keep]
    # evaluate to snapshots[:0] (an empty slice) and silently prune nothing.
    keep = max(1, keep)
    snapshots = list_snapshots(snapshots_path)
    for entry in snapshots[:-keep]:
        shutil.rmtree(os.path.join(snapshots_path, entry), ignore_errors=True)


def publish_snapshot(backup_path, snapshots_path, incomplete_path, final_path, keep):
    # Publish the fully built snapshot with a single rename to a brand new name.
    # This is the only operation correctness depends on: renaming to a name that
    # does not yet exist is atomic and supported on every filesystem (including
    # remote NFS/CIFS mounts), and stays within one directory so it never
    # crosses a device boundary. Until it succeeds the previous generation
    # remains the latest one, so a crash never destroys a good backup.
    fsync_path(incomplete_path)
    os.rename(incomplete_path, final_path)
    fsync_path(snapshots_path)

    update_latest_pointer(backup_path, final_path)

    prune_snapshots(snapshots_path, keep)


def publish_snapshot_threaded(backup_path, snapshots_path, incomplete_path, final_path, keep):
    return deferToThreadPool(reactor, get_thread_pool(), publish_snapshot,
                             backup_path, snapshots_path, incomplete_path, final_path, keep)


@defer.inlineCallbacks
def backup_sqlite_database_and_files(backup_path, backup_retention):
    source_path = os.path.join(Settings.working_path, '')
    excludes = get_excludes(backup_path)

    # backups/ and thus backups/tmp/ always live on the local working volume;
    # snapshots/ may instead be a remote mount. The database snapshot is taken
    # on local disk (tmp/) and only then transferred into the snapshot like any
    # other file, so the SQLite read lock is never held over the network.
    # tmp/ and snapshots/ are created at startup by State.create_directories();
    # makedirs with exist_ok=True is kept as a safety net (e.g. tests invoking
    # this directly with a custom backup_path, or a backups/ tree removed at
    # runtime).
    tmp_path = os.path.join(backup_path, 'tmp')
    snapshots_path = os.path.join(backup_path, 'snapshots')
    os.makedirs(tmp_path, exist_ok=True)
    os.makedirs(snapshots_path, exist_ok=True)
    cleanup_staging(tmp_path)
    cleanup_incomplete_snapshots(snapshots_path)

    # Hardlink unchanged files against the previous snapshot: each generation
    # is a full, independent tree on disk but only changed files cost space.
    # Where the target filesystem has no hardlink support the copy falls back
    # to a copy of its own, so this stays a pure optimization.
    link_dest = get_latest_snapshot(snapshots_path)

    name = datetime.now().strftime('%Y%m%d-%H%M%S-%f')
    incomplete_path = os.path.join(snapshots_path, name + '.incomplete')
    final_path = os.path.join(snapshots_path, name)
    os.makedirs(incomplete_path)

    destination_path = os.path.join(incomplete_path, '')
    staging_db = os.path.join(tmp_path, name + '.db')

    # Files are copied before the database snapshot and again afterwards: any
    # row present in the snapshot is guaranteed to find its file on disk, while
    # the second pass captures files written during the snapshot. The local
    # staging copy is then shipped into the snapshot (no lock held) and securely
    # removed even if any step fails.
    try:
        yield copy_files(source_path, destination_path, excludes, link_dest)
        yield backup_sqlite_database_threaded(staging_db)
        yield copy_files(source_path, destination_path, excludes, link_dest)
        yield copy_files(staging_db, os.path.join(incomplete_path, 'globaleaks.db'))
    finally:
        yield remove_staging_database_threaded(staging_db)

    yield publish_snapshot_threaded(backup_path, snapshots_path, incomplete_path, final_path, backup_retention)

@transact
def db_backup_log(session, exception):
    if exception:
        result = f'KO: {exception}'
        db_log(session, tid=1, type='backup', user_id='system', data=result)
    else:
        db_log(session, tid=1, type='backup', user_id='system', data='OK')

@transact_sync
def wrap_get_backups_parameter(session):
    config = ConfigFactory(session, 1)
    return (
        config.get_val('backup_enabled'),
        config.get_val('backup_time'),
        min(24, max(1, config.get_val('backup_period'))),
        config.get_val('backup_retention')
    )

@defer.inlineCallbacks
def do_backup():
    backup_enabled, backup_time, backup_period, backup_retention = yield wrap_get_backups_parameter()

    if not backup_enabled or not backup_time or not backup_period:
        return

    # The backup destination is not configurable: it is always the 'backups'
    # directory inside the working path, where the AppArmor profile confines
    # the backend's writes.
    backup_path = Settings.backups_path

    try:
        os.makedirs(backup_path, exist_ok=True)
        yield backup_sqlite_database_and_files(backup_path, backup_retention)
    except Exception as e:
        log.err("Backup failed: %s", e)
        yield db_backup_log(e)
        return

    yield db_backup_log(None)


class BackupList(BaseHandler):
    check_roles = 'admin'

    @inlineCallbacks
    def get(self):
        # Backup is a global (tenant 1) feature: the backups directory is owned
        # by the root tenant only, so its inventory is exposed there only. The
        # listing is read-only and never touches the live data or the snapshots.
        if self.request.tid != 1:
            raise errors.ForbiddenOperation

        snapshots_path = Settings.backups_snapshots_path
        backups = yield list_backups_threaded(snapshots_path)
        returnValue(backups)


def next_run(now, backup_time, backup_period):
    # Backups run on a grid anchored at backup_time and stepped by the period:
    # with backup_period < 24h the first run lands on the next grid slot rather
    # than waiting for tomorrow's backup_time. Aligning here and looping at the
    # same interval keeps every subsequent run on the grid.
    period_s = backup_period * SECONDS_IN_HOUR

    backup_dt = datetime.strptime(backup_time, "%H:%M")
    anchor = now.replace(hour=backup_dt.hour, minute=backup_dt.minute, second=0, microsecond=0)

    if now <= anchor:
        nxt = anchor
    else:
        steps = -(-int((now - anchor).total_seconds()) // period_s)
        nxt = anchor + timedelta(seconds=steps * period_s)
        if nxt <= now:
            nxt += timedelta(seconds=period_s)

    return int((nxt - now).total_seconds())


class Backup(PeriodJob):
    interval = 24 * SECONDS_IN_HOUR

    def get_delay(self):
        _, backup_time, backup_period, _ = wrap_get_backups_parameter()
        if not backup_time or not backup_period:
            self.interval = Backup.interval
            return 24 * SECONDS_IN_HOUR

        self.interval = backup_period * SECONDS_IN_HOUR

        return next_run(datetime.now(), backup_time, backup_period)

    def operation(self):
        return do_backup()
