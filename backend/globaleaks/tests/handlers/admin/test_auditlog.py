from twisted.internet.defer import inlineCallbacks

from globaleaks.handlers.admin import auditlog
from globaleaks.rest import errors
from globaleaks.tests import helpers

class TestAuditLog(helpers.TestHandlerWithPopulatedDB):
    _handler = auditlog.AuditLog

    @inlineCallbacks
    def test_get(self):
        yield self.perform_full_submission_actions()

        handler = self.request({}, role='admin')
        response = yield handler.get()

        self.assertTrue(isinstance(response, list))
        # With the audit log enhancements, we now log file uploads and comments too
        self.assertGreaterEqual(len(response), 2)


class TestAccessLog(helpers.TestHandlerWithPopulatedDB):
    _handler = auditlog.AccessLog

    def test_get(self):
        handler = self.request({}, role='admin')

        # During tests the file does not exists but this is enought to test
        return self.assertRaises(errors.ResourceNotFound, handler.get)


class TestDebugLog(helpers.TestHandlerWithPopulatedDB):
    _handler = auditlog.DebugLog

    def test_get(self):
        handler = self.request({}, role='admin')

        # During tests the file does not exists but this is enought to test
        return self.assertRaises(errors.ResourceNotFound, handler.get)


class TestTipsCollection(helpers.TestHandlerWithPopulatedDB):
    _handler = auditlog.TipsCollection

    @inlineCallbacks
    def test_get(self):
        yield self.perform_full_submission_actions()

        handler = self.request({}, role='admin')
        response = yield handler.get()

        self.assertTrue(isinstance(response, list))
        self.assertEqual(len(response), 2)


class TestAuditLogByObject(helpers.TestHandlerWithPopulatedDB):
    _handler = auditlog.AuditLogByObject

    @inlineCallbacks
    def _get_test_tip_id(self):
        """Helper method to get a tip ID for testing"""
        self._handler = auditlog.TipsCollection
        tips_handler = self.request({}, role='admin')
        tips = yield tips_handler.get()
        self.assertTrue(len(tips) > 0)
        self._handler = auditlog.AuditLogByObject
        return tips[0]['id']

    @inlineCallbacks
    def test_get(self):
        """Test basic retrieval of audit log for a tip"""
        yield self.perform_full_submission_actions()
        tip_id = yield self._get_test_tip_id()

        handler = self.request({}, role='admin')
        response = yield handler.get(tip_id)

        self.assertTrue(isinstance(response, list))
        self.assertGreater(len(response), 0)

    @inlineCallbacks
    def test_get_with_complete_submission(self):
        """Test that audit log entries have proper structure with data fields"""
        yield self.perform_full_submission_actions()
        tip_id = yield self._get_test_tip_id()

        handler = self.request({}, role='admin')
        logs = yield handler.get(tip_id)

        # Verify we get audit logs
        self.assertGreater(len(logs), 0)

        # Verify each log has required fields
        for log in logs:
            self.assertIn('date', log)
            self.assertIn('type', log)
            self.assertIn('data', log)

            # If it's a file-related action, verify it has file metadata
            if log['type'] in ['upload_file', 'delete_attachment', 'delete_file']:
                self.assertTrue(isinstance(log['data'], dict))
                # File operations should have either file_type or other metadata
                self.assertTrue(len(log['data']) > 0)


class TestJobsTiming(helpers.TestHandler):
    _handler = auditlog.JobsTiming

    @inlineCallbacks
    def test_get(self):
        handler = self.request({}, role='admin')

        yield handler.get()
