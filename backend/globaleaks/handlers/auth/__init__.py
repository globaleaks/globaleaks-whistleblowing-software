# -*- coding: utf-8 -*-
#
# Handlers dealing with platform authentication
from datetime import timedelta
from random import SystemRandom
from sqlalchemy import or_
from twisted.internet.defer import inlineCallbacks, returnValue

import globaleaks.handlers.auth.token

from globaleaks.handlers.base import connection_check, BaseHandler
from globaleaks.models import InternalTip, User, UserProfile
from globaleaks.orm import db_log, transact, tw
from globaleaks.rest import errors, requests
from globaleaks.sessions import initialize_submission_session, Sessions
from globaleaks.settings import Settings
from globaleaks.state import State
from globaleaks.utils.crypto import Base64Encoder, GCE
from globaleaks.utils.utility import datetime_now, deferred_sleep, uuid4


def db_login_failure(session, tid, whistleblower=False):
    Settings.failed_login_attempts[tid] = Settings.failed_login_attempts.get(tid, 0) + 1

    db_log(session, tid=tid, type='whistleblower_login_failure' if whistleblower else 'login_failure')

    raise errors.InvalidAuthentication


def login_delay(tid):
    """
    The function in case of failed_login_attempts introduces
    an exponential increasing delay between 0 and 42 seconds

    the function implements the following table:
     ----------------------------------
    | failed_attempts |      delay     |
    | x < 5           | 0              |
    | 5               | random(5, 25)  |
    | 6               | random(6, 36)  |
    | 7               | random(7, 42)  |
    | 8 <= x <= 42    | random(x, 42)  |
    | x > 42          | 42             |
     ----------------------------------
    """
    failed_attempts = Settings.failed_login_attempts.get(tid, 0)

    if failed_attempts < 5:
        return

    n = failed_attempts * failed_attempts
    min_sleep = failed_attempts if failed_attempts < 42 else 42
    max_sleep = n if n < 42 else 42

    return deferred_sleep(SystemRandom().randint(min_sleep, max_sleep))


@transact
def login_whistleblower(session, tid, receipt, client_using_tor, operator_id=None):
    """
    Login transaction for whistleblowers' access

    :param session: An ORM session
    :param tid: A tenant ID
    :param receipt: A provided receipt
    :return: Returns a user session in case of success
    """
    hash = GCE.hash_password(receipt, State.tenants[tid].cache.receipt_salt)

    itip = session.query(InternalTip) \
                  .filter(InternalTip.tid == tid,
                          InternalTip.receipt_hash == hash).one_or_none()

    if itip is None:
        db_login_failure(session, tid, 1)

    itip.wb_last_access = datetime_now()
    itip.tor = itip.tor and client_using_tor

    crypto_prv_key = ''
    if itip.crypto_pub_key:
        user_key = GCE.derive_key(receipt.encode(), State.tenants[tid].cache.receipt_salt)
        crypto_prv_key = GCE.symmetric_decrypt(user_key, Base64Encoder.decode(itip.crypto_prv_key))

    itip.access_count += 1
    if operator_id is not None:
        itip.receipt_change_needed = True
        itip.operator_id = operator_id

    db_log(session, tid=tid, type='whistleblower_login', user_id=operator_id, object_id=itip.id)

    session = Sessions.new(tid, itip.id, tid, 'whistleblower', crypto_prv_key)

    if itip.receipt_change_needed:
        session.properties["new_receipt"] = GCE.generate_receipt()

    return session


@transact
def login(session, tid, username, password, authcode, client_using_tor, client_ip):
    """
    Login transaction for users' access

    :param session: An ORM session
    :param tid: A tenant ID
    :param username: A provided username
    :param password: A provided password
    :param authcode: A provided authcode
    :param client_using_tor: A boolean signaling Tor usage
    :param client_ip:  The client IP
    :return: Returns a user session in case of success
    """
    if tid in State.tenants and State.tenants[tid].cache.simplified_login:
        user, profile = (session.query(User,UserProfile).join(UserProfile,User.profile_id == UserProfile.id).filter(or_(User.id == username, User.username == username),
                   UserProfile.enabled.is_(True),User.tid == tid).one_or_none())
    else:
        user, profile = (session.query(User,UserProfile).join(UserProfile,User.profile_id == UserProfile.id).filter(or_(User.username == username),
                   UserProfile.enabled.is_(True),User.tid == tid).one_or_none())

    if not user or not GCE.check_password(password, user.salt, user.hash):
        db_login_failure(session, tid, 0)

    connection_check(tid, user.role, client_ip, client_using_tor)

    if user.two_factor_secret:
        if authcode == '':
            raise errors.TwoFactorAuthCodeRequired

        State.totp_verify(user.two_factor_secret, authcode)

    crypto_prv_key = ''
    user_key = GCE.derive_key(password.encode(), user.salt)
    if user.crypto_prv_key:
        crypto_prv_key = GCE.symmetric_decrypt(user_key, Base64Encoder.decode(user.crypto_prv_key))
    elif State.tenants[tid].cache.encryption:
       # Special condition where the user is accessing for the first time via password
       # on a system with no escrow keys.
        crypto_prv_key, _ = GCE.generate_keypair()

        # Force the password change on which the user key will be created
        user.password_change_needed = True

    # Require password change if password change threshold is exceeded
    if State.tenants[tid].cache.password_change_period > 0 and \
       user.password_change_date < datetime_now() - timedelta(days=State.tenants[tid].cache.password_change_period):
        user.password_change_needed = True

    user.last_login = datetime_now()

    db_log(session, tid=tid, type='login', user_id=user.id)

    session = Sessions.new(tid, user.id, user.tid, user.role, crypto_prv_key, user.crypto_escrow_prv_key)

    if user.role == 'receiver' and profile.can_edit_general_settings:
        session.permissions['can_edit_general_settings'] = True

    return session


