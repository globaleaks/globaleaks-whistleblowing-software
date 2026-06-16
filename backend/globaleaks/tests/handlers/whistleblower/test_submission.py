from types import SimpleNamespace

from twisted.internet.defer import inlineCallbacks
from twisted.trial import unittest

from globaleaks import models
from globaleaks.db import db_fix_receipt_auth_downgrade
from globaleaks.handlers import auth
from globaleaks.handlers.whistleblower import submission, wbtip
from globaleaks.jobs import delivery
from globaleaks.orm import transact
from globaleaks.rest import errors
from globaleaks.tests import helpers
from globaleaks.utils.crypto import GCE


@transact
def inject_legacy_receipt_report(session, context_id):
    itip = models.InternalTip()
    itip.tid = 1
    itip.context_id = context_id
    itip.progressive = 9999
    _, itip.receipt_hash = GCE.calculate_key_and_hash('1234123412341234', helpers.VALID_SALT)
    session.add(itip)
    session.flush()
    return itip.id


@transact
def run_fix_receipt_auth_downgrade(session):
    db_fix_receipt_auth_downgrade(session)


@transact
def get_receipt_hash(session, itip_id):
    return session.query(models.InternalTip.receipt_hash) \
                  .filter(models.InternalTip.id == itip_id).one()[0]


@transact
def set_context_selection_policy(session, context_id, allow_recipients_selection):
    context = session.query(models.Context).filter(models.Context.id == context_id).one()
    context.allow_recipients_selection = allow_recipients_selection
    context.select_all_receivers = not allow_recipients_selection


@transact
def set_context_select_all_receivers(session, context_id, value):
    session.query(models.Context).filter(models.Context.id == context_id).one().select_all_receivers = value


@transact
def set_receiver_forcefully_selected(session, user_id, value):
    session.query(models.User).filter(models.User.id == user_id).one().forcefully_selected = value


@transact
def validate_submission_receivers(session, context_id, steps, answers, requested_receivers):
    context = session.query(models.Context).filter(models.Context.id == context_id).one()
    submission.db_validate_submission_receivers(session, context, steps, answers, False, requested_receivers)


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


def trigger_steps(triggered, triggered2=None):
    return [{
        'children': [
            {
                'id': 'f-select',
                'type': 'selectbox',
                'triggered_by_options': [],
                'options': [
                    {'id': 'opt-trigger', 'trigger_receiver': triggered},
                    {'id': 'opt-plain', 'trigger_receiver': []},
                ],
                'children': []
            },
            {
                'id': 'f-select-2',
                'type': 'selectbox',
                'triggered_by_options': [],
                'options': [
                    {'id': 'opt-trigger-2', 'trigger_receiver': triggered2 or []},
                ],
                'children': []
            }
        ]
    }]


def gated_trigger_steps(triggered):
    # f-gated is enabled only when opt-gate is selected on f-gate
    return [{
        'children': [
            {
                'id': 'f-gate',
                'type': 'selectbox',
                'triggered_by_options': [],
                'options': [
                    {'id': 'opt-gate', 'trigger_receiver': []},
                    {'id': 'opt-other', 'trigger_receiver': []},
                ],
                'children': []
            },
            {
                'id': 'f-gated',
                'type': 'selectbox',
                'triggered_by_options': [{'field': 'f-gate', 'option': 'opt-gate', 'sufficient': True}],
                'options': [
                    {'id': 'opt-gated-trigger', 'trigger_receiver': triggered},
                ],
                'children': []
            }
        ]
    }]


