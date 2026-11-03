"""
The audit log of the account of the user in session.

Whatever pertains to the account is shown to its owner: the operations the
user performed, those performed by an administrator or by the system on the
account, and those performed by whoever used the account, failed logins
included. An entry pertains to the account when it names it either as who
acted or as the object acted upon.
"""
from sqlalchemy import or_

from globaleaks import models
from globaleaks.handlers.auditlog import serialize_log
from globaleaks.handlers.base import BaseHandler
from globaleaks.orm import transact


def db_get_user_audit_log(session, user_id):
    """
    The audit log of an account.

    :param session: An ORM session
    :param user_id: The ID of the user owning the account
    :return: The serialized entries, most recent first
    """
    # Identifiers are unique across the sites: the entries recorded on a site
    # other than the one of the account, as the actions of an administrator of
    # the root site on a subsite, belong to the account all the same
    logs = session.query(models.AuditLog) \
                  .filter(or_(models.AuditLog.user_id == user_id,
                              models.AuditLog.object_id == user_id)) \
                  .order_by(models.AuditLog.date.desc(), models.AuditLog.id.desc()) \
                  .all()

    # Who acted is named by the entry, falling back on the identifier when
    # the user is gone
    actors = {log.user_id for log in logs if log.user_id}
    usernames = dict(session.query(models.User.id, models.User.username)
                            .filter(models.User.id.in_(actors)))

    return [serialize_log(log, usernames.get(log.user_id, log.user_id or '')) for log in logs]


@transact
def get_user_audit_log(session, user_id):
    return db_get_user_audit_log(session, user_id)


class UserAuditLog(BaseHandler):
    """
    Handler providing the audit log of the account of the user in session
    """
    check_roles = 'user'

    def get(self):
        return get_user_audit_log(self.session.user_id)
