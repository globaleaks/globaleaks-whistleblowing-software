import json
import unicodedata

from nacl.encoding import Base64Encoder
from sqlalchemy.sql.expression import distinct, func, or_

from globaleaks import models
from globaleaks.handlers.base import BaseHandler
from globaleaks.models import serializers
from globaleaks.orm import db_log, transact
from globaleaks.rest import requests, errors
from globaleaks.utils.crypto import GCE
from globaleaks.utils.utility import is_uuid4, uuid4


ALLOWED_METADATA_FIELDS = {
    'creation_date', 'update_date', 'expiration_date', 'status', 'substatus',
    'context_id', 'score', 'important', 'updated', 'file_count',
    'comment_count', 'receiver_ids', 'subscription', 'searchable_content',
    'comment_content', 'file_name', 'file_type'
}
ALLOWED_OPERATORS = {'contains', 'in', 'between'}
DATE_FIELDS = {'creation_date', 'update_date', 'expiration_date'}
SORT_FIELDS = {
    'important', 'reminder_date', 'progressive', 'context_name', 'label',
    'reportModificationStr', 'submissionStatusStr', 'creation_date',
    'update_date', 'expiration_date', 'receiver_count', 'score'
}
DIRECT_SORT_FIELDS = {
    'important': models.InternalTip.important,
    'reminder_date': models.InternalTip.reminder_date,
    'progressive': models.InternalTip.progressive,
    'creation_date': models.InternalTip.creation_date,
    'update_date': models.InternalTip.update_date,
    'expiration_date': models.InternalTip.expiration_date,
    'score': models.InternalTip.score
}


def validate_tabs(tabs, admin=False):
    if len(tabs) > 50:
        raise errors.InputValidationError
    ids = set()
    for tab in tabs:
        if not isinstance(tab, dict) or 'id' not in tab or not isinstance(tab['id'], str) or not is_uuid4(tab['id']):
            raise errors.InputValidationError
        if tab['id'] in ids:
            raise errors.InputValidationError
        ids.add(tab['id'])
        if 'name' not in tab or not isinstance(tab['name'], str) or not tab['name'].strip() or len(tab['name']) > 255:
            raise errors.InputValidationError
        if 'query' not in tab or not isinstance(tab['query'], dict):
            raise errors.InputValidationError
        query = tab['query']
        if 'negated' not in query or 'filters' not in query or not isinstance(query['negated'], bool) or not isinstance(query['filters'], list):
            raise errors.InputValidationError
        if len(query['filters']) > 30:
            raise errors.InputValidationError
        for item in query['filters']:
            if not isinstance(item, dict) or \
                    not {'operator', 'field', 'negated', 'value'}.issubset(item) or \
                    item['operator'] not in ALLOWED_OPERATORS or \
                    not isinstance(item['field'], str) or \
                    not isinstance(item['negated'], bool):
                raise errors.InputValidationError
            value = item['value']
            if item['operator'] == 'in' and (not isinstance(value, list) or len(value) > 100):
                raise errors.InputValidationError
            if item['operator'] == 'contains' and (not isinstance(value, str) or len(value) > 1000):
                raise errors.InputValidationError
            if item['operator'] == 'between' and (item['field'] not in DATE_FIELDS or not isinstance(value, list) or len(value) != 2 or not all(isinstance(v, (int, float)) for v in value)):
                raise errors.InputValidationError
            if admin and item['field'] not in ALLOWED_METADATA_FIELDS:
                raise errors.ForbiddenOperation


def normalize_tabs(tabs):
    normalized = []
    for position, tab in enumerate(tabs):
        query = tab['query']
        filters = [{
            'id': item['id'],
            'field': item['field'],
            'operator': item['operator'],
            'value': item['value'],
            'label': item['label'] if 'label' in item else item['field'],
            'negated': item['negated']
        } for item in query['filters']]
        normalized.append({
            'id': tab['id'],
            'name': tab['name'].strip(),
            'query': {'negated': query['negated'], 'filters': filters},
            'position': position
        })
    return normalized


