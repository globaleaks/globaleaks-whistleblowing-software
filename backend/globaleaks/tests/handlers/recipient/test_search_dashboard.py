import json

from datetime import timedelta

from nacl.encoding import Base64Encoder
from twisted.internet.defer import inlineCallbacks, maybeDeferred

from globaleaks import models
from globaleaks.db import seeding
from globaleaks.handlers.public import serialize_questionnaire
from globaleaks.handlers.recipient import TipsCollection
from globaleaks.handlers.recipient.search_dashboard import AdminDashboard, AdminSearchSuggestions, \
    RecipientDashboard, RecipientSearchSuggestions, SearchExportAudit, SORT_FIELDS, \
    db_get_batched_content, db_get_serialized_content
from globaleaks.orm import transact
from globaleaks.rest import errors
from globaleaks.tests import helpers
from globaleaks.utils.crypto import GCE
from globaleaks.utils.utility import datetime_now


FAR_FUTURE = 32503680000000


def stored(itip, text):
    if not itip.crypto_tip_pub_key:
        return text
    return Base64Encoder.encode(GCE.asymmetric_encrypt(itip.crypto_tip_pub_key, text.encode())).decode()


def answer_entries(answers):
    for field_id, entries in answers.items():
        if not isinstance(entries, list):
            continue
        for entry in entries:
            if isinstance(entry, dict):
                yield field_id, entry
                yield from answer_entries(entry)


@transact
def add_comment(session, report_id, author_id, text, visibility='public'):
    itip = session.get(models.InternalTip, report_id)
    comment = models.Comment()
    comment.internaltip_id = report_id
    comment.author_id = author_id
    comment.content = stored(itip, text)
    comment.visibility = visibility
    session.add(comment)
    session.flush()
    return comment.id


@transact
def add_receiver_file(session, report_id, author_id, name, visibility='public'):
    itip = session.get(models.InternalTip, report_id)
    rfile = models.ReceiverFile()
    rfile.internaltip_id = report_id
    rfile.author_id = author_id
    rfile.name = stored(itip, name)
    rfile.content_type = stored(itip, 'application/octet-stream')
    rfile.size = 0
    rfile.visibility = visibility
    session.add(rfile)
    session.flush()
    return rfile.id


@transact
def add_whistleblower_file(session, report_id, user_id, name):
    itip = session.get(models.InternalTip, report_id)
    rtip = session.query(models.ReceiverTip).filter_by(internaltip_id=report_id, receiver_id=user_id).one()
    ifile = models.InternalFile()
    ifile.internaltip_id = report_id
    ifile.tid = itip.tid
    ifile.name = stored(itip, name)
    ifile.reference_id = ''
    session.add(ifile)
    session.flush()
    wbfile = models.WhistleblowerFile()
    wbfile.internalfile_id = ifile.id
    wbfile.receivertip_id = rtip.id
    session.add(wbfile)


@transact
def set_identity(session, report_id, user_id, identity, replies):
    itip = session.get(models.InternalTip, report_id)
    value = stored(itip, json.dumps(identity)) if itip.crypto_tip_pub_key else identity
    data = session.query(models.InternalTipData).filter_by(internaltip_id=report_id,
                                                          key='whistleblower_identity').one_or_none()
    if data is None:
        data = models.InternalTipData()
        data.internaltip_id = report_id
        data.key = 'whistleblower_identity'
        session.add(data)
    data.value = value

    session.query(models.IdentityAccessRequest).filter_by(internaltip_id=report_id).delete()
    for position, reply in enumerate(replies):
        iar = models.IdentityAccessRequest()
        iar.internaltip_id = report_id
        iar.request_user_id = user_id
        iar.request_date = datetime_now() + timedelta(seconds=position)
        iar.reply = reply
        session.add(iar)


@transact
def remove_user_key(session, user_id):
    session.query(models.User).filter(models.User.id == user_id).update({'crypto_pub_key': ''})


