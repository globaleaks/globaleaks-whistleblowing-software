import base64
import os
import time

from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.twofactor.totp import TOTP
from cryptography.hazmat.primitives.hashes import SHA1

from nacl.encoding import Base32Encoder

from twisted.internet.defer import inlineCallbacks

from globaleaks.handlers import user
from globaleaks.handlers.base import BaseHandler
from globaleaks.handlers.user.operation import UserOperationHandler
from globaleaks.rest import errors
from globaleaks.state import State
from globaleaks.tests import helpers
from globaleaks.utils.crypto import generateRandomPassword, GCE, sha256
from globaleaks.utils.utility import datetime_null


class TestUserInstance(helpers.TestHandlerWithPopulatedDB):
    _handler = user.UserInstance

    @inlineCallbacks
    def test_get(self):
        handler = self.request(user_id=self.dummyReceiver_1['id'], role='receiver')

        yield handler.get()

    @inlineCallbacks
    def test_handler_update_key(self):
        handler = self.request(user_id=self.dummyReceiver_1['id'], role='receiver')

        response = yield handler.get()

        # perform and test key update
        response['pgp_key_public'] = helpers.PGPKEYS['VALID_PGP_KEY2_PUB']
        response['pgp_key_remove'] = False
        handler = self.request(response, user_id=self.dummyReceiver_1['id'], role='receiver')
        response = yield handler.put()

        self.assertEqual(response['pgp_key_fingerprint'],
                         'CECDC5D2B721900E65639268846C82DB1F9B45E2')

        self.assertEqual(response['pgp_key_public'],
                         helpers.PGPKEYS['VALID_PGP_KEY2_PUB'])

        # perform and test key removal
        response['pgp_key_remove'] = True
        handler = self.request(response, user_id=self.dummyReceiver_1['id'], role='receiver')
        response = yield handler.put()

        self.assertEqual(response['pgp_key_fingerprint'], '')
        self.assertEqual(response['pgp_key_public'], '')
        self.assertEqual(response['pgp_key_expiration'], datetime_null())

    @inlineCallbacks
    def test_load_malformed_key(self):
        handler = self.request(user_id=self.dummyReceiver_1['id'], role='receiver')

        response = yield handler.get()

        response['pgp_key_public'] = helpers.PGPKEYS['VALID_PGP_KEY1_PUB'].replace('A', 'B')
        response['pgp_key_remove'] = False
        handler = self.request(response, user_id=self.dummyReceiver_1['id'], role='receiver')
        yield self.assertFailure(handler.put(), errors.InputValidationError)

    @inlineCallbacks
    def test_change_name(self):
        handler = self.request(user_id=self.dummyReceiver_1['id'], role='receiver')

        response = yield handler.get()
        response['name'] = "Test Name"
        handler = self.request(response, user_id=self.dummyReceiver_1['id'], role='receiver',
                               permissions={'can_edit_general_settings': True})

        response = yield handler.put()
        self.assertEqual(response['name'], 'Test Name')

    @inlineCallbacks
    def test_start_email_change_process(self):
        handler = self.request(user_id=self.dummyReceiver_1['id'], role='receiver')

        response = yield handler.get()

        email = "change1@test.com"
        response['mail_address'] = email
        handler = self.request(response, user_id=self.dummyReceiver_1['id'], role='receiver',
                               permissions={'can_edit_general_settings': True})
        response = yield handler.put()

        self.assertNotEqual(response['mail_address'], email)
        self.assertEqual(response['change_email_address'], email)

        email = "change2@test.com"
        response['mail_address'] = email
        handler = self.request(response, user_id=self.dummyReceiver_1['id'], role='receiver',
                               permissions={'can_edit_general_settings': True})
        response = yield handler.put()

        self.assertEqual(response['change_email_address'], email)


class TestUser2FAEnrollment(helpers.TestHandlerWithPopulatedDB):
    _handler = user.operation.UserOperationHandler

    @inlineCallbacks
    def test_2fa(self):
        totp_secret = 'B6IZ6BEH6BMWDBZ2ND7PGAQN2GIBVOVX'

        # Attempt enrolling for 2FA with an invalid token
        data_request = {
            'operation': 'enable_2fa',
            'args': {
                'secret': totp_secret,
                'token': 'invalid_token'
            }
        }

        handler = self.request(data_request, role='receiver')

        self.assertFailure(handler.put(), errors.InvalidTwoFactorAuthCode)

        # Attempt enrolling for 2FA with a valid token
        totp = TOTP(Base32Encoder.decode(totp_secret), 6, SHA1(), 30, default_backend())  # noqa: S303 - SHA1 mandated by the TOTP standard (RFC 6238)
        current_token = totp.generate(time.time()).decode()

        data_request = {
            'operation': 'enable_2fa',
            'args': {
                'secret': totp_secret,
                'token': current_token
            }
        }

        handler = self.request(data_request, role='receiver')

        yield handler.put()

        self.state.TwoFactorTokens.clear()

        data_request = {
            'operation': 'disable_2fa',
            'args': {}
        }

        current_token = totp.generate(time.time()).decode()

        handler = self.request(data_request, role='receiver', headers={'x-confirmation': current_token})

        yield handler.put()