def get_default_tabs(session, tid):
    tabs = [{
        'id': tab.id,
        'name': tab.name,
        'query': tab.query,
        'position': tab.position
    } for tab in session.query(models.SearchDashboardTab)
                        .filter(models.SearchDashboardTab.tid == tid,
                                models.SearchDashboardTab.user_id.is_(None))
                        .order_by(models.SearchDashboardTab.position)]
    return normalize_tabs(tabs)


def assign_tab_ids(session, tid, user_id, tabs):
    supplied_ids = [tab['id'] for tab in tabs if isinstance(tab, dict) and 'id' in tab and tab['id']]
    rows = session.query(models.SearchDashboardTab).filter(models.SearchDashboardTab.id.in_(supplied_ids)) if supplied_ids else []
    existing = {row.id for row in rows if row.tid == tid and row.user_id == user_id}
    if any(row.tid != tid or row.user_id != user_id for row in rows):
        raise errors.ForbiddenOperation
    for tab in tabs:
        if not isinstance(tab, dict):
            continue
        if 'id' not in tab or tab['id'] not in existing:
            tab['id'] = uuid4()
        if 'query' not in tab or \
                not isinstance(tab['query'], dict) or \
                'filters' not in tab['query'] or \
                not isinstance(tab['query']['filters'], list):
            continue
        for item in tab['query']['filters']:
            if isinstance(item, dict) and ('id' not in item or not item['id']):
                item['id'] = uuid4()


@transact
def get_recipient_dashboard(session, tid, user_session):
    defaults = get_default_tabs(session, tid)

    personal = []
    rows = session.query(models.SearchDashboardTab) \
                  .filter(models.SearchDashboardTab.tid == tid,
                          models.SearchDashboardTab.user_id == user_session.user_id) \
                  .order_by(models.SearchDashboardTab.position)
    for row in rows:
        try:
            plaintext = GCE.asymmetric_decrypt(user_session.cc, Base64Encoder.decode(row.encrypted_data.encode()))
            tab = json.loads(plaintext.decode())
            if isinstance(tab, list):
                personal.extend(normalize_tabs(tab))
            else:
                tab.update({'id': row.id, 'position': row.position})
                normalized = normalize_tabs([tab])[0]
                normalized['position'] = row.position
                personal.append(normalized)
        except Exception:
            continue
    return {'defaults': defaults, 'personal': personal}


def redact_content(content, ranges):
    result = list(content)
    for item in sorted(ranges, key=lambda value: value['start']):
        start = item.get('start', 0)
        end = item.get('end', 0) + 1
        if start < end:
            result[start:end] = '\u2591' * (end - start)
    return ''.join(result)


def normalize_search_value(value):
    value = '' if value is None else value
    return ''.join(character for character in unicodedata.normalize('NFD', str(value)).lower().strip()
                   if unicodedata.category(character) != 'Mn')


def validate_search_query(query):
    if not isinstance(query, dict) or \
            not isinstance(query.get('negated'), bool) or \
            not isinstance(query.get('filters'), list) or \
            len(query['filters']) > 30:
        raise errors.InputValidationError
    ids = set()
    for item in query['filters']:
        if not isinstance(item, dict) or not {'id', 'field', 'operator', 'value', 'negated'}.issubset(item) or \
                not isinstance(item['id'], str) or not item['id'] or item['id'] in ids or \
                item['field'] not in ALLOWED_METADATA_FIELDS or \
                item['operator'] not in ALLOWED_OPERATORS or \
                not isinstance(item['negated'], bool):
            raise errors.InputValidationError
        ids.add(item['id'])
        if item['operator'] == 'contains' and (not isinstance(item['value'], str) or len(item['value']) > 1000):
            raise errors.InputValidationError
        if item['operator'] == 'in' and (not isinstance(item['value'], list) or len(item['value']) > 100 or
                                         not all(isinstance(value, (str, int, float, bool)) for value in item['value'])):
            raise errors.InputValidationError
        if item['operator'] == 'between' and (item['field'] not in DATE_FIELDS or
                                               not isinstance(item['value'], list) or
                                               len(item['value']) != 2 or
                                               not all(isinstance(value, (int, float)) for value in item['value'])):
            raise errors.InputValidationError


