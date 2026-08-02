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


@transact
def get_subscriber(session):
    subscriber = session.query(models.Subscriber).first()

    return {
        'subdomain': subscriber.subdomain,
        'name': subscriber.name,
        'surname': subscriber.surname,
        'email': subscriber.email,
        'organization_name': subscriber.organization_name,
        'organization_email': subscriber.organization_email
    }


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
    def test_post_with_organization_requested(self):
        yield tw(db_set_config_variable, 1, 'enable_signup', True)
        yield tw(db_set_config_variable, 1, 'signup_request_organization', True)

        handler = self.request(self.dummySignup)
        yield handler.post()

        subscriber = yield get_subscriber()
        self.assertEqual(subscriber['organization_name'], self.dummySignup['organization_name'])
        self.assertEqual(subscriber['organization_email'], self.dummySignup['organization_email'])

    @inlineCallbacks
    def test_post_with_organization_not_requested(self):
        yield tw(db_set_config_variable, 1, 'enable_signup', True)

        handler = self.request(self.dummySignup)
        yield handler.post()

        # The data of the organization are not collected and are dropped even
        # when a client submits them
        subscriber = yield get_subscriber()
        self.assertEqual(subscriber['organization_name'], '')
        self.assertEqual(subscriber['organization_email'], '')

    @inlineCallbacks
    def test_post_with_subdomain_not_requested(self):
        yield tw(db_set_config_variable, 1, 'enable_signup', True)
        yield tw(db_set_config_variable, 1, 'signup_request_subdomain', False)

        handler = self.request(self.dummySignup)
        yield handler.post()

        # The subscriber keeps a placeholder subdomain, the column being unique,
        # while the site is left with no subdomain configured
        subscriber = yield get_subscriber()
        self.assertTrue(subscriber['subdomain'])
        self.assertNotEqual(subscriber['subdomain'], self.dummySignup['subdomain'])

    @inlineCallbacks
    def test_post_with_invite_only_and_no_invitation(self):
        yield tw(db_set_config_variable, 1, 'enable_signup', True)
        yield tw(db_set_config_variable, 1, 'signup_invite_only', True)

        handler = self.request(self.dummySignup)
        yield self.assertFailure(handler.post(), errors.ForbiddenOperation)

    @inlineCallbacks
    def test_post_without_subdomain_when_requested(self):
        yield tw(db_set_config_variable, 1, 'enable_signup', True)

        request = dict(self.dummySignup)
        request['subdomain'] = ''

        handler = self.request(request)
        yield self.assertFailure(handler.post(), errors.InputValidationError)


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
