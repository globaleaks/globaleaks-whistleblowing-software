import copy

from twisted.internet.defer import inlineCallbacks

from globaleaks import models
from globaleaks.handlers.admin import context
from globaleaks.handlers.admin.field import create_field
from globaleaks.handlers import public
from globaleaks.handlers.whistleblower import submission
from globaleaks.orm import transact
from globaleaks.rest import errors
from globaleaks.tests import helpers


@transact
def apply_supplementary(session, context_id, receivers):
    channel = session.query(models.Context).filter(models.Context.id == context_id).one()
    return submission.db_add_supplementary_receivers(session, channel, receivers)


@transact
def public_context(session, context_id):
    channel = session.query(models.Context).filter(models.Context.id == context_id).one()
    return public.serialize_context(session, channel, 'en', public.db_prepare_contexts_serialization(session, [channel]))


@transact
def disable_receiver(session, receiver_id):
    session.query(models.User).filter(models.User.id == receiver_id).one().enabled = False


@transact
def first_step(session, questionnaire_id):
    return session.query(models.Step.id).filter(models.Step.questionnaire_id == questionnaire_id).first()[0]


@transact
def delivered_receivers(session):
    return {tip.receiver_id for tip in session.query(models.ReceiverTip)}


class TestSupplementaryReceivers(helpers.TestHandlerWithPopulatedDB):
    _handler = submission.SubmissionInstance

    @inlineCallbacks
    def configure(self, if_none=None, if_single=None, receivers=None):
        request = copy.deepcopy(self.dummy_context)
        request['supplementary_receivers_if_none'] = if_none or []
        request['supplementary_receivers_if_single'] = if_single or []
        if receivers is not None:
            request['receivers'] = receivers
        response = yield context.update_context(1, request['id'], request, 'en')
        return response

    @inlineCallbacks
    def test_settings_are_saved_and_public(self):
        r1, r2 = self.dummy_receiver_1['id'], self.dummy_receiver_2['id']
        saved = yield self.configure([r1], [r2])
        loaded = yield context.get_context(1, saved['id'], 'en')
        published = yield public_context(saved['id'])
        for response in [saved, loaded, published]:
            self.assertEqual(response['supplementary_receivers_if_none'], [r1])
            self.assertEqual(response['supplementary_receivers_if_single'], [r2])

    @inlineCallbacks
    def test_empty_defaults_preserve_selection(self):
        r1 = self.dummy_receiver_1['id']
        self.assertEqual((yield apply_supplementary(self.dummy_context['id'], [])), set())
        self.assertEqual((yield apply_supplementary(self.dummy_context['id'], [r1])), {r1})

    @inlineCallbacks
    def test_none_rule_does_not_cascade_to_single_rule(self):
        r1, r2 = self.dummy_receiver_1['id'], self.dummy_receiver_2['id']
        yield self.configure([r1], [r2])
        self.assertEqual((yield apply_supplementary(self.dummy_context['id'], [])), {r1})

    @inlineCallbacks
    def test_single_rule_deduplicates_recipients(self):
        r1, r2 = self.dummy_receiver_1['id'], self.dummy_receiver_2['id']
        yield self.configure(if_single=[r1, r2, r2])
        self.assertEqual((yield apply_supplementary(self.dummy_context['id'], [r1])), {r1, r2})

    @inlineCallbacks
    def test_two_recipients_do_not_apply_supplementary_rules(self):
        r1, r2 = self.dummy_receiver_1['id'], self.dummy_receiver_2['id']
        yield self.configure([r1], [r2])
        self.assertEqual((yield apply_supplementary(self.dummy_context['id'], [r1, r2])), {r1, r2})

    @inlineCallbacks
    def test_disabled_recipients_are_not_added_or_published(self):
        r1, r2 = self.dummy_receiver_1['id'], self.dummy_receiver_2['id']
        yield self.configure([r2], [r2])
        yield disable_receiver(r2)
        self.assertEqual((yield apply_supplementary(self.dummy_context['id'], [r1])), {r1})
        response = yield public_context(self.dummy_context['id'])
        self.assertEqual(response['supplementary_receivers_if_none'], [])
        self.assertEqual(response['supplementary_receivers_if_single'], [])

    @inlineCallbacks
    def test_foreign_tenant_recipient_is_rejected(self):
        request = copy.deepcopy(self.dummy_context)
        request['id'] = ''
        request['supplementary_receivers_if_none'] = [self.dummy_receiver_1['id']]
        yield self.assertFailure(context.create_context(2, None, request, 'en'), errors.InputValidationError)

    @inlineCallbacks
    def test_non_recipient_is_rejected(self):
        yield self.assertFailure(self.configure([self.dummy_admin['id']]), errors.InputValidationError)

    @inlineCallbacks
    def test_none_rule_delivers_a_real_submission(self):
        r1, r2 = self.dummy_receiver_1['id'], self.dummy_receiver_2['id']
        yield self.configure([r1], [r2], receivers=[])
        request = yield self.get_dummy_submission(self.dummy_context['id'])
        request['receivers'] = []
        yield self.request(request, role='whistleblower').post()
        self.assertEqual((yield delivered_receivers()), {r1})

    @inlineCallbacks
    def test_single_rule_delivers_to_both_recipients(self):
        r1, r2 = self.dummy_receiver_1['id'], self.dummy_receiver_2['id']
        yield self.configure(if_single=[r2], receivers=[r1])
        request = yield self.get_dummy_submission(self.dummy_context['id'])
        request['receivers'] = [r1]
        yield self.request(request, role='whistleblower').post()
        self.assertEqual((yield delivered_receivers()), {r1, r2})

    @inlineCallbacks
    def test_single_rule_runs_after_recipient_triggers(self):
        r1, r2 = self.dummy_receiver_1['id'], self.dummy_receiver_2['id']
        yield self.configure(if_single=[r2])
        field = helpers.get_dummy_field()
        field['instance'] = 'instance'
        field['type'] = 'selectbox'
        field['step_id'] = yield first_step(self.dummy_context['questionnaire_id'])
        field['options'][0]['trigger_receiver'] = [r1]
        created = yield create_field(1, field, 'en')
        request = yield self.get_dummy_submission(self.dummy_context['id'])
        request['answers'][created['id']] = [{'value': created['options'][0]['id']}]
        request['receivers'] = [r1]
        yield self.request(request, role='whistleblower').post()
        self.assertEqual((yield delivered_receivers()), {r1, r2})
