import os

from twisted.internet.defer import inlineCallbacks

from globaleaks.handlers.whistleblower import attachment
from globaleaks.models.config import db_set_config_variable
from globaleaks.orm import tw
from globaleaks.rest import errors
from globaleaks.tests import helpers


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
    def test_post_file_rejected_above_max_disk_space(self):
        yield tw(db_set_config_variable, 1, 'max_disk_space', 1)

        handler = self.request(role='whistleblower')
        handler.uploaded_file['size'] = 512 * 1024
        yield handler.post()

        handler.uploaded_file = self.get_dummy_attachment()
        handler.uploaded_file['size'] = 600 * 1024
        yield self.assertFailure(handler.post(), errors.TenantLimitExceeded)

        self.assertEqual(len(handler.session.files), 1)
        self.assertFalse(os.path.exists(handler.uploaded_file['body'].filepath))

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

    @inlineCallbacks
    def test_post_rejected_above_max_disk_space(self):
        yield self.perform_full_submission_actions()
        yield tw(db_set_config_variable, 1, 'max_disk_space', 1)

        wbtips_desc = yield self.get_wbtips()
        handler = self.request(role='whistleblower', user_id=wbtips_desc[0]['id'])
        handler.uploaded_file['size'] = 2 * 1024 * 1024
        yield self.assertFailure(handler.post(), errors.TenantLimitExceeded)
        self.assertFalse(os.path.exists(handler.uploaded_file['body'].filepath))