def chained_trigger_steps(triggered):
    # f-c (carrying the trigger_receiver) is enabled only through f-b, which is
    # itself enabled only when opt-a1 is selected on f-a
    return [{
        'children': [
            {
                'id': 'f-a',
                'type': 'selectbox',
                'triggered_by_options': [],
                'options': [
                    {'id': 'opt-a1', 'trigger_receiver': []},
                    {'id': 'opt-a2', 'trigger_receiver': []},
                ],
                'children': []
            },
            {
                'id': 'f-b',
                'type': 'selectbox',
                'triggered_by_options': [{'field': 'f-a', 'option': 'opt-a1', 'sufficient': True}],
                'options': [
                    {'id': 'opt-b1', 'trigger_receiver': []},
                ],
                'children': []
            },
            {
                'id': 'f-c',
                'type': 'selectbox',
                'triggered_by_options': [{'field': 'f-b', 'option': 'opt-b1', 'sufficient': True}],
                'options': [
                    {'id': 'opt-c-trigger', 'trigger_receiver': triggered},
                ],
                'children': []
            }
        ]
    }]


class TestReceiversOverrideEvaluation(unittest.TestCase):
    def test_no_selected_trigger_option_yields_no_override(self):
        steps = trigger_steps(['r1', 'r2'])
        self.assertIsNone(submission.evaluate_receivers_override(steps, {}, False))
        self.assertIsNone(submission.evaluate_receivers_override(steps, {'f-select': [{'value': 'opt-plain'}]}, False))

    def test_selected_trigger_option_yields_override(self):
        steps = trigger_steps(['r1', 'r2'])
        answers = {'f-select': [{'value': 'opt-trigger'}]}
        self.assertEqual(submission.evaluate_receivers_override(steps, answers, False), ['r1', 'r2'])

    def test_last_selected_trigger_option_wins(self):
        # The override matches the client: the last selected option that
        # declares a trigger_receiver replaces the previous one
        steps = trigger_steps(['r1'], ['r2', 'r3'])
        answers = {'f-select': [{'value': 'opt-trigger'}], 'f-select-2': [{'value': 'opt-trigger-2'}]}
        self.assertEqual(submission.evaluate_receivers_override(steps, answers, False), ['r2', 'r3'])

    def test_trigger_option_on_disabled_field_is_ignored(self):
        # A trigger option selected on a field that is not enabled by its own
        # triggering conditions must not produce an override
        steps = gated_trigger_steps(['r1'])
        answers = {'f-gate': [{'value': 'opt-other'}], 'f-gated': [{'value': 'opt-gated-trigger'}]}
        self.assertIsNone(submission.evaluate_receivers_override(steps, answers, False))

        # When the gating option is selected the field becomes enabled and the
        # override is produced
        answers = {'f-gate': [{'value': 'opt-gate'}], 'f-gated': [{'value': 'opt-gated-trigger'}]}
        self.assertEqual(submission.evaluate_receivers_override(steps, answers, False), ['r1'])

    def test_trigger_through_disabled_source_field_is_ignored(self):
        # A modified client cannot smuggle an override by selecting the trigger
        # option of an intermediate field that is itself not enabled: the client
        # clears disabled fields before evaluating downstream triggers
        steps = chained_trigger_steps(['r1'])

        smuggled = {'f-a': [{'value': 'opt-a2'}],
                    'f-b': [{'value': 'opt-b1'}],
                    'f-c': [{'value': 'opt-c-trigger'}]}
        self.assertIsNone(submission.evaluate_receivers_override(steps, smuggled, False))

        legit = {'f-a': [{'value': 'opt-a1'}],
                 'f-b': [{'value': 'opt-b1'}],
                 'f-c': [{'value': 'opt-c-trigger'}]}
        self.assertEqual(submission.evaluate_receivers_override(steps, legit, False), ['r1'])

    def test_evaluation_does_not_mutate_answers(self):
        steps = chained_trigger_steps(['r1'])
        answers = {'f-a': [{'value': 'opt-a2'}], 'f-b': [{'value': 'opt-b1'}]}
        submission.evaluate_receivers_override(steps, answers, False)
        self.assertEqual(answers, {'f-a': [{'value': 'opt-a2'}], 'f-b': [{'value': 'opt-b1'}]})


