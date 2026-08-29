"""
The audit log exported on the area of the auditor.

The implementation is the shared one: here it is only bound to the role that
reads it, the actor the analysis defines for the oversight of the platform,
which reaches this area alone and no administrative API.
"""
from globaleaks.handlers import auditlog


class AuditLog(auditlog.AuditLogHandler):
    check_roles = 'auditor'


class AccessLog(auditlog.AccessLogHandler):
    check_roles = 'auditor'


class DebugLog(auditlog.DebugLogHandler):
    check_roles = 'auditor'


class JobsTiming(auditlog.JobsTimingHandler):
    check_roles = 'auditor'


class TipsCollection(auditlog.TipsCollectionHandler):
    check_roles = 'auditor'


class UsersAudit(auditlog.UsersAuditHandler):
    check_roles = 'auditor'
