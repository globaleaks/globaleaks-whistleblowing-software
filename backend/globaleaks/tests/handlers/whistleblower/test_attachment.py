import os

from twisted.internet.defer import inlineCallbacks
from twisted.trial import unittest

from globaleaks.handlers.whistleblower import attachment
from globaleaks.rest import errors
from globaleaks.tests import helpers


class TestAttachmentAuthentication(unittest.TestCase):
    def test_submission_attachment_rejects_missing_session(self):
        handler = attachment.SubmissionAttachment.__new__(attachment.SubmissionAttachment)
        handler.session = None

        self.assertRaises(errors.NotAuthenticated, handler.post)

    def test_post_submission_attachment_rejects_missing_session(self):
        handler = attachment.PostSubmissionAttachment.__new__(attachment.PostSubmissionAttachment)
        handler.session = None

        self.assertRaises(errors.NotAuthenticated, handler.post)


class TestSubmissionAttachment(helpers.TestHandlerWithPopulatedDB):
    _handler = attachment.SubmissionAttachment

    @inlineCallbacks
    def test_post_file_and_verify_deletion_after_submission_expiration(self):
        for _ in range(3):
            handler = self.request(role='whistleblower')
            yield handler.post()

        self.state.tokens.reactor.pump([1] * (self.state.tokens.timeout - 1))

        for f in handler.session.files:
            path = os.path.abspath(os.path.join(self.state.settings.tmp_path, f['filename']))
            self.assertTrue(os.path.exists(path))

        self.state.tokens.reactor.advance(1)

        for f in handler.session.files:
            path = os.path.abspath(os.path.join(self.state.settings.attachments_path, f['filename']))
            yield self.assertFalse(os.path.exists(path))

    @inlineCallbacks
    def test_post_file_on_unexistent_submission(self):
        handler = self.request()
        yield self.assertRaises(errors.NotAuthenticated, handler.post, 'unexistent_submission')


class TestPostSubmissionAttachment(helpers.TestHandlerWithPopulatedDB):
    _handler = attachment.PostSubmissionAttachment

    @inlineCallbacks
    def test_post(self):
        yield self.perform_full_submission_actions()

        wbtips_desc = yield self.get_wbtips()
        for wbtip_desc in wbtips_desc:
            handler = self.request(role='whistleblower', user_id=wbtip_desc['id'])
            yield handler.post()