def flatten_search_values(value):
    if isinstance(value, dict):
        return [item for nested in value.values() for item in flatten_search_values(nested)]
    if isinstance(value, (list, tuple, set)):
        return [item for nested in value for item in flatten_search_values(nested)]
    return [value]


def filter_matches(value, item):
    candidates = flatten_search_values(value)
    if item['operator'] == 'between':
        start, end = item['value']
        return any(hasattr(candidate, 'timestamp') and start <= candidate.timestamp() * 1000 <= end
                   for candidate in candidates)
    if item['operator'] == 'contains':
        term = normalize_search_value(item['value'])
        return any(term in normalize_search_value(candidate) for candidate in candidates)
    accepted = {normalize_search_value(value) for value in item['value']}
    return any(normalize_search_value(candidate) in accepted for candidate in candidates)


def answered_content(fields, answers):
    content = []
    for field in fields:
        values = answers.get(field.get('id'))
        if values:
            content.extend([field.get('label', ''), values])
            selected = {normalize_search_value(value) for value in flatten_search_values(values)}
            content.extend(option.get('label', '') for option in field.get('options', [])
                           if normalize_search_value(option.get('id')) in selected)
        content.extend(answered_content(field.get('children', []), answers))
    return content


def file_types(files):
    extensions = []
    for name in files:
        name = str(name).strip()
        if '.' not in name:
            continue
        extension = name.rsplit('.', 1)[1].lower()
        if extension:
            extensions.append(extension)
    return extensions


def localized_value(item, field, language):
    return models.get_localized_values({}, item, [field], language)[field]


def batches(values, size=500):
    for index in range(0, len(values), size):
        yield values[index:index + size]


def get_search_metadata(session, tid, language, reports, fields):
    report_ids = list(reports)
    receiver_ids = {}
    receiver_names = {}
    contexts = {}
    status_labels = {}
    substatus_labels = {}
    comment_counts = {}
    file_counts = {}
    subscriptions = {report_id: 0 for report_id in report_ids}

    if fields & {'context_id', 'searchable_content'}:
        context_ids = {itip.context_id for _, itip in reports.values()}
        contexts = {context.id: localized_value(context, 'name', language)
                    for context in session.query(models.Context)
                                          .filter(models.Context.tid == tid,
                                                  models.Context.id.in_(context_ids))}
    if fields & {'status', 'substatus', 'searchable_content'}:
        status_labels = {status.id: localized_value(status, 'label', language)
                         for status in session.query(models.SubmissionStatus)
                                              .filter(models.SubmissionStatus.tid == tid)}
        substatus_labels = {substatus.id: localized_value(substatus, 'label', language)
                            for substatus in session.query(models.SubmissionSubStatus)
                                                    .filter(models.SubmissionSubStatus.tid == tid)}
    if fields & {'receiver_ids', 'searchable_content'}:
        for report_ids_batch in batches(report_ids):
            for report_id, receiver_id in session.query(models.ReceiverTip.internaltip_id,
                                                        models.ReceiverTip.receiver_id) \
                                                 .filter(models.ReceiverTip.internaltip_id.in_(report_ids_batch)):
                receiver_ids.setdefault(report_id, []).append(receiver_id)
        user_ids = {user_id for values in receiver_ids.values() for user_id in values}
        for user_ids_batch in batches(list(user_ids)):
            receiver_names.update({user.id: user.name for user in session.query(models.User)
                                                                .filter(models.User.id.in_(user_ids_batch))})
    if 'comment_count' in fields:
        for report_ids_batch in batches(report_ids):
            comment_counts.update(dict(session.query(models.Comment.internaltip_id,
                                                     func.count(distinct(models.Comment.id)))
                                              .filter(models.Comment.internaltip_id.in_(report_ids_batch),
                                                      models.Comment.visibility == 0)
                                              .group_by(models.Comment.internaltip_id)))
    if 'file_count' in fields:
        for report_ids_batch in batches(report_ids):
            file_counts.update(dict(session.query(models.InternalFile.internaltip_id,
                                                  func.count(distinct(models.InternalFile.id)))
                                           .filter(models.InternalFile.internaltip_id.in_(report_ids_batch))
                                           .group_by(models.InternalFile.internaltip_id)))
    if 'subscription' in fields:
        creation_dates = {report_id: itip.creation_date for report_id, (_, itip) in reports.items()}
        for report_ids_batch in batches(report_ids):
            for data in session.query(models.InternalTipData) \
                               .filter(models.InternalTipData.internaltip_id.in_(report_ids_batch),
                                       models.InternalTipData.key == 'whistleblower_identity'):
                subscriptions[data.internaltip_id] = 1 if data.creation_date == creation_dates[data.internaltip_id] else 2

    return contexts, status_labels, substatus_labels, receiver_ids, receiver_names, comment_counts, file_counts, subscriptions