class TestUserOperations(helpers.TestHandlerWithPopulatedDB):
    _handler = UserOperationHandler

    def _test_operation_handler(self, operation, args=None, headers=None, properties=None):
        data_request = {
            'operation': operation,
            'args': args if args is not None else {}
        }

        handler = self.request(data_request, role='receiver', headers=headers, properties=properties)
        handler.request.path = b'/api/user/operations'
        return handler.put()

    @inlineCallbacks
    def test_user_change_password(self):
        # The voluntary password change requires confirmation of the current
        # credential; the confirmation is encoded as the client encodes it.
        self.patch(BaseHandler, 'check_confirmation', BaseHandler.real_check_confirmation)

        confirmation = base64.b64encode(helpers.VALID_KEY.encode('utf-16-le')).decode()

        yield self.assertFailure(self._test_operation_handler('change_password',
                                                              {'password': helpers.VALID_KEY},
                                                              headers={'x-confirmation': confirmation}),
                                 errors.PasswordReuseError)

        NEW_KEY = GCE.derive_key(generateRandomPassword(20), helpers.VALID_SALT)

        yield self._test_operation_handler('change_password',
                                           {'password': NEW_KEY},
                                           headers={'x-confirmation': confirmation})

    def test_user_change_password_requires_current_credential(self):
        # A voluntary password change without a valid confirmation of the
        # current credential must be rejected (CWE-620). The confirmation
        # check is synchronous and raises before any deferred is created.
        self.patch(BaseHandler, 'check_confirmation', BaseHandler.real_check_confirmation)

        NEW_KEY = GCE.derive_key(generateRandomPassword(20), helpers.VALID_SALT)

        self.assertRaises(errors.InvalidAuthentication,
                          self._test_operation_handler,
                          'change_password', {'password': NEW_KEY})

        WRONG_KEY = GCE.derive_key(generateRandomPassword(20), helpers.VALID_SALT)
        wrong_confirmation = base64.b64encode(WRONG_KEY.encode('utf-16-le')).decode()
        self.assertRaises(errors.InvalidAuthentication,
                          self._test_operation_handler,
                          'change_password', {'password': NEW_KEY},
                          headers={'x-confirmation': wrong_confirmation})

    @inlineCallbacks
    def test_user_change_password_forced_skips_confirmation(self):
        # When a password change is forced (first login or password reset) the
        # session is flagged and the confirmation of the current credential is
        # not required, as the user may be recovering access through a reset
        # token.
        self.patch(BaseHandler, 'check_confirmation', BaseHandler.real_check_confirmation)

        NEW_KEY = GCE.derive_key(generateRandomPassword(20), helpers.VALID_SALT)

        yield self._test_operation_handler('change_password',
                                           {'password': NEW_KEY},
                                           properties={'password_change_needed': True})

    def test_user_get_recovery_key(self):
        return self._test_operation_handler('get_recovery_key')

    def test_user_get_usernames(self):
        return self._test_operation_handler('get_users_names')

    def test_user_accepted_privacy_policy(self):
        return self._test_operation_handler('accepted_privacy_policy')

    @inlineCallbacks
    def test_reset_token_session_restricted_to_change_password(self):
        reset_token = 'a' * 64
        properties = {'reset_token': reset_token}

        # An operation other than the password change is not dispatched
        handler = self.request({'operation': 'get_users_names', 'args': {}},
                               role='receiver', properties=properties)
        handler.request.path = b'/api/user/operations'
        self.assertIsNone((yield handler.put()))

        # The password change itself remains available
        token_path = os.path.abspath(os.path.join(
            State.settings.ramdisk_path, sha256(reset_token).decode()))
        with open(token_path, "w") as f:
            f.write(self.dummyReceiver_1['id'])

        new_key = GCE.derive_key(generateRandomPassword(20), helpers.VALID_SALT)
        handler = self.request({'operation': 'change_password', 'args': {'password': new_key}},
                               role='receiver', properties=properties)
        handler.request.path = b'/api/user/operations'
        yield handler.put()