# Field ids shaped like the UUIDs the answers validation acts upon
F_GROUP = 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa'
F_CHILD = 'bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb'
F_LEAF = 'cccccccc-cccc-cccc-cccc-cccccccccccc'
F_UNKNOWN = 'dddddddd-dddd-dddd-dddd-dddddddddddd'


def schema_with_fieldgroup():
    # A questionnaire with a top-level input field and a fieldgroup carrying a
    # single leaf child; the fieldgroup is the only place a nested field id is
    # allowed to map to a list of entries.
    return [{
        'children': [
            {'id': F_LEAF, 'type': 'inputbox', 'children': []},
            {
                'id': F_GROUP,
                'type': 'fieldgroup',
                'children': [
                    {'id': F_CHILD, 'type': 'inputbox', 'children': []}
                ]
            }
        ]
    }]


class TestAnswersSchemaValidation(unittest.TestCase):
    def test_conformant_answers_are_accepted(self):
        steps = schema_with_fieldgroup()
        answers = {
            F_LEAF: [{'value': 'x'}],
            F_GROUP: [{F_CHILD: [{'value': 'y'}]}]
        }
        # No exception expected
        submission.db_validate_submission_answers(steps, answers)

    def test_leaf_answer_data_is_left_untouched(self):
        # Non-list entry attributes (value, transient UI flags, checkbox option
        # ids mapping to strings) are not recursion targets and must pass.
        steps = schema_with_fieldgroup()
        answers = {
            F_LEAF: [{'value': 'x', 'required_status': False, F_UNKNOWN: 'True'}]
        }
        submission.db_validate_submission_answers(steps, answers)

    def test_unknown_top_level_field_is_rejected(self):
        steps = schema_with_fieldgroup()
        answers = {F_UNKNOWN: [{'value': 'x'}]}
        self.assertRaises(errors.InputValidationError,
                          submission.db_validate_submission_answers, steps, answers)

    def test_nested_field_not_in_fieldgroup_is_rejected(self):
        # A field id nested where the schema does not define it as a child
        steps = schema_with_fieldgroup()
        answers = {F_GROUP: [{F_UNKNOWN: [{'value': 'x'}]}]}
        self.assertRaises(errors.InputValidationError,
                          submission.db_validate_submission_answers, steps, answers)

    def test_nested_list_under_a_leaf_field_is_rejected(self):
        # A leaf field has no children: smuggling a nested field-id list into
        # its entry must be rejected.
        steps = schema_with_fieldgroup()
        answers = {F_LEAF: [{F_CHILD: [{'value': 'x'}]}]}
        self.assertRaises(errors.InputValidationError,
                          submission.db_validate_submission_answers, steps, answers)

    def test_deeply_nested_answers_are_rejected(self):
        # The denial-of-service payload: a field id recursively nested far
        # beyond the recursion limit. The validation, driven by the schema,
        # rejects it at the first level without recursing.
        steps = schema_with_fieldgroup()
        entry = {}
        cur = entry
        for _ in range(3000):
            child = {}
            cur[F_GROUP] = [child]
            cur = child
        answers = {F_GROUP: [entry]}
        self.assertRaises(errors.InputValidationError,
                          submission.db_validate_submission_answers, steps, answers)

    def test_non_uuid_keys_and_non_list_values_are_ignored(self):
        # Keys that are not field-id shaped, or that do not carry a list, are
        # never recursed into by the readers and are intentionally not policed.
        steps = schema_with_fieldgroup()
        answers = {F_LEAF: [{'not-a-uuid': [{'value': 'x'}], 'value': 'y'}]}
        submission.db_validate_submission_answers(steps, answers)


