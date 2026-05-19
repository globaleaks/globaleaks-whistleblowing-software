from twisted.internet.defer import inlineCallbacks

from globaleaks import models
from globaleaks.handlers.admin import user
from globaleaks.handlers.user import db_set_email_validation_token, validate_email
from globaleaks.orm import db_get, transact, tw
from globaleaks.tests import helpers
from globaleaks.utils.crypto import sha256
from globaleaks.utils.utility import datetime_now


@transact
def set_email_validation_token(session, user_id, validation_token, email):
    user = db_get(session, models.User, models.User.id == user_id)
    db_set_email_validation_token(user, email, validation_token)


class TestEmailValidationInstance(helpers.TestHandlerWithPopulatedDB):
    _handler = validate_email.EmailValidation

    @inlineCallbacks
    def test_get_success(self):
        handler = self.request()
        yield set_email_validation_token(
            self.dummyReceiver_1['id'],
            u"token",
            u"test@changeemail.com"
        )

        yield handler.get(u"token")

        # Now we check if the token was update
        for r in (yield tw(user.db_get_users, 1, 'receiver', 'en')):
            if r['id'] == self.dummyReceiver_1['id']:
                self.assertEqual(r['mail_address'], 'test@changeemail.com')
                break

    @inlineCallbacks
    def test_get_failure(self):
        handler = self.request()
        yield set_email_validation_token(
            self.dummyReceiver_1['id'],
            u"token",
            u"test@changeemail.com"
        )

        yield handler.get(u"wrong_token")

        # Now we check if the token was update
        for r in (yield tw(user.db_get_users, 1, 'receiver', 'en')):
            if r['id'] == self.dummyReceiver_1['id']:
                self.assertNotEqual(r['mail_address'], 'test@changeemail.com')
                break
