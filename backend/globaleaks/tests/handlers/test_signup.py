from twisted.internet.defer import inlineCallbacks
from globaleaks import models
from globaleaks.handlers import signup
from globaleaks.models.config import db_set_config_variable
from globaleaks.orm import transact, tw
from globaleaks.rest import errors
from globaleaks.tests import helpers


@transact
def get_signup_token(session):
    return session.query(models.Subscriber.activation_token).first()[0]


class TestSignup(helpers.TestHandler):
    _handler = signup.Signup

    def test_post_with_signup_disabled(self):
        handler = self.request(self.dummySignup)
        return self.assertFailure(handler.post(), errors.ForbiddenOperation)

    @inlineCallbacks
    def test_post_with_signup_enabled(self):
        yield tw(db_set_config_variable, 1, 'enable_signup', True)

        handler = self.request(self.dummySignup)
        yield handler.post()


class TestSignupActivation(helpers.TestHandler):
    _handler = signup.SignupActivation

    @inlineCallbacks
    def _signup(self):
        yield tw(db_set_config_variable, 1, 'enable_signup', True)

        yield self.test_model_count(models.User, 0)

        self._handler = signup.Signup
        handler = self.request(self.dummySignup)
        yield handler.post()

        self._handler = signup.SignupActivation
        handler = self.request(self.dummySignup)
        token = yield get_signup_token()
        yield handler.post(token)

    def test_get_with_signup_disabled(self):
        handler = self.request(self.dummySignup)
        return self.assertFailure(handler.post(u'valid_or_invalid'), errors.ForbiddenOperation)

    @inlineCallbacks
    def test_valid_signup(self):
        yield self._signup()

        yield self.test_model_count(models.User, 2)

    @inlineCallbacks
    def test_invalid_signup_with_invalid_activation_token(self):
        yield tw(db_set_config_variable, 1, 'enable_signup', True)

        handler = self.request(self.dummySignup)
        r = yield handler.post(u'invalid')

        self.assertTrue(not r)
