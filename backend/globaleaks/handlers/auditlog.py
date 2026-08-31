"""
The audit log of the platform.

The implementation lives here once and is exported by the areas entitled to
read it: the administrator, on its own administrative area, and the auditor,
the role the analysis defines for the oversight of the platform. The handlers
below carry no role: whoever exports them declares the one it serves.
"""
import os

from sqlalchemy import or_
from sqlalchemy.sql.expression import distinct, func

from globaleaks import models
from globaleaks.handlers.base import BaseHandler
from globaleaks.orm import transact
from globaleaks.state import State
from globaleaks.utils.crypto import GCE


def serialize_log(log, username=''):
    return {
        'date': log.date,
        'type': log.type,
        'user_id': log.user_id,
        'username': username,
        'object_id': log.object_id,
        'data': log.data
    }


def decrypt_log_hashes(user_key, tip_prv_key, logs):
    """
    Reveal the fingerprints the entries carry of what has been deleted.

    :param user_key: The key of the user reading the log
    :param tip_prv_key: The key of the report, wrapped for that user
    :param logs: The serialized entries
    """
    from globaleaks.handlers.whistleblower.submission import decrypt_hashes

    tip_key = GCE.asymmetric_decrypt(user_key, tip_prv_key)

    for entry in logs:
        if entry['data']:
            decrypt_hashes(tip_key, entry['data'])


@transact
def get_audit_log(session, tid):
    # The auditor reaches no other API: who acted is named by the entries
    # themselves, falling back on the identifier when the user is gone
    usernames = dict(session.query(models.User.id, models.User.username)
                            .filter(models.User.tid == tid))

    logs = session.query(models.AuditLog) \
                  .filter(models.AuditLog.tid == tid) \
                  .order_by(models.AuditLog.date.desc())

    return [serialize_log(log, usernames.get(log.user_id, log.user_id or '')) for log in logs]


def db_get_report_audit_log(session, tid, itip_id):
    """
    The audit log of a report.

    :param session: An ORM session
    :param tid: A tenant ID
    :param itip_id: The ID of the report
    :return: The serialized entries, most recent first
    """
    internalfiles = session.query(models.InternalFile.id) \
                           .filter(models.InternalFile.internaltip_id == itip_id)

    objects = [
        # An entry naming the report itself: how a deletion stays in the log once its object is gone
        models.AuditLog.object_id == itip_id,
        models.AuditLog.object_id.in_(internalfiles),
        models.AuditLog.object_id.in_(
            session.query(models.Comment.id)
                   .filter(models.Comment.internaltip_id == itip_id)),
        models.AuditLog.object_id.in_(
            session.query(models.ReceiverFile.id)
                   .filter(models.ReceiverFile.internaltip_id == itip_id)),
        # A file of the report is delivered to each recipient through a row of
        # its own, that the access to the file names
        models.AuditLog.object_id.in_(
            session.query(models.WhistleblowerFile.id)
                   .filter(models.WhistleblowerFile.internalfile_id.in_(internalfiles)))
    ]

    logs = session.query(models.AuditLog) \
                  .filter(models.AuditLog.tid == tid, or_(*objects)) \
                  .order_by(models.AuditLog.date.desc())

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

    for itip in session.query(models.InternalTip).filter(models.InternalTip.tid == tid).order_by(models.InternalTip.progressive.desc()):
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


class TipsCollectionHandler(BaseHandler):
    """
    This Handler returns the list of the tips
    """

    def get(self):
        return get_tips(self.request.tid)


class JobsTimingHandler(BaseHandler):
    """
    This handler return the timing for the latest scheduler execution
    """

    def get(self):
        response = []

        for job in State.jobs:
            response.append({
                'name': job.name,
                'timings': job.last_executions
            })

        return response


class AuditLogHandler(BaseHandler):
    """
    Handler providing the audit log of the tenant
    """

    def get(self):
        return get_audit_log(self.request.tid)


class AccessLogHandler(BaseHandler):
    """
    Handler that provide access to the access.log file
    """
    root_tenant_only = True

    def get(self):
        path = os.path.abspath(os.path.join(self.state.settings.working_path, 'log/access.log'))
        return self.write_file_as_download('access.log', path)


class DebugLogHandler(BaseHandler):
    """
    Handler that provide access to the globaleaks.log file
    """
    root_tenant_only = True

    def get(self):
        path = os.path.abspath(os.path.join(self.state.settings.working_path, 'log/globaleaks.log'))
        return self.write_file_as_download('globaleaks.log', path)


def serialize_user_audit(user):
    """
    Serialize the audit view of a user: the traits relevant to the oversight
    """
    return {
        'id': user.id,
        'username': user.username,
        'role': user.role,
        'name': user.name,
        'two_factor': user.two_factor_secret != '',
        'creation_date': user.creation_date,
        'last_login': user.last_login
    }


@transact
def get_users_audit(session, tid):
    return [serialize_user_audit(user)
            for user in session.query(models.User).filter(models.User.tid == tid)]


class UsersAuditHandler(BaseHandler):
    """
    Handler providing the audit view of the users of the tenant
    """

    def get(self):
        return get_users_audit(self.request.tid)
