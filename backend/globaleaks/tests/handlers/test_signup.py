import re

from twisted.internet.defer import inlineCallbacks, returnValue
from globaleaks import models
from globaleaks.handlers import signup
from globaleaks.handlers.admin import tenant
from globaleaks.handlers.admin.invite import create_invite
from globaleaks.models.config import ConfigFactory, DEFAULT_PROFILE_ID, db_set_config_variable
from globaleaks.orm import transact, tw
from globaleaks.rest import errors
from globaleaks.sessions import Session
from globaleaks.tests import helpers
from globaleaks.tests.handlers.admin.test_tenant import db_compose_profile, \
                                                       get_dummy_tenant_desc


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


class TestSignupWithInvitation(helpers.TestHandler):
    _handler = signup.Signup

    def admin_session(self):
        """
        Session of the administrator issuing the invitation, that the audit log
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
        return self.assertFailure(handler.post('valid_or_invalid'), errors.ForbiddenOperation)


    @inlineCallbacks
    def test_invalid_signup_with_invalid_activation_token(self):
        yield tw(db_set_config_variable, 1, 'enable_signup', True)

        handler = self.request(self.dummySignup)
        r = yield handler.post('invalid')

        self.assertTrue(not r)


@transact
def db_profile_uuid(session, tid):
    return ConfigFactory(session, tid).get_val('uuid')


@transact
def db_provisioned_site(session, subdomain):
    """
    Return what a registration made of the site it created: the channels the
    """
    subscriber = session.query(models.Subscriber) \
                        .filter(models.Subscriber.subdomain == subdomain).one()

    contexts = session.query(models.Context) \
                      .filter(models.Context.tid == subscriber.tid).all()

    user = session.query(models.User) \
                  .filter(models.User.tid == subscriber.tid).one()

    profile = session.query(models.UserProfile) \
                     .filter(models.UserProfile.id == user.profile_id).one_or_none()

    received = [rc.context_id for rc in session.query(models.ReceiverContext)
                                               .filter(models.ReceiverContext.receiver_id == user.id)]

    return {
        'tid': subscriber.tid,
        'channels': {context.id: context.name for context in contexts},
        'role': user.role,
        'profile_name': profile.name if profile is not None else None,
        'received': received
    }


class TestSignupFromAProfile(helpers.TestHandlerWithPopulatedDB):
    """
    A registration completed builds a site made as the profile the platform
    """
    _handler = signup.Signup

    @inlineCallbacks
    def setUp(self):
        yield helpers.TestHandlerWithPopulatedDB.setUp(self)

        profile = yield tenant.create(get_dummy_tenant_desc('signup-profile'),
                                      is_profile=True)
        self.profile_tid = profile['id']
        self.composed = yield db_compose_profile(self.profile_tid)

        # the profile elects the user profile assigned to the accounts of the
        # sites made from it, and the platform assigns the profile itself to
        # the sites the registrations create
        yield tw(db_set_config_variable, self.profile_tid,
                 'default_user_profile', self.composed['profile_id'])

        uuid = yield db_profile_uuid(self.profile_tid)
        yield tw(db_set_config_variable, 1, 'signup_profile', uuid)

        yield tw(db_set_config_variable, 1, 'enable_signup', True)
        yield tw(db_set_config_variable, 1, 'signup_auto_authorize', False)

    @inlineCallbacks
    def _complete_signup(self):
        self._handler = signup.Signup
        yield self.request(self.dummySignup).post()

        self._handler = signup.SignupActivation
        token = yield get_signup_token()
        self.assertTrue(token)
        yield self.request(self.dummySignup).post(token)

    @inlineCallbacks
    def test_the_site_created_is_made_as_the_profile(self):
        yield self._complete_signup()

        provisioned = yield db_provisioned_site(self.dummySignup['subdomain'])

        self.assertIn('Channel of the profile',
                      [name.get('en') for name in provisioned['channels'].values()])

    @inlineCallbacks
    def test_the_account_provisioned_carries_the_profile_of_the_profile(self):
        yield self._complete_signup()

        provisioned = yield db_provisioned_site(self.dummySignup['subdomain'])

        self.assertEqual(provisioned['role'], 'receiver')
        self.assertEqual(provisioned['profile_name'], 'Recipients of the profile')

    @inlineCallbacks
    def test_the_account_provisioned_receives_on_the_channel_of_the_profile(self):
        yield self._complete_signup()

        provisioned = yield db_provisioned_site(self.dummySignup['subdomain'])

        named = [context_id for context_id, name in provisioned['channels'].items()
                 if name.get('en') == 'Channel of the profile']

        self.assertTrue(named)
        for context_id in named:
            self.assertIn(context_id, provisioned['received'])
