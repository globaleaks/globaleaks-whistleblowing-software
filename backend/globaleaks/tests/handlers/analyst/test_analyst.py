# -*- coding: utf-8 -*-
from twisted.internet.defer import inlineCallbacks

from globaleaks.handlers import analyst
from globaleaks.tests import helpers


class TestStatistics(helpers.TestHandlerWithPopulatedDB):
    _handler = analyst.Statistics

    @inlineCallbacks
    def setUp(self):
        yield helpers.TestHandlerWithPopulatedDB.setUp(self)
        yield self.perform_full_submission_actions()

    @inlineCallbacks
    def test_get(self):
        handler = self.request(user_id=self.dummyAnalyst['id'], role='analyst')
        stats = yield handler.get()
        self.assertEqual(stats['reports_count'], 2)
        self.assertEqual(stats['reports_with_no_access'], 2)
        self.assertEqual(stats['reports_anonymous'], 2)
        self.assertEqual(stats['reports_subscribed'], 0)
        self.assertEqual(stats['reports_initially_anonymous'], 0)
        self.assertEqual(stats['reports_mobile'], 0)
        self.assertEqual(stats['reports_tor'], 2)

class StatisticalInterest(helpers.TestHandlerWithPopulatedDB):
    _handler = analyst.StatisticalInterest

    @inlineCallbacks
    def setUp(self):
        yield helpers.TestHandlerWithPopulatedDB.setUp(self)
        yield self.perform_full_submission_actions()

    @inlineCallbacks
    def test_get(self):
        handler = self.request(user_id=self.dummyAnalyst['id'], role='analyst')
        stats = yield handler.get()
        expected_output = [
            {'id': 'internal_tip_id', 'label': 'internal_tip_id'},
            {'id': 'internal_tip_status', 'label': 'internal_tip_status'},
            {'id': 'internal_tip_creation_date', 'label': 'internal_tip_creation_date'},
            {'id': 'internal_tip_update_date', 'label': 'internal_tip_update_date'},
            {'id': 'internal_tip_expiration_date', 'label': 'internal_tip_expiration_date'},
            {'id': 'internal_tip_receiver_count', 'label': 'internal_tip_receiver_count'},
            {'id': 'last_access', 'label': 'last_access'},
            {'id': 'internal_tip_creation_date_month', 'label': 'internal_tip_creation_date_month'},
            {'id': 'internal_tip_creation_date_years', 'label': 'internal_tip_creation_date_years'},
            {'id': 'internal_tip_file_count', 'label': 'internal_tip_file_count'},
            {'id': 'internal_tip_comment_count', 'label': 'internal_tip_comment_count'}
        ]

        # Controlla che il risultato sia quello atteso
        self.assertEqual(stats, expected_output)