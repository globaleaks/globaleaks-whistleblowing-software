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
        self.assertEqual(len(response), 2)


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
    def test_get(self):
        yield self.perform_full_submission_actions()

        # Get a tip ID to test with by setting the handler temporarily
        self._handler = auditlog.TipsCollection
        tips_handler = self.request({}, role='admin')
        tips = yield tips_handler.get()
        self.assertTrue(len(tips) > 0)
        tip_id = tips[0]['id']

        # Reset handler and test admin access
        self._handler = auditlog.TipAuditLog
        handler = self.request({}, role='admin')
        response = yield handler.get(tip_id)

        self.assertTrue(isinstance(response, list))

    @inlineCallbacks
    def test_get_auditor(self):
        yield self.perform_full_submission_actions()

        # Get a tip ID to test with by setting the handler temporarily
        self._handler = auditlog.TipsCollection
        tips_handler = self.request({}, role='admin')
        tips = yield tips_handler.get()
        self.assertTrue(len(tips) > 0)
        tip_id = tips[0]['id']

        # Reset handler and test auditor access
        self._handler = auditlog.TipAuditLog
        handler = self.request({}, role='auditor')
        response = yield handler.get(tip_id)

        self.assertTrue(isinstance(response, list))


class TestJobsTiming(helpers.TestHandler):
    _handler = auditlog.JobsTiming

    @inlineCallbacks
    def test_get(self):
        handler = self.request({}, role='admin')

        yield handler.get()
