from sqlalchemy.sql.expression import func, and_, false
from globaleaks import models
from globaleaks.handlers.base import BaseHandler
from globaleaks.orm import transact, tw
from twisted.internet.defer import inlineCallbacks
import json
from datetime import datetime, timedelta
from globaleaks.rest import errors, requests
from globaleaks.utils.utility import datetime_now, uuid4


def _empty_time_metrics():
    return {
        "avg_opening_time_hours": 0,
        "avg_first_reply_time_hours": 0,
        "avg_closure_time_hours": 0,
        "avg_access_time_hours": 0,
        "avg_response_time_hours": 0,
        "avg_identity_disclosure_time_hours": 0,
        "avg_exchanges_per_report": 0,
        "total_exchanges": 0,
        "reports_with_exchanges": 0
    }


def _hours_between(later, earlier):
    if later is None or earlier is None:
        return None
    try:
        return (later - earlier).total_seconds() / 3600.0
    except Exception:
        return None


def _parse_filters(raw_filters):
    if raw_filters in (None, b'', ''):
        return None

    if isinstance(raw_filters, (bytes, bytearray)):
        try:
            raw_filters = raw_filters.decode('utf-8')
        except Exception:
            raise errors.InputValidationError("Invalid request body encoding")

    if isinstance(raw_filters, str):
        try:
            raw_filters = json.loads(raw_filters)
        except Exception:
            raise errors.InputValidationError("Invalid JSON body")

    if raw_filters is None:
        return None

    if not isinstance(raw_filters, dict):
        raise errors.InputValidationError("Filters payload must be a JSON object")

    return raw_filters


def _parse_filter_date(value, field_name):
    if value in (None, ''):
        return None

    if isinstance(value, datetime):
        return value

    if isinstance(value, (int, float)):
        timestamp = value / 1000.0 if value > 10**11 else value
        return datetime.fromtimestamp(timestamp)

    if isinstance(value, str):
        parsed = None
        text = value.strip()
        if not text:
            return None

        if text.isdigit():
            timestamp = float(text)
            timestamp = timestamp / 1000.0 if timestamp > 10**11 else timestamp
            return datetime.fromtimestamp(timestamp)

        for date_format in ('%Y-%m-%d', '%Y-%m-%dT%H:%M:%S', '%Y-%m-%dT%H:%M:%S.%f'):
            try:
                parsed = datetime.strptime(text, date_format)
                break
            except ValueError:
                continue

        if parsed is not None:
            return parsed

        try:
            return datetime.fromisoformat(text.replace('Z', '+00:00')).replace(tzinfo=None)
        except ValueError:
            raise errors.InputValidationError("Invalid %s format" % field_name)

    raise errors.InputValidationError("Invalid %s type" % field_name)


def _context_name_candidates(context_name):
    candidates = set()
    if isinstance(context_name, dict):
        for value in context_name.values():
            if isinstance(value, str) and value.strip():
                candidates.add(value.strip())
        if isinstance(context_name.get('en'), str) and context_name.get('en').strip():
            candidates.add(context_name.get('en').strip())
    elif isinstance(context_name, str) and context_name.strip():
        candidates.add(context_name.strip())

    return candidates


def _normalize_channel_filters(channel_filter):
    raw_values = channel_filter if isinstance(channel_filter, list) else [channel_filter]
    normalized_values = set()

    for value in raw_values:
        if isinstance(value, dict):
            maybe_id = value.get('id')
            maybe_label = value.get('label')
            if maybe_id:
                normalized_values.add(str(maybe_id).strip())
            if isinstance(maybe_label, dict):
                normalized_values.update(_context_name_candidates(maybe_label))
            elif isinstance(maybe_label, str) and maybe_label.strip():
                normalized_values.add(maybe_label.strip())
        elif isinstance(value, str) and value.strip():
            normalized_values.add(value.strip())
        elif value is not None:
            normalized_values.add(str(value).strip())

    return normalized_values


