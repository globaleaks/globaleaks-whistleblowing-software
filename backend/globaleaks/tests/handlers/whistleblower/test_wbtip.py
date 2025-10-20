from twisted.internet.defer import inlineCallbacks, returnValue

from globaleaks.handlers import auth
from globaleaks.handlers.whistleblower import wbtip
from globaleaks.jobs.delivery import Delivery
from globaleaks.tests import helpers


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

    def _assert_upload_log(self, upload_log):
        """Helper method to assert upload log entry"""
        self.assertIsNotNone(upload_log, "upload_file log entry should exist")
        self.assertIn('file_type', upload_log['data'], "file_type should be in log data")
        self.assertIn('filename', upload_log['data'], "filename should be in log data")

    def _assert_comment_log(self, comment_log):
        """Helper method to assert comment log entry"""
        self.assertIsNotNone(comment_log, "add_comment log entry should exist")
        if comment_log.get('data'):
            self.assertNotIn('content', comment_log['data'], "content should not be in log data")

    @inlineCallbacks
    def _upload_attachment(self, wbtip_desc):
        """Helper to upload an attachment"""
        from globaleaks.handlers.whistleblower import attachment
        self._handler = attachment.PostSubmissionAttachment
        handler = self.request(role='whistleblower', user_id=wbtip_desc['id'])
        yield handler.post()

    @inlineCallbacks
    def _get_logs(self, wbtip_desc):
        """Helper to get audit logs"""
        self._handler = wbtip.ReportAuditLog
        handler = self.request(role='whistleblower', user_id=wbtip_desc['id'])
        logs = yield handler.get()
        returnValue(logs)

    @inlineCallbacks
    def _post_comment(self, wbtip_desc, content):
        """Helper to post a comment"""
        body = {'content': content, 'visibility': "internal"}
        self._handler = wbtip.WBTipCommentCollection
        handler = self.request(body, role='whistleblower', user_id=wbtip_desc['id'])
        yield handler.post()

    @inlineCallbacks
    def test_get(self):
        wbtips_desc = yield self.get_wbtips()
        for wbtip_desc in wbtips_desc:
            handler = self.request(role='whistleblower', user_id=wbtip_desc['id'])

            yield handler.get()

    @inlineCallbacks
    def test_audit_log_for_file_upload(self):
        """Test that whistleblower file uploads create audit log entries with file_type and filename"""
        wbtips_desc = yield self.get_wbtips()
        wbtip_desc = wbtips_desc[0]
        
        yield self._upload_attachment(wbtip_desc)
        logs = yield self._get_logs(wbtip_desc)

        upload_log = next((log for log in logs if log['type'] == 'upload_file'), None)
        self._assert_upload_log(upload_log)

    @inlineCallbacks
    def test_audit_log_for_comment(self):
        """Test that whistleblower comments create audit log entries without content"""
        wbtips_desc = yield self.get_wbtips()
        wbtip_desc = wbtips_desc[0]
        
        yield self._post_comment(wbtip_desc, "This is a whistleblower test comment")
        logs = yield self._get_logs(wbtip_desc)

        comment_log = next((log for log in logs if log['type'] == 'add_comment'), None)
        self._assert_comment_log(comment_log)
