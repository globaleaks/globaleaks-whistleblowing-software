import json

from nacl.encoding import Base64Encoder

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
    'comment_content', 'file_name'
}
ALLOWED_OPERATORS = {'contains', 'in', 'between'}
DATE_FIELDS = {'creation_date', 'update_date', 'expiration_date'}


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


@transact
def get_searchable_content(session, tid, user_session, language, report_ids, fields):
    if not report_ids or len(report_ids) > 100 or not fields or len(fields) > 2 or not set(fields).issubset({'comments', 'files'}):
        raise errors.InputValidationError
    reports = []
    rows = session.query(models.ReceiverTip, models.InternalTip) \
                  .filter(models.ReceiverTip.receiver_id == user_session.user_id,
                          models.ReceiverTip.internaltip_id == models.InternalTip.id,
                          models.InternalTip.tid == tid,
                          models.InternalTip.id.in_(report_ids))

    for recipient_tip, internal_tip in rows:
        report = serializers.serialize_rtip(session, internal_tip, recipient_tip, language)
        redactions = {item['reference_id']: item['temporary_redaction'] for item in report['redactions']}
        can_view_unredacted = user_session.permissions.can_mask_information or user_session.permissions.can_redact_information
        comments = []
        files = []

        try:
            tip_key = None
            if internal_tip.crypto_tip_pub_key:
                tip_key = GCE.asymmetric_decrypt(user_session.cc, Base64Encoder.decode(recipient_tip.crypto_tip_prv_key))
            if 'comments' in fields:
                for comment in report['comments']:
                    content = comment['content']
                    if tip_key and content:
                        content = GCE.asymmetric_decrypt(tip_key, Base64Encoder.decode(content.encode())).decode()
                    if not can_view_unredacted and comment['id'] in redactions:
                        content = redact_content(content, redactions[comment['id']])
                    comments.append(content)

            if 'files' in fields:
                for file in report['wbfiles']:
                    name = file['name']
                    if tip_key and name:
                        name = GCE.asymmetric_decrypt(tip_key, Base64Encoder.decode(name.encode())).decode()
                    files.append(name)
                files.extend(file['name'] for file in report['rfiles'])
        except Exception:
            continue

        reports.append({'id': internal_tip.id, 'comments': comments, 'files': files})

    return reports


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


class SearchableContent(BaseHandler):
    check_roles = 'receiver'

    def post(self):
        request = self.validate_request(self.request.content.read(), requests.SearchableContentDesc)
        return get_searchable_content(self.request.tid, self.session, self.request.language,
                                      request['report_ids'], request['fields'])


class AdminDashboard(BaseHandler):
    check_roles = 'admin'

    def get(self):
        return get_admin_dashboard(self.request.tid)

    def put(self):
        request = self.validate_request(self.request.content.read(), requests.SearchDashboardDesc)
        return set_admin_dashboard(self.request.tid, self.session, request['tabs'])


class SearchExportAudit(BaseHandler):
    check_roles = 'receiver'

    def post(self):
        request = self.validate_request(self.request.content.read(), requests.SearchExportAuditDesc)
        return log_search(self.request.tid, self.session, request, 'export_search_results')
