from twisted.internet.defer import inlineCallbacks, returnValue
from globaleaks import models
from globaleaks.handlers import signup
from globaleaks.handlers.admin.invite import create_invite
from globaleaks.models.config import DEFAULT_PROFILE_ID, db_set_config_variable
from globaleaks.orm import transact, tw
from globaleaks.rest import errors
from globaleaks.state import State
from globaleaks.tests import helpers


@transact
def get_signup_token(session):
    return session.query(models.Subscriber.activation_token).first()[0]


@transact
def get_invitation(session):
    subscriber = session.query(models.Subscriber).one()

    return {
        'token': subscriber.activation_token,
        'organization_name': subscriber.organization_name,
        'organization_email': subscriber.organization_email
    }


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
    def test_post_with_the_data_published_by_the_identity_provider(self):
        yield tw(db_set_config_variable, 1, 'enable_signup', True)
        yield tw(db_set_config_variable, DEFAULT_PROFILE_ID, 'idp', True)

        verify_token = State.oidcauth.verify_token
        self.addCleanup(setattr, State.oidcauth, 'verify_token', verify_token)

        # The claims not conforming to the format expected for the field they
        # are trusted for are discarded in favor of the compiled values
        State.oidcauth.verify_token = lambda *args: {'sub': 'subject1',
                                                     'given_name': 'Mario',
                                                     'family_name': 'Rossi',
                                                     'email': 'not an address'}

        handler = self.request(self.dummySignup, headers={'Authorization': 'Bearer token'})
        yield handler.post()

        subscriber = yield get_subscriber()
        self.assertEqual(subscriber['name'], 'Mario')
        self.assertEqual(subscriber['surname'], 'Rossi')
        self.assertEqual(subscriber['email'], self.dummySignup['email'])

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


class TestSignupWithInvitation(helpers.TestHandler):
    _handler = signup.Signup

    @inlineCallbacks
    def _invite(self):
        yield tw(db_set_config_variable, 1, 'enable_signup', True)
        yield tw(db_set_config_variable, 1, 'signup_invite_only', True)

        yield create_invite({'organization_name': 'Autorità Nazionale Anticorruzione',
                             'email': 'protocollo@anticorruzione.it'}, 'en')

        invitation = yield get_invitation()

        returnValue(invitation)

    @inlineCallbacks
    def test_post_with_an_invitation(self):
        invitation = yield self._invite()

        # The identity of the organization is the one the invitation has been
        # issued to and is never the one submitted by the client
        request = dict(self.dummySignup)
        request['token'] = invitation['token']
        request['organization_name'] = 'Another Organization'
        request['organization_email'] = 'another@example.org'

        handler = self.request(request)
        yield handler.post()

        subscriber = yield get_subscriber()
        self.assertEqual(subscriber['organization_name'], invitation['organization_name'])
        self.assertEqual(subscriber['organization_email'], invitation['organization_email'])

        # The address of the user is the one collected on the registration
        self.assertEqual(subscriber['email'], self.dummySignup['email'])

    @inlineCallbacks
    def test_post_with_an_invitation_and_no_authentication(self):
        invitation = yield self._invite()
        yield tw(db_set_config_variable, DEFAULT_PROFILE_ID, 'idp', True)

        # An invitation does not exempt from the authentication required by the
        # identity provider configured for the registrations
        request = dict(self.dummySignup)
        request['token'] = invitation['token']

        handler = self.request(request)
        yield self.assertFailure(handler.post(), errors.ForbiddenOperation)

    @inlineCallbacks
    def test_post_with_an_invitation_and_authentication(self):
        invitation = yield self._invite()
        yield tw(db_set_config_variable, DEFAULT_PROFILE_ID, 'idp', True)

        verify_token = State.oidcauth.verify_token
        self.addCleanup(setattr, State.oidcauth, 'verify_token', verify_token)

        State.oidcauth.verify_token = lambda *args: {'sub': 'subject1'}

        request = dict(self.dummySignup)
        request['token'] = invitation['token']

        handler = self.request(request, headers={'Authorization': 'Bearer token'})
        yield handler.post()

        subscriber = yield get_subscriber()
        self.assertEqual(subscriber['organization_name'], invitation['organization_name'])

    @inlineCallbacks
    def test_post_with_an_invalid_invitation(self):
        yield self._invite()

        request = dict(self.dummySignup)
        request['token'] = 'invalid'

        handler = self.request(request)
        yield self.assertFailure(handler.post(), errors.ForbiddenOperation)


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
