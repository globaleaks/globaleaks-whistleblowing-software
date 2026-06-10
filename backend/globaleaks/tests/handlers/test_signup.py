import re

from twisted.internet.defer import inlineCallbacks
from globaleaks import models
from globaleaks.handlers import signup
from globaleaks.handlers.admin import tenant
from globaleaks.models.config import db_set_config_variable
from globaleaks.orm import transact, tw
from globaleaks.rest import errors
from globaleaks.tests import helpers


@transact
def get_signup_token(session):
    # The raw activation token is delivered via email only (the DB stores
    # the SHA-256 of the token). Extract it back from the scheduled mail.
    mail = session.query(models.Mail) \
                  .order_by(models.Mail.creation_date.desc()).first()
    match = re.search(r'activation\?token=([A-Za-z0-9]+)', mail.body)
    return match.group(1)


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

    @inlineCallbacks
    def test_post_rejects_existing_tenant_subdomain(self):
        yield tw(db_set_config_variable, 1, 'enable_signup', True)

        # An administrator-created tenant already owns the requested subdomain
        yield tenant.create({'active': True, 'mode': 'default',
                             'name': 'victim', 'subdomain': self.dummySignup['subdomain']})

        # A public signup must not be able to hijack the same subdomain
        handler = self.request(self.dummySignup)
        yield self.assertFailure(handler.post(), errors.ForbiddenOperation)


class TestSignupActivation(helpers.TestHandler):
    _handler = signup.SignupActivation

    @inlineCallbacks
    def _signup(self, mode):
        yield tw(db_set_config_variable, 1, 'enable_signup', True)
        yield tw(db_set_config_variable, 1, 'mode', mode)

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
    def test_valid_signup_in_default_mode(self):
        yield self._signup('default')

        yield self.test_model_count(models.User, 2)

    @inlineCallbacks
    def test_valid_signup_in_demo_mode(self):
        yield self._signup('demo')

        yield self.test_model_count(models.User, 2)

    @inlineCallbacks
    def test_valid_signup_in_wbpa_mode(self):
        yield self._signup('wbpa')

        yield self.test_model_count(models.User, 1)

    @inlineCallbacks
    def test_invalid_signup_with_invalid_activation_token(self):
        yield tw(db_set_config_variable, 1, 'enable_signup', True)

        handler = self.request(self.dummySignup)
        r = yield handler.post(u'invalid')

        self.assertTrue(not r)
