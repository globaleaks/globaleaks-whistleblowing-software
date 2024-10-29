# -*- coding: utf-8
import operator
import os

from sqlalchemy.sql.expression import distinct, func

from globaleaks.utils.backup import get_list_from_audit_log_file
from globaleaks import models
from globaleaks.handlers.base import BaseHandler
from globaleaks.orm import transact
from globaleaks.state import State


def serialize_log(log):
    return {
        'date': log.date,
        'type': log.type,
        'user_id': log.user_id,
        'object_id': log.object_id,
        'data': log.data
    }


@transact
def get_audit_log_since_last_backup(session, tid):
    if tid != 1:
        logs = list()
    else:
        logs = get_list_from_audit_log_file(session)

    return [serialize_log(log) for log in logs]


@transact
def get_audit_log(session, tid):
    logs = session.query(models.AuditLog).filter(models.AuditLog.tid == tid)

    return [serialize_log(log) for log in logs]


@transact
def get_tips(session, tid):
    tips = []

    comments_by_itip = {}
    files_by_itip = {}
    receiver_count_by_itip = {}

    # Fetch comments count
    for itip_id, count in session.query(models.InternalTip.id,
                                        func.count(distinct(models.Comment.id))) \
                                 .filter(models.Comment.internaltip_id == models.InternalTip.id,
                                         models.InternalTip.tid == tid) \
                                 .group_by(models.InternalTip.id):
        comments_by_itip[itip_id] = count

    # Fetch files count
    for itip_id, count in session.query(models.InternalTip.id,
                                        func.count(distinct(models.InternalFile.id))) \
                                 .filter(models.InternalFile.internaltip_id == models.InternalTip.id,
                                         models.InternalTip.tid == tid) \
                                 .group_by(models.InternalTip.id):
        files_by_itip[itip_id] = count

    # Fetch number of receivers who has access to each itip
    for itip_id, count in session.query(models.ReceiverTip.internaltip_id,
                                        func.count(models.ReceiverTip.id)) \
                                 .filter(models.ReceiverTip.internaltip_id == models.InternalTip.id,
                                         models.InternalTip.tid == tid) \
                                 .group_by(models.ReceiverTip.internaltip_id):
        receiver_count_by_itip[itip_id] = count

    for itip in session.query(models.InternalTip).filter(models.InternalTip.tid == tid):
        tips.append({
            'id': itip.id,
            'progressive': itip.progressive,
            'creation_date': itip.creation_date,
            'last_update': itip.update_date,
            'expiration_date': itip.expiration_date,
            'context_id': itip.context_id,
            'status': itip.status,
            'substatus': itip.substatus,
            'tor': itip.tor,
            'comments': comments_by_itip.get(itip.id, 0),
            'files': files_by_itip.get(itip.id, 0),
            'receiver_count': receiver_count_by_itip.get(itip.id, 0),
            'last_access': itip.last_access
        })

    return tips


class TipsCollection(BaseHandler):
    """
    This Handler returns the list of the tips
    """
    check_roles = 'admin'

    def get(self):
        return get_tips(self.request.tid)


class RecentEventsCollection(BaseHandler):
    """
    This handler is refreshed constantly by an admin page
    and provide real time update about the GlobaLeaks status
    """
    check_roles = 'admin'

    def get(self):
        templist = [e.serialize() for e in State.tenants[self.request.tid].EventQ]

        templist.sort(key=operator.itemgetter('creation_date'))

        return templist


class JobsTiming(BaseHandler):
    """
    This handler return the timing for the latest scheduler execution
    """
    check_roles = 'admin'

    def get(self):
        response = []

        for job in State.jobs:
            response.append({
                'name': job.name,
                'timings': job.last_executions
            })

        return response


class AuditLog(BaseHandler):
    """
    Handler that provide access to the access.log file
    """
    check_roles = 'admin'

    def get(self):
        return get_audit_log(self.request.tid)


class BackupLog(BaseHandler):
    """
    Handler that provide access to the audit log since last backup
    """
    check_roles = 'admin'

    def get(self):
        return get_audit_log_since_last_backup(self.request.tid)


class AccessLog(BaseHandler):
    """
    Handler that provide access to the access.log file
    """
    check_roles = 'admin'
    root_tenant_only = True

    def get(self):
        path = os.path.abspath(os.path.join(self.state.settings.working_path, 'log/access.log'))
        return self.write_file_as_download('access.log', path)


class DebugLog(BaseHandler):
    """
    Handler that provide access to the access.log file
    """
    check_roles = 'admin'
    root_tenant_only = True

    def get(self):
        path = os.path.abspath(os.path.join(self.state.settings.working_path, 'log/globaleaks.log'))
        return self.write_file_as_download('globaleaks.log', path)
