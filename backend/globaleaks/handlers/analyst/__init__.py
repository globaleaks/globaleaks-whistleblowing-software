from sqlalchemy.sql.expression import func, and_
from globaleaks import models
from globaleaks.handlers.base import BaseHandler
from globaleaks.orm import transact, tw
from twisted.internet.defer import inlineCallbacks
import json
from datetime import datetime, timedelta
from globaleaks.rest import errors, requests
from globaleaks.utils.utility import datetime_now, uuid4
from sqlalchemy import distinct


def apply_filters_to_query(session, query, filters, tid):
    if not filters:
        return query

    if 'context_id' in filters and filters['context_id']:
        query = query.filter(models.InternalTip.context_id == filters['context_id'])

    if 'status' in filters and filters['status']:
        status_labels = filters['status'] if isinstance(filters['status'], list) else [filters['status']]

        status_ids = []
        for label in status_labels:
            status_record = session.query(models.SubmissionStatus.id).filter(
                models.SubmissionStatus.tid == tid,
                models.SubmissionStatus.label.contains(label)
            ).first()
            if status_record:
                status_ids.append(status_record[0])

        if status_ids:
            query = query.filter(models.InternalTip.status.in_(status_ids))

    if 'tags' in filters and filters['tags']:
        pass

    if 'tenant' in filters and filters['tenant']:
        pass

    if 'channel' in filters and filters['channel']:
        channel_values = filters['channel'] if isinstance(filters['channel'], list) else [filters['channel']]

        contexts = session.query(models.Context.id, models.Context.name).filter(
            models.Context.tid == tid
        ).all()

        context_id_list = []
        for ctx_id, ctx_name in contexts:
            if ctx_id in channel_values or ctx_name in channel_values:
                context_id_list.append(ctx_id)

        if context_id_list:
            query = query.filter(models.InternalTip.context_id.in_(context_id_list))

    if 'date_from' in filters and filters['date_from']:
        try:
            if isinstance(filters['date_from'], (int, float)):
                date_from = datetime.fromtimestamp(filters['date_from'] / 1000)
            else:
                date_from = datetime.strptime(filters['date_from'], '%Y-%m-%d')
            query = query.filter(models.InternalTip.creation_date >= date_from)
        except (ValueError, TypeError):
            pass

    if 'date_to' in filters and filters['date_to']:
        try:
            if isinstance(filters['date_to'], (int, float)):
                date_to = datetime.fromtimestamp(filters['date_to'] / 1000)
            else:
                date_to = datetime.strptime(filters['date_to'], '%Y-%m-%d') + timedelta(days=1)
            query = query.filter(models.InternalTip.creation_date < date_to)
        except (ValueError, TypeError):
            pass

    return query

def calculate_time_based_metrics(session, tid, filters=None):
    try:
        base_query = session.query(models.InternalTip).filter(models.InternalTip.tid == tid)
        base_query = apply_filters_to_query(session, base_query, filters, tid)

        try:
            access_times = session.query(
                func.extract(
                    'epoch',
                    func.coalesce(models.InternalTip.last_access, models.InternalTip.creation_date)
                    - models.InternalTip.creation_date
                ) / 3600
            ).filter(
                models.InternalTip.tid == tid,
                models.InternalTip.access_count > 0
            )
            access_times = apply_filters_to_query(session, access_times, filters, tid)
            avg_access_time = access_times.scalar() or 0
        except Exception:
            avg_access_time = 0

        try:
            response_times = session.query(
                func.extract(
                    'epoch',
                    func.min(models.Comment.creation_date) - models.InternalTip.creation_date
                ) / 3600
            ).join(
                models.Comment, models.Comment.internaltip_id == models.InternalTip.id
            ).filter(
                models.InternalTip.tid == tid,
                models.Comment.author_id.isnot(None)
            ).group_by(models.InternalTip.id)

            response_times = apply_filters_to_query(session, response_times, filters, tid)

            avg_response_times = response_times.all()
            avg_response_time = sum(avg_response_times) / len(avg_response_times) if avg_response_times else 0
        except Exception:
            avg_response_time = 0

        try:
            disclosure_times = session.query(
                func.extract(
                    'epoch',
                    models.InternalTipData.creation_date - models.InternalTip.creation_date
                ) / 3600
            ).join(
                models.InternalTipData,
                and_(
                    models.InternalTipData.internaltip_id == models.InternalTip.id,
                    models.InternalTipData.key == 'whistleblower_identity',
                    models.InternalTipData.creation_date != models.InternalTip.creation_date
                )
            ).filter(models.InternalTip.tid == tid)
            disclosure_times = apply_filters_to_query(session, disclosure_times, filters, tid)
            disclosure_times_list = disclosure_times.all()
            avg_disclosure_time = sum(disclosure_times_list) / len(disclosure_times_list) if disclosure_times_list else 0
        except Exception:
            avg_disclosure_time = 0

        try:
            exchange_counts = session.query(
                func.count(models.Comment.id)
            ).join(
                models.InternalTip, models.Comment.internaltip_id == models.InternalTip.id
            ).filter(models.InternalTip.tid == tid)
            exchange_counts = apply_filters_to_query(session, exchange_counts, filters, tid)
            total_exchanges = exchange_counts.scalar() or 0
        except Exception:
            total_exchanges = 0

        try:
            tips_with_exchanges = session.query(
                func.count(distinct(models.InternalTip.id))
            ).join(
                models.Comment, models.Comment.internaltip_id == models.InternalTip.id
            ).filter(models.InternalTip.tid == tid)
            tips_with_exchanges = apply_filters_to_query(session, tips_with_exchanges, filters, tid)
            num_tips_with_exchanges = tips_with_exchanges.scalar() or 0
        except Exception:
            num_tips_with_exchanges = 0

        avg_exchanges_per_tip = total_exchanges / num_tips_with_exchanges if num_tips_with_exchanges > 0 else 0

        return {
            "avg_access_time_hours": round(avg_access_time, 2),
            "avg_response_time_hours": round(avg_response_time, 2),
            "avg_identity_disclosure_time_hours": round(avg_disclosure_time, 2),
            "avg_exchanges_per_report": round(avg_exchanges_per_tip, 2),
            "total_exchanges": total_exchanges,
            "reports_with_exchanges": num_tips_with_exchanges
        }
    except Exception:
        return {
            "avg_access_time_hours": 0,
            "avg_response_time_hours": 0,
            "avg_identity_disclosure_time_hours": 0,
            "avg_exchanges_per_report": 0,
            "total_exchanges": 0,
            "reports_with_exchanges": 0
        }


