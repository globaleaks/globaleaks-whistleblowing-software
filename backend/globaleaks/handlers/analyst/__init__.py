from sqlalchemy.sql.expression import func, and_, false
from nacl.encoding import Base64Encoder
from globaleaks import models
from globaleaks.handlers.base import BaseHandler
from globaleaks.models.config import DEFAULT_PROFILE_ID, db_get_config_variable, db_get_pid, db_set_config_variable
from globaleaks.orm import transact, tw
from twisted.internet.defer import inlineCallbacks
import json
from datetime import datetime, timedelta
from globaleaks.rest import errors, requests
from globaleaks.utils.crypto import GCE
from globaleaks.utils.utility import uuid4
from nacl.exceptions import CryptoError


def _empty_time_metrics():
    return {
        "avg_opening_time_hours": 0,
        "avg_first_reply_time_hours": 0,
        "avg_closure_time_hours": 0,
        "avg_exchanges_per_report": 0,
        "total_exchanges": 0,
        "reports_with_exchanges": 0
    }


def _hours_between(later, earlier):
    if later is None or earlier is None:
        return None
    try:
        return (later - earlier).total_seconds() / 3600.0
    except (TypeError, AttributeError):
        return None


def _round_time_metric(hours):
    if hours is None:
        return 0

    return round(hours, 4)


def _get_status_from_audit_log_data(log_data):
    if isinstance(log_data, dict):
        return log_data.get('status')

    if isinstance(log_data, str):
        try:
            parsed = json.loads(log_data)
        except (TypeError, ValueError):
            return None

        if isinstance(parsed, dict):
            return parsed.get('status')

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


def _localized_label(value, language='en'):
    if isinstance(value, dict):
        lang_value = value.get(language)
        if isinstance(lang_value, str) and lang_value.strip():
            return lang_value.strip()

        english = value.get('en')
        if isinstance(english, str) and english.strip():
            return english.strip()

        for localized_value in value.values():
            if isinstance(localized_value, str) and localized_value.strip():
                return localized_value.strip()

        return ''

    if isinstance(value, str):
        return value.strip()

    return str(value).strip() if value is not None else ''


def _decode_stat_answers(raw_stat_answers, stat_prv_key):
    if raw_stat_answers in (None, '', {}):
        return {}

    if isinstance(raw_stat_answers, dict):
        return raw_stat_answers

    if isinstance(raw_stat_answers, str):
        stat_text = raw_stat_answers.strip()
        if not stat_text:
            return {}

        try:
            parsed = json.loads(stat_text)
            if isinstance(parsed, dict):
                return parsed
        except ValueError:
            # Not plain JSON: the answers may be encrypted, and are read below
            pass

        if not stat_prv_key:
            return {}

        try:
            encrypted_payload = Base64Encoder.decode(stat_text.encode('utf-8'))
            decrypted = GCE.asymmetric_decrypt(stat_prv_key, encrypted_payload).decode('utf-8')
            parsed = json.loads(decrypted)
            if isinstance(parsed, dict):
                return parsed
        except (ValueError, CryptoError):
            return {}

    return {}


def _get_user_stat_prv_key(session, tid, user_id, user_cc):
    if not user_id or not user_cc:
        return None

    encrypted_stat_key = session.query(models.User.crypto_global_stat_prv_key) \
                                .filter(models.User.id == user_id,
                                        models.User.tid == tid) \
                                .one_or_none()

    if not encrypted_stat_key or not encrypted_stat_key[0]:
        return None

    try:
        return GCE.asymmetric_decrypt(user_cc, Base64Encoder.decode(encrypted_stat_key[0].encode()))
    except (ValueError, CryptoError):
        return None