def get_report_content(session, user_session, language, recipient_tip, internal_tip):
    comments = []
    files = []
    answers = []
    label = internal_tip.label
    if recipient_tip.receiver_id != user_session.user_id:
        return label if not internal_tip.crypto_tip_pub_key else '', comments, files, answers

    report = serializers.serialize_rtip(session, internal_tip, recipient_tip, language)
    redactions = {item['reference_id']: item['temporary_redaction'] for item in report['redactions']}
    can_view_unredacted = user_session.permissions.can_mask_information or user_session.permissions.can_redact_information
    tip_key = None
    if internal_tip.crypto_tip_pub_key:
        tip_key = GCE.asymmetric_decrypt(user_session.cc, Base64Encoder.decode(recipient_tip.crypto_tip_prv_key))
        if label:
            label = GCE.asymmetric_decrypt(tip_key, Base64Encoder.decode(label.encode())).decode()

    for comment in report['comments']:
        content = comment['content']
        if tip_key and content:
            content = GCE.asymmetric_decrypt(tip_key, Base64Encoder.decode(content.encode())).decode()
        if not can_view_unredacted and comment['id'] in redactions:
            content = redact_content(content, redactions[comment['id']])
        comments.append(content)

    for file in report['wbfiles']:
        name = file['name']
        if tip_key and name:
            name = GCE.asymmetric_decrypt(tip_key, Base64Encoder.decode(name.encode())).decode()
        files.append(name)
    files.extend(file['name'] for file in report['rfiles'])

    for questionnaire in report['questionnaires']:
        questionnaire_answers = questionnaire['answers']
        if tip_key and questionnaire_answers:
            questionnaire_answers = json.loads(
                GCE.asymmetric_decrypt(tip_key, Base64Encoder.decode(questionnaire_answers.encode())).decode()
            )
        if isinstance(questionnaire_answers, dict):
            for step in questionnaire['steps']:
                answers.extend(answered_content(step.get('children', []), questionnaire_answers))

    return label, comments, files, answers


def sort_value(value):
    if value is None:
        return 0, ''
    if hasattr(value, 'timestamp'):
        return 1, value.timestamp()
    if isinstance(value, str):
        return 1, normalize_search_value(value)
    return 1, value


