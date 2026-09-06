from twisted.internet.defer import inlineCallbacks

from globaleaks import models
from globaleaks.handlers import auth
from globaleaks.models.config import db_set_config_variable
from globaleaks.orm import tw
from globaleaks.rest import errors
from globaleaks.sessions import Sessions
from globaleaks.handlers.user import reset_password
from globaleaks.tests import helpers


class TestPasswordResetInstance(helpers.TestHandlerWithPopulatedDB):
    _handler = reset_password.PasswordResetHandler

    @inlineCallbacks
    def test_post(self):
        data_request = {
            'username': self.dummy_receiver_1['username']
        }

        handler = self.request(data_request)

        yield handler.post()

        # Check that an mail has been created
        yield self.test_model_count(models.Mail, 1)

    @inlineCallbacks
    def test_put(self):
        # Use a valid 64-character hex token format
        valid_reset_token = 'a' * 64
        self.write_reset_token(valid_reset_token, self.dummy_receiver_1['id'])

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

        # The issued session is handed to /login?token=<id> and adopted via
        # /api/auth/tokenauth, so it must be presentable as an authtoken.
        session = Sessions.get(ret['token'])
        self.assertTrue(session.properties.get('authtoken'))

    @inlineCallbacks
    def test_reset_token_is_adoptable_via_tokenauth(self):
        # End-to-end: the session issued by a successful password reset is handed
        # to the client as /login?token=<id> and adopted through
        # /api/auth/tokenauth. The full chain must work -- issuing the reset and
        # then adopting the returned token at the tokenauth endpoint.
        valid_reset_token = 'a' * 64
        self.write_reset_token(valid_reset_token, self.dummy_receiver_1['id'])

        handler = self.request({'reset_token': valid_reset_token,
                                'recovery_key': helpers.USER_REC_KEY_PLAIN,
                                'auth_code': ''})
        ret = yield handler.put()
        self.assertEqual(ret['status'], 'success')

        # Adopt the issued token through the tokenauth endpoint.
        handler = self.request({'authtoken': ret['token']}, handler_cls=auth.TokenAuthHandler)
        response = yield handler.post()
        self.assertIn('id', response)

    @inlineCallbacks
    def test_post_disabled_user(self):
        # Disabled users must not be eligible for password reset token issuance
        yield self.set_user_enabled(self.dummy_receiver_1['id'], False)

        data_request = {
            'username': self.dummy_receiver_1['username']
        }

        handler = self.request(data_request)

        yield handler.post()

        # No mail must have been created for a disabled user
        yield self.test_model_count(models.Mail, 0)

    @inlineCallbacks
    def test_put_disabled_user(self):
        # A reset token issued for an account that is later disabled must not
        # validate nor create a session
        yield self.set_user_enabled(self.dummy_receiver_1['id'], False)

        valid_reset_token = 'a' * 64
        self.write_reset_token(valid_reset_token, self.dummy_receiver_1['id'])

        handler = self.request({'reset_token': valid_reset_token, 'recovery_key': helpers.USER_REC_KEY_PLAIN, 'auth_code': ''})
        ret = yield handler.put()
        self.assertEqual(ret['status'], 'invalid_reset_token_provided')

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


class TestProtectedPasswordReset(helpers.TestHandlerWithPopulatedDB):
    # A freshly initialized database is required so that the protected_users
    # config row (added after the archived test database was generated) is
    # present and can be set.
    initialize_test_database_using_archived_db = False

    _handler = reset_password.PasswordResetHandler

    @inlineCallbacks
    def test_post_protected_user(self):
        # Protected users must not be eligible for self-service password reset
        # token issuance, and the generic response must be preserved
        yield tw(db_set_config_variable, 1, 'protected_users', [self.dummy_receiver_1['id']])

        data_request = {
            'username': self.dummy_receiver_1['username']
        }

        handler = self.request(data_request)

        yield handler.post()

        # No mail must have been created for a protected user
        yield self.test_model_count(models.Mail, 0)
