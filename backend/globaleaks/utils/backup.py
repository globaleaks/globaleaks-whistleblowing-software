
import json
import os

from globaleaks.models.config import ConfigFactory
from globaleaks.utils.utility import iso8601_to_datetime
from globaleaks import models
from globaleaks.utils.log import log


def get_backups_parameter(session):
    config = ConfigFactory(session, 1)
    backup_enable = config.get_val('backup_enable')
    backup_time_iso_8601 = config.get_val('backup_time_ISO_8601')
    backup_destination_path = config.get_val('backup_destination_path')

    return {
        'backup_enable': backup_enable,
        'backup_time_iso_8601': backup_time_iso_8601,
        'backup_destination_path': backup_destination_path
    }


def get_audit_log_file_path(backup_destination_path):
    return os.path.join(backup_destination_path, 'audit.log')


def write_audit_log_on_file(session, row):
    backup_params = get_backups_parameter(
        session)
    backup_enable = backup_params['backup_enable']
    backup_time_iso_8601 = backup_params['backup_time_iso_8601']
    backup_destination_path = backup_params['backup_destination_path']

    if not backup_enable or not backup_time_iso_8601 or not backup_destination_path:
        return

    audit_log_path = get_audit_log_file_path(backup_destination_path)
    if not os.path.exists(audit_log_path):
        reset_audit_log_file(backup_destination_path)

    with open(audit_log_path, 'a') as outfile:
        outfile.write(json.dumps((audit_log_to_dict(row))) + '\n')


def audit_log_to_dict(row):
    audit_log = dict()
    audit_log['id'] = row.id
    audit_log['tid'] = row.tid
    audit_log['date'] = row.date.isoformat()
    audit_log['type'] = row.type
    audit_log['user_id'] = row.user_id
    audit_log['object_id'] = row.object_id
    audit_log['data'] = row.data
    return audit_log


def dict_to_audit_log(audit_log_dict):
    audit_log = models.AuditLog()
    audit_log.date = iso8601_to_datetime(audit_log_dict['date'])
    audit_log.type = audit_log_dict['type']
    audit_log.user_id = audit_log_dict['user_id']
    audit_log.object_id = audit_log_dict['object_id']
    audit_log.data = audit_log_dict['data']
    return audit_log


def get_list_from_audit_log_file(session):
    backup_params = get_backups_parameter(
        session)
    backup_enable = backup_params['backup_enable']
    backup_time_iso_8601 = backup_params['backup_time_iso_8601']
    backup_destination_path = backup_params['backup_destination_path']

    if not backup_enable or not backup_time_iso_8601 or not backup_destination_path:
        return

    audit_log_path = get_audit_log_file_path(backup_destination_path)
    audit_log_list = list()

    with open(audit_log_path, 'r') as file:
        for line in file:
            audit_log_list.append(dict_to_audit_log(json.loads(line)))

    return audit_log_list


def reset_audit_log_file(backup_destination_path):
    audit_log_path = get_audit_log_file_path(backup_destination_path)

    if not os.path.exists(backup_destination_path):
        os.mkdir(backup_destination_path)

    with open(audit_log_path, 'w') as outfile:
        outfile.write('')