@transact
def get_search_suggestions(session, tid, language, request):
    field = request['field']
    operator = request['operator']
    value = request['value'].strip()
    if field not in ALLOWED_METADATA_FIELDS or operator not in {'contains', 'in'} or len(value) < 4 or len(value) > 1000:
        raise errors.InputValidationError
    if field in {'searchable_content', 'comment_content', 'file_name', 'file_type'}:
        return {'suggestions': [], 'exists': False, 'verifiable': False}

    candidates = []
    if field in {'status', 'substatus'}:
        statuses = session.query(models.SubmissionStatus).filter(models.SubmissionStatus.tid == tid)
        substatuses = session.query(models.SubmissionSubStatus).filter(models.SubmissionSubStatus.tid == tid)
        if field == 'status':
            candidates.extend(item for status in statuses for item in (status.id, localized_value(status, 'label', language)))
        else:
            candidates.extend(item for substatus in substatuses
                              for item in (substatus.id, localized_value(substatus, 'label', language)))
    elif field == 'context_id':
        candidates.extend(item for context in session.query(models.Context).filter(models.Context.tid == tid)
                          for item in (context.id, localized_value(context, 'name', language)))
    elif field == 'receiver_ids':
        candidates.extend(item for user in session.query(models.User).filter(models.User.tid == tid,
                                                                              models.User.role == 'receiver',
                                                                              models.User.enabled == True)
                          for item in (user.id, user.name))
    elif field == 'score':
        candidates.extend(['0', '1', '2', '3', 'None', 'Low', 'Medium', 'High'])
    elif field == 'important':
        candidates.extend(['true', 'false'])
    elif field == 'updated':
        candidates.extend(['true', 'false', 'new', 'updated'])
    elif field == 'subscription':
        candidates.extend(['0', '1', '2', 'Not subscribed', 'Subscribed', 'Subscription updated'])
    elif field in {'file_count', 'comment_count'}:
        model = models.InternalFile if field == 'file_count' else models.Comment
        count_query = session.query(func.count(distinct(model.id))) \
                             .filter(model.internaltip_id == models.InternalTip.id,
                                     models.InternalTip.tid == tid)
        if field == 'comment_count':
            count_query = count_query.filter(models.Comment.visibility == 0)
        candidates.extend(str(count) for count, in count_query.group_by(models.InternalTip.id))

    normalized_value = normalize_search_value(value)
    suggestions = sorted({str(candidate) for candidate in candidates
                          if normalized_value in normalize_search_value(candidate)})[:10]
    exists = bool(suggestions) if operator == 'contains' else any(
        normalize_search_value(candidate) == normalized_value for candidate in candidates
    )
    return {'suggestions': suggestions, 'exists': exists, 'verifiable': True}