@transact
def get_personal_tab_rows(session, user_id):
    return [(row.name, bool(row.encrypted_data)) for row in session.query(models.SearchDashboardTab)
                                                                   .filter(models.SearchDashboardTab.user_id == user_id)]


@transact
def get_audit_types(session, user_id):
    return [row.type for row in session.query(models.AuditLog).filter(models.AuditLog.user_id == user_id)]


@transact
def compare_content(session, user_session):
    rtips = {rtip.internaltip_id: rtip for rtip in session.query(models.ReceiverTip)
                                                          .filter(models.ReceiverTip.receiver_id == user_session.user_id)}
    itips = session.query(models.InternalTip).filter(models.InternalTip.id.in_(rtips)).all()
    batched = db_get_batched_content(session, 1, user_session, 'en', itips, rtips)

    def normalized(content):
        return {key: sorted(map(str, values)) for key, values in content.items()}

    return [(normalized(batched[itip.id]),
             normalized(db_get_serialized_content(session, user_session, 'en', rtips[itip.id], itip)))
            for itip in itips]


@transact
def get_seed_target(session, receiver_id):
    context = session.query(models.Context).filter(models.Context.tid == 1).first()
    questionnaire = session.query(models.Questionnaire).filter_by(id=context.questionnaire_id).one()
    schema = serialize_questionnaire(session, 1, questionnaire, None)
    file_field_id = next((field['id'] for step in schema['steps'] for field in step['children']
                          if field['type'] == 'fileupload'), 'none')
    return [(1, receiver_id, context.id, context.questionnaire_id, file_field_id)]


def search_filter(field, operator, value, negated=False):
    return {'id': f'{field}-{operator}-{json.dumps(value)}-{negated}', 'field': field,
            'operator': operator, 'value': value, 'negated': negated}


def tab(name, filters=None, negated=False, tab_id=''):
    return {'id': tab_id, 'name': name, 'query': {'negated': negated, 'filters': filters or []}, 'position': 0}


def ids(result):
    return {report['id'] for report in result['reports']}


class SearchTestMixin:
    def search(self, filters=None, search='', page=1, sort='creation_date', descending=True,
               unread=False, negated=False, paginate=True, user_id=None, body=None):
        request = body or {
            'page': page,
            'search': search,
            'unread': unread,
            'sort': sort,
            'descending': descending,
            'query': {'negated': negated, 'filters': filters or []},
            'paginate': paginate
        }
        handler = self.request(body=json.dumps(request), user_id=user_id or self.dummy_receiver_1['id'],
                               role='receiver', handler_cls=TipsCollection)
        return maybeDeferred(handler.post)

    def search_all(self, filters=None, **kwargs):
        return self.search(filters, paginate=False, **kwargs)

    def suggest(self, field, operator, value, role='receiver', permissions=None):
        handler_cls = RecipientSearchSuggestions if role == 'receiver' else AdminSearchSuggestions
        user_id = self.dummy_receiver_1['id'] if role == 'receiver' else self.dummy_admin['id']
        handler = self.request(body=json.dumps({'field': field, 'operator': operator, 'value': value}),
                               user_id=user_id, role=role, handler_cls=handler_cls, permissions=permissions)
        return maybeDeferred(handler.post)

    def recipient_tabs(self, method, tabs=None, user_id=None):
        body = json.dumps({'tabs': tabs}) if tabs is not None else ''
        handler = self.request(body=body, user_id=user_id or self.dummy_receiver_1['id'],
                               role='receiver', handler_cls=RecipientDashboard)
        return maybeDeferred(getattr(handler, method))

    def admin_tabs(self, method, tabs=None, permissions=None):
        body = json.dumps({'tabs': tabs}) if tabs is not None else ''
        handler = self.request(body=body, user_id=self.dummy_admin['id'], role='admin',
                               handler_cls=AdminDashboard,
                               permissions=permissions or {'can_manage_case_management': True})
        return maybeDeferred(getattr(handler, method))

    @inlineCallbacks
    def listed(self, user_id=None):
        handler = self.request(user_id=user_id or self.dummy_receiver_1['id'], role='receiver',
                               handler_cls=TipsCollection)
        return (yield handler.get())

    @inlineCallbacks
    def accessible_report(self):
        listed = yield self.listed()
        return next(report for report in listed if report['accessible'])


