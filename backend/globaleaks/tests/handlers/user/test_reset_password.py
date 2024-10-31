# -*- coding: utf-8 -*-
import os
from twisted.internet.defer import inlineCallbacks

from globaleaks import models
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
        valid_reset_token = 'valid_reset_token'

        try:
            with open(os.path.abspath(os.path.join(State.settings.ramdisk_path, valid_reset_token)), "w") as f:
                f.write(self.dummyReceiver_1['id'])
        except:
            pass

        # Wrong token
        handler = self.request({'reset_token': 'wrong_token', 'recovery_key': '', 'auth_code': ''})
        ret = yield handler.put()
        self.assertEqual(ret['status'], 'invalid_reset_token_provided')

        # Missing recovery key
        handler = self.request({'reset_token': 'valid_reset_token', 'recovery_key': '', 'auth_code': ''})
        ret = yield handler.put()
        self.assertEqual(ret['status'], 'require_recovery_key')

        # Wrong recovery key
        handler = self.request({'reset_token': 'valid_reset_token', 'recovery_key': 'wrong_recovery_key', 'auth_code': ''})
        ret = yield handler.put()
        self.assertEqual(ret['status'], 'require_recovery_key')

        # Success
        handler = self.request({'reset_token': 'valid_reset_token', 'recovery_key': helpers.USER_REC_KEY_PLAIN, 'auth_code': ''})
        ret = yield handler.put()
        self.assertEqual(ret['status'], 'success')
