"""
The audit log exported on the administrative area.

The implementation is the shared one: here it is only bound to the role that
reads it and to the permission scoping which administrators read it.
"""
from globaleaks.handlers import auditlog


class AuditLog(auditlog.AuditLogHandler):
    check_roles = 'admin'
    require_permission = 'can_manage_auditlog'


class AccessLog(auditlog.AccessLogHandler):
    check_roles = 'admin'
    require_permission = 'can_manage_auditlog'


class DebugLog(auditlog.DebugLogHandler):
    check_roles = 'admin'
    require_permission = 'can_manage_auditlog'


class JobsTiming(auditlog.JobsTimingHandler):
    check_roles = 'admin'
    require_permission = 'can_manage_auditlog'


class TipsCollection(auditlog.TipsCollectionHandler):
    check_roles = 'admin'
    require_permission = 'can_manage_auditlog'


class UsersAudit(auditlog.UsersAuditHandler):
    check_roles = 'admin'
    require_permission = 'can_manage_auditlog'
