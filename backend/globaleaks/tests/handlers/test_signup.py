import re

from twisted.internet.defer import inlineCallbacks, returnValue
from globaleaks import models
from globaleaks.handlers import signup
from globaleaks.handlers.admin import tenant
from globaleaks.handlers.admin.invite import create_invite
from globaleaks.models.config import DEFAULT_PROFILE_ID, db_set_config_variable
from globaleaks.orm import transact, tw
from globaleaks.rest import errors
from globaleaks.sessions import Session
from globaleaks.state import State
from globaleaks.tests import helpers


@transact
def get_signup_token(session):
    # The raw activation token is delivered via email only (the DB stores
    # the SHA-256 of the token). Extract it back from the scheduled mails:
    # the link authorizing the platform is carried by the notification
    # delivered to the administrators. A registration authorized
    # automatically is activated on the spot and produces no such mail.
    for mail in session.query(models.Mail) \
                       .order_by(models.Mail.creation_date.desc()):
        match = re.search(r'activation\?token=([A-Za-z0-9]+)', mail.body)
        if match:
            return match.group(1)

    return ''


@transact
def get_invitation(session):
    subscriber = session.query(models.Subscriber).one()

    return {
        'organization_name': subscriber.organization_name,
        'organization_email': subscriber.organization_email
    }


@transact
def get_mail_addresses(session, subject):
    return sorted(mail.address for mail in session.query(models.Mail)
                                                  .filter(models.Mail.subject == subject))


@transact
def get_mail_bodies(session, subject):
    return [mail.body for mail in session.query(models.Mail)
                                         .filter(models.Mail.subject == subject)]


@transact
def get_mails(session, subject):
    return [{'address': mail.address, 'body': mail.body}
            for mail in session.query(models.Mail)
                               .filter(models.Mail.subject == subject)]


@transact
def get_provisioned_user(session):
    subscriber = session.query(models.Subscriber).first()
    tenant = session.query(models.Tenant).filter(models.Tenant.id == subscriber.tid).one()
    user = session.query(models.User).filter(models.User.tid == subscriber.tid).one_or_none()

    return {
        'tenant_active': tenant.active,
        'role': user.role if user else '',
        'username': user.username if user else '',
        'salt': user.salt if user else '',
        'hash': user.hash if user else '',
        'password_change_needed': user.password_change_needed if user else None
    }