def db_get_statistical_questions(session, tid, language='en'):
    """
    Return the questions the statistics account for: the question templates of

    :param session: An ORM session
    :param tid: A tenant ID
    :param language: The language of the serialization
    :return: The questions, by the ID of their template
    """
    template_rows = session.query(models.Field.id, models.Field.label) \
                           .filter(models.Field.tid.in_({1, tid}),
                                   models.Field.instance == 'template',
                                   models.Field.fieldgroup_id.is_(None),
                                   models.Field.type.in_(('selectbox', 'multichoice', 'checkbox')),
                                   models.Field.statistical == True) \
                           .all()

    questions = {
        str(template_id): {
            'template_id': str(template_id),
            'title': _localized_label(label, language),
            'options': []
        } for template_id, label in template_rows
    }

    if not questions:
        return questions

    option_rows = session.query(models.FieldOption.field_id, models.FieldOption.id, models.FieldOption.label) \
                         .filter(models.FieldOption.field_id.in_(list(questions))) \
                         .all()

    for field_id, option_id, option_label in option_rows:
        option_id_str = str(option_id)
        questions[str(field_id)]['options'].append({
            'id': option_id_str,
            'label': _localized_label(option_label, language) or option_id_str
        })

    return questions


def db_get_metric_catalog(session, tid, language='en'):
    """
    Return the metrics a template is composed of, carrying no value

    :param session: An ORM session
    :param tid: A tenant ID
    :param language: The language of the serialization
    :return: The catalog of the metrics of the site
    """
    questions = db_get_statistical_questions(session, tid, language)

    return {
        'question_template_dropdown_metrics': [{
            'id': 'question_template_dropdown_%s' % question['template_id'],
            'template_id': question['template_id'],
            'title': question['title'] or question['template_id'],
            'options': question['options']
        } for question in sorted(questions.values(), key=lambda q: (q['title'] or '').lower())]
    }


def calculate_dropdown_template_metrics(session, tid, filtered_tips_subquery, language='en', user_id=None, user_cc=None):
    questions = db_get_statistical_questions(session, tid, language)
    if not questions:
        return []

    template_ids = list(questions)
    template_metrics = {
        template_id: {
            'template_id': template_id,
            'title': question['title'],
            'option_labels': {option['id']: option['label'] for option in question['options']},
            'option_counts': {option['id']: 0 for option in question['options']},
            'total_answers': 0
        } for template_id, question in questions.items()
    }

    field_template_rows = session.query(models.Field.id, models.Field.template_id) \
                                 .filter(models.Field.tid.in_({1, tid}),
                                         models.Field.type.in_(('selectbox', 'multichoice', 'checkbox')),
                                         models.Field.template_id.in_(template_ids)) \
                                 .all()

    field_to_template = {
        str(field_id): str(template_id)
        for field_id, template_id in field_template_rows
    }

    stat_prv_key = _get_user_stat_prv_key(session, tid, user_id, user_cc)
    stat_rows = session.query(models.InternalTipAnswers.stat_answers) \
                       .join(filtered_tips_subquery, filtered_tips_subquery.c.id == models.InternalTipAnswers.internaltip_id) \
                       .all()

    for stat_answers, in stat_rows:
        stat_answers_dict = _decode_stat_answers(stat_answers, stat_prv_key)
        if not stat_answers_dict:
            continue

        for answer_key, answer_value in stat_answers_dict.items():
            if answer_value in (None, ''):
                continue
            answer_key_str = str(answer_key).strip()
            template_id = None
            key_is_field_mapping = False

            if answer_key_str.startswith('template:'):
                template_id = answer_key_str.split('template:', 1)[1]
            elif answer_key_str in field_to_template:
                template_id = field_to_template[answer_key_str]
                key_is_field_mapping = True
            elif answer_key_str in template_metrics:
                template_id = answer_key_str

            if template_id not in template_metrics:
                continue

            template_answer_key = 'template:%s' % template_id
            if key_is_field_mapping and template_answer_key in stat_answers_dict:
                continue

            if answer_key_str == template_id and template_answer_key in stat_answers_dict:
                continue

            metric_data = template_metrics[template_id]

            # checkbox answers carry a list of selected option ids; single-choice
            # answers (selectbox/multichoice) carry a single option id.
            selected_values = answer_value if isinstance(answer_value, list) else [answer_value]
            for selected_value in selected_values:
                if selected_value in (None, ''):
                    continue

                answer_value_key = str(selected_value)
                metric_data['total_answers'] += 1

                if answer_value_key not in metric_data['option_counts']:
                    metric_data['option_counts'][answer_value_key] = 0
                    metric_data['option_labels'][answer_value_key] = answer_value_key

                metric_data['option_counts'][answer_value_key] += 1

    dropdown_metrics = []
    for template_id, metric_data in sorted(template_metrics.items(), key=lambda x: x[1]['title'].lower()):
        total_answers = metric_data['total_answers']
        option_entries = []
        for option_id, count in sorted(metric_data['option_counts'].items(), key=lambda x: x[1], reverse=True):
            option_entries.append({
                'id': option_id,
                'label': metric_data['option_labels'].get(option_id, option_id),
                'count': count,
                'percentage': round((count * 100.0 / total_answers), 1) if total_answers else 0
            })

        dropdown_metrics.append({
            'id': 'question_template_dropdown_%s' % template_id,
            'template_id': template_id,
            'title': metric_data['title'] or template_id,
            'total_answers': total_answers,
            'options': option_entries
        })

    return dropdown_metrics


