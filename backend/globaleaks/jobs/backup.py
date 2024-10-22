from datetime import datetime, timedelta
import os
import sqlite3
import subprocess


from globaleaks.utils.backup import get_backups_parameter, reset_audit_log_file
from globaleaks import models
from globaleaks.orm import db_log, transact
from globaleaks.utils.utility import datetime_now
from globaleaks.jobs.job import LoopingJob
from globaleaks.settings import Settings
from globaleaks.utils.log import log

from twisted.internet.defer import inlineCallbacks


__all__ = ['Backup']


def run_rsync(session, source_path, destination_path):
    try:
        rsync_command = ["rsync", "-av", source_path, destination_path]
        subprocess.run(rsync_command, check=True)
    except Exception as e:
        db_backup_log(session, e)


def backup_sqlite_database_and_attachments(session, backup_db_path, backup_attachments_path):
    run_rsync(session, Settings.attachments_path, backup_attachments_path)
    source_conn = sqlite3.connect(Settings.db_file_path)
    dest_conn = sqlite3.connect(backup_db_path)
    source_conn.execute('BEGIN TRANSACTION EXCLUSIVE;')
    source_conn.backup(dest_conn)
    run_rsync(session, Settings.attachments_path, backup_attachments_path)
    source_conn.commit()
    source_conn.close()
    dest_conn.close()


def get_last_backup_log(session):
    last_backup = session.query(models.AuditLog).filter(models.AuditLog.type == 'backup', models.AuditLog.data == 'OK') \
        .order_by(models.AuditLog.date.desc()) \
        .limit(1).one_or_none()
    session.close()
    return last_backup


def db_backup_log(session, exception):
    if exception:
        result = 'KO: ' + str(exception)
        db_log(session, tid=1, type='backup', user_id='system', data=result)
    else:
        db_log(session, tid=1, type='backup', user_id='system', data='OK')


@transact
def do_backup(session):
    backup_enable, backup_time_iso_8601, backup_destination_path = get_backups_parameter(
        session)

    if not backup_enable or not backup_time_iso_8601 or not backup_destination_path:
        return

    try:
        backup_time_iso_8601_object = datetime.strptime(
            backup_time_iso_8601, '%H:%M').time()
        if datetime_now().time() <= backup_time_iso_8601_object:
            return
    except Exception as e:
        db_backup_log(session, e)
        return

    if not os.path.exists(backup_destination_path):
        os.mkdir(backup_destination_path)

    last_backup_log = get_last_backup_log(session)

    if not last_backup_log or last_backup_log.date + timedelta(days=1) <= datetime_now():
        try:
            backup_sqlite_database_and_attachments(session, os.path.join(
                                                   backup_destination_path, 'globaleaks' + datetime_now().strftime('%Y-%m-%d_%H:%M') + '.db'),
                                                   backup_destination_path)
        except Exception as e:
            db_backup_log(session, e)
            return
        finally:
            reset_audit_log_file(backup_destination_path)
            db_backup_log(session, None)


class Backup(LoopingJob):
    interval = 60
    monitor_interval = 600

    def operation(self):
        """
        This function executes backup's operations
        """
        log.info("START BACKUP JOB")
        do_backup()
        log.info("END BACKUP JOB")