# Field and option ids shaped like the UUIDs the answers validation acts upon
F_TEXT = 'eeeeeeee-eeee-eeee-eeee-eeeeeeeeeeee'
F_SELECT = 'ffffffff-ffff-ffff-ffff-ffffffffffff'
F_CHECK = '99999999-9999-9999-9999-999999999999'
F_EMAIL = '88888888-8888-8888-8888-888888888888'
F_DATE = '77777777-7777-7777-7777-777777777777'
F_DATERANGE = '66666666-6666-6666-6666-666666666666'
F_TOS = '55555555-5555-5555-5555-555555555555'
OPT_A = '11111111-1111-1111-1111-111111111111'
OPT_B = '22222222-2222-2222-2222-222222222222'
OPT_UNKNOWN = '33333333-3333-3333-3333-333333333333'


def schema_with_constraints():
    # A questionnaire mixing a length-bounded text field, an input-validated
    # text field, the three kinds of choice fields and the date/daterange/tos
    # fields, used to exercise the per-field answer validation.
    options = [{'id': OPT_A}, {'id': OPT_B}]
    return [{
        'children': [
            {'id': F_TEXT, 'type': 'inputbox', 'children': [],
             'attrs': {'min_len': {'value': '2'}, 'max_len': {'value': '5'}}},
            {'id': F_EMAIL, 'type': 'inputbox', 'children': [],
             'attrs': {'input_validation': {'value': 'email'}}},
            {'id': F_SELECT, 'type': 'selectbox', 'children': [], 'options': options},
            {'id': F_CHECK, 'type': 'checkbox', 'children': [], 'options': options},
            {'id': F_DATE, 'type': 'date', 'children': [], 'attrs': {}},
            {'id': F_DATERANGE, 'type': 'daterange', 'children': [], 'attrs': {}},
            {'id': F_TOS, 'type': 'tos', 'children': [], 'attrs': {}},
        ]
    }]