@transact
def search_reports(session, tid, user_session, language, request):
    page = request['page']
    page_size = request['page_size']
    if page < 1 or page_size < 1 or page_size > 100 or len(request['search']) > 1000 or \
            request['sort'] not in SORT_FIELDS:
        raise errors.InputValidationError
    query = request['query']
    validate_search_query(query)
    receiver_contexts = [context_id for context_id, in session.query(models.Context.id)
                                                           .join(models.ReceiverContext,
                                                                 models.Context.id == models.ReceiverContext.context_id)
                                                           .filter(models.Context.allow_recipients_selection == False,
                                                                   models.ReceiverContext.receiver_id == user_session.user_id)]
    if not query['filters'] and not query['negated'] and not request['search'] and not request['unread'] and \
            request['sort'] in DIRECT_SORT_FIELDS:
        sort_column = DIRECT_SORT_FIELDS[request['sort']]
        authorized_reports = session.query(models.InternalTip.id) \
                                    .filter(models.ReceiverTip.internaltip_id == models.InternalTip.id,
                                            models.InternalTip.tid == tid,
                                            or_(models.ReceiverTip.receiver_id == user_session.user_id,
                                                models.InternalTip.context_id.in_(receiver_contexts))) \
                                    .distinct()
        total = authorized_reports.count()
        order = sort_column.desc() if request['descending'] else sort_column.asc()
        id_order = models.InternalTip.id.desc() if request['descending'] else models.InternalTip.id.asc()
        offset = (page - 1) * page_size
        return {
            'report_ids': [report_id for report_id, in authorized_reports.order_by(order, id_order)
                                                                         .offset(offset)
                                                                         .limit(page_size)],
            'page': page,
            'page_size': page_size,
            'total': total
        }
    rows = session.query(models.ReceiverTip, models.InternalTip) \
                  .filter(models.ReceiverTip.internaltip_id == models.InternalTip.id,
                          models.InternalTip.tid == tid,
                          or_(models.ReceiverTip.receiver_id == user_session.user_id,
                              models.InternalTip.context_id.in_(receiver_contexts)))
    reports = {}
    for recipient_tip, internal_tip in rows:
        if internal_tip.id not in reports or recipient_tip.receiver_id == user_session.user_id:
            reports[internal_tip.id] = recipient_tip, internal_tip
    fields = {item['field'] for item in query['filters']}
    if request['search']:
        fields.update(ALLOWED_METADATA_FIELDS)
    if request['sort'] == 'context_name':
        fields.add('context_id')
    elif request['sort'] == 'submissionStatusStr':
        fields.add('status')
    elif request['sort'] == 'receiver_count':
        fields.add('receiver_ids')
    contexts, status_labels, substatus_labels, receiver_ids, receiver_names, comment_counts, file_counts, subscriptions = \
        get_search_metadata(session, tid, language, reports, fields)
    needs_content = any(item['field'] in {'searchable_content', 'comment_content', 'file_name', 'file_type'}
                        for item in query['filters']) or bool(request['search']) or request['sort'] == 'label'
    matching_reports = []

    for report_id, (recipient_tip, internal_tip) in reports.items():
        updated = recipient_tip.last_access < internal_tip.update_date
        status_text = status_labels.get(internal_tip.status, '')
        substatus_text = substatus_labels.get(internal_tip.substatus, '')
        if substatus_text:
            status_text += ' – ' + substatus_text
        report_modification = 'New' if internal_tip.status == 'new' else 'Updated' if not updated else ''
        assigned_ids = receiver_ids.get(report_id, [])
        assigned_names = [receiver_names.get(receiver_id, '') for receiver_id in assigned_ids]
        label, comments, files, answers = internal_tip.label, [], [], []
        try:
            if needs_content:
                label, comments, files, answers = get_report_content(
                    session, user_session, language, recipient_tip, internal_tip
                )
        except Exception:
            label, comments, files, answers = '', [], [], []

        score_labels = {0: 'None', 1: 'Low', 2: 'Medium', 3: 'High'}
        values = {
            'creation_date': internal_tip.creation_date,
            'update_date': internal_tip.update_date,
            'expiration_date': internal_tip.expiration_date,
            'status': [internal_tip.status, status_text],
            'substatus': [internal_tip.substatus, substatus_text],
            'context_id': [internal_tip.context_id, contexts.get(internal_tip.context_id, '')],
            'score': [internal_tip.score, score_labels.get(internal_tip.score, '')],
            'important': internal_tip.important,
            'updated': [updated, report_modification,
                        'new' if internal_tip.status == 'new' else 'updated' if not updated else ''],
            'file_count': file_counts.get(report_id, 0),
            'comment_count': comment_counts.get(report_id, 0),
            'receiver_ids': [assigned_ids, assigned_names],
            'subscription': [subscriptions[report_id],
                             ['Not subscribed', 'Subscribed', 'Subscription updated'][subscriptions[report_id]]],
            'comment_content': comments,
            'file_name': files,
            'file_type': file_types(files)
        }
        values['searchable_content'] = [internal_tip.progressive, label,
                                        contexts.get(internal_tip.context_id, ''), status_text,
                                        assigned_names, answers, comments, files]
        matches_all = all(not filter_matches(values[item['field']], item) if item['negated']
                          else filter_matches(values[item['field']], item)
                          for item in query['filters'])
        if query['negated'] == matches_all or request['unread'] and not updated:
            continue
        if request['search'] and not filter_matches(list(values.values()), {
                'operator': 'contains', 'value': request['search']}):
            continue
        sort_values = {
            'important': internal_tip.important,
            'reminder_date': internal_tip.reminder_date,
            'progressive': internal_tip.progressive,
            'context_name': contexts.get(internal_tip.context_id, ''),
            'label': label,
            'reportModificationStr': report_modification,
            'submissionStatusStr': status_text,
            'creation_date': internal_tip.creation_date,
            'update_date': internal_tip.update_date,
            'expiration_date': internal_tip.expiration_date,
            'receiver_count': len(assigned_ids),
            'score': internal_tip.score
        }
        matching_reports.append((report_id, sort_value(sort_values[request['sort']])))

    matching_reports.sort(key=lambda item: (item[1], item[0]), reverse=request['descending'])
    total = len(matching_reports)
    offset = (page - 1) * page_size
    return {
        'report_ids': [report_id for report_id, _ in matching_reports[offset:offset + page_size]],
        'page': page,
        'page_size': page_size,
        'total': total
    }