def _context_display_label(context_name):
    if isinstance(context_name, dict):
        english = context_name.get('en')
        if isinstance(english, str) and english.strip():
            return english.strip()
        for value in context_name.values():
            if isinstance(value, str) and value.strip():
                return value.strip()
        return ''

    if isinstance(context_name, str):
        return context_name.strip()

    return str(context_name).strip() if context_name is not None else ''


def apply_filters_to_query(session, query, filters, tid):
    if not filters:
        return query

    if 'context_id' in filters and filters['context_id']:
        query = query.filter(models.InternalTip.context_id == filters['context_id'])

    if 'channel' in filters and filters['channel']:
        channel_values = _normalize_channel_filters(filters['channel'])

        contexts = session.query(models.Context.id, models.Context.name).filter(models.Context.tid == tid).all()

        context_id_list = []
        for ctx_id, ctx_name in contexts:
            ctx_id_str = str(ctx_id)
            ctx_name_values = _context_name_candidates(ctx_name)
            if ctx_id_str in channel_values or bool(ctx_name_values.intersection(channel_values)):
                context_id_list.append(ctx_id)

        if context_id_list:
            query = query.filter(models.InternalTip.context_id.in_(context_id_list))
        else:
            query = query.filter(false())

    if 'date_from' in filters and filters['date_from']:
        date_from = _parse_filter_date(filters['date_from'], 'date_from')
        query = query.filter(models.InternalTip.creation_date >= date_from)

    if 'date_to' in filters and filters['date_to']:
        date_to_value = filters['date_to']
        date_to = _parse_filter_date(date_to_value, 'date_to')
        if isinstance(date_to_value, str):
            date_to_text = date_to_value.strip()
            if date_to_text and len(date_to_text) == 10 and date_to_text[4] == '-' and date_to_text[7] == '-':
                date_to = date_to + timedelta(days=1)
        query = query.filter(models.InternalTip.creation_date < date_to)

    return query

