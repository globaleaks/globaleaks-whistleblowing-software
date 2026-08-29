from collections import Counter

from twisted.internet.defer import inlineCallbacks

from globaleaks.handlers import auditor as auditlog
from globaleaks.rest import errors
from globaleaks.tests import helpers

class TestAuditLog(helpers.TestHandlerWithPopulatedDB):
    _handler = auditlog.AuditLog

    @inlineCallbacks
    def test_get(self):
        yield self.perform_full_submission_actions()

        handler = self.request({}, user_id=self.dummyAnalyst['id'], role='auditor')
        response = yield handler.get()

        self.assertTrue(isinstance(response, list))

        # A full submission run records, for each of the two reports, its
        # creation, the files attached to it and the comments exchanged on it
        types = Counter(entry['type'] for entry in response)

        self.assertEqual(types['whistleblower_new_report'], 2)
        self.assertEqual(types['whistleblower_add_answers'], 2)
        self.assertEqual(types['whistleblower_upload_file'], 4)
        self.assertEqual(types['whistleblower_add_comment'], 2)
        self.assertEqual(types['add_comment'], 2)
        self.assertEqual(len(response), sum(types.values()))

    def test_get_as_admin_is_refused(self):
        # The audit log is the domain of the auditor role alone: the
        # administrators hold no mixed access to it
        handler = self.request({}, role='admin')

        return self.assertRaises(errors.NotAuthenticated, handler.get)

    @inlineCallbacks
    def test_the_entries_name_who_acted(self):
        yield self.perform_full_submission_actions()

        handler = self.request({}, user_id=self.dummyAnalyst['id'], role='auditor')
        response = yield handler.get()

        # The auditor reaches no other API: the entries carry the username
        self.assertTrue(all('username' in entry for entry in response))


class TestAccessLog(helpers.TestHandlerWithPopulatedDB):
    _handler = auditlog.AccessLog

    def test_get(self):
        handler = self.request({}, user_id=self.dummyAnalyst['id'], role='auditor')

        # During tests the file does not exists but this is enought to test
        return self.assertRaises(errors.ResourceNotFound, handler.get)


class TestDebugLog(helpers.TestHandlerWithPopulatedDB):
    _handler = auditlog.DebugLog

    def test_get(self):
        handler = self.request({}, user_id=self.dummyAnalyst['id'], role='auditor')

        # During tests the file does not exists but this is enought to test
        return self.assertRaises(errors.ResourceNotFound, handler.get)


class TestTipsCollection(helpers.TestHandlerWithPopulatedDB):
    _handler = auditlog.TipsCollection

    @inlineCallbacks
    def test_get(self):
        yield self.perform_full_submission_actions()

        handler = self.request({}, user_id=self.dummyAnalyst['id'], role='auditor')
        response = yield handler.get()

        self.assertTrue(isinstance(response, list))
        self.assertEqual(len(response), 2)


class TestJobsTiming(helpers.TestHandler):
    _handler = auditlog.JobsTiming

    @inlineCallbacks
    def test_get(self):
        handler = self.request({}, user_id=self.dummyAnalyst['id'], role='auditor')

        yield handler.get()