class AuthenticationHandler(BaseHandler):
    """
    Login handler for internal users
    """
    check_roles = 'any'

    @inlineCallbacks
    def post(self):
        request = self.validate_request(self.request.content.read(), requests.AuthDesc)

        tid = int(request['tid'])
        if tid == 0:
            tid = self.request.tid

        yield login_delay(tid)

        session = yield login(tid,
                              request['username'],
                              request['password'],
                              request['authcode'],
                              self.request.client_using_tor,
                              self.request.client_ip)

        if tid != self.request.tid:
            returnValue({
                'redirect': 'https://%s/#/login?token=%s' % (State.tenants[tid].cache.hostname, session.id)
            })

        returnValue(session.serialize())


class TokenAuthHandler(BaseHandler):
    """
    Login handler for token based authentication
    """
    check_roles = 'any'

    @inlineCallbacks
    def post(self):
        request = self.validate_request(self.request.content.read(), requests.TokenAuthDesc)

        yield login_delay(self.request.tid)

        session = Sessions.get(request['authtoken'])
        if session is None:
            yield tw(db_login_failure, self.request.tid, 0)

        connection_check(self.request.tid, session.user_role,
                         self.request.client_ip, self.request.client_using_tor)

        session = Sessions.regenerate(session)

        returnValue(session.serialize())


class ReceiptAuthHandler(BaseHandler):
    """
    Receipt handler for whistleblowers
    """
    check_roles = 'any'

    @inlineCallbacks
    def post(self):
        request = self.validate_request(self.request.content.read(), requests.ReceiptAuthDesc)

        yield login_delay(self.request.tid)

        connection_check(self.request.tid, 'whistleblower',
                         self.request.client_ip, self.request.client_using_tor)

        operator_id = None
        if self.session and self.session.properties.get('operator_session', False):
            # this is actually a recipient operating on behalf of a whistleblower
            operator_id = self.session.properties.get('operator_session')

        if request['receipt']:
            session = yield login_whistleblower(self.request.tid, request['receipt'],
                                                self.request.client_using_tor, operator_id)
        else:
            if not self.state.accept_submissions or self.state.tenants[self.request.tid].cache['disable_submissions']:
                raise errors.SubmissionDisabled

            session = initialize_submission_session(self.request.tid)

        if operator_id:
            session.properties["operator_session"] = self.session.user_id
            del Sessions[self.session.id]

        returnValue(session.serialize())


class SessionHandler(BaseHandler):
    """
    Session handler for authenticated users
    """
    check_roles = {'user', 'whistleblower'}

    def post(self):
        """
        Reset session timout
        """
        request = self.validate_request(self.request.content.read(), requests.SessionUpdateDesc)

        try:
            self.session.token.validate(request['token'].encode())
            Sessions.reset_timeout(self.session)
        except:
            pass
        else:
            self.session.token = self.state.tokens.new(self.request.tid)

        return self.session.serialize()

    @inlineCallbacks
    def delete(self):
        """
        Logout
        """
        if self.session.user_role == 'whistleblower':
            yield tw(db_log, tid=self.session.tid,  type='whistleblower_logout',
                     user_id=self.session.properties.get("operator_session"))
        else:
            yield tw(db_log, tid=self.session.tid,  type='logout', user_id=self.session.user_id)

        del Sessions[self.session.id]


class TenantAuthSwitchHandler(BaseHandler):
    """
    Login handler for switching tenant
    """
    check_roles = 'admin'

    def get(self, tid):
        if self.request.tid != 1:
            raise errors.InvalidAuthentication

        tid = int(tid)
        session = Sessions.new(tid,
                               self.session.user_id,
                               self.session.user_tid,
                               self.session.user_role,
                               self.session.cc,
                               self.session.ek)

        session.properties['management_session'] = True

        return {'redirect': '/t/%s/#/login?token=%s' % (State.tenants[tid].cache.uuid, session.id)}


class OperatorAuthSwitchHandler(BaseHandler):
    """
    Login handler for switching tenant
    """
    check_roles = 'receiver'

    def get(self):
        session = Sessions.new(self.session.user_tid,
                               uuid4(),
                               self.session.user_tid,
                               "whistleblower",
                               self.session.cc,
                               self.session.ek)

        session.properties['operator_session'] = self.session.user_id

        return {'redirect': '/#/login?token=%s' % session.id}