def _get_filtered_tips_subquery(session, tid, filters):
    filtered_tips_query = session.query(models.InternalTip.id).filter(models.InternalTip.tid == tid)
    filtered_tips_query = apply_filters_to_query(session, filtered_tips_query, filters, tid)
    return filtered_tips_query.subquery()


def _count_filtered_tips(session, tid, filtered_tips_subquery, *extra_conditions):
    query = session.query(func.count(models.InternalTip.id)) \
                   .join(filtered_tips_subquery, filtered_tips_subquery.c.id == models.InternalTip.id) \
                   .filter(models.InternalTip.tid == tid)

    if extra_conditions:
        query = query.filter(*extra_conditions)

    return query.scalar() or 0


def _count_identity_tips(session, tid, filtered_tips_subquery, equals_creation_date):
    creation_date_condition = models.InternalTipData.creation_date == models.InternalTip.creation_date \
        if equals_creation_date else \
        models.InternalTipData.creation_date != models.InternalTip.creation_date

    return session.query(func.count(func.distinct(models.InternalTip.id))) \
                  .join(filtered_tips_subquery, filtered_tips_subquery.c.id == models.InternalTip.id) \
                  .join(models.InternalTipData,
                        and_(models.InternalTipData.internaltip_id == models.InternalTip.id,
                             models.InternalTipData.key == 'whistleblower_identity',
                             creation_date_condition)) \
                  .filter(models.InternalTip.tid == tid) \
                  .scalar() or 0


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


