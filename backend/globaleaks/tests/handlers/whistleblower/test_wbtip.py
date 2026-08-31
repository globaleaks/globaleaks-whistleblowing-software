from unittest.mock import patch

from twisted.internet.defer import inlineCallbacks, succeed


from globaleaks import models
from globaleaks.handlers import auth
from globaleaks.handlers.whistleblower import wbtip
from globaleaks.jobs.delivery import Delivery
from globaleaks.models.config import db_set_config_variable
from globaleaks.orm import transact
from globaleaks.rest import errors
from globaleaks.tests import helpers
from globaleaks.tests.helpers import VALID_SALT
from globaleaks.utils.crypto import GCE
from globaleaks.utils.utility import datetime_now


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

    @transact
    def set_antivirus_enabled(self, session, enabled):
        db_set_config_variable(session, 1, 'antivirus_enabled', enabled)

    @transact
    def set_wbfile_antivirus_state(self, session, file_id, state):
        db_set_config_variable(session, 1, 'antivirus_enabled', True)
        ifile = session.query(models.InternalFile).filter_by(id=file_id).one()
        ifile.state = state
        ifile.verification_date = datetime_now()

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
    def test_post_with_deeply_nested_answers_is_pruned(self):
        # A modified client cannot persist identity answers nested beyond the
        # questionnaire schema: such a report would later exhaust the recursion
        # limit when an assigned recipient opens, exports or redacts it. The
        # schema-driven traversal drops the nested payload (the identity field is
        # not a child of itself) so the operation succeeds carrying no such data,
        # without ever recursing to the attacker-controlled depth.
        identity_field_id = yield self.get_whistleblower_identity_field_id(self.dummyContext['id'])

        body = {
          'identity_field_id': identity_field_id,
          'identity_field_answers': helpers.forge_nested_answers(identity_field_id)
        }

        wbtips_desc = yield self.get_wbtips()
        for wbtip_desc in wbtips_desc:
            handler = self.request(body, role='whistleblower', user_id=wbtip_desc['id'])
            yield handler.post()


@transact
def ask_of_every_report(session, context_id, questionnaire_id):
    """
    Elect on a channel the additional questionnaire it asks by itself
    """
    session.query(models.Context) \
           .filter(models.Context.id == context_id) \
           .update({'additional_questionnaire_id': questionnaire_id})

    session.add(models.ContextAdditionalQuestionnaire({'context_id': context_id,
                                                       'questionnaire_id': questionnaire_id}))


@transact
def ask_of_the_report(session, questionnaire_id):
    """
    Ask an additional questionnaire of the reports, as their recipients do
    """
    session.query(models.InternalTip) \
           .update({'additional_questionnaire_id': questionnaire_id})


class TestWBTipAdditionalQuestionnaire(helpers.TestHandlerWithPopulatedDB):
    """
    The additional questionnaire a channel elects is asked of every report
    """
    _handler = wbtip.WBTipAdditionalQuestionnaire

    @inlineCallbacks
    def setUp(self):
        yield helpers.TestHandlerWithPopulatedDB.setUp(self)
        # The elected questionnaire reuses the schema composing the reports so
        # that the fill-form endpoint stores answers
        yield ask_of_every_report(self.dummyContext['id'], self.dummyContext['questionnaire_id'])
        yield self.perform_full_submission_actions()

    @inlineCallbacks
    def test_the_election_is_asked_of_the_report_from_the_moment_it_is_filed(self):
        wbtips_desc = yield self.get_wbtips()
        for wbtip_desc in wbtips_desc:
            self.assertEqual(wbtip_desc['additional_questionnaire_id'],
                             self.dummyContext['questionnaire_id'])

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
    def test_post_with_deeply_nested_answers_is_pruned(self):
        # A modified client cannot persist answers nested beyond the
        # questionnaire schema: such a report would later exhaust the recursion
        # limit when an assigned recipient opens, exports or redacts it. The
        # schema-driven traversal drops the nested payload at the first level
        # (the forged field is not defined there) so the operation succeeds
        # carrying no such data, without recursing to the attacker depth.
        body = {
          'cmd': 'fill',
          'answers': helpers.forge_nested_answers('aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa')
        }

        wbtips_desc = yield self.get_wbtips()
        for wbtip_desc in wbtips_desc:
            handler = self.request(body, role='whistleblower', user_id=wbtip_desc['id'])
            yield handler.post()