@transact
def get_stats(session, tid, filters=None):
    try:
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
    except Exception:
        return {
            "reports_count": 0,
            "reports_with_no_access": 0,
            "reports_anonymous": 0,
            "reports_subscribed": 0,
            "reports_initially_anonymous": 0,
            "reports_mobile": 0,
            "reports_tor": 0,
            "avg_access_time_hours": 0,
            "avg_response_time_hours": 0,
            "avg_identity_disclosure_time_hours": 0,
            "avg_exchanges_per_report": 0,
            "total_exchanges": 0,
            "reports_with_exchanges": 0
        }

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

    def get(self):
        filter_type = self.get_param('type')
        tid = self.request.tid

        if filter_type == 'status':
            return self.get_status_options(tid)
        elif filter_type == 'tags':
            return self.get_tag_options(tid)
        elif filter_type == 'tenant':
            return self.get_tenant_options(tid)
        elif filter_type == 'channel':
            return self.get_channel_options(tid)
        else:
            return {
                'status': self.get_status_options(tid),
                'tags': self.get_tag_options(tid),
                'tenant': self.get_tenant_options(tid),
                'channel': self.get_channel_options(tid)
            }

    def get_param(self, name):
        args = self.request.args.get(name.encode())
        return args[0].decode() if args else ''

    def get_status_options(self, tid):
        try:
            statuses = self.session.query(
                models.SubmissionStatus.id,
                models.SubmissionStatus.label
            ).filter(
                models.SubmissionStatus.tid == tid
            ).order_by(models.SubmissionStatus.order).all()

            options = []
            for status_id, label_dict in statuses:
                if status_id and label_dict:
                    label_text = label_dict.get('en', list(label_dict.values())[0] if label_dict else status_id)
                    options.append({
                        'id': status_id,
                        'label': label_text
                    })

            return options
        except Exception as e:
            return []

    def get_tag_options(self, tid):
        try:
            tags = self.session.query(models.InternalTipData.value) \
                .join(models.InternalTip, models.InternalTipData.internaltip_id == models.InternalTip.id) \
                .filter(models.InternalTip.tid == tid,
                        models.InternalTipData.key.like('%tag%')) \
                .distinct().limit(20).all()

            options = []
            for i, (tag,) in enumerate(tags, 1):
                if tag and tag.strip():
                    options.append({
                        'id': i,
                        'label': tag.strip()
                    })

            return options
        except Exception:
            return []

    def get_tenant_options(self, tid):
        try:
            tenants = self.session.query(models.Tenant.id, models.Tenant.name) \
                .filter(models.Tenant.id == tid) \
                .all()

            options = []
            for i, (tenant_id, name) in enumerate(tenants, 1):
                if name:
                    options.append({
                        'id': i,
                        'label': name
                    })

            return options
        except Exception:
            return []

    def get_channel_options(self, tid):
        try:
            channels = self.session.query(
                models.Context.id,
                models.Context.name
            ).filter(
                models.Context.tid == tid
            ).order_by(models.Context.name).all()

            options = []
            for context_id, channel_name in channels:
                if channel_name:
                    options.append({
                        'id': context_id,
                        'label': channel_name
                    })

            return options
        except Exception:
            return []


class Statistics(BaseHandler):
    check_roles = 'analyst'

    def post(self):
        filters = json.loads(self.request.content.read())
        return get_stats(self.request.tid, filters if filters else None)

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


def serialize_statistical_template(session, template):
    return {
        'id': template.id,
        'tid': template.tid,
        'label': template.label,
        'creation_date': template.creation_date,
        'data': template.data if template.data is not None else _default_template()['data']
    }


def serialize_statistical_report(session, report):
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
    return serialize_statistical_template(session, template)


def list_statistical_templates(session, tid):
    templates = db_list_statistical_templates(session, tid)
    return [serialize_statistical_template(session, t) for t in templates]


def get_statistical_template(session, tid, template_id):
    template = db_get_statistical_template(session, tid, template_id)
    return serialize_statistical_template(session, template)


def update_statistical_template(session, tid, template_id, request):
    template = db_update_statistical_template(session, tid, template_id, request)
    return serialize_statistical_template(session, template)


def delete_statistical_template(session, tid, template_id):
    return db_delete_statistical_template(session, tid, template_id)


def create_statistical_report(session, tid, request):
    report = db_create_statistical_report(session, tid, request)
    return serialize_statistical_report(session, report)


def list_statistical_reports(session, tid):
    reports = db_list_statistical_reports(session, tid)
    return [serialize_statistical_report(session, r) for r in reports]


def get_statistical_report(session, tid, report_id):
    report = db_get_statistical_report(session, tid, report_id)
    return serialize_statistical_report(session, report)


def update_statistical_report(session, tid, report_id, request):
    report = db_update_statistical_report(session, tid, report_id, request)
    return serialize_statistical_report(session, report)


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
