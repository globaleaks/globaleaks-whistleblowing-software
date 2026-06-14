from twisted.internet.defer import inlineCallbacks

from globaleaks import models
from globaleaks.handlers import auth
from globaleaks.handlers.whistleblower import wbtip
from globaleaks.jobs.delivery import Delivery
from globaleaks.orm import transact
from globaleaks.rest import errors
from globaleaks.tests import helpers
from globaleaks.tests.helpers import VALID_SALT
from globaleaks.utils.crypto import GCE


class TestWBTipInstance(helpers.TestHandlerWithPopulatedDB):
    _handler = wbtip.WBTipInstance

    @inlineCallbacks
    def setUp(self):
        yield helpers.TestHandlerWithPopulatedDB.setUp(self)
        yield self.perform_full_submission_actions()

    @inlineCallbacks
    def test_get(self):
        wbtips_desc = yield self.get_wbtips()
        for wbtip_desc in wbtips_desc:
            handler = self.request(role='whistleblower', user_id=wbtip_desc['id'])

            yield handler.get()


class TestWBTipCommentCollection(helpers.TestHandlerWithPopulatedDB):
    _handler = wbtip.WBTipCommentCollection

    @inlineCallbacks
    def setUp(self):
        yield helpers.TestHandlerWithPopulatedDB.setUp(self)
        yield self.perform_full_submission_actions()

    @inlineCallbacks
    def test_post(self):
        body = {
            'content': "can you provide an evidence of what you are telling?",
            'visibility': "internal"
        }

        wbtips_desc = yield self.get_wbtips()
        for wbtip_desc in wbtips_desc:
            handler = self.request(body, role='whistleblower', user_id=wbtip_desc['id'])

            yield handler.post()


class TestWhistleblowerFileDownload(helpers.TestHandlerWithPopulatedDB):
    _handler = wbtip.WhistleblowerFileDownload

    @inlineCallbacks
    def test_get(self):
        yield self.perform_minimal_submission_actions()
        yield Delivery().run()

        wbtip_descs = yield self.get_wbtips()
        for wbtip_desc in wbtip_descs:
            wbfile_ids = yield self.get_ifiles_by_wbtip_id(wbtip_desc['id'])
            for wbfile_id in wbfile_ids:
                handler = self.request(role='whistleblower', user_id=wbtip_desc['id'])
                yield handler.get(wbfile_id)
                self.assertNotEqual(handler.request.getResponseBody(), '')


class WBTipIdentityHandler(helpers.TestHandlerWithPopulatedDB):
    _handler = wbtip.WBTipIdentityHandler

    @inlineCallbacks
    def setUp(self):
        yield helpers.TestHandlerWithPopulatedDB.setUp(self)
        yield self.perform_full_submission_actions()

    @transact
    def get_whistleblower_identity_field_id(self, session, context_id):
        context = session.query(models.Context) \
                         .filter(models.Context.id == context_id).one()

        field = session.query(models.Field) \
                       .filter(models.Field.template_id == 'whistleblower_identity',
                               models.Field.step_id == models.Step.id,
                               models.Step.questionnaire_id == context.questionnaire_id).one()

        return field.id

    @inlineCallbacks
    def test_post(self):
        identity_field_id = yield self.get_whistleblower_identity_field_id(self.dummyContext['id'])

        body = {
          'identity_field_id': identity_field_id,
          'identity_field_answers': {}
        }

        wbtips_desc = yield self.get_wbtips()
        for wbtip_desc in wbtips_desc:
            handler = self.request(body, role='whistleblower', user_id=wbtip_desc['id'])

            yield handler.post()

    @inlineCallbacks
    def test_post_with_deeply_nested_answers_rejected(self):
        # A modified client cannot persist identity answers nested beyond the
        # questionnaire schema: such a report would later exhaust the recursion
        # limit when an assigned recipient opens, exports or redacts it.
        identity_field_id = yield self.get_whistleblower_identity_field_id(self.dummyContext['id'])

        body = {
          'identity_field_id': identity_field_id,
          'identity_field_answers': helpers.forge_nested_answers(identity_field_id)
        }

        wbtips_desc = yield self.get_wbtips()
        for wbtip_desc in wbtips_desc:
            handler = self.request(body, role='whistleblower', user_id=wbtip_desc['id'])
            yield self.assertFailure(handler.post(), errors.InputValidationError)


