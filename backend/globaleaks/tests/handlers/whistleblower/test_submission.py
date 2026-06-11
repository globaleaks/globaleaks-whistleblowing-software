from types import SimpleNamespace

from twisted.internet.defer import inlineCallbacks
from twisted.trial import unittest

from globaleaks import models
from globaleaks.handlers import auth
from globaleaks.handlers.whistleblower import submission, wbtip
from globaleaks.jobs import delivery
from globaleaks.orm import transact
from globaleaks.rest import errors
from globaleaks.tests import helpers


@transact
def get_internaltip_score(session):
    return session.query(models.InternalTip.score) \
                  .filter(models.InternalTip.tid == 1) \
                  .order_by(models.InternalTip.creation_date.desc()) \
                  .first()[0]


def scoring_steps():
    return [{
        'children': [
            {
                'id': 'f-select',
                'type': 'selectbox',
                'options': [
                    {'id': 'opt-add', 'score_type': 'addition', 'score_points': 10},
                    {'id': 'opt-mul', 'score_type': 'multiplier', 'score_points': 3},
                ],
                'children': []
            },
            {
                'id': 'f-check',
                'type': 'checkbox',
                'options': [
                    {'id': 'opt-chk', 'score_type': 'addition', 'score_points': 5},
                ],
                'children': []
            },
            {
                'id': 'f-group',
                'type': 'fieldgroup',
                'options': [],
                'children': [
                    {
                        'id': 'f-nested',
                        'type': 'selectbox',
                        'options': [
                            {'id': 'opt-nested', 'score_type': 'addition', 'score_points': 100},
                        ],
                        'children': []
                    }
                ]
            }
        ]
    }]


class TestServersideScore(unittest.TestCase):
    context = SimpleNamespace(score_threshold_medium=10, score_threshold_high=50)

    def evaluate(self, answers):
        return submission.db_evaluate_answers_score(self.context, scoring_steps(), answers)

    def test_no_answers_scores_zero(self):
        self.assertEqual(self.evaluate({}), 0)

    def test_addition_lands_in_medium_band(self):
        self.assertEqual(self.evaluate({'f-select': [{'value': 'opt-add'}]}), 1)

    def test_multiplier_alone_does_not_raise_band(self):
        # sum stays 0, the multiplier applies to 0
        self.assertEqual(self.evaluate({'f-select': [{'value': 'opt-mul'}]}), 0)

    def test_checkbox_addition_accumulates(self):
        self.assertEqual(self.evaluate({'f-check': [{'opt-chk': True}]}), 0)

    def test_nested_fieldgroup_reaches_high_band(self):
        answers = {'f-group': [{'f-nested': [{'value': 'opt-nested'}]}]}
        self.assertEqual(self.evaluate(answers), 2)

    def test_malformed_answers_are_ignored(self):
        # non-dict entries and non-list answers must not raise
        self.assertEqual(self.evaluate({'f-select': 'not-a-list'}), 0)
        self.assertEqual(self.evaluate({'f-select': ['not-a-dict']}), 0)


class TestSubmission(helpers.TestHandlerWithPopulatedDB):
    _handler = submission.SubmissionInstance

    files_created = 6

    @inlineCallbacks
    def create_submission(self, request):
        self.submission_desc = yield self.get_dummy_submission(self.dummyContext['id'])
        handler = self.request(self.submission_desc, role='whistleblower')
        yield handler.post()

    @inlineCallbacks
    def create_submission_with_files(self, request):
        self.submission_desc = yield self.get_dummy_submission(self.dummyContext['id'])
        handler = self.request(self.submission_desc, role='whistleblower')
        self.emulate_file_upload(handler.session, 3)
        yield handler.post()

    @inlineCallbacks
    def test_create_submission_with_no_recipients(self):
        self.submission_desc = yield self.get_dummy_submission(self.dummyContext['id'])
        self.submission_desc['receivers'] = []
        handler = self.request(self.submission_desc, role='whistleblower')
        self.assertFailure(handler.post(), errors.InputValidationError)

    @inlineCallbacks
    def test_create_simple_submission(self):
        self.submission_desc = yield self.get_dummy_submission(self.dummyContext['id'])
        yield self.create_submission(self.submission_desc)

    @inlineCallbacks
    def test_create_submission_attach_files_finalize_and_verify_file_creation(self):
        self.submission_desc = yield self.get_dummy_submission(self.dummyContext['id'])
        yield self.create_submission_with_files(self.submission_desc)
        yield delivery.Delivery().run()

    @inlineCallbacks
    def test_update_submission(self):
        self.submission_desc = yield self.get_dummy_submission(self.dummyContext['id'])

        self.submission_desc['answers'] = yield self.fill_random_answers(self.dummyContext['questionnaire_id'])

        yield self.create_submission(self.submission_desc)

        session = yield auth.login_whistleblower(1, self.submission_desc['receipt'], True)

        wbtip_desc, _ = yield wbtip.get_wbtip(session.user_id, 'en')

        self.assertTrue('data' in wbtip_desc)

    @inlineCallbacks
    def test_submission_cannot_downgrade_tenant_receipt_auth_mode(self):
        # A key-mode tenant must reject a receipt that is not the client-derived key.
        if not self.clientside_hashing:
            return

        self.assertEqual((yield auth.get_auth_type(1, ''))['type'], 'key')

        self.submission_desc = yield self.get_dummy_submission(self.dummyContext['id'])
        self.submission_desc['receipt'] = '1234123412341234'
        handler = self.request(self.submission_desc, role='whistleblower')
        yield self.assertFailure(handler.post(), errors.InputValidationError)

        self.assertEqual((yield auth.get_auth_type(1, ''))['type'], 'key')


class TestSubmissionServersideHashing(TestSubmission):
    clientside_hashing = False
    wb_legacy_receipt_seed = True