def calculate_time_based_metrics(session, tid, filters=None):
    filtered_tips_query = session.query(models.InternalTip.id).filter(models.InternalTip.tid == tid)
    filtered_tips_query = apply_filters_to_query(session, filtered_tips_query, filters, tid)

    if filtered_tips_query.first() is None:
        return _empty_time_metrics()
    filtered_tips_subquery = filtered_tips_query.subquery()

    tip_rows = session.query(
        models.InternalTip.id,
        models.InternalTip.creation_date
    ).join(
        filtered_tips_subquery, filtered_tips_subquery.c.id == models.InternalTip.id
    ).filter(
        models.InternalTip.tid == tid
    ).all()

    tip_creation_map = {tip_id: creation_date for tip_id, creation_date in tip_rows}

    first_opened_by_tip = {}
    first_closed_by_tip = {}
    status_logs = session.query(
        models.AuditLog.object_id,
        models.AuditLog.date,
        models.AuditLog.data
    ).join(
        filtered_tips_subquery, filtered_tips_subquery.c.id == models.AuditLog.object_id
    ).filter(
        and_(
            models.AuditLog.tid == tid,
            models.AuditLog.type == 'update_report_status'
        )
    ).order_by(models.AuditLog.date.asc()).all()

    for object_id, log_date, log_data in status_logs:
        status = log_data.get('status') if isinstance(log_data, dict) else None
        if status == 'opened' and object_id not in first_opened_by_tip:
            first_opened_by_tip[object_id] = log_date
        elif status == 'closed' and object_id not in first_closed_by_tip:
            first_closed_by_tip[object_id] = log_date

    opening_times = []
    closure_times = []
    for tip_id, creation_date in tip_creation_map.items():
        opened_date = first_opened_by_tip.get(tip_id)
        closed_date = first_closed_by_tip.get(tip_id)

        opening_hours = _hours_between(opened_date, creation_date)
        if opening_hours is not None:
            opening_times.append(opening_hours)

        closure_hours = _hours_between(closed_date, creation_date)
        if closure_hours is not None:
            closure_times.append(closure_hours)

    avg_opening_time = sum(opening_times) / len(opening_times) if opening_times else 0
    avg_closure_time = sum(closure_times) / len(closure_times) if closure_times else 0

    first_comment_subq = session.query(
        models.Comment.internaltip_id,
        func.min(models.Comment.creation_date).label('first_comment_date')
    ).join(
        models.InternalTip, models.Comment.internaltip_id == models.InternalTip.id
    ).join(
        filtered_tips_subquery, filtered_tips_subquery.c.id == models.InternalTip.id
    ).filter(
        and_(
            models.InternalTip.tid == tid,
            models.Comment.author_id.isnot(None)
        )
    ).group_by(models.Comment.internaltip_id).subquery()

    response_query = session.query(
        first_comment_subq.c.first_comment_date,
        models.InternalTip.creation_date
    ).join(
        first_comment_subq, first_comment_subq.c.internaltip_id == models.InternalTip.id
    )
    response_times = []
    for first_comment_date, creation_date in response_query.all():
        hours = _hours_between(first_comment_date, creation_date)
        if hours is not None:
            response_times.append(hours)
    avg_first_reply_time = sum(response_times) / len(response_times) if response_times else 0

    exchange_counts_query = session.query(
        models.Comment.internaltip_id,
        func.count(models.Comment.id).label('cnt')
    ).join(
        models.InternalTip, models.Comment.internaltip_id == models.InternalTip.id
    ).join(
        filtered_tips_subquery, filtered_tips_subquery.c.id == models.InternalTip.id
    ).filter(
        models.InternalTip.tid == tid
    ).group_by(models.Comment.internaltip_id)

    exchange_data = exchange_counts_query.all()
    total_exchanges = sum(cnt for _, cnt in exchange_data)
    num_tips_with_exchanges = len(exchange_data)
    avg_exchanges_per_tip = total_exchanges / num_tips_with_exchanges if num_tips_with_exchanges > 0 else 0

    return {
        "avg_opening_time_hours": round(avg_opening_time, 2),
        "avg_first_reply_time_hours": round(avg_first_reply_time, 2),
        "avg_closure_time_hours": round(avg_closure_time, 2),
        "avg_access_time_hours": round(avg_opening_time, 2),
        "avg_response_time_hours": round(avg_first_reply_time, 2),
        "avg_identity_disclosure_time_hours": round(avg_closure_time, 2),
        "avg_exchanges_per_report": round(avg_exchanges_per_tip, 2),
        "total_exchanges": total_exchanges,
        "reports_with_exchanges": num_tips_with_exchanges
    }

@transact
def get_stats(session, tid, filters=None):
    base_query = session.query(func.count(models.InternalTip.id)).filter(models.InternalTip.tid == tid)
    base_query = apply_filters_to_query(session, base_query, filters, tid)
    reports_count = base_query.one()[0]
    no_access_query = session.query(func.count(models.InternalTip.id)) \
                            .filter(models.InternalTip.tid == tid,
                models.InternalTip.access_count == 0)
    no_access_query = apply_filters_to_query(session, no_access_query, filters, tid)

    num_tips_no_access = no_access_query.one()[0]
    mobile_query = session.query(func.count(models.InternalTip.id)) \
                            .filter(models.InternalTip.tid == tid,
                models.InternalTip.mobile == True)
    mobile_query = apply_filters_to_query(session, mobile_query, filters, tid)
    num_tips_mobile = mobile_query.one()[0]
    tor_query = session.query(func.count(models.InternalTip.id)) \
                            .filter(models.InternalTip.tid == tid,
                models.InternalTip.tor == True)
    tor_query = apply_filters_to_query(session, tor_query, filters, tid)
    num_tips_tor = tor_query.one()[0]
    subscribed_query = session.query(func.count(models.InternalTip.id)) \
                            .filter(models.InternalTip.tid == tid) \
                            .join(models.InternalTipData,
                                  and_(models.InternalTipData.internaltip_id == models.InternalTip.id,
                                       models.InternalTipData.key == 'whistleblower_identity',
                                       models.InternalTipData.creation_date == models.InternalTip.creation_date))
    subscribed_query = apply_filters_to_query(session, subscribed_query, filters, tid)
    num_subscribed_tips = subscribed_query.one()[0]
    initially_anonymous_query = session.query(func.count(models.InternalTip.id)) \
                                    .filter(models.InternalTip.tid == tid) \
                                    .join(models.InternalTipData,
                                          and_(models.InternalTipData.internaltip_id == models.InternalTip.id,
                                               models.InternalTipData.key == 'whistleblower_identity',
                                               models.InternalTipData.creation_date != models.InternalTip.creation_date))
    initially_anonymous_query = apply_filters_to_query(session, initially_anonymous_query, filters, tid)
    num_initially_anonymous_tips = initially_anonymous_query.one()[0]
    num_anonymous_tips = reports_count - num_subscribed_tips - num_initially_anonymous_tips
    time_metrics = calculate_time_based_metrics(session, tid, filters)

    stats = {
        "reports_count": reports_count,
        "reports_with_no_access": num_tips_no_access,
        "reports_anonymous": num_anonymous_tips,
        "reports_subscribed": num_subscribed_tips,
        "reports_initially_anonymous": num_initially_anonymous_tips,
        "reports_mobile": num_tips_mobile,
        "reports_tor": num_tips_tor
    }

    stats.update(time_metrics)
    return stats
    