class TestSearchDashboard(SearchTestMixin, helpers.TestHandlerWithPopulatedDB):
    _handler = TipsCollection

    @inlineCallbacks
    def setUp(self):
        yield super().setUp()
        yield self.perform_full_submission_actions()

    @inlineCallbacks
    def test_search_returns_the_reports_of_the_listing(self):
        listed = yield self.listed()
        result = yield self.search_all()
        self.assertEqual(result['total'], len(listed))
        expected = {report['id']: report for report in listed}
        for report in result['reports']:
            self.assertEqual({**report, 'answers': None}, {**expected[report['id']], 'answers': None})

    @inlineCallbacks
    def test_pages_are_bounded(self):
        everything = yield self.search_all()
        result = yield self.search(page=999)
        self.assertEqual(result['page'], max(1, -(-everything['total'] // 20)))
        self.assertLessEqual(len(result['reports']), 20)
        self.assertEqual(result['total'], everything['total'])

        unpaginated = yield self.search(page=3, paginate=False)
        self.assertEqual(unpaginated['page'], 1)
        self.assertEqual(ids(unpaginated), ids(everything))

    @inlineCallbacks
    def test_every_sort_field_orders_both_ways(self):
        for field in SORT_FIELDS:
            ascending = yield self.search_all(sort=field, descending=False)
            descending = yield self.search_all(sort=field, descending=True)
            self.assertEqual([report['id'] for report in ascending['reports']],
                             [report['id'] for report in reversed(descending['reports'])], field)

    @inlineCallbacks
    def test_unread_only(self):
        listed = yield self.listed()
        result = yield self.search_all(unread=True)
        self.assertEqual(ids(result), {report['id'] for report in listed if report['updated']})

    @inlineCallbacks
    def test_invalid_requests_are_refused(self):
        valid = {'page': 1, 'search': '', 'unread': False, 'sort': 'creation_date', 'descending': True,
                 'query': {'negated': False, 'filters': []}, 'paginate': True}

        def request(**changes):
            return {**valid, **changes}

        def query(*filters):
            return request(query={'negated': False, 'filters': list(filters)})

        invalid = [
            request(page=0),
            request(sort='id'),
            request(search='x' * 1001),
            request(paginate='yes'),
            request(query={'filters': []}),
            query(search_filter('id', 'in', ['x'])),
            query(search_filter('status', 'equals', ['new'])),
            query(search_filter('status', 'in', 'new')),
            query(search_filter('status', 'in', [{'nested': 'value'}])),
            query(search_filter('status', 'in', ['new'] * 101)),
            query(search_filter('status', 'contains', ['new'])),
            query(search_filter('comment_content', 'contains', 'x' * 1001)),
            query(search_filter('status', 'between', [0, 1])),
            query(search_filter('creation_date', 'between', [0])),
            query(search_filter('creation_date', 'between', ['a', 'b'])),
            query(search_filter('creation_date', 'last_days', 15)),
            query(search_filter('creation_date', 'last_days', True)),
            query(search_filter('status', 'last_days', 10)),
            query({**search_filter('status', 'in', ['new']), 'negated': 'no'}),
            query({**search_filter('status', 'in', ['new']), 'id': ''}),
            query(search_filter('status', 'in', ['new']), search_filter('status', 'in', ['new'])),
            query(*[{**search_filter('status', 'in', ['new']), 'id': str(i)} for i in range(31)]),
        ]
        for body in invalid:
            yield self.assertFailure(self.search(body=body), errors.InputValidationError)

    @inlineCallbacks
    def test_filters_on_the_same_field_match_any_value(self):
        new = yield self.search_all([search_filter('status', 'in', ['new'])])
        self.assertGreater(new['total'], 0)

        either = yield self.search_all([search_filter('status', 'in', ['new']),
                                        search_filter('status', 'in', ['not-a-real-status'])])
        self.assertEqual(ids(either), ids(new))

        merged = yield self.search_all([search_filter('status', 'in', ['new', 'not-a-real-status'])])
        self.assertEqual(ids(merged), ids(new))

    @inlineCallbacks
    def test_negated_filters_exclude_each_value(self):
        everything = yield self.search_all()
        new = yield self.search_all([search_filter('status', 'in', ['new'])])
        excluded = yield self.search_all([search_filter('status', 'in', ['new'], True),
                                          search_filter('status', 'in', ['not-a-real-status'], True)])
        self.assertEqual(ids(excluded), ids(everything) - ids(new))

    @inlineCallbacks
    def test_filters_on_different_fields_must_all_match(self):
        report = yield self.accessible_report()
        new = yield self.search_all([search_filter('status', 'in', ['new'])])
        channel = yield self.search_all([search_filter('context_id', 'in', [report['context_id']])])
        both = yield self.search_all([search_filter('status', 'in', ['new']),
                                      search_filter('context_id', 'in', [report['context_id']])])
        self.assertEqual(ids(both), ids(new) & ids(channel))

        none = yield self.search_all([search_filter('status', 'in', ['new']),
                                      search_filter('context_id', 'in', ['not-a-channel'])])
        self.assertEqual(none['total'], 0)

    @inlineCallbacks
    def test_negated_query_is_the_complement(self):
        everything = yield self.search_all()
        filters = [search_filter('status', 'in', ['new']), search_filter('important', 'in', [False])]
        matching = yield self.search_all(filters)
        complement = yield self.search_all(filters, negated=True)
        self.assertEqual(ids(complement), ids(everything) - ids(matching))

    @inlineCallbacks
    def test_date_filters(self):
        everything = yield self.search_all()
        for field in ('creation_date', 'update_date'):
            whole = yield self.search_all([search_filter(field, 'between', [0, FAR_FUTURE])])
            self.assertEqual(ids(whole), ids(everything))

            past = yield self.search_all([search_filter(field, 'between', [0, 1000])])
            self.assertEqual(past['total'], 0)

            recent = yield self.search_all([search_filter(field, 'last_days', 10)])
            self.assertEqual(ids(recent), ids(everything))

            older = yield self.search_all([search_filter(field, 'last_days', 10, True)])
            self.assertEqual(older['total'], 0)

    @inlineCallbacks
    def test_text_matching_ignores_case_and_accents(self):
        report = yield self.accessible_report()
        yield add_comment(report['id'], self.dummy_receiver_1['id'], 'Résumé of the Ünïcode evidence')
        for term in ('resume of the unicode', 'RÉSUMÉ', 'ünïcode EVIDENCE'):
            result = yield self.search_all([search_filter('comment_content', 'contains', term)])
            self.assertIn(report['id'], ids(result), term)
            result = yield self.search_all(search=term)
            self.assertIn(report['id'], ids(result), term)

    @inlineCallbacks
    def test_comment_file_and_file_type_filters(self):
        report = yield self.accessible_report()
        receiver_id = self.dummy_receiver_1['id']
        yield add_comment(report['id'], receiver_id, 'Payment approved without the second signature')
        yield add_receiver_file(report['id'], receiver_id, 'Ledger-2024.XLSX')
        yield add_whistleblower_file(report['id'], receiver_id, 'scanned-contract.odt')

        for filters in ([search_filter('comment_content', 'contains', 'second signature')],
                        [search_filter('file_name', 'contains', 'ledger-2024')],
                        [search_filter('file_name', 'contains', 'scanned-contract')],
                        [search_filter('file_type', 'in', ['xlsx'])],
                        [search_filter('file_type', 'in', ['odt', 'not-a-type'])],
                        [search_filter('searchable_content', 'contains', 'second signature')]):
            result = yield self.search_all(filters)
            self.assertEqual(ids(result), {report['id']}, filters)

        excluded = yield self.search_all([search_filter('file_type', 'in', ['xlsx'], True)])
        self.assertNotIn(report['id'], ids(excluded))

    @inlineCallbacks
    def test_free_text_searches_only_readable_content(self):
        report = yield self.accessible_report()
        yield add_comment(report['id'], self.dummy_receiver_1['id'], 'Searchable remark about procurement')

        for term in (report['context_id'], report['id'], self.dummy_receiver_1['id']):
            result = yield self.search_all(search=term)
            self.assertEqual(result['total'], 0, term)

        for term in (report['context_name'], 'remark about procurement'):
            result = yield self.search_all(search=term)
            self.assertIn(report['id'], ids(result), term)

    @inlineCallbacks
    def test_free_text_and_filters_combine(self):
        report = yield self.accessible_report()
        yield add_comment(report['id'], self.dummy_receiver_1['id'], 'Combined criteria marker')
        matching = yield self.search_all([search_filter('context_id', 'in', [report['context_id']])],
                                         search='criteria marker')
        self.assertEqual(ids(matching), {report['id']})
        excluded = yield self.search_all([search_filter('context_id', 'in', ['not-a-channel'])],
                                         search='criteria marker')
        self.assertEqual(excluded['total'], 0)

    @inlineCallbacks
    def test_content_of_other_recipients_follows_its_visibility(self):
        report = yield self.accessible_report()
        other_id = self.dummy_receiver_2['id']
        yield add_comment(report['id'], other_id, 'Note kept personal by the colleague', 'personal')
        yield add_comment(report['id'], other_id, 'Note shared internally by the colleague', 'internal')
        yield add_receiver_file(report['id'], other_id, 'colleague-private.pdf', 'personal')
        yield add_comment(report['id'], self.dummy_receiver_1['id'], 'Note kept personal by myself', 'personal')

        for term, found in (('kept personal by the colleague', False),
                            ('colleague-private', False),
                            ('shared internally by the colleague', True),
                            ('kept personal by myself', True)):
            result = yield self.search_all(search=term)
            self.assertEqual(report['id'] in ids(result), found, term)

    @inlineCallbacks
    def test_masked_comment_is_not_searchable(self):
        receiver_id = self.dummy_receiver_1['id']
        report = yield self.accessible_report()
        text = 'visible introduction CONFIDENTIALNAME visible conclusion'
        comment_id = yield add_comment(report['id'], receiver_id, text)
        start = text.index('CONFIDENTIALNAME')
        yield self.add_redaction(report['id'], comment_id, [{'start': start, 'end': start + len('CONFIDENTIALNAME')}])

        for privileged in (True, False):
            yield self.set_redaction_privileges(receiver_id, privileged)
            for term, found in (('CONFIDENTIALNAME', False), ('visible introduction', True), (chr(0x2591), False)):
                by_filter = yield self.search_all([search_filter('comment_content', 'contains', term)])
                by_text = yield self.search_all(search=term)
                self.assertEqual(report['id'] in ids(by_filter), found, (privileged, term))
                self.assertEqual(report['id'] in ids(by_text), found, (privileged, term))

    @inlineCallbacks
    def test_masked_file_is_not_searchable(self):
        receiver_id = self.dummy_receiver_1['id']
        report = yield self.accessible_report()
        file_id = yield add_receiver_file(report['id'], receiver_id, 'MASKEDFILENAME.pdf')
        yield self.add_redaction(report['id'], file_id, [])

        for privileged in (True, False):
            yield self.set_redaction_privileges(receiver_id, privileged)
            result = yield self.search_all([search_filter('file_name', 'contains', 'maskedfilename')])
            self.assertNotIn(report['id'], ids(result))

    @inlineCallbacks
    def test_masked_answer_is_not_searchable(self):
        receiver_id = self.dummy_receiver_1['id']
        listed = yield self.listed()
        report, entry = next((report, entry) for report in listed if isinstance(report['answers'], dict)
                             for _, entry in answer_entries(report['answers'])
                             if isinstance(entry.get('value'), str) and len(entry['value']) >= 30)
        redacted_value = entry['value']
        for listed_report in listed:
            for field_id, answer_entry in answer_entries(listed_report['answers']):
                value = answer_entry.get('value', '')
                start = value.find(redacted_value) if isinstance(value, str) else -1
                if start >= 0:
                    yield self.add_redaction(listed_report['id'], field_id,
                                             [{'start': start, 'end': start + len(redacted_value)}],
                                             answer_entry['index'])

        for privileged in (True, False):
            yield self.set_redaction_privileges(receiver_id, privileged)
            result = yield self.search_all([search_filter('searchable_content', 'contains', redacted_value)])
            self.assertNotIn(report['id'], ids(result))
            result = yield self.search_all(search=redacted_value)
            self.assertNotIn(report['id'], ids(result))

    @inlineCallbacks
    def test_identity_is_searchable_only_once_access_is_granted(self):
        receiver_id = self.dummy_receiver_1['id']
        report = yield self.accessible_report()
        identity = {'name': [{'value': 'Whistleblowername Identityexample'}]}

        for replies, found in (([], False),
                               (['pending'], False),
                               (['denied'], False),
                               (['authorized'], True),
                               (['authorized', 'pending'], False),
                               (['denied', 'authorized'], True)):
            yield set_identity(report['id'], receiver_id, identity, replies)
            result = yield self.search_all(search='whistleblowername identityexample')
            self.assertEqual(report['id'] in ids(result), found, replies)

    @inlineCallbacks
    def test_batched_content_matches_the_report(self):
        receiver_id = self.dummy_receiver_1['id']
        other_id = self.dummy_receiver_2['id']
        listed = yield self.listed()
        accessible = [report for report in listed if report['accessible']]
        for report in accessible:
            for author_id, visibility in ((other_id, 'personal'), (other_id, 'internal'),
                                          (other_id, 'public'), (receiver_id, 'personal')):
                yield add_comment(report['id'], author_id, f'note {visibility} {author_id[:8]}', visibility)
                yield add_receiver_file(report['id'], author_id, f'{visibility}-{author_id[:8]}.pdf', visibility)
            yield add_whistleblower_file(report['id'], receiver_id, 'evidence.docx')
        yield set_identity(accessible[0]['id'], receiver_id, {'name': [{'value': 'Granted identity'}]},
                           ['authorized'])

        handler = self.request(user_id=receiver_id, role='receiver')
        compared = yield compare_content(handler.session)
        self.assertEqual(len(compared), len(accessible))
        for batched, serialized in compared:
            self.assertEqual(batched, serialized)
            self.assertIn('evidence.docx', batched['files'])
            self.assertIn(f'note internal {other_id[:8]}', batched['comments'])
            self.assertIn(f'note personal {receiver_id[:8]}', batched['comments'])
            self.assertNotIn(f'note personal {other_id[:8]}', batched['comments'])
        self.assertTrue(any('Granted identity' in batched['identity'] for batched, _ in compared))

    @inlineCallbacks
    def test_content_suggestions(self):
        report = yield self.accessible_report()
        yield add_comment(report['id'], self.dummy_receiver_1['id'], 'Suggestion target sentence')
        yield add_receiver_file(report['id'], self.dummy_receiver_1['id'], 'suggested.xlsx')

        result = yield self.suggest('comment_content', 'contains', 'target sentence')
        self.assertEqual(result, {'suggestions': ['target sentence'], 'exists': True, 'verifiable': True})

        result = yield self.suggest('comment_content', 'contains', 'missing sentence')
        self.assertEqual(result, {'suggestions': [], 'exists': False, 'verifiable': True})

        result = yield self.suggest('file_type', 'in', 'xlsx')
        self.assertTrue(result['exists'])

        yield self.assertFailure(self.suggest('comment_content', 'contains', 'abc'), errors.InputValidationError)
        yield self.assertFailure(self.suggest('comment_content', 'between', 'target'), errors.InputValidationError)

    @inlineCallbacks
    def test_metadata_suggestions(self):
        result = yield self.suggest('status', 'contains', 'opene')
        self.assertIn('opened', result['suggestions'])
        self.assertTrue(result['exists'])

        result = yield self.suggest('status', 'in', 'opened')
        self.assertTrue(result['exists'])

        result = yield self.suggest('status', 'in', 'zzzzz')
        self.assertEqual(result, {'suggestions': [], 'exists': False, 'verifiable': True})

        yield self.assertFailure(self.suggest('status', 'contains', 'new'), errors.InputValidationError)
        yield self.assertFailure(self.suggest('not_a_field', 'contains', 'value'), errors.InputValidationError)

    @inlineCallbacks
    def test_personal_tabs_are_encrypted(self):
        receiver_id = self.dummy_receiver_1['id']
        saved = yield self.recipient_tabs('put', [tab('New reports', [search_filter('status', 'in', ['new'])])])
        loaded = yield self.recipient_tabs('get')
        self.assertEqual(loaded, saved)
        self.assertTrue(loaded['personal'][0]['id'])
        self.assertEqual((yield get_personal_tab_rows(receiver_id)), [('', True)])

    @inlineCallbacks
    def test_personal_tabs_without_user_key(self):
        receiver_id = self.dummy_receiver_1['id']
        yield remove_user_key(receiver_id)
        saved = yield self.recipient_tabs('put', [tab('New reports', [search_filter('status', 'in', ['new'])])])
        loaded = yield self.recipient_tabs('get')
        self.assertEqual(loaded, saved)
        self.assertEqual((yield get_personal_tab_rows(receiver_id)), [('New reports', False)])

    @inlineCallbacks
    def test_saving_tabs_replaces_them_in_order(self):
        yield self.recipient_tabs('put', [tab('First'), tab('Second'), tab('Third')])
        loaded = yield self.recipient_tabs('get')
        self.assertEqual([item['name'] for item in loaded['personal']], ['First', 'Second', 'Third'])
        self.assertEqual([item['position'] for item in loaded['personal']], [0, 1, 2])

        kept = loaded['personal'][2]
        yield self.recipient_tabs('put', [kept, tab('Fourth')])
        loaded = yield self.recipient_tabs('get')
        self.assertEqual([item['name'] for item in loaded['personal']], ['Third', 'Fourth'])
        self.assertEqual(loaded['personal'][0]['id'], kept['id'])

    @inlineCallbacks
    def test_tabs_of_other_users_cannot_be_taken_over(self):
        saved = yield self.recipient_tabs('put', [tab('Mine')])
        taken = saved['personal'][0]
        yield self.assertFailure(self.recipient_tabs('put', [taken], user_id=self.dummy_receiver_2['id']),
                                 errors.ForbiddenOperation)
        yield self.assertFailure(self.admin_tabs('put', [taken]), errors.ForbiddenOperation)
        loaded = yield self.recipient_tabs('get')
        self.assertEqual(loaded['personal'], saved['personal'])

    @inlineCallbacks
    def test_invalid_tabs_are_refused(self):
        for tabs in ([tab('')],
                     [tab('   ')],
                     [tab('x' * 256)],
                     [tab(str(i)) for i in range(51)],
                     [tab('Wrong filter', [search_filter('status', 'between', [0, 1])])],
                     [{'id': '', 'name': 'No query', 'position': 0}]):
            yield self.assertFailure(self.recipient_tabs('put', tabs), errors.InputValidationError)
            yield self.assertFailure(self.admin_tabs('put', tabs), errors.InputValidationError)

    @inlineCallbacks
    def test_admin_tabs_are_the_defaults_of_recipients(self):
        saved = yield self.admin_tabs('put', [tab('Open cases', [search_filter('status', 'in', ['opened'])]),
                                             tab('Recent', [search_filter('creation_date', 'last_days', 10)])])
        self.assertEqual([item['name'] for item in saved['tabs']], ['Open cases', 'Recent'])
        self.assertEqual((yield self.admin_tabs('get')), saved)

        for user_id in (self.dummy_receiver_1['id'], self.dummy_receiver_2['id']):
            loaded = yield self.recipient_tabs('get', user_id=user_id)
            self.assertEqual(loaded['defaults'], saved['tabs'])
            self.assertEqual(loaded['personal'], [])
        self.assertIn('update_search_dashboard', (yield get_audit_types(self.dummy_admin['id'])))

    @inlineCallbacks
    def test_admin_routes_require_the_case_management_permission(self):
        denied = {'can_manage_case_management': False}
        yield self.assertFailure(self.admin_tabs('get', permissions=denied), errors.ForbiddenOperation)
        yield self.assertFailure(self.admin_tabs('put', [tab('Denied')], permissions=denied),
                                 errors.ForbiddenOperation)
        yield self.assertFailure(self.suggest('status', 'contains', 'opene', role='admin', permissions=denied),
                                 errors.ForbiddenOperation)

        result = yield self.suggest('status', 'contains', 'opene', role='admin',
                                    permissions={'can_manage_case_management': True})
        self.assertTrue(result['exists'])

    @inlineCallbacks
    def test_export_is_audited(self):
        handler = self.request(body=json.dumps({'filter_types': ['status'], 'result_count': 3}),
                               user_id=self.dummy_receiver_1['id'], role='receiver', handler_cls=SearchExportAudit)
        yield handler.post()
        self.assertIn('export_search_results', (yield get_audit_types(self.dummy_receiver_1['id'])))


class TestSearchDashboardLargeDataset(SearchTestMixin, helpers.TestHandlerWithPopulatedDB):
    _handler = TipsCollection
    reports = 250

    @inlineCallbacks
    def setUp(self):
        yield super().setUp()
        target = yield get_seed_target(self.dummy_receiver_1['id'])
        seeding._seed_reports(target, self.reports)

    @inlineCallbacks
    def test_pages_cover_every_report_once(self):
        everything = yield self.search_all()
        self.assertGreaterEqual(everything['total'], self.reports)

        seen = []
        for page in range(1, -(-everything['total'] // 20) + 1):
            result = yield self.search(page=page)
            self.assertEqual(result['page'], page)
            self.assertEqual(len(result['reports']), min(20, everything['total'] - (page - 1) * 20))
            seen.extend(report['id'] for report in result['reports'])

        self.assertEqual(len(seen), len(set(seen)))
        self.assertEqual(set(seen), ids(everything))

    @inlineCallbacks
    def test_content_is_found_in_every_batch(self):
        for number in (5, 105, 245):
            result = yield self.search_all([search_filter('comment_content', 'contains', f'demo report {number}:')])
            self.assertEqual(result['total'], 1, number)
            result = yield self.search_all(search=f'review note for demo report {number}:')
            self.assertEqual(result['total'], 1, number)

        responses = yield self.search_all([search_filter('file_name', 'contains', 'recipient-response-')])
        self.assertEqual(responses['total'], self.reports // 20)

    @inlineCallbacks
    def test_suggestions_find_content_in_the_last_batch(self):
        result = yield self.suggest('comment_content', 'contains', 'demo report 245:')
        self.assertTrue(result['exists'])
        result = yield self.suggest('comment_content', 'contains', 'demo report 999:')
        self.assertFalse(result['exists'])

    @inlineCallbacks
    def test_filters_combine_over_many_reports(self):
        everything = yield self.search_all()
        closed = yield self.search_all([search_filter('status', 'in', ['closed'])])
        opened = yield self.search_all([search_filter('status', 'in', ['opened'])])
        either = yield self.search_all([search_filter('status', 'in', ['closed']),
                                        search_filter('status', 'in', ['opened'])])
        neither = yield self.search_all([search_filter('status', 'in', ['closed'], True),
                                         search_filter('status', 'in', ['opened'], True)])
        self.assertTrue(ids(closed) and ids(opened))
        self.assertEqual(ids(either), ids(closed) | ids(opened))
        self.assertEqual(ids(neither), ids(everything) - ids(either))

        commented = yield self.search_all([search_filter('status', 'in', ['closed']),
                                           search_filter('comment_content', 'contains', 'review note')])
        self.assertTrue(ids(commented))
        self.assertTrue(ids(commented) <= ids(closed))