@transact
def set_recipient_dashboard(session, tid, user_session, tabs):
    user = session.query(models.User).filter(models.User.tid == tid, models.User.id == user_session.user_id).one()
    if not user.crypto_pub_key:
        raise errors.ForbiddenOperation
    assign_tab_ids(session, tid, user.id, tabs)
    validate_tabs(tabs)
    tabs = normalize_tabs(tabs)
    session.query(models.SearchDashboardTab) \
           .filter(models.SearchDashboardTab.tid == tid,
                   models.SearchDashboardTab.user_id == user.id) \
           .delete(synchronize_session=False)

    for position, tab in enumerate(tabs):
        encrypted_data = Base64Encoder.encode(
            GCE.asymmetric_encrypt(user.crypto_pub_key, json.dumps(tab).encode())
        ).decode()
        session.add(models.SearchDashboardTab({
            'id': tab['id'],
            'tid': tid,
            'user_id': user.id,
            'encrypted_data': encrypted_data,
            'position': position
        }))

    return {'defaults': get_default_tabs(session, tid), 'personal': tabs}


@transact
def get_admin_dashboard(session, tid):
    return {'tabs': get_default_tabs(session, tid)}


@transact
def set_admin_dashboard(session, tid, user_session, tabs):
    assign_tab_ids(session, tid, None, tabs)
    validate_tabs(tabs, admin=True)
    tabs = normalize_tabs(tabs)
    session.query(models.SearchDashboardTab) \
           .filter(models.SearchDashboardTab.tid == tid,
                   models.SearchDashboardTab.user_id.is_(None)) \
           .delete(synchronize_session=False)
    for position, tab in enumerate(tabs):
        session.add(models.SearchDashboardTab({
            'id': tab['id'],
            'tid': tid,
            'name': tab['name'],
            'query': tab['query'],
            'position': position
        }))
    db_log(session, tid=tid, type='update_search_dashboard', user_id=user_session.user_id,
           data={'tabs': len(tabs)})
    return {'tabs': tabs}


@transact
def log_search(session, tid, user_session, request, event_type):
    db_log(session, tid=tid, type=event_type, user_id=user_session.user_id,
           data={'filter_types': request['filter_types'], 'result_count': request['result_count']})


class RecipientDashboard(BaseHandler):
    check_roles = 'receiver'

    def get(self):
        return get_recipient_dashboard(self.request.tid, self.session)

    def put(self):
        request = self.validate_request(self.request.content.read(), requests.SearchDashboardDesc)
        return set_recipient_dashboard(self.request.tid, self.session, request['tabs'])


class RecipientSearchSuggestions(BaseHandler):
    check_roles = 'receiver'

    def post(self):
        request = self.validate_request(self.request.content.read(), requests.SearchDashboardSuggestionDesc)
        if request['field'] not in {'searchable_content', 'comment_content', 'file_name', 'file_type'}:
            return get_search_suggestions(self.request.tid, self.request.language, request)
        value = request['value'].strip()
        minimum_length = 1 if request['field'] == 'file_type' else 4
        if len(value) < minimum_length or len(value) > 1000 or request['operator'] not in {'contains', 'in'}:
            raise errors.InputValidationError
        result = search_reports(self.request.tid, self.session, self.request.language, {
            'page': 1,
            'page_size': 1,
            'search': '',
            'unread': False,
            'sort': 'creation_date',
            'descending': True,
            'query': {
                'negated': False,
                'filters': [{
                    'id': 'suggestion',
                    'field': request['field'],
                    'operator': request['operator'],
                    'value': [value] if request['operator'] == 'in' else value,
                    'negated': False
                }]
            }
        })
        result.addCallback(lambda page: {
            'suggestions': [value] if page['total'] else [],
            'exists': page['total'] > 0,
            'verifiable': True
        })
        return result


class AdminDashboard(BaseHandler):
    check_roles = 'admin'

    def get(self):
        return get_admin_dashboard(self.request.tid)

    def put(self):
        request = self.validate_request(self.request.content.read(), requests.SearchDashboardDesc)
        return set_admin_dashboard(self.request.tid, self.session, request['tabs'])


class AdminSearchSuggestions(BaseHandler):
    check_roles = 'admin'

    def post(self):
        request = self.validate_request(self.request.content.read(), requests.SearchDashboardSuggestionDesc)
        return get_search_suggestions(self.request.tid, self.request.language, request)


class SearchExportAudit(BaseHandler):
    check_roles = 'receiver'

    def post(self):
        request = self.validate_request(self.request.content.read(), requests.SearchExportAuditDesc)
        return log_search(self.request.tid, self.session, request, 'export_search_results')