def _default_template():
    return {
        'label': 'GlobaLeaks',
        'creation_date': datetime_now(),
        'data': {
            'config': {
                'selectedMetrics': ['reports_received', 'reports_not_accessed', 'anonymous_reports'],
                'selectedCharts': []
            },
            'permissions': {
                'canEdit': True,
                'canDelete': False,
                'canExport': True
            }
        }
    }


class FilterOptions(BaseHandler):
    check_roles = 'analyst'

    @inlineCallbacks
    def get(self):
        tid = self.request.tid
        channel_options = yield tw(get_channel_options, tid)
        return {'channel': channel_options}

def get_channel_options(session, tid):
    channels = session.query(models.Context.id, models.Context.name).filter(models.Context.tid == tid).order_by(models.Context.name).all()
    options = []
    for context_id, channel_name in channels:
        label = _context_display_label(channel_name)
        if label:
            options.append({'id': context_id, 'label': label})
    
    return options


class Statistics(BaseHandler):
    check_roles = 'analyst'

    def get(self):
        return get_stats(self.request.tid, None)

    def post(self):
        filters = _parse_filters(self.request.content.read())
        return get_stats(self.request.tid, filters)

def db_create_statistical_template(session, tid, request):
    default = _default_template()
    request['id'] = uuid4()
    request['tid'] = tid
    request['data'] = default['data']

    template = models.StatisticalReportTemplate(request)
    session.add(template)
    session.flush()
    return template


def db_list_statistical_templates(session, tid):
    return session.query(models.StatisticalReportTemplate).filter(models.StatisticalReportTemplate.tid == tid).all()


def db_get_statistical_template(session, tid, template_id):
    template = session.query(models.StatisticalReportTemplate).filter(models.StatisticalReportTemplate.tid == tid,
                                                                      models.StatisticalReportTemplate.id == template_id).first()
    if not template:
        raise errors.ResourceNotFound
    return template


def db_update_statistical_template(session, tid, template_id, request):
    template = db_get_statistical_template(session, tid, template_id)
    template.update(request)
    return template


def db_delete_statistical_template(session, tid, template_id):
    template = db_get_statistical_template(session, tid, template_id)
    session.delete(template)


def db_create_statistical_report(session, tid, request):
    request['id'] = uuid4()
    request['tid'] = tid
    report = models.StatisticalReport(request)
    session.add(report)
    session.flush()
    return report


def db_list_statistical_reports(session, tid):
    return session.query(models.StatisticalReport).filter(models.StatisticalReport.tid == tid).all()


def db_get_statistical_report(session, tid, report_id):
    report = session.query(models.StatisticalReport).filter(models.StatisticalReport.tid == tid,
                                                           models.StatisticalReport.id == report_id).first()
    if not report:
        raise errors.ResourceNotFound
    return report