def calculate_time_based_metrics(session, tid, filtered_tips_subquery):
    tip_rows = session.query(
        models.InternalTip.id,
        models.InternalTip.creation_date
    ).join(
        filtered_tips_subquery, filtered_tips_subquery.c.id == models.InternalTip.id
    ).filter(
        models.InternalTip.tid == tid
    ).all()
    if not tip_rows:
        return _empty_time_metrics()

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
        status = _get_status_from_audit_log_data(log_data)
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

        closure_start_date = opened_date or creation_date
        closure_hours = _hours_between(closed_date, closure_start_date)
        if closure_hours is not None:
            closure_times.append(closure_hours)

    avg_opening_time = sum(opening_times) / len(opening_times) if opening_times else 0
    avg_closure_time = sum(closure_times) / len(closure_times) if closure_times else 0

    # The first reply to the whistleblower is the first public content
    # authored by a recipient: a comment or an uploaded file
    first_receiver_comment_rows = session.query(
        models.Comment.internaltip_id,
        func.min(models.Comment.creation_date)
    ).join(
        models.InternalTip, models.Comment.internaltip_id == models.InternalTip.id
    ).join(
        filtered_tips_subquery, filtered_tips_subquery.c.id == models.InternalTip.id
    ).filter(
        and_(
            models.InternalTip.tid == tid,
            models.Comment.author_id.isnot(None),
            models.Comment.visibility == 0
        )
    ).group_by(models.Comment.internaltip_id).all()

    first_receiver_file_rows = session.query(
        models.ReceiverFile.internaltip_id,
        func.min(models.ReceiverFile.creation_date)
    ).join(
        models.InternalTip, models.ReceiverFile.internaltip_id == models.InternalTip.id
    ).join(
        filtered_tips_subquery, filtered_tips_subquery.c.id == models.InternalTip.id
    ).filter(
        and_(
            models.InternalTip.tid == tid,
            models.ReceiverFile.visibility == 0
        )
    ).group_by(models.ReceiverFile.internaltip_id).all()

    first_recipient_reply_by_tip = {}
    for internaltip_id, first_date in first_receiver_comment_rows + first_receiver_file_rows:
        current = first_recipient_reply_by_tip.get(internaltip_id)
        if current is None or first_date < current:
            first_recipient_reply_by_tip[internaltip_id] = first_date

    response_times = []
    for internaltip_id, first_reply_date in first_recipient_reply_by_tip.items():
        hours = _hours_between(first_reply_date, tip_creation_map.get(internaltip_id))
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
        "avg_opening_time_hours": _round_time_metric(avg_opening_time),
        "avg_first_reply_time_hours": _round_time_metric(avg_first_reply_time),
        "avg_closure_time_hours": _round_time_metric(avg_closure_time),
        "avg_exchanges_per_report": round(avg_exchanges_per_tip, 2),
        "total_exchanges": total_exchanges,
        "reports_with_exchanges": num_tips_with_exchanges
    }


def db_get_stats(session, tid, filters=None, language='en', user_id=None, user_cc=None):
    filtered_tips_subquery = _get_filtered_tips_subquery(session, tid, filters)

    reports_count = _count_filtered_tips(session, tid, filtered_tips_subquery)
    num_tips_no_access = _count_filtered_tips(session, tid, filtered_tips_subquery, models.InternalTip.access_count == 0)
    num_tips_mobile = _count_filtered_tips(session, tid, filtered_tips_subquery, models.InternalTip.mobile.is_(True))
    num_tips_tor = _count_filtered_tips(session, tid, filtered_tips_subquery, models.InternalTip.tor.is_(True))

    num_subscribed_tips = _count_identity_tips(session, tid, filtered_tips_subquery, equals_creation_date=True)
    num_initially_anonymous_tips = _count_identity_tips(session, tid, filtered_tips_subquery, equals_creation_date=False)

    num_anonymous_tips = max(0, reports_count - num_subscribed_tips - num_initially_anonymous_tips)
    time_metrics = calculate_time_based_metrics(session, tid, filtered_tips_subquery)

    stats = {
        "reports_count": reports_count,
        "reports_with_no_access": num_tips_no_access,
        "reports_anonymous": num_anonymous_tips,
        "reports_subscribed": num_subscribed_tips,
        "reports_initially_anonymous": num_initially_anonymous_tips,
        "reports_mobile": num_tips_mobile,
        "reports_tor": num_tips_tor
    }

    stats["question_template_dropdown_metrics"] = calculate_dropdown_template_metrics(
        session,
        tid,
        filtered_tips_subquery=filtered_tips_subquery,
        language=language,
        user_id=user_id,
        user_cc=user_cc
    )
    stats.update(time_metrics)
    return stats


@transact
def get_stats(session, tid, filters=None, language='en', user_id=None, user_cc=None):
    return db_get_stats(session, tid, filters, language, user_id, user_cc)


# The template of the platform is designated by a conventional identifier, so
# that it can be recognized wherever it is presented and replaced in the future
DEFAULT_TEMPLATE_ID = 'globaleaks'


def empty_template_data():
    """
    Return the configuration of a template holding no metric: a template is
    """
    return {
        'config': {
            'selectedMetrics': [],
            'selectedCharts': []
        }
    }


