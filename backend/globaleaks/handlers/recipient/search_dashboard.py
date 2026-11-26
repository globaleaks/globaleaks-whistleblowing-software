import json
import unicodedata

from datetime import timedelta

from nacl.encoding import Base64Encoder
from sqlalchemy.orm import aliased
from sqlalchemy.sql.expression import and_, distinct, func, or_
from twisted.internet.defer import inlineCallbacks

from globaleaks import models
from globaleaks.handlers.base import BaseHandler
from globaleaks.handlers.recipient.rtip import redact_report as db_redact_report
from globaleaks.handlers.whistleblower.submission import decrypt_tip, index_answers
from globaleaks.models import serializers
from globaleaks.orm import db_log, transact
from globaleaks.rest import requests, errors
from globaleaks.utils.crypto import GCE
from globaleaks.utils.log import log
from globaleaks.utils.utility import datetime_now, is_uuid4, uuid4


ALLOWED_METADATA_FIELDS = {
    'creation_date', 'update_date', 'expiration_date', 'status', 'substatus',
    'context_id', 'score', 'important', 'updated', 'file_count',
    'comment_count', 'receiver_ids', 'subscription', 'searchable_content',
    'comment_content', 'file_name', 'file_type'
}
ALLOWED_OPERATORS = {'contains', 'in', 'between', 'last_days'}
CONTENT_FIELDS = {'searchable_content', 'comment_content', 'file_name', 'file_type'}
DATE_FIELDS = {'creation_date', 'update_date', 'expiration_date'}
LAST_DAYS_VALUES = {10, 20}
MASK = chr(0x2591)
PAGE_SIZE = 20
SCORE_LABELS = {0: 'None', 1: 'Low', 2: 'Medium', 3: 'High'}
SUBSCRIPTION_LABELS = ['Not subscribed', 'Subscribed', 'Subscription updated']
SORT_FIELDS = {
    'important', 'reminder_date', 'progressive', 'context_name', 'label',
    'reportModificationStr', 'submissionStatusStr', 'channel_progressive_sort_key', 'creation_date',
    'update_date', 'expiration_date', 'receiver_count', 'score', 'subscription', 'lastUpdateRead'
}


def validate_filter(item):
    if not isinstance(item, dict) or \
            not {'id', 'field', 'operator', 'value', 'negated'}.issubset(item) or \
            not isinstance(item['id'], str) or not item['id'] or \
            not isinstance(item['field'], str) or item['field'] not in ALLOWED_METADATA_FIELDS or \
            not isinstance(item['operator'], str) or item['operator'] not in ALLOWED_OPERATORS or \
            not isinstance(item['negated'], bool):
        raise errors.InputValidationError

    operator, value = item['operator'], item['value']
    if operator == 'contains' and (not isinstance(value, str) or len(value) > 1000):
        raise errors.InputValidationError
    if operator == 'in' and (not isinstance(value, list) or len(value) > 100 or
                             not all(isinstance(v, (str, int, float, bool)) for v in value)):
        raise errors.InputValidationError
    if operator == 'between' and (item['field'] not in DATE_FIELDS or
                                  not isinstance(value, list) or len(value) != 2 or
                                  not all(isinstance(v, (int, float)) for v in value)):
        raise errors.InputValidationError
    if operator == 'last_days' and (item['field'] not in DATE_FIELDS or
                                    type(value) is not int or value not in LAST_DAYS_VALUES):
        raise errors.InputValidationError


def validate_search_query(query):
    if not isinstance(query, dict) or \
            not isinstance(query.get('negated'), bool) or \
            not isinstance(query.get('filters'), list) or \
            len(query['filters']) > 30:
        raise errors.InputValidationError

    ids = set()
    for item in query['filters']:
        validate_filter(item)
        if item['id'] in ids:
            raise errors.InputValidationError
        ids.add(item['id'])


