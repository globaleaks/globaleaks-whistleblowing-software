import os
from twisted.internet.defer import inlineCallbacks

from globaleaks import models
from globaleaks.rest import errors
from globaleaks.state import State
from globaleaks.tests import helpers


class TestPasswordResetInstance(helpers.TestHandlerWithPopulatedDB):
    from globaleaks.handlers.user import reset_password
    _handler = reset_password.PasswordResetHandler

    @inlineCallbacks
    def test_post(self):
        data_request = {
            'username': self.dummyReceiver_1['username']
        }

        handler = self.request(data_request)

        yield handler.post()

        # Check that an mail has been created
        yield self.test_model_count(models.Mail, 1)

    @inlineCallbacks
    def test_put(self):
        # Use a valid 64-character hex token format
        valid_reset_token = 'a' * 64

        with open(os.path.abspath(os.path.join(State.settings.ramdisk_path, valid_reset_token)), "w") as f:
            f.write(self.dummyReceiver_1['id'])

        # Wrong token (valid format but non-existent)
        handler = self.request({'reset_token': 'b' * 64, 'recovery_key': '', 'auth_code': ''})
        ret = yield handler.put()
        self.assertEqual(ret['status'], 'invalid_reset_token_provided')

        # Missing recovery key
        handler = self.request({'reset_token': valid_reset_token, 'recovery_key': '', 'auth_code': ''})
        ret = yield handler.put()
        self.assertEqual(ret['status'], 'require_recovery_key')

        # Wrong recovery key
        handler = self.request({'reset_token': valid_reset_token, 'recovery_key': 'wrong_recovery_key', 'auth_code': ''})
        ret = yield handler.put()
        self.assertEqual(ret['status'], 'require_recovery_key')

        # Success
        handler = self.request({'reset_token': valid_reset_token, 'recovery_key': helpers.USER_REC_KEY_PLAIN, 'auth_code': ''})
        ret = yield handler.put()
        self.assertEqual(ret['status'], 'success')

    def test_put_rejects_invalid_token_format(self):
        """Test that reset tokens not matching the expected hex format are rejected"""
        invalid_tokens = [
            '../../../etc/passwd',
            '/etc/passwd',
            'valid_reset_token',
            '../../secret',
            'a' * 63,  # Too short
            'a' * 65,  # Too long
            'g' * 64,  # Invalid hex characters
        ]

        for invalid_token in invalid_tokens:
            handler = self.request({'reset_token': invalid_token, 'recovery_key': '', 'auth_code': ''})
            self.assertRaises(errors.InputValidationError, handler.put)