class TestAnswersConstraintsValidation(unittest.TestCase):
    def test_text_within_length_bounds_is_accepted(self):
        steps = schema_with_constraints()
        submission.db_validate_submission_answers(steps, {F_TEXT: [{'value': 'hello'}]})

    def test_text_exceeding_max_len_is_rejected(self):
        steps = schema_with_constraints()
        self.assertRaises(errors.InputValidationError,
                          submission.db_validate_submission_answers,
                          steps, {F_TEXT: [{'value': 'too-long'}]})

    def test_text_shorter_than_min_len_is_rejected(self):
        steps = schema_with_constraints()
        self.assertRaises(errors.InputValidationError,
                          submission.db_validate_submission_answers,
                          steps, {F_TEXT: [{'value': 'a'}]})

    def test_empty_text_is_accepted_regardless_of_min_len(self):
        # Mirroring the client, an empty answer bypasses the length bounds: its
        # presence is governed by the conditional required-field policy.
        steps = schema_with_constraints()
        submission.db_validate_submission_answers(steps, {F_TEXT: [{'value': ''}]})

    def test_non_string_text_value_is_rejected(self):
        steps = schema_with_constraints()
        self.assertRaises(errors.InputValidationError,
                          submission.db_validate_submission_answers,
                          steps, {F_TEXT: [{'value': ['x']}]})

    def test_existing_selectbox_option_is_accepted(self):
        steps = schema_with_constraints()
        submission.db_validate_submission_answers(steps, {F_SELECT: [{'value': OPT_A}]})

    def test_unselected_selectbox_is_accepted(self):
        steps = schema_with_constraints()
        submission.db_validate_submission_answers(steps, {F_SELECT: [{'value': ''}]})

    def test_inexistent_selectbox_option_is_rejected(self):
        steps = schema_with_constraints()
        self.assertRaises(errors.InputValidationError,
                          submission.db_validate_submission_answers,
                          steps, {F_SELECT: [{'value': OPT_UNKNOWN}]})

    def test_existing_checkbox_options_are_accepted(self):
        steps = schema_with_constraints()
        answers = {F_CHECK: [{OPT_A: True, OPT_B: False, 'required_status': False}]}
        submission.db_validate_submission_answers(steps, answers)

    def test_inexistent_checkbox_option_is_rejected(self):
        steps = schema_with_constraints()
        self.assertRaises(errors.InputValidationError,
                          submission.db_validate_submission_answers,
                          steps, {F_CHECK: [{OPT_UNKNOWN: True}]})

    def test_valid_email_input_validation_is_accepted(self):
        steps = schema_with_constraints()
        submission.db_validate_submission_answers(steps, {F_EMAIL: [{'value': 'wb@example.com'}]})

    def test_invalid_email_input_validation_is_rejected(self):
        steps = schema_with_constraints()
        self.assertRaises(errors.InputValidationError,
                          submission.db_validate_submission_answers,
                          steps, {F_EMAIL: [{'value': 'not-an-email'}]})

    def test_valid_date_is_accepted(self):
        steps = schema_with_constraints()
        submission.db_validate_submission_answers(steps, {F_DATE: [{'value': '2026-06-17T00:00:00.000Z'}]})

    def test_malformed_date_is_rejected(self):
        steps = schema_with_constraints()
        self.assertRaises(errors.InputValidationError,
                          submission.db_validate_submission_answers,
                          steps, {F_DATE: [{'value': '2026-13-40T00:00:00.000Z'}]})

    def test_non_string_date_is_rejected(self):
        steps = schema_with_constraints()
        self.assertRaises(errors.InputValidationError,
                          submission.db_validate_submission_answers,
                          steps, {F_DATE: [{'value': 12345}]})

    def test_valid_daterange_is_accepted(self):
        steps = schema_with_constraints()
        submission.db_validate_submission_answers(steps, {F_DATERANGE: [{'value': '1000000000000:2000000000000'}]})

    def test_inverted_daterange_is_rejected(self):
        steps = schema_with_constraints()
        self.assertRaises(errors.InputValidationError,
                          submission.db_validate_submission_answers,
                          steps, {F_DATERANGE: [{'value': '2000000000000:1000000000000'}]})

    def test_malformed_daterange_is_rejected(self):
        steps = schema_with_constraints()
        self.assertRaises(errors.InputValidationError,
                          submission.db_validate_submission_answers,
                          steps, {F_DATERANGE: [{'value': 'notanumber:2000000000000'}]})

    def test_daterange_with_wrong_arity_is_rejected(self):
        steps = schema_with_constraints()
        self.assertRaises(errors.InputValidationError,
                          submission.db_validate_submission_answers,
                          steps, {F_DATERANGE: [{'value': '1000000000000'}]})

    def test_boolean_tos_is_accepted(self):
        steps = schema_with_constraints()
        submission.db_validate_submission_answers(steps, {F_TOS: [{'value': True}]})

    def test_non_boolean_tos_is_rejected(self):
        steps = schema_with_constraints()
        self.assertRaises(errors.InputValidationError,
                          submission.db_validate_submission_answers,
                          steps, {F_TOS: [{'value': 'accepted'}]})


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


def block_submission_steps():
    return [{
        'children': [
            {
                'id': 'f-select',
                'type': 'selectbox',
                'options': [
                    {'id': 'opt-plain', 'block_submission': False},
                    {'id': 'opt-block', 'block_submission': True},
                ],
                'children': []
            },
            {
                'id': 'f-check',
                'type': 'checkbox',
                'options': [
                    {'id': 'opt-chk-block', 'block_submission': True},
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
                            {'id': 'opt-nested-block', 'block_submission': True},
                        ],
                        'children': []
                    }
                ]
            }
        ]
    }]