def default_template_data():
    """
    Return the configuration of the template a platform starts with: the
    """
    return {
        'config': {
            'selectedMetrics': [
                {'id': 'reports_received', 'title': 'Reports', 'chartType': 'number'}
            ],
            'selectedCharts': [
                {'id': 'returning_whistleblowers', 'title': 'Returning whistleblowers', 'chartType': 'pie'},
                {'id': 'anonymity', 'title': 'Anonymity', 'chartType': 'pie'},
                {'id': 'tor', 'title': 'Tor', 'chartType': 'pie'},
                {'id': 'mobile', 'title': 'Mobile', 'chartType': 'pie'}
            ]
        }
    }


def db_load_default_statistical_template(session):
    """
    Transaction for loading the statistical template of the platform

    :param session: An ORM session
    """
    template = session.query(models.StatisticalReportTemplate) \
                      .filter(models.StatisticalReportTemplate.id == DEFAULT_TEMPLATE_ID) \
                      .one_or_none()

    if template is None:
        template = models.StatisticalReportTemplate({'id': DEFAULT_TEMPLATE_ID, 'tid': DEFAULT_PROFILE_ID})
        session.add(template)

    template.label = 'GlobaLeaks'
    template.data = default_template_data()


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
        return get_stats(
            self.request.tid,
            None,
            self.request.language,
            self.session.user_id,
            self.session.cc
        )

    def post(self):
        filters = _parse_filters(self.request.content.read())
        return get_stats(
            self.request.tid,
            filters,
            self.request.language,
            self.session.user_id,
            self.session.cc
        )


def db_create_statistical_template(session, tid, request):
    request['id'] = uuid4()
    request['tid'] = tid
    request['data'] = request.get('data') or empty_template_data()

    template = models.StatisticalReportTemplate(request)
    session.add(template)
    session.flush()

    return template


def db_statistical_template_tids(session, tid):
    """
    Return the tenants holding the templates a site is presented with: the site

    :param session: An ORM session
    :param tid: A tenant ID
    :return: The tenant IDs the templates are looked up on
    """
    return {DEFAULT_PROFILE_ID, db_get_pid(session, tid) or DEFAULT_PROFILE_ID, tid}


def db_list_statistical_templates(session, tid):
    """
    Return the templates a site is presented with: the template of the platform

    :param session: An ORM session
    :param tid: A tenant ID
    :return: The templates of the site
    """
    templates = session.query(models.StatisticalReportTemplate) \
                       .filter(models.StatisticalReportTemplate.tid.in_(db_statistical_template_tids(session, tid))).all()

    return sorted(templates, key=lambda t: (t.id != DEFAULT_TEMPLATE_ID, t.label.lower()))


def db_get_statistical_template(session, tid, template_id):
    template = session.query(models.StatisticalReportTemplate) \
                      .filter(models.StatisticalReportTemplate.tid.in_(db_statistical_template_tids(session, tid)),
                              models.StatisticalReportTemplate.id == template_id).one_or_none()
    if not template:
        raise errors.ResourceNotFound

    return template


def db_get_own_statistical_template(session, tid, template_id):
    """
    Return a template of the site, the only kind a site writes: the template of

    :param session: An ORM session
    :param tid: A tenant ID
    :param template_id: The ID of the template
    :return: The template the site holds
    """
    template = db_get_statistical_template(session, tid, template_id)

    if template.tid != tid or template.id == DEFAULT_TEMPLATE_ID:
        raise errors.ForbiddenOperation

    return template


def db_get_default_statistical_template(session, tid, templates):
    """
    Return the ID of the template the statistics of a site are presented with:

    :param session: An ORM session
    :param tid: A tenant ID
    :param templates: The templates of the site
    :return: The ID of the template presenting the statistics
    """
    template_id = db_get_config_variable(session, tid, 'default_statistical_template')

    if not any(template.id == template_id for template in templates):
        template_id = DEFAULT_TEMPLATE_ID

    return template_id


def db_update_statistical_template(session, tid, template_id, request):
    template = db_get_own_statistical_template(session, tid, template_id)
    template.update(request)

    return template