def db_update_statistical_report(session, tid, report_id, request):
    report = db_get_statistical_report(session, tid, report_id)
    report.update(request)
    return report


def db_delete_statistical_report(session, tid, report_id):
    report = db_get_statistical_report(session, tid, report_id)
    session.delete(report)


def serialize_statistical_template(template):
    return {
        'id': template.id,
        'tid': template.tid,
        'label': template.label,
        'creation_date': template.creation_date,
        'data': template.data if template.data is not None else _default_template()['data']
    }


def serialize_statistical_report(report):
    return {
        'id': report.id,
        'tid': report.tid,
        'label': report.label,
        'creation_date': report.creation_date,
        'template_id': report.template_id,
        'data': report.data
    }


def create_statistical_template(session, tid, request):
    template = db_create_statistical_template(session, tid, request)
    return serialize_statistical_template(template)


def list_statistical_templates(session, tid):
    templates = db_list_statistical_templates(session, tid)
    return [serialize_statistical_template(t) for t in templates]


def get_statistical_template(session, tid, template_id):
    template = db_get_statistical_template(session, tid, template_id)
    return serialize_statistical_template(template)


def update_statistical_template(session, tid, template_id, request):
    template = db_update_statistical_template(session, tid, template_id, request)
    return serialize_statistical_template(template)


def delete_statistical_template(session, tid, template_id):
    return db_delete_statistical_template(session, tid, template_id)


def create_statistical_report(session, tid, request):
    report = db_create_statistical_report(session, tid, request)
    return serialize_statistical_report(report)


def list_statistical_reports(session, tid):
    reports = db_list_statistical_reports(session, tid)
    return [serialize_statistical_report(r) for r in reports]


def get_statistical_report(session, tid, report_id):
    report = db_get_statistical_report(session, tid, report_id)
    return serialize_statistical_report(report)


def update_statistical_report(session, tid, report_id, request):
    report = db_update_statistical_report(session, tid, report_id, request)
    return serialize_statistical_report(report)


def delete_statistical_report(session, tid, report_id):
    return db_delete_statistical_report(session, tid, report_id)


class StatisticalReportTemplates(BaseHandler):
    check_roles = 'analyst'

    def get(self):
        return tw(list_statistical_templates, self.request.tid)

    @inlineCallbacks
    def post(self):
        request = json.loads(self.request.content.read())
        request = yield self.validate_request(json.dumps(request), requests.AdminStatisticalTemplateDesc)
        res = yield tw(create_statistical_template, self.request.tid, request)
        return res


class StatisticalReportTemplateInstance(BaseHandler):
    check_roles = 'analyst'

    def get(self, template_id):
        return tw(get_statistical_template, self.request.tid, template_id)

    @inlineCallbacks
    def put(self, template_id):
        request = json.loads(self.request.content.read())
        request = yield self.validate_request(json.dumps(request), requests.AdminStatisticalTemplateDesc)
        res = yield tw(update_statistical_template, self.request.tid, template_id, request)
        return res

    def delete(self, template_id):
        return tw(delete_statistical_template, self.request.tid, template_id)


class StatisticalReports(BaseHandler):
    check_roles = 'analyst'

    def get(self):
        return tw(list_statistical_reports, self.request.tid)

    @inlineCallbacks
    def post(self):
        request = json.loads(self.request.content.read())
        request = yield self.validate_request(json.dumps(request), requests.AdminStatisticalReportDesc)
        res = yield tw(create_statistical_report, self.request.tid, request)
        return res


class StatisticalReportInstance(BaseHandler):
    check_roles = 'analyst'

    def get(self, report_id):
        return tw(get_statistical_report, self.request.tid, report_id)

    @inlineCallbacks
    def put(self, report_id):
        request = json.loads(self.request.content.read())
        request = yield self.validate_request(json.dumps(request), requests.AdminStatisticalReportDesc)
        res = yield tw(update_statistical_report, self.request.tid, report_id, request)
        return res

    def delete(self, report_id):
        return tw(delete_statistical_report, self.request.tid, report_id)