def validate_tabs(tabs):
    if len(tabs) > 50:
        raise errors.InputValidationError

    ids = set()
    for tab in tabs:
        if not isinstance(tab, dict) or \
                not isinstance(tab.get('id'), str) or not is_uuid4(tab['id']) or tab['id'] in ids or \
                not isinstance(tab.get('name'), str) or not tab['name'].strip() or len(tab['name']) > 255:
            raise errors.InputValidationError
        ids.add(tab['id'])
        validate_search_query(tab.get('query'))


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
    rows = session.query(models.SearchDashboardTab) \
                  .filter(models.SearchDashboardTab.id.in_(supplied_ids)).all() if supplied_ids else []
    if any(row.tid != tid or row.user_id != user_id for row in rows):
        raise errors.ForbiddenOperation
    existing = {row.id for row in rows}
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
        if row.encrypted_data:
            try:
                plaintext = GCE.asymmetric_decrypt(user_session.cc, Base64Encoder.decode(row.encrypted_data.encode()))
                tab = json.loads(plaintext.decode())
            except Exception:
                log.err('Unable to decrypt a personal search dashboard tab')
                continue
        else:
            tab = {'name': row.name, 'query': row.query}

        tab['id'] = row.id
        normalized = normalize_tabs([tab])[0]
        normalized['position'] = row.position
        personal.append(normalized)

    return {'defaults': defaults, 'personal': personal}


def normalize_search_value(value):
    value = '' if value is None else str(value).lower().strip()
    if value.isascii():
        return value
    return ''.join(character for character in unicodedata.normalize('NFD', value)
                   if unicodedata.category(character) != 'Mn')


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
    if item['operator'] == 'last_days':
        start = datetime_now().replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=item['value'] - 1)
        return any(hasattr(candidate, 'timestamp') and candidate >= start for candidate in candidates)
    if item['operator'] == 'contains':
        term = normalize_search_value(item['value'])
        return any(term in normalize_search_value(candidate) for candidate in candidates)
    accepted = {normalize_search_value(value) for value in item['value']}
    return any(normalize_search_value(candidate) in accepted for candidate in candidates)


def selected_option_labels(fields, answers):
    labels = []
    for field in fields:
        values = answers.get(field.get('id'))
        if values and field.get('options') and not contains_masking_placeholder(values):
            selected = {str(value) for value in flatten_search_values(values)}
            labels.extend(option.get('label', '') for option in field['options']
                          if str(option.get('id')) in selected)
        labels.extend(selected_option_labels(field.get('children', []), answers))
    return labels


def listed_answer_values(answers):
    if isinstance(answers, dict):
        if 'value' in answers:
            return flatten_search_values(unmasked_text(answers['value']))
        return [value for key, nested in answers.items() if key != 'index'
                for value in listed_answer_values(nested)]
    if isinstance(answers, (list, tuple, set)):
        return [value for nested in answers for value in listed_answer_values(nested)]
    return [unmasked_text(answers)]


