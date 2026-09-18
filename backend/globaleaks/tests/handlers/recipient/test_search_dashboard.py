import json

from twisted.internet.defer import inlineCallbacks

from globaleaks.handlers.recipient import TipsCollection
from globaleaks.handlers.recipient.search_dashboard import RecipientDashboard
from globaleaks.tests import helpers


class TestSearchDashboard(helpers.TestHandlerWithPopulatedDB):
    _handler = TipsCollection

    @inlineCallbacks
    def setUp(self):
        yield super().setUp()
        yield self.perform_full_submission_actions()

    def search(self, filters=None, page=1, sort='creation_date'):
        request = {
            'page': page,
            'search': '',
            'unread': False,
            'sort': sort,
            'descending': True,
            'query': {'negated': False, 'filters': filters or []}
        }
        handler = self.request(body=json.dumps(request), user_id=self.dummy_receiver_1['id'], role='receiver')
        return handler.post()

    @inlineCallbacks
    def test_search_preserves_report_listing(self):
        handler = self.request(user_id=self.dummy_receiver_1['id'], role='receiver')
        listed = yield handler.get()
        result = yield self.search(sort='channel_progressive_sort_key')
        self.assertEqual(result['total'], len(listed))
        expected = {report['id']: report for report in listed}
        for report in result['reports']:
            self.assertEqual(report, expected[report['id']])

    @inlineCallbacks
    def test_filters_and_page_bounds(self):
        result = yield self.search(page=999)
        self.assertEqual(result['page'], max(1, (result['total'] + 19) // 20))
        self.assertLessEqual(len(result['reports']), 20)
        result = yield self.search([{
            'id': 'missing-status', 'field': 'status', 'operator': 'in',
            'value': ['not-a-real-status'], 'negated': False
        }])
        self.assertEqual(result, {'reports': [], 'page': 1, 'total': 0})

    @inlineCallbacks
    def test_personal_tab_round_trip(self):
        query = {'negated': False, 'filters': [{
            'id': '', 'field': 'status', 'operator': 'in', 'value': ['new'], 'negated': False
        }]}
        handler = self.request(body=json.dumps({'tabs': [{'id': '', 'name': 'New reports', 'query': query, 'position': 0}]}),
                               user_id=self.dummy_receiver_1['id'], role='receiver', handler_cls=RecipientDashboard)
        saved = yield handler.put()
        handler = self.request(user_id=self.dummy_receiver_1['id'], role='receiver', handler_cls=RecipientDashboard)
        loaded = yield handler.get()
        self.assertEqual(loaded, saved)
        self.assertTrue(loaded['personal'][0]['id'])

    @inlineCallbacks
    def test_search_preserves_answer_masking(self):
        receiver_id = self.dummy_receiver_1['id']
        handler = self.request(user_id=receiver_id, role='receiver')
        listed = yield handler.get()
        target = next((report, field_id, entry) for report in listed
                      for field_id, entries in report['answers'].items() for entry in entries
                      if isinstance(entry.get('value'), str) and entry['value'])
        report, field_id, entry = target
        yield self.add_redaction(report['id'], field_id, [{'start': 0, 'end': 100}], entry['index'])
        yield self.set_redaction_privileges(receiver_id, False)
        result = yield self.search()
        masked = next(item for item in result['reports'] if item['id'] == report['id'])
        answer = next(item for item in masked['answers'][field_id] if item['index'] == entry['index'])
        self.assertNotEqual(answer['value'], entry['value'])
        self.assertIn(chr(0x2591), answer['value'])