def db_delete_statistical_template(session, tid, template_id):
    template = db_get_own_statistical_template(session, tid, template_id)

    # A template a report is built on is kept, or the report would lose its layout
    if session.query(models.StatisticalReport) \
              .filter(models.StatisticalReport.tid == tid,
                      models.StatisticalReport.template_id == template.id).first():
        raise errors.ForbiddenOperation

    session.delete(template)


def db_create_statistical_report(session, tid, request, language='en', user_id=None, user_cc=None):
    request['id'] = uuid4()
    request['tid'] = tid

    # A report is built on a template the site is presented with
    db_get_statistical_template(session, tid, request['template_id'])

    # A report is a frozen snapshot: the statistics are computed once, at
    # creation, and stored so that the view renders the stored values
    data = request.get('data') or {}
    data['snapshot'] = db_get_stats(session, tid, data.get('filters') or None, language, user_id, user_cc)
    request['data'] = data

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


def serialize_statistical_template(template, tid, default_id):
    """
    Serialize a template of the statistics

    :param template: The template to be serialized
    :param tid: The tenant ID the template is presented to
    :param default_id: The ID of the template presenting the statistics
    :return: The serialization of the template
    """
    return {
        'id': template.id,
        'tid': template.tid,
        'label': template.label,
        'creation_date': template.creation_date,
        'editable': template.tid == tid and template.id != DEFAULT_TEMPLATE_ID,
        'default': template.id == default_id,
        'data': template.data if template.data is not None else empty_template_data()
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
    return serialize_statistical_template(template, tid, db_get_config_variable(session, tid, 'default_statistical_template'))


def list_statistical_templates(session, tid):
    templates = db_list_statistical_templates(session, tid)
    default_id = db_get_default_statistical_template(session, tid, templates)
    return [serialize_statistical_template(t, tid, default_id) for t in templates]


def get_statistical_template(session, tid, template_id):
    template = db_get_statistical_template(session, tid, template_id)
    return serialize_statistical_template(template, tid, db_get_config_variable(session, tid, 'default_statistical_template'))


def update_statistical_template(session, tid, template_id, request):
    template = db_update_statistical_template(session, tid, template_id, request)
    return serialize_statistical_template(template, tid, db_get_config_variable(session, tid, 'default_statistical_template'))


def get_metric_catalog(session, tid, language='en'):
    return db_get_metric_catalog(session, tid, language)


def set_default_statistical_template(session, tid, template_id):
    """
    Configure the template the statistics of a site are presented with

    :param session: An ORM session
    :param tid: A tenant ID
    :param template_id: The ID of the template to be presented
    """
    db_get_statistical_template(session, tid, template_id)

    db_set_config_variable(session, tid, 'default_statistical_template', template_id)


def delete_statistical_template(session, tid, template_id):
    return db_delete_statistical_template(session, tid, template_id)


def create_statistical_report(session, tid, request, language='en', user_id=None, user_cc=None):
    report = db_create_statistical_report(session, tid, request, language, user_id, user_cc)
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


class MetricCatalog(BaseHandler):
    # The catalog names the metrics and carries none of their values: it is read
    # by whoever is presented the templates, and says nothing about the reports
    check_roles = {'analyst', 'admin'}

    def get(self):
        return tw(get_metric_catalog, self.request.tid, self.request.language)


class StatisticalReportTemplates(BaseHandler):
    # Composed by the analysts and by the administrators holding the permission
    check_roles = {'analyst', 'admin'}

    require_permission = {'post': 'can_configure_statistical_report_templates'}

    def get(self):
        return tw(list_statistical_templates, self.request.tid)

    @inlineCallbacks
    def post(self):
        request = json.loads(self.request.content.read())
        request = yield self.validate_request(json.dumps(request), requests.AdminStatisticalTemplateDesc)
        res = yield tw(create_statistical_template, self.request.tid, request)
        return res


class StatisticalReportTemplateInstance(BaseHandler):
    check_roles = {'analyst', 'admin'}

    require_permission = {'put': 'can_configure_statistical_report_templates',
                          'delete': 'can_configure_statistical_report_templates'}

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
        res = yield tw(create_statistical_report, self.request.tid, request,
                       self.request.language, self.session.user_id, self.session.cc)
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