class TestBlockSubmissionEvaluation(unittest.TestCase):
    def evaluate(self, answers):
        return submission.db_evaluate_block_submission(block_submission_steps(), answers)

    def test_no_answers_do_not_block(self):
        self.assertFalse(self.evaluate({}))

    def test_non_blocking_option_does_not_block(self):
        self.assertFalse(self.evaluate({'f-select': [{'value': 'opt-plain'}]}))

    def test_selectbox_blocking_option_blocks(self):
        self.assertTrue(self.evaluate({'f-select': [{'value': 'opt-block'}]}))

    def test_checkbox_blocking_option_blocks(self):
        self.assertTrue(self.evaluate({'f-check': [{'opt-chk-block': True}]}))

    def test_blocking_option_nested_in_fieldgroup_blocks(self):
        answers = {'f-group': [{'f-nested': [{'value': 'opt-nested-block'}]}]}
        self.assertTrue(self.evaluate(answers))

    def test_malformed_answers_do_not_block(self):
        self.assertFalse(self.evaluate({'f-select': 'not-a-list'}))
        self.assertFalse(self.evaluate({'f-select': ['not-a-dict']}))


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
    def test_create_submission_with_recipients_subset_rejected_when_selection_disabled(self):
        # The dummy context disables recipients selection: the backend must
        # reject a client-supplied subset of the configured recipients.
        self.submission_desc = yield self.get_dummy_submission(self.dummyContext['id'])
        self.submission_desc['receivers'] = [self.dummyReceiver_1['id']]
        handler = self.request(self.submission_desc, role='whistleblower')
        yield self.assertFailure(handler.post(), errors.InputValidationError)

    @inlineCallbacks
    def test_create_submission_with_recipient_not_configured_on_the_context_rejected(self):
        self.submission_desc = yield self.get_dummy_submission(self.dummyContext['id'])
        self.submission_desc['receivers'].append('00000000-0000-0000-0000-000000000000')
        handler = self.request(self.submission_desc, role='whistleblower')
        yield self.assertFailure(handler.post(), errors.InputValidationError)

    @inlineCallbacks
    def test_create_submission_with_deeply_nested_answers_rejected(self):
        # A modified client cannot persist answers nested beyond the
        # questionnaire schema: such a report would later exhaust the recursion
        # limit when an assigned recipient opens or exports it.
        self.submission_desc = yield self.get_dummy_submission(self.dummyContext['id'])
        self.submission_desc['answers'] = helpers.forge_nested_answers('aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa')
        handler = self.request(self.submission_desc, role='whistleblower')
        yield self.assertFailure(handler.post(), errors.InputValidationError)

    @inlineCallbacks
    def test_create_submission_must_include_mandatory_recipients_when_selection_allowed(self):
        yield set_context_selection_policy(self.dummyContext['id'], True)
        yield set_receiver_forcefully_selected(self.dummyReceiver_2['id'], False)

        # A selection omitting the mandatory recipient is rejected
        self.submission_desc = yield self.get_dummy_submission(self.dummyContext['id'])
        self.submission_desc['receivers'] = [self.dummyReceiver_2['id']]
        handler = self.request(self.submission_desc, role='whistleblower')
        yield self.assertFailure(handler.post(), errors.InputValidationError)

        # A selection omitting an optional recipient is accepted
        self.submission_desc = yield self.get_dummy_submission(self.dummyContext['id'])
        self.submission_desc['receivers'] = [self.dummyReceiver_1['id']]
        handler = self.request(self.submission_desc, role='whistleblower')
        yield handler.post()

    @inlineCallbacks
    def test_selection_disabled_with_select_all_requires_the_full_set(self):
        # allow_recipients_selection=False + select_all_receivers=True (the
        # dummy context default): the client selects every configured recipient,
        # so the backend accepts exactly the full set and rejects a subset.
        yield validate_submission_receivers(self.dummyContext['id'], [], {},
                                            {self.dummyReceiver_1['id'], self.dummyReceiver_2['id']})

        yield self.assertFailure(validate_submission_receivers(self.dummyContext['id'], [], {},
                                                               {self.dummyReceiver_1['id']}),
                                 errors.InputValidationError)

    @inlineCallbacks
    def test_selection_disabled_without_select_all_requires_only_mandatory(self):
        # allow_recipients_selection=False + select_all_receivers=False: the
        # client pre-selects only the forcefully selected recipients, so the
        # backend must accept exactly that set and reject the full one that the
        # client would never submit in this configuration.
        yield set_context_select_all_receivers(self.dummyContext['id'], False)
        yield set_receiver_forcefully_selected(self.dummyReceiver_2['id'], False)

        # Only the mandatory recipient is accepted
        yield validate_submission_receivers(self.dummyContext['id'], [], {},
                                            {self.dummyReceiver_1['id']})

        # The full set, that the client would not submit, is rejected
        yield self.assertFailure(validate_submission_receivers(self.dummyContext['id'], [], {},
                                                               {self.dummyReceiver_1['id'], self.dummyReceiver_2['id']}),
                                 errors.InputValidationError)

        # An empty selection, omitting the mandatory recipient, is rejected
        yield self.assertFailure(validate_submission_receivers(self.dummyContext['id'], [], {}, set()),
                                 errors.InputValidationError)

    @inlineCallbacks
    def test_triggered_recipients_override_takes_precedence(self):
        steps = trigger_steps([self.dummyReceiver_2['id']])
        answers = {'f-select': [{'value': 'opt-trigger'}]}

        # The triggered override derogates both the mandatory recipients
        # and the disabled recipients selection configured on the context
        yield validate_submission_receivers(self.dummyContext['id'], steps, answers,
                                            {self.dummyReceiver_2['id']})

        # A selection not matching the triggered override is rejected, both
        # when missing a triggered recipient and when adding an extra one
        yield self.assertFailure(validate_submission_receivers(self.dummyContext['id'], steps, answers,
                                                               {self.dummyReceiver_1['id']}),
                                 errors.InputValidationError)

        yield self.assertFailure(validate_submission_receivers(self.dummyContext['id'], steps, answers,
                                                               {self.dummyReceiver_1['id'], self.dummyReceiver_2['id']}),
                                 errors.InputValidationError)

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
    def test_existing_session_cannot_finalize_when_submissions_disabled(self):
        # An existing submission session must not be able to finalize a report
        # once intake has been disabled, either administratively or by the
        # low-disk lockout that flips State.accept_submissions to False.
        self.submission_desc = yield self.get_dummy_submission(self.dummyContext['id'])
        handler = self.request(self.submission_desc, role='whistleblower')

        self.state.accept_submissions = False
        try:
            yield self.assertFailure(handler.post(), errors.SubmissionDisabled)
        finally:
            self.state.accept_submissions = True

        self.state.tenants[1].cache['disable_submissions'] = True
        try:
            yield self.assertFailure(handler.post(), errors.SubmissionDisabled)
        finally:
            self.state.tenants[1].cache['disable_submissions'] = False

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

    @inlineCallbacks
    def test_fix_receipt_auth_downgrade_restores_key_mode(self):
        if not self.clientside_hashing:
            return

        yield self.perform_full_submission_actions()
        receipt = self.dummySubmission['receipt']

        # A legacy-format report switches the tenant to password mode
        malicious_id = yield inject_legacy_receipt_report(self.dummyContext['id'])
        self.assertEqual((yield auth.get_auth_type(1, ''))['type'], 'password')
        yield self.assertFailure(auth.login_whistleblower(1, receipt, True),
                                 errors.InvalidAuthentication)

        yield run_fix_receipt_auth_downgrade()

        # The fix restores key mode and access to the existing report
        self.assertEqual((yield auth.get_auth_type(1, ''))['type'], 'key')
        session = yield auth.login_whistleblower(1, receipt, True)
        self.assertTrue(session is not None)
        self.assertEqual(len((yield get_receipt_hash(malicious_id))), 64)


class TestSubmissionServersideHashing(TestSubmission):
    clientside_hashing = False
    wb_legacy_receipt_seed = True