class TestWBTipAdditionalQuestionnaireRequestedOnTheReport(helpers.TestHandlerWithPopulatedDB):
    """
    The questionnaire the recipients ask of a single report is presented to the
    """
    _handler = wbtip.WBTipAdditionalQuestionnaire

    @inlineCallbacks
    def setUp(self):
        yield helpers.TestHandlerWithPopulatedDB.setUp(self)
        yield self.perform_full_submission_actions()
        # The channel of the reports elects no additional questionnaire: the
        # request is the one the recipients make on the single report
        yield ask_of_the_report('default')

    def fill(self, wbtip_desc, answers):
        body = {
          'cmd': 'fill',
          'answers': answers
        }

        return self.request(body, role='whistleblower', user_id=wbtip_desc['id']).post()

    @inlineCallbacks
    def test_the_request_is_presented_with_the_report(self):
        wbtips_desc = yield self.get_wbtips()
        for wbtip_desc in wbtips_desc:
            self.assertEqual(wbtip_desc['additional_questionnaire_id'], 'default')
            self.assertEqual(wbtip_desc['additional_questionnaire']['id'], 'default')
            self.assertTrue(wbtip_desc['additional_questionnaire']['steps'])

    @inlineCallbacks
    def test_post(self):
        answers = yield self.fill_random_answers('default')

        wbtips_desc = yield self.get_wbtips()
        for wbtip_desc in wbtips_desc:
            self.assertEqual(len(wbtip_desc['questionnaires']), 1)

            yield self.fill(wbtip_desc, answers)

        wbtips_desc = yield self.get_wbtips()
        for wbtip_desc in wbtips_desc:
            self.assertEqual(len(wbtip_desc['questionnaires']), 2)

            # The request has been answered and no longer stands: the report is
            # asked nothing until the recipients ask another questionnaire
            self.assertEqual(wbtip_desc['additional_questionnaire_id'], '')

    @inlineCallbacks
    def test_a_report_answers_more_than_one_over_its_life(self):
        answers = yield self.fill_random_answers('default')

        wbtips_desc = yield self.get_wbtips()
        for wbtip_desc in wbtips_desc:
            yield self.fill(wbtip_desc, answers)

        second = yield self.copy_questionnaire(self.dummyContext['questionnaire_id'], 'second')
        yield ask_of_the_report(second['id'])

        answers = yield self.fill_random_answers(second['id'])

        wbtips_desc = yield self.get_wbtips()
        for wbtip_desc in wbtips_desc:
            self.assertEqual(wbtip_desc['additional_questionnaire_id'], second['id'])

            yield self.fill(wbtip_desc, answers)

        wbtips_desc = yield self.get_wbtips()
        for wbtip_desc in wbtips_desc:
            # The questionnaire composing the report and the two it has been
            # asked since, each named by the questionnaire it was given to
            self.assertEqual([questionnaire['questionnaire_id'] for questionnaire in wbtip_desc['questionnaires']],
                             [self.dummyContext['questionnaire_id'], 'default', second['id']])

            self.assertEqual(wbtip_desc['additional_questionnaire_id'], '')

    @inlineCallbacks
    def test_a_report_asked_nothing_answers_nothing(self):
        yield ask_of_the_report('')

        answers = yield self.fill_random_answers('default')

        wbtips_desc = yield self.get_wbtips()
        for wbtip_desc in wbtips_desc:
            yield self.fill(wbtip_desc, answers)

        wbtips_desc = yield self.get_wbtips()
        for wbtip_desc in wbtips_desc:
            self.assertEqual(len(wbtip_desc['questionnaires']), 1)


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


class TestReportAuditLog(helpers.TestHandlerWithPopulatedDB):
    _handler = wbtip.ReportAuditLog

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

    #
    # The log of a report names the objects the report is made of, so that an
    # entry can be traced back to the file or the comment it acts upon
    #
