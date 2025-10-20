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


class TestTipAuditLog(helpers.TestHandlerWithPopulatedDB):
    _handler = auditlog.TipAuditLog

    @inlineCallbacks
    def _get_test_tip_id(self):
        """Helper method to get a tip ID for testing"""
        self._handler = auditlog.TipsCollection
        tips_handler = self.request({}, role='admin')
        tips = yield tips_handler.get()
        self.assertTrue(len(tips) > 0)
        self._handler = auditlog.TipAuditLog
        return tips[0]['id']

    @inlineCallbacks
    def test_get(self):
        yield self.perform_full_submission_actions()
        tip_id = yield self._get_test_tip_id()

        handler = self.request({}, role='admin')
        response = yield handler.get(tip_id)

        self.assertTrue(isinstance(response, list))


class TestJobsTiming(helpers.TestHandler):
    _handler = auditlog.JobsTiming

    @inlineCallbacks
    def test_get(self):
        handler = self.request({}, role='admin')

        yield handler.get()