def unmasked_text(value):
    if isinstance(value, str):
        return value.replace(MASK, ' ')
    if isinstance(value, dict):
        return {key: unmasked_text(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [unmasked_text(item) for item in value]
    return value


def contains_masking_placeholder(value):
    if isinstance(value, str):
        return MASK in value
    if isinstance(value, dict):
        return any(contains_masking_placeholder(item) for item in value.values())
    if isinstance(value, (list, tuple, set)):
        return any(contains_masking_placeholder(item) for item in value)
    return False


def file_types(files):
    extensions = []
    for filename in files:
        name = str(filename).strip()
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


def get_search_metadata(session, tid, language, fields, listed_reports):
    report_ids = [report['id'] for report in listed_reports]
    status_labels = {}
    substatus_labels = {}
    receiver_names = {}
    comment_counts = {}
    file_counts = {}

    if fields & {'status', 'substatus', 'searchable_content'}:
        status_labels = {status.id: localized_value(status, 'label', language)
                         for status in session.query(models.SubmissionStatus)
                                              .filter(models.SubmissionStatus.tid == tid)}
        substatus_labels = {substatus.id: localized_value(substatus, 'label', language)
                            for substatus in session.query(models.SubmissionSubStatus)
                                                    .filter(models.SubmissionSubStatus.tid == tid)}
    if fields & {'receiver_ids', 'searchable_content'}:
        user_ids = list({user_id for report in listed_reports for user_id in report['receiver_ids']})
        for user_ids_batch in batches(user_ids):
            receiver_names.update(session.query(models.User.id, models.User.name)
                                         .filter(models.User.id.in_(user_ids_batch)))
    if 'comment_count' in fields:
        for report_ids_batch in batches(report_ids):
            comment_counts.update(session.query(models.Comment.internaltip_id,
                                                func.count(distinct(models.Comment.id)))
                                         .filter(models.Comment.internaltip_id.in_(report_ids_batch),
                                                 models.Comment.visibility == 'public')
                                         .group_by(models.Comment.internaltip_id))
    if 'file_count' in fields:
        for report_ids_batch in batches(report_ids):
            file_counts.update(session.query(models.InternalFile.internaltip_id,
                                             func.count(distinct(models.InternalFile.id)))
                                      .filter(models.InternalFile.internaltip_id.in_(report_ids_batch))
                                      .group_by(models.InternalFile.internaltip_id))

    return status_labels, substatus_labels, receiver_names, comment_counts, file_counts


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
    if field in CONTENT_FIELDS:
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
            count_query = count_query.filter(models.Comment.visibility == 'public')
        candidates.extend(str(count) for count, in count_query.group_by(models.InternalTip.id))

    normalized_value = normalize_search_value(value)
    suggestions = sorted({str(candidate) for candidate in candidates
                          if normalized_value in normalize_search_value(candidate)})[:10]
    exists = bool(suggestions) if operator == 'contains' else any(
        normalize_search_value(candidate) == normalized_value for candidate in candidates
    )
    return {'suggestions': suggestions, 'exists': exists, 'verifiable': True}


def decrypt_text(tip_key, value):
    if tip_key is None or not value:
        return value
    return GCE.asymmetric_decrypt(tip_key, Base64Encoder.decode(value.encode())).decode()


def readable(values):
    return [unmasked_text(value) for value in values]


def empty_content():
    return {'comments': [], 'files': [], 'answers': [], 'identity': []}


def questionnaire_text(steps, answers):
    if not isinstance(answers, dict):
        return []
    text = listed_answer_values(answers)
    for step in steps:
        text.extend(selected_option_labels(step.get('children', []), answers))
    return text


def visible_to(model, author, user_id, tid):
    return or_(model.visibility == 'public',
               and_(model.visibility == 'personal', model.author_id == user_id),
               and_(model.visibility == 'internal', or_(model.author_id == user_id, author.tid == tid)))


def db_get_serialized_content(session, user_session, language, rtip, itip):
    report = serializers.serialize_rtip(session, itip, rtip, language)
    if itip.crypto_tip_pub_key:
        report = decrypt_tip(user_session.cc, Base64Encoder.decode(rtip.crypto_tip_prv_key), report)
    else:
        for questionnaire in report['questionnaires']:
            if isinstance(questionnaire['answers'], dict):
                index_answers(questionnaire['answers'])

    report = db_redact_report.method(session, user_session, report, enforce=True)

    content = empty_content()
    content['comments'] = readable(comment['content'] for comment in report['comments'])
    content['files'] = readable(file['name'] for file in report['wbfiles'] + report['rfiles'] if not file.get('masked'))
    for questionnaire in report['questionnaires']:
        content['answers'].extend(questionnaire_text(questionnaire['steps'], questionnaire['answers']))
    identity = report.get('data', {}).get('whistleblower_identity')
    if isinstance(identity, dict):
        content['identity'] = flatten_search_values(unmasked_text(identity))
    return content


def db_get_batched_content(session, tid, user_session, language, itips, rtips):
    report_ids = [itip.id for itip in itips]
    contents = {report_id: empty_content() for report_id in report_ids}
    if not report_ids:
        return contents

    user_id = user_session.user_id
    tip_keys = {itip.id: GCE.asymmetric_decrypt(user_session.cc, Base64Encoder.decode(rtips[itip.id].crypto_tip_prv_key))
                for itip in itips if itip.crypto_tip_pub_key}

    replies = {}
    for report_id, reply in session.query(models.IdentityAccessRequest.internaltip_id,
                                          models.IdentityAccessRequest.reply) \
                                   .filter(models.IdentityAccessRequest.internaltip_id.in_(report_ids)) \
                                   .order_by(models.IdentityAccessRequest.request_date):
        replies[report_id] = reply
    identity_granted = {report_id for report_id, reply in replies.items() if reply not in ('denied', 'pending')}

    answers_rows = session.query(models.InternalTipAnswers.internaltip_id,
                                 models.InternalTipAnswers.questionnaire_hash,
                                 models.InternalTipAnswers.answers) \
                          .filter(models.InternalTipAnswers.internaltip_id.in_(report_ids)) \
                          .order_by(models.InternalTipAnswers.creation_date).all()
    schemas = {schema.hash: serializers.serialize_archived_questionnaire_schema(schema.schema, language)
               for schema in session.query(models.ArchivedSchema)
                                    .filter(models.ArchivedSchema.hash.in_({row[1] for row in answers_rows}))}

    questionnaires = {}
    for report_id, schema_hash, answers in answers_rows:
        if schema_hash not in schemas:
            continue
        if report_id in tip_keys:
            answers = json.loads(decrypt_text(tip_keys[report_id], answers))
        questionnaires.setdefault(report_id, []).append({'steps': schemas[schema_hash]})
        contents[report_id]['answers'].extend(questionnaire_text(schemas[schema_hash], answers))

    denied_files = {report_id: {'1'} if report_id in identity_granted else
                    set(serializers.get_identity_files(questionnaires.get(report_id, [])))
                    for report_id in report_ids}

    for report_id, identity in session.query(models.InternalTipData.internaltip_id,
                                             models.InternalTipData.value) \
                                      .filter(models.InternalTipData.internaltip_id.in_(report_ids),
                                              models.InternalTipData.key == 'whistleblower_identity'):
        if report_id not in identity_granted or not identity:
            continue
        if report_id in tip_keys:
            identity = json.loads(decrypt_text(tip_keys[report_id], identity))
        if isinstance(identity, list):
            identity = identity[0]
        if isinstance(identity, dict):
            contents[report_id]['identity'] = flatten_search_values(unmasked_text(identity))

    author = aliased(models.User)
    for report_id, text in session.query(models.Comment.internaltip_id, models.Comment.content) \
                                  .outerjoin(author, author.id == models.Comment.author_id) \
                                  .filter(models.Comment.internaltip_id.in_(report_ids),
                                          visible_to(models.Comment, author, user_id, tid)):
        contents[report_id]['comments'].extend(readable([decrypt_text(tip_keys.get(report_id), text)]))

    for report_id, name in session.query(models.ReceiverFile.internaltip_id, models.ReceiverFile.name) \
                                  .outerjoin(author, author.id == models.ReceiverFile.author_id) \
                                  .filter(models.ReceiverFile.internaltip_id.in_(report_ids),
                                          visible_to(models.ReceiverFile, author, user_id, tid)):
        contents[report_id]['files'].extend(readable([decrypt_text(tip_keys.get(report_id), name)]))

    rtip_ids = [rtips[report_id].id for report_id in report_ids]
    for report_id, name, reference_id in session.query(models.InternalFile.internaltip_id,
                                                       models.InternalFile.name,
                                                       models.InternalFile.reference_id) \
                                                .join(models.WhistleblowerFile,
                                                      models.WhistleblowerFile.internalfile_id == models.InternalFile.id) \
                                                .filter(models.WhistleblowerFile.receivertip_id.in_(rtip_ids)):
        if (reference_id or '')[:36] not in denied_files[report_id]:
            contents[report_id]['files'].extend(readable([decrypt_text(tip_keys.get(report_id), name)]))

    return contents


def db_get_search_content(session, tid, user_session, language, report_ids):
    itips = {itip.id: itip for itip in session.query(models.InternalTip)
                                              .filter(models.InternalTip.id.in_(report_ids))}
    rtips = {rtip.internaltip_id: rtip for rtip in session.query(models.ReceiverTip)
                                                          .filter(models.ReceiverTip.internaltip_id.in_(report_ids),
                                                                  models.ReceiverTip.receiver_id == user_session.user_id)}
    redacted = {report_id for report_id, in session.query(models.Redaction.internaltip_id)
                                                   .filter(models.Redaction.internaltip_id.in_(report_ids))}

    contents = {}
    batched = []
    for report_id in report_ids:
        itip, rtip = itips.get(report_id), rtips.get(report_id)
        if itip is None or rtip is None or (itip.crypto_tip_pub_key and not rtip.crypto_tip_prv_key):
            contents[report_id] = empty_content()
        elif report_id in redacted:
            contents[report_id] = db_get_serialized_content(session, user_session, language, rtip, itip)
        else:
            batched.append(itip)

    contents.update(db_get_batched_content(session, tid, user_session, language, batched, rtips))
    return contents


def report_values(report, metadata):
    status_labels, substatus_labels, receiver_names, comment_counts, file_counts = metadata
    status_text = status_labels.get(report['status'], '')
    substatus_text = substatus_labels.get(report['substatus'], '')
    if substatus_text:
        status_text += ' – ' + substatus_text
    if report['type'] == 'request' and (report['allow_transmission'] or report['status'] == 'closed'):
        status_text = 'Authorized' if report['allow_transmission'] else 'Denied'
    assigned_names = [receiver_names.get(receiver_id, '') for receiver_id in report['receiver_ids']]
    modification = 'new' if report['status'] == 'new' else 'updated' if report['updated'] else ''

    return {
        'creation_date': report['creation_date'],
        'update_date': report['update_date'],
        'expiration_date': report['expiration_date'],
        'status': [report['status'], status_text],
        'substatus': [report['substatus'], substatus_text],
        'context_id': [report['context_id'], report['context_name']],
        'score': [report['score'], SCORE_LABELS.get(report['score'], '')],
        'important': report['important'],
        'updated': [report['updated'], modification],
        'file_count': file_counts.get(report['id'], 0),
        'comment_count': comment_counts.get(report['id'], 0),
        'receiver_ids': [report['receiver_ids'], assigned_names],
        'subscription': [report['subscription'], SUBSCRIPTION_LABELS[report['subscription']]],
        'comment_content': [],
        'file_name': [],
        'file_type': [],
        'searchable_content': [report['channel_progressive'], report['label'], report['context_name'],
                               status_text, assigned_names]
    }


def add_content(values, content):
    values['comment_content'] = content['comments']
    values['file_name'] = content['files']
    values['file_type'] = file_types(content['files'])
    values['searchable_content'] = values['searchable_content'] + \
        [content['answers'], content['identity'], content['comments'], content['files']]


def matches_all(values, filters):
    included = {}
    for item in filters:
        matched = filter_matches(values[item['field']], item)
        if item['negated']:
            if matched:
                return False
        else:
            included[item['field']] = included.get(item['field'], False) or matched
    return all(included.values())


def report_sort_value(report, values, field):
    if field == 'submissionStatusStr':
        return sort_value(values['status'][1])
    if field == 'reportModificationStr':
        return sort_value(values['updated'][1])
    if field == 'lastUpdateRead':
        return sort_value(report['last_access'] >= report['update_date'])
    return sort_value(report[field])


def db_matching_reports(session, tid, user_session, language, query, search='', unread=False, sort=None):
    from globaleaks.handlers.recipient import db_get_receivertips  # noqa: PLC0415

    search = {'operator': 'contains', 'value': search} if search else None
    fields = {item['field'] for item in query['filters']}
    if search:
        fields.add('searchable_content')
    if sort == 'submissionStatusStr':
        fields.add('status')

    reports = db_get_receivertips(session, tid, user_session, language, include_answers=False)
    if unread:
        reports = [report for report in reports if report['updated']]

    metadata = get_search_metadata(session, tid, language, fields, reports)
    metadata_filters = [item for item in query['filters'] if item['field'] not in CONTENT_FIELDS]
    content_filters = [item for item in query['filters'] if item['field'] in CONTENT_FIELDS]

    candidates = []
    for report in reports:
        values = report_values(report, metadata)
        metadata_match = matches_all(values, metadata_filters)
        if metadata_match or query['negated']:
            needs_content = (content_filters and metadata_match) or \
                (search and not filter_matches(values['searchable_content'], search))
            candidates.append((report, values, metadata_match, needs_content))

    for batch in batches(candidates, 100):
        content_ids = [report['id'] for report, _, _, needs_content in batch if needs_content]
        contents = db_get_search_content(session, tid, user_session, language, content_ids) if content_ids else {}
        for report, values, metadata_match, _ in batch:
            if report['id'] in contents:
                add_content(values, contents[report['id']])
            if query['negated'] == (metadata_match and matches_all(values, content_filters)):
                continue
            if search and not filter_matches(values['searchable_content'], search):
                continue
            yield report, values


@transact
def search_reports(session, tid, user_session, language, request):
    if request['page'] < 1 or len(request['search']) > 1000 or request['sort'] not in SORT_FIELDS:
        raise errors.InputValidationError
    validate_search_query(request['query'])

    matching = [(report, report_sort_value(report, values, request['sort']))
                for report, values in db_matching_reports(session, tid, user_session, language, request['query'],
                                                           request['search'], request['unread'], request['sort'])]
    matching.sort(key=lambda item: (item[1], item[0]['id']), reverse=request['descending'])
    reports = [report for report, _ in matching]
    total = len(reports)

    if not request['paginate']:
        return {'reports': reports, 'page': 1, 'total': total}

    page = min(request['page'], max(1, -(-total // PAGE_SIZE)))
    offset = (page - 1) * PAGE_SIZE
    return {'reports': reports[offset:offset + PAGE_SIZE], 'page': page, 'total': total}


@transact
def content_value_exists(session, tid, user_session, language, field, operator, value):
    query = {'negated': False, 'filters': [{
        'id': 'suggestion',
        'field': field,
        'operator': operator,
        'value': [value] if operator == 'in' else value,
        'negated': False
    }]}
    return next(db_matching_reports(session, tid, user_session, language, query), None) is not None


@transact
def set_recipient_dashboard(session, tid, user_session, tabs):
    user = session.query(models.User).filter(models.User.tid == tid, models.User.id == user_session.user_id).one()
    assign_tab_ids(session, tid, user.id, tabs)
    validate_tabs(tabs)
    tabs = normalize_tabs(tabs)
    session.query(models.SearchDashboardTab) \
           .filter(models.SearchDashboardTab.tid == tid,
                   models.SearchDashboardTab.user_id == user.id) \
           .delete(synchronize_session=False)

    for position, tab in enumerate(tabs):
        row = {'id': tab['id'], 'tid': tid, 'user_id': user.id, 'position': position}
        if user.crypto_pub_key:
            row['encrypted_data'] = Base64Encoder.encode(
                GCE.asymmetric_encrypt(user.crypto_pub_key, json.dumps(tab).encode())
            ).decode()
        else:
            row['name'] = tab['name']
            row['query'] = tab['query']
        session.add(models.SearchDashboardTab(row))

    return {'defaults': get_default_tabs(session, tid), 'personal': tabs}


@transact
def get_admin_dashboard(session, tid):
    return {'tabs': get_default_tabs(session, tid)}


@transact
def set_admin_dashboard(session, tid, user_session, tabs):
    assign_tab_ids(session, tid, None, tabs)
    validate_tabs(tabs)
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

    @inlineCallbacks
    def post(self):
        request = self.validate_request(self.request.content.read(), requests.SearchDashboardSuggestionDesc)
        if request['field'] not in CONTENT_FIELDS:
            return (yield get_search_suggestions(self.request.tid, self.request.language, request))

        value = request['value'].strip()
        minimum_length = 1 if request['field'] == 'file_type' else 4
        if len(value) < minimum_length or len(value) > 1000 or request['operator'] not in {'contains', 'in'}:
            raise errors.InputValidationError

        exists = yield content_value_exists(self.request.tid, self.session, self.request.language,
                                            request['field'], request['operator'], value)
        return {'suggestions': [value] if exists else [], 'exists': exists, 'verifiable': True}


class AdminDashboard(BaseHandler):
    check_roles = 'admin'
    require_permission = 'can_manage_case_management'

    def get(self):
        return get_admin_dashboard(self.request.tid)

    def put(self):
        request = self.validate_request(self.request.content.read(), requests.SearchDashboardDesc)
        return set_admin_dashboard(self.request.tid, self.session, request['tabs'])


class AdminSearchSuggestions(BaseHandler):
    check_roles = 'admin'
    require_permission = 'can_manage_case_management'

    def post(self):
        request = self.validate_request(self.request.content.read(), requests.SearchDashboardSuggestionDesc)
        return get_search_suggestions(self.request.tid, self.request.language, request)


class SearchExportAudit(BaseHandler):
    check_roles = 'receiver'

    def post(self):
        request = self.validate_request(self.request.content.read(), requests.SearchExportAuditDesc)
        return log_search(self.request.tid, self.session, request, 'export_search_results')