class TestWBTipAdditionalQuestionnaire(helpers.TestHandlerWithPopulatedDB):
    _handler = wbtip.WBTipAdditionalQuestionnaire

    @inlineCallbacks
    def setUp(self):
        yield helpers.TestHandlerWithPopulatedDB.setUp(self)
        yield self.perform_full_submission_actions()
        # Enable an additional questionnaire on the context reusing the main
        # questionnaire schema so that the fill-form endpoint stores answers.
        yield self.set_additional_questionnaire(self.dummyContext['id'],
                                                self.dummyContext['questionnaire_id'])

    @transact
    def set_additional_questionnaire(self, session, context_id, questionnaire_id):
        session.query(models.Context) \
               .filter(models.Context.id == context_id) \
               .update({'additional_questionnaire_id': questionnaire_id})

    @inlineCallbacks
    def test_post(self):
        answers = yield self.fill_random_answers(self.dummyContext['questionnaire_id'])

        body = {
          'cmd': 'fill',
          'answers': answers
        }

        wbtips_desc = yield self.get_wbtips()
        for wbtip_desc in wbtips_desc:
            handler = self.request(body, role='whistleblower', user_id=wbtip_desc['id'])
            yield handler.post()

    @inlineCallbacks
    def test_post_with_deeply_nested_answers_rejected(self):
        # A modified client cannot persist answers nested beyond the
        # questionnaire schema: such a report would later exhaust the recursion
        # limit when an assigned recipient opens, exports or redacts it.
        body = {
          'cmd': 'fill',
          'answers': helpers.forge_nested_answers('aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa')
        }

        wbtips_desc = yield self.get_wbtips()
        for wbtip_desc in wbtips_desc:
            handler = self.request(body, role='whistleblower', user_id=wbtip_desc['id'])
            yield self.assertFailure(handler.post(), errors.InputValidationError)


class TestOperationChangeReceipt(helpers.TestHandlerWithPopulatedDB):
    @inlineCallbacks
    def setUp(self):
        yield helpers.TestHandlerWithPopulatedDB.setUp(self)
        yield self.perform_full_submission_actions()

    @inlineCallbacks
    def test_put(self):
        old_receipt = self.dummySubmission['receipt']
        new_receipt = '1234123412341234'

        if self.clientside_hashing:
            new_receipt_for_server = GCE.derive_key(new_receipt, VALID_SALT)
        else:
            new_receipt_for_server = new_receipt

        # 1. Verify the old receipt works
        self._handler = auth.ReceiptAuthHandler

        handler = self.request({
            'receipt': old_receipt
        })

        response = yield handler.post()
        self.assertTrue('id' in response)

        # 2. Change the receipt
        self._handler = wbtip.Operations

        body = {
          'operation': 'change_receipt',
          'args': {
              'receipt': new_receipt_for_server
          }
        }

        wbtip_desc = (yield self.get_wbtips())[0]
        handler = self.request(body, role='whistleblower', user_id=wbtip_desc['id'])
        yield handler.put()

        # 3. Verify the new receipt works
        self._handler = auth.ReceiptAuthHandler
        handler = self.request({
            'receipt': new_receipt_for_server
        })

        response = yield handler.post()
        self.assertTrue('id' in response)


class TestOperationChangeReceiptServersideHashing(TestOperationChangeReceipt):
    clientside_hashing = False
    wb_legacy_receipt_seed = True