@transact
def get_subscriber(session):
    subscriber = session.query(models.Subscriber).first()

    return {
        'subdomain': subscriber.subdomain,
        'name': subscriber.name,
        'surname': subscriber.surname,
        'email': subscriber.email,
        'phone': subscriber.phone,
        'organization_name': subscriber.organization_name,
        'organization_email': subscriber.organization_email,
        'organization_location': subscriber.organization_location
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
    def test_post_rejects_existing_tenant_subdomain(self):
        yield tw(db_set_config_variable, 1, 'enable_signup', True)

        # An administrator-created tenant already owns the requested subdomain
        yield tenant.create({'active': True, 'profile': 'default',
                             'name': 'victim', 'subdomain': self.dummySignup['subdomain']})

        # A public signup must not be able to hijack the same subdomain
        handler = self.request(self.dummySignup)
        yield self.assertFailure(handler.post(), errors.ForbiddenOperation)

    @inlineCallbacks
    def test_post_collects_the_organization_data(self):
        yield tw(db_set_config_variable, 1, 'enable_signup', True)

        handler = self.request(self.dummySignup)
        yield handler.post()

        # The name of the organization is always collected; its email address
        # is known only through an invitation and is dropped otherwise
        subscriber = yield get_subscriber()
        self.assertEqual(subscriber['organization_name'], self.dummySignup['organization_name'])
        self.assertEqual(subscriber['organization_email'], '')

    @inlineCallbacks
    def test_post_without_organization_name(self):
        yield tw(db_set_config_variable, 1, 'enable_signup', True)

        # The name of the organization is mandatory
        request = dict(self.dummySignup, organization_name='')
        handler = self.request(request)
        yield self.assertFailure(handler.post(), errors.InputValidationError)

    @inlineCallbacks
    def test_post_with_organization_details_not_requested(self):
        yield tw(db_set_config_variable, 1, 'enable_signup', True)
        yield tw(db_set_config_variable, 1, 'signup_request_phone', False)
        yield tw(db_set_config_variable, 1, 'signup_request_location', False)

        handler = self.request(self.dummySignup)
        yield handler.post()

        # The details not asked for are dropped even when a client submits them
        subscriber = yield get_subscriber()
        self.assertEqual(subscriber['phone'], '')
        self.assertEqual(subscriber['organization_location'], '')

    @inlineCallbacks
    def test_post_with_organization_details_missing(self):
        yield tw(db_set_config_variable, 1, 'enable_signup', True)

        # The details asked for are mandatory
        request = dict(self.dummySignup, phone='')
        handler = self.request(request)
        yield self.assertFailure(handler.post(), errors.InputValidationError)

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

        # The email published by the identity provider only prefills the form:
        # the address compiled by the user is the one registered
        State.oidcauth.verify_token = lambda *args: {'sub': 'subject1',
                                                     'given_name': 'Mario',
                                                     'family_name': 'Rossi',
                                                     'email': 'mario.rossi@example.org'}

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
    def test_post_provisions_an_admin_account_without_a_default_profile(self):
        yield tw(db_set_config_variable, 1, 'enable_signup', True)
        yield tw(db_set_config_variable, 1, 'default_user_profile', '')
        yield tw(db_set_config_variable, DEFAULT_PROFILE_ID, 'default_user_profile', '')

        handler = self.request(self.dummySignup)
        yield handler.post()

        # With no default user profile configured the user is provisioned as
        # the administrator of its own platform
        provisioned = yield get_provisioned_user()
        self.assertEqual(provisioned['role'], 'admin')
        self.assertEqual(provisioned['username'], self.dummySignup['email'])

    @inlineCallbacks
    def test_post_activation_mail_carries_the_credentials(self):
        yield tw(db_set_config_variable, 1, 'enable_signup', True)

        handler = self.request(self.dummySignup)
        yield handler.post()

        # The credentials reference the email address of the user as the
        # username together with the generated password
        bodies = yield get_mail_bodies('Access instructions')
        self.assertEqual(len(bodies), 1)
        self.assertIn('Username: ' + self.dummySignup['email'], bodies[0])
        self.assertIn('Password: ', bodies[0])

    @inlineCallbacks
    def test_post_with_automatic_authorization_provisions_the_account(self):
        yield tw(db_set_config_variable, 1, 'enable_signup', True)
        yield tw(db_set_config_variable, DEFAULT_PROFILE_ID, 'default_user_profile', 'admin')

        handler = self.request(self.dummySignup)
        yield handler.post()

        # The account is provisioned upon the activation with the email
        # address of the user as its username and a generated password that
        # must be changed on first login
        provisioned = yield get_provisioned_user()
        self.assertTrue(provisioned['tenant_active'])
        self.assertEqual(provisioned['role'], 'admin')
        self.assertEqual(provisioned['username'], self.dummySignup['email'])
        self.assertTrue(provisioned['hash'])
        self.assertTrue(provisioned['password_change_needed'])

    @inlineCallbacks
    def test_post_without_automatic_authorization_defers_the_provisioning(self):
        yield tw(db_set_config_variable, 1, 'enable_signup', True)
        yield tw(db_set_config_variable, 1, 'signup_auto_authorize', False)

        handler = self.request(self.dummySignup)
        yield handler.post()

        # No account exists until the platform is authorized
        provisioned = yield get_provisioned_user()
        self.assertFalse(provisioned['tenant_active'])
        self.assertEqual(provisioned['username'], '')

    @inlineCallbacks
    def test_post_without_automatic_authorization_confirms_the_registration(self):
        yield tw(db_set_config_variable, 1, 'enable_signup', True)
        yield tw(db_set_config_variable, 1, 'signup_auto_authorize', False)

        handler = self.request(self.dummySignup)
        yield handler.post()

        # The registration is confirmed on its own and the access
        # instructions are delivered only upon the activation
        addresses = yield get_mail_addresses('Registration confirmation')
        self.assertEqual(addresses, [self.dummySignup['email']])

        addresses = yield get_mail_addresses('Access instructions')
        self.assertEqual(addresses, [])

    @inlineCallbacks
    def test_post_with_automatic_authorization_sends_only_the_activation(self):
        yield tw(db_set_config_variable, 1, 'enable_signup', True)

        handler = self.request(self.dummySignup)
        yield handler.post()

        # The activation is automatic and contextual to the registration: the
        # confirmation of the activation is the only one sent
        addresses = yield get_mail_addresses('Registration confirmation')
        self.assertEqual(addresses, [])

        addresses = yield get_mail_addresses('Access instructions')
        self.assertEqual(addresses, [self.dummySignup['email']])

    @inlineCallbacks
    def test_post_without_subdomain_when_requested(self):
        yield tw(db_set_config_variable, 1, 'enable_signup', True)

        request = dict(self.dummySignup)
        request['subdomain'] = ''

        handler = self.request(request)
        yield self.assertFailure(handler.post(), errors.InputValidationError)


class TestSignupWithInvitation(helpers.TestHandler):
    _handler = signup.Signup

    def admin_session(self):
        """
        Session of the administrator issuing the invitation, that the audit log
        of the accreditation names as the one that acted
        """
        return Session(1, self.dummyAdmin['id'], 1, 'admin', 'admin', '')

    @inlineCallbacks
    def _invite(self):
        yield tw(db_set_config_variable, 1, 'enable_signup', True)
        yield tw(db_set_config_variable, 1, 'signup_invite_only', True)

        created = yield create_invite(1, self.admin_session(),
                                      {'organization_name': 'Autorità Nazionale Anticorruzione',
                                       'email': 'protocollo@anticorruzione.it'}, 'en')

        invitation = yield get_invitation()
        invitation['token'] = created['token']

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
    def test_post_with_an_invitation_confirms_to_both_addresses(self):
        invitation = yield self._invite()
        yield tw(db_set_config_variable, 1, 'signup_auto_authorize', False)

        request = dict(self.dummySignup)
        request['token'] = invitation['token']

        handler = self.request(request)
        yield handler.post()

        # The confirmation of the registration is sent to the user and to the
        # address the invitation was delivered to
        addresses = yield get_mail_addresses('Registration confirmation')
        self.assertEqual(addresses, sorted([self.dummySignup['email'],
                                            invitation['organization_email']]))

    @inlineCallbacks
    def test_post_with_an_invitation_confirms_once_when_the_addresses_match(self):
        yield tw(db_set_config_variable, 1, 'enable_signup', True)
        yield tw(db_set_config_variable, 1, 'signup_invite_only', True)
        yield tw(db_set_config_variable, 1, 'signup_auto_authorize', False)

        # The invitation is delivered to the same address the user registers with
        created = yield create_invite(1, self.admin_session(),
                                      {'organization_name': 'Autorità Nazionale Anticorruzione',
                                       'email': self.dummySignup['email']}, 'en')

        request = dict(self.dummySignup)
        request['token'] = created['token']

        handler = self.request(request)
        yield handler.post()

        addresses = yield get_mail_addresses('Registration confirmation')
        self.assertEqual(addresses, [self.dummySignup['email']])

    @inlineCallbacks
    def test_post_with_an_invitation_and_automatic_authorization_notifies_the_activation(self):
        invitation = yield self._invite()

        request = dict(self.dummySignup)
        request['token'] = invitation['token']

        handler = self.request(request)
        yield handler.post()

        # The activation is contextual to the registration: its confirmation,
        # with the access instructions, is the only one sent and reaches both
        # the user and the address the invitation was delivered to
        addresses = yield get_mail_addresses('Registration confirmation')
        self.assertEqual(addresses, [])

        addresses = yield get_mail_addresses('Access instructions')
        self.assertEqual(addresses, sorted([self.dummySignup['email'],
                                            invitation['organization_email']]))

    @inlineCallbacks
    def test_post_with_an_invitation_keeps_credentials_off_the_invited_address(self):
        invitation = yield self._invite()

        request = dict(self.dummySignup)
        request['token'] = invitation['token']

        handler = self.request(request)
        yield handler.post()

        # The credentials are delivered only to the address of the user and
        # never to the address the invitation was delivered to
        mails = yield get_mails('Access instructions')
        self.assertEqual(len(mails), 2)
        for mail in mails:
            if mail['address'] == self.dummySignup['email']:
                self.assertIn('Username: ', mail['body'])
            else:
                self.assertNotIn('Username: ', mail['body'])

    @inlineCallbacks
    def test_post_with_an_invalid_invitation(self):
        yield self._invite()

        request = dict(self.dummySignup)
        request['token'] = 'invalid'

        handler = self.request(request)
        yield self.assertFailure(handler.post(), errors.ForbiddenOperation)

class TestSignupActivation(helpers.TestHandlerWithPopulatedDB):
    _handler = signup.SignupActivation

    @inlineCallbacks
    def _signup(self):
        yield tw(db_set_config_variable, 1, 'enable_signup', True)
        # Exercise the explicit activation flow rather than the automatic one,
        # provisioning the default administrator account upon activation; the
        # token authorizing the platform is carried by the notification
        # delivered to the administrators of the root tenant
        yield tw(db_set_config_variable, 1, 'signup_auto_authorize', False)
        yield tw(db_set_config_variable, DEFAULT_PROFILE_ID, 'default_user_profile', 'admin')

        self._handler = signup.Signup
        handler = self.request(self.dummySignup)
        yield handler.post()

        self._handler = signup.SignupActivation
        handler = self.request(self.dummySignup)
        token = yield get_signup_token()
        self.assertTrue(token)
        yield handler.post(token)

    def test_get_with_signup_disabled(self):
        handler = self.request(self.dummySignup)
        return self.assertFailure(handler.post(u'valid_or_invalid'), errors.ForbiddenOperation)

    @inlineCallbacks
    def test_valid_signup(self):
        yield self._signup()

        # The account is provisioned upon the activation
        provisioned = yield get_provisioned_user()
        self.assertTrue(provisioned['tenant_active'])
        self.assertEqual(provisioned['role'], 'admin')
        self.assertEqual(provisioned['username'], self.dummySignup['email'])

    @inlineCallbacks
    def test_invalid_signup_with_invalid_activation_token(self):
        yield tw(db_set_config_variable, 1, 'enable_signup', True)

        handler = self.request(self.dummySignup)
        r = yield handler.post(u'invalid')

        self.assertTrue(not r)
