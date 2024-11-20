from datetime import datetime, timedelta
import os
import sqlite3
import subprocess


from globaleaks.utils.backup import get_backups_parameter, reset_audit_log_file
from globaleaks import models
from globaleaks.orm import db_log, transact, transact_sync
from globaleaks.utils.utility import datetime_now
from globaleaks.jobs.job import LoopingJob
from globaleaks.settings import Settings
from globaleaks.utils.log import log


__all__ = ['Backup']


def run_rsync(source_path, destination_path):
    try:
        rsync_command = ["rsync", "-av", source_path, destination_path]
        subprocess.run(rsync_command, check=True)
    except Exception as e:
        db_backup_log(e)


def backup_sqlite_database_and_attachments(backup_db_path, backup_attachments_path):
    run_rsync(Settings.attachments_path, backup_attachments_path)
    source_conn = sqlite3.connect(Settings.db_file_path)
    dest_conn = sqlite3.connect(backup_db_path)
    source_conn.execute('BEGIN TRANSACTION EXCLUSIVE;')
    source_conn.backup(dest_conn)
    run_rsync(Settings.attachments_path, backup_attachments_path)
    source_conn.commit()
    source_conn.close()
    dest_conn.close()


@transact_sync
def get_last_backup_log(session):
    last_backup = session.query(models.AuditLog).filter(models.AuditLog.type == 'backup', models.AuditLog.data == 'OK') \
        .order_by(models.AuditLog.date.desc()) \
        .limit(1).one_or_none()
    return last_backup


@transact
def db_backup_log(session, exception):
    if exception:
        result = 'KO: ' + str(exception)
        db_log(session, tid=1, type='backup', user_id='system', data=result)
    else:
        db_log(session, tid=1, type='backup', user_id='system', data='OK')


@transact_sync
def wrap_get_backups_parameter(session):
    backup_params = get_backups_parameter(session)
    return (backup_params['backup_enable'], backup_params['backup_time_iso_8601'], backup_params['backup_destination_path'])


def do_backup():
    backup_enable, backup_time_iso_8601, backup_destination_path = wrap_get_backups_parameter()

    if not backup_enable or not backup_time_iso_8601 or not backup_destination_path:
        return

    try:
        backup_time_iso_8601_object = datetime.strptime(
            backup_time_iso_8601, '%H:%M').time()
        if datetime_now().time() <= backup_time_iso_8601_object:
            return
    except Exception as e:
        db_backup_log(e)
        return

    if not os.path.exists(backup_destination_path):
        os.mkdir(backup_destination_path)

    last_backup_log = get_last_backup_log()

    if not last_backup_log or last_backup_log.date + timedelta(days=1) <= datetime_now():
        try:
            backup_sqlite_database_and_attachments(os.path.join(
                                                   backup_destination_path, 'globaleaks.db'),
                                                   backup_destination_path)
        except Exception as e:
            db_backup_log(e)
            return
        finally:
            reset_audit_log_file(backup_destination_path)
            db_backup_log(None)


class Backup(LoopingJob):
    interval = 300
    monitor_interval = 600
    invalidate_cache = True

    def operation(self):
        """
        This function executes backup's operations
        """
        do_backup()
