from datetime import timedelta

from globaleaks import models
from globaleaks.models.config import ConfigFactory
from globaleaks.rest import errors
from globaleaks.utils.utility import datetime_now


COMMENTS_CLOSED_MESSAGE = "This report is closed and no longer accepts comments."


def get_comment_period_after_closure_days(session, tid):
    value = ConfigFactory(session, tid).get_val('comment_period_after_closure_days')
    return max(0, value)


def get_current_comment_closure_date(session, itip):
    if itip.status != 'closed':
        return None

    closure_date = None

    audit_logs = session.query(models.AuditLog.date, models.AuditLog.data) \
                        .filter(models.AuditLog.tid == itip.tid,
                                models.AuditLog.object_id == itip.id,
                                models.AuditLog.type == 'update_report_status') \
                        .order_by(models.AuditLog.date.desc(),
                                  models.AuditLog.id.desc())

    for audit_date, audit_data in audit_logs:
        status = audit_data.get('status') if isinstance(audit_data, dict) else None
        if status == 'closed':
            closure_date = audit_date
            continue

        if closure_date is not None:
            break

    return closure_date or itip.update_date


def is_comment_submission_allowed(session, itip):
    if itip.status != 'closed':
        return True

    period = get_comment_period_after_closure_days(session, itip.tid)
    if period == 0:
        return False

    closure_date = get_current_comment_closure_date(session, itip)
    return datetime_now() <= closure_date + timedelta(days=period)


def assert_comment_submission_allowed(session, itip):
    if not is_comment_submission_allowed(session, itip):
        raise errors.InputValidationError(COMMENTS_CLOSED_MESSAGE)
