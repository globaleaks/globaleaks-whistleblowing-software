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

    @inlineCallbacks
    def test_questionnaire_hashes(self):
        wbtips_desc = yield self.get_wbtips()
        for wbtip_desc in wbtips_desc:
            self.verify_questionnaire_hashes(wbtip_desc)


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

    @inlineCallbacks
    def test_get_allows_infected_file(self):
        yield self.perform_minimal_submission_actions()
        yield Delivery().run()

        wbtip_desc = (yield self.get_wbtips())[0]
        wbfile_id = (yield self.get_ifiles_by_wbtip_id(wbtip_desc['id']))[0]

        yield self.set_wbfile_antivirus_state(wbfile_id, models.EnumStateFile.infected.name)

        handler = self.request(role='whistleblower', user_id=wbtip_desc['id'])
        yield handler.get(wbfile_id)
        self.assertNotEqual(handler.request.getResponseBody(), '')

    @inlineCallbacks
    def test_get_allows_infected_file_after_unsafe_scan(self):
        yield self.perform_minimal_submission_actions()
        yield self.set_antivirus_enabled(True)

        with patch('globaleaks.jobs.delivery.FileAnalysis.scan_file', return_value=succeed('unsafe')):
            yield Delivery().run()

        wbtip_desc = (yield self.get_wbtips())[0]
        wbfile_id = (yield self.get_ifiles_by_wbtip_id(wbtip_desc['id']))[0]

        handler = self.request(role='whistleblower', user_id=wbtip_desc['id'])
        yield handler.get(wbfile_id)
        self.assertNotEqual(handler.request.getResponseBody(), '')

    @inlineCallbacks
    def test_get_allows_pending_file(self):
        yield self.perform_minimal_submission_actions()
        yield Delivery().run()

        wbtip_desc = (yield self.get_wbtips())[0]
        wbfile_id = (yield self.get_ifiles_by_wbtip_id(wbtip_desc['id']))[0]

        yield self.set_wbfile_antivirus_state(wbfile_id, models.EnumStateFile.pending.name)

        handler = self.request(role='whistleblower', user_id=wbtip_desc['id'])
        yield handler.get(wbfile_id)
        self.assertNotEqual(handler.request.getResponseBody(), '')


class WBTipIdentityHandler(helpers.TestHandlerWithPopulatedDB):
    _handler = wbtip.WBTipIdentityHandler

    @inlineCallbacks
    def setUp(self):
        yield helpers.TestHandlerWithPopulatedDB.setUp(self)
        yield self.perform_full_submission_actions()

    @inlineCallbacks
    def test_put(self):
        # FIXME:
        #  The current test simply update a not existing field rising the code coverage
        #  and testing that all goes well even if a wrong id is provided or the feature
        #  is not enable.
        #
        #  As improval we should load effectively a whistleblower_identity_field on the
        #  context and validate the update.
        body = {
          'identity_field_id': 'b1f82a33-8df1-43d2-b36f-da53f0000000',
          'identity_field_answers': {}
        }

        wbtips_desc = yield self.get_wbtips()
        for wbtip_desc in wbtips_desc:
            handler = self.request(body, role='whistleblower', user_id=wbtip_desc['id'])

            yield handler.post()


class TestOperationChangeReceipt(helpers.TestHandlerWithPopulatedDB):
    @inlineCallbacks
    def setUp(self):
        yield helpers.TestHandlerWithPopulatedDB.setUp(self)
        yield self.perform_full_submission_actions()

    @inlineCallbacks
    def test_put(self):
        old_receipt = self.dummySubmission['receipt']
        new_receipt = '1234123412341234'

        # 1. Verify the old receipt works
        self._handler = auth.ReceiptAuthHandler

        handler = self.request({
            'receipt': old_receipt
        })

        response = yield handler.post()
        self.assertTrue('id' in response)

        # 2. Change the receipt
        self._handler = wbtip.Operations

        session_properties = {
            'new_receipt': new_receipt
        }

        body = {
          'operation': 'change_receipt',
          'args': {}
        }

        wbtip_desc = (yield self.get_wbtips())[0]
        handler = self.request(body, role='whistleblower', user_id=wbtip_desc['id'], properties=session_properties)
        yield handler.put()

        # 3. Verify the new receipt works
        self._handler = auth.ReceiptAuthHandler
        handler = self.request({
            'receipt': new_receipt
        })

        response = yield handler.post()
        self.assertTrue('id' in response)


class TestOperationChangeReceiptServersideHashing(TestOperationChangeReceipt):
    clientside_hashing = False


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

            yield handler.get(wbtip_desc['id'])
