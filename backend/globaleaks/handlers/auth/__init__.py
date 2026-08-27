# Handlers dealing with platform authentication
import json
from datetime import timedelta
from sqlalchemy import exists, func, or_, and_

from nacl.encoding import Base64Encoder
from twisted.internet.defer import inlineCallbacks

import globaleaks.handlers.auth.token

from globaleaks.handlers.base import connection_check, BaseHandler
from globaleaks.models import InternalTip, User
from globaleaks.models.config import ConfigFactory
from globaleaks.orm import db_log, transact, tw
from globaleaks.rest import errors, requests
from globaleaks.sessions import initialize_submission_session, Sessions
from globaleaks.state import State
from globaleaks.utils.crypto import GCE, sha256
from globaleaks.utils.log import log
from globaleaks.utils.utility import datetime_now


def db_receipt_auth_is_legacy(session, tid):
    # Legacy server-hashed mode while any pre-key receipt_hash (length < 64) remains.
    return session.query(exists().where(and_(InternalTip.tid == tid,
                                              func.length(InternalTip.receipt_hash) < 64))).scalar()


def db_set_receipt_hash(session, tid, itip, receipt):
    # In key mode the receipt must be the client-derived 32-byte key; rejecting
    # any other format prevents a submission from downgrading the tenant mode.
    if not db_receipt_auth_is_legacy(session, tid):
        try:
            key = Base64Encoder.decode(receipt.encode())
        except Exception:
            raise errors.InputValidationError

        if len(key) != 32:
            raise errors.InputValidationError

        itip.receipt_hash = sha256(key).decode()
    else:
        salt = ConfigFactory(session, tid).get_val('receipt_salt')
        key, itip.receipt_hash = GCE.calculate_key_and_hash(receipt, salt)

    return key


def db_login_failure(session, tid, whistleblower=False, user_id=None):
    # A login failure aborts the whole transaction; discard any pending state
    # first so that only the audit entry below can be persisted.
    session.rollback()

    db_log(session, tid=tid, type='whistleblower_login_failure' if whistleblower else 'login_failure', user_id=user_id)

    # The entry must be committed before aborting: the raise below reaches the
    # @transact wrapper, whose rollback would otherwise discard it and leave
    # failed authentications entirely unrecorded.
    session.commit()

    raise errors.InvalidAuthentication


@transact
def login_whistleblower(session, tid, receipt, client_using_tor, dpop_jkt=''):
    """
    Login transaction for whistleblowers' access

    :param session: An ORM session
    :param tid: A tenant ID
    :param receipt: A provided receipt
    :return: Returns a user session in case of success
    """
    try:
        if not db_receipt_auth_is_legacy(session, tid):
            key = Base64Encoder.decode(receipt.encode())
            hash = sha256(key).decode()
        else:
            salt = ConfigFactory(session, tid).get_val('receipt_salt')
            key, hash = GCE.calculate_key_and_hash(receipt, salt)
    except Exception:
        db_login_failure(session, tid, 0)

    itip = session.query(InternalTip) \
                  .filter(InternalTip.tid == tid,
                          InternalTip.receipt_hash == hash).one_or_none()

    if itip is None:
        db_login_failure(session, tid, 1)

    itip.wb_last_access = datetime_now()
    itip.tor = itip.tor and client_using_tor

    crypto_prv_key = ''
    if itip.crypto_pub_key:
        crypto_prv_key = GCE.symmetric_decrypt(key, Base64Encoder.decode(itip.crypto_prv_key))

    itip.access_count += 1

    db_log(session, tid=tid, type='whistleblower_login', object_id=itip.id)

    session = Sessions.new(tid, itip.id, tid, 'whistleblower', crypto_prv_key, dpop_jkt=dpop_jkt)

    session.properties["receipt_change_needed"] = itip.receipt_change_needed

    return session


@transact
def login(session, tid, username, password, authcode, client_using_tor, client_ip, dpop_jkt=''):
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
        user = session.query(User).filter(or_(User.id == username,
                                              User.username == username),
                                          User.enabled.is_(True),
                                          User.tid == tid).one_or_none()
    else:
        user = session.query(User).filter(User.username == username,
                                          User.enabled.is_(True),
                                          User.tid == tid).one_or_none()

    if not user:
        db_login_failure(session, tid, 0)

    connection_check(tid, user.role, client_ip, client_using_tor)

    try:
        if len(user.hash) == 64:
            key = Base64Encoder.decode(password.encode())
            hash = sha256(key).decode()
        else:
            key, hash = GCE.calculate_key_and_hash(password, user.salt)
    except Exception:
        db_login_failure(session, tid, 0, user_id=user.id)

    if not password or not GCE.check_equality(hash, user.hash):
        db_login_failure(session, tid, 0, user_id=user.id)

    if user.two_factor_secret:
        if authcode == '':
            raise errors.TwoFactorAuthCodeRequired

        State.totp_verify(user.two_factor_secret, authcode)

    if len(user.hash) != 64:
        user.password_change_needed = True

    crypto_prv_key = ''
    if user.crypto_prv_key:
        crypto_prv_key = GCE.symmetric_decrypt(key, Base64Encoder.decode(user.crypto_prv_key))
    elif State.tenants[tid].cache.encryption:
        # Special condition where the user is accessing for the first time via password
        # on a system with no escrow keys.
        crypto_prv_key, _ = GCE.generate_keypair()

        # Force password change on which the user key will be created
        user.password_change_needed = True

    # Require password change if password change threshold is exceeded
    if State.tenants[tid].cache.password_change_period > 0 and \
       user.password_change_date < datetime_now() - timedelta(days=State.tenants[tid].cache.password_change_period):
        user.password_change_needed = True

    user.last_login = datetime_now()

    db_log(session, tid=tid, type='login', user_id=user.id)

    session = Sessions.new(tid, user.id, user.tid, user.role, crypto_prv_key, user.crypto_escrow_prv_key != '', dpop_jkt=dpop_jkt)

    session.properties['password_change_needed'] = user.password_change_needed
    session.properties['require_two_factor'] = State.tenants[tid].cache.two_factor and not user.two_factor_secret
    session.permissions['can_edit_general_settings'] = user.role == 'receiver' and user.can_edit_general_settings

    return session


@transact
def get_auth_type(session, tid, username):
    salt = ConfigFactory(session, tid).get_val('receipt_salt')

    if not username: # whistleblower
        if not db_receipt_auth_is_legacy(session, tid):
            return {'type': 'key', 'salt': salt}

    else:
        user = session.query(User).filter(User.tid == tid, or_(User.username == username, User.id == username)).one_or_none()

        # Always calculate the user salt to not disclose if the user exists or not
        salt = GCE.generate_salt(salt + ":" + username)

        salt = salt if not user else user.salt

        if not user or len(user.hash) == 64:
            return {'type': 'key', 'salt': salt}

    return {'type': 'password'}


class AuthTypeHandler(BaseHandler):
    """
    Get auth type for specified user
    """
    check_roles = 'any'

    def post(self):
        username = json.loads(self.request.content.read())['username']
        return get_auth_type(self.request.tid, username)


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

        session = yield login(tid,
                              request['username'],
                              request['password'],
                              request['authcode'],
                              self.request.client_using_tor,
                              self.request.client_ip,
                              self.get_dpop_thumbprint())

        if tid != self.request.tid:
            # The session is issued for the redirect login flow: a freshly loaded
            # client on the target tenant adopts it via /api/auth/tokenauth with
            # its own DPoP key. Flag it as presentable as an authtoken so that
            # token login is restricted to such sessions and never accepts a
            # primary session id.
            session.properties['authtoken'] = True
            return {
                'redirect': 'https://%s/#/login?token=%s' % (State.tenants[tid].cache.hostname, session.id)
            }

        return session.serialize()


class TokenAuthHandler(BaseHandler):
    """
    Login handler for token based authentication
    """
    check_roles = 'any'

    @inlineCallbacks
    def post(self):
        request = self.validate_request(self.request.content.read(), requests.TokenAuthDesc)

        session = Sessions.get(request['authtoken'])

        # Restrict token login to sessions issued for the redirect flow. Rejecting
        # any other session id prevents a captured primary session id from being
        # adopted and bound to a client-supplied DPoP key without proof of
        # possession of the key the session was originally bound to.
        if session is None or not session.properties.get('authtoken'):
            yield tw(db_login_failure, self.request.tid, 0)
            raise errors.InvalidAuthentication

        connection_check(session.tid, session.role,
                         self.request.client_ip, self.request.client_using_tor)

        session = Sessions.regenerate(session, dpop_jkt=self.get_dpop_thumbprint())

        # The redirect login is single-use: the adopted session becomes a primary
        # session and cannot be adopted again.
        session.properties.pop('authtoken', None)

        return session.serialize()


class ReceiptAuthHandler(BaseHandler):
    """
    Receipt handler for whistleblowers
    """
    check_roles = 'any'

    @inlineCallbacks
    def post(self):
        request = self.validate_request(self.request.content.read(), requests.ReceiptAuthDesc)

        connection_check(self.request.tid, 'whistleblower',
                         self.request.client_ip, self.request.client_using_tor)

        dpop_jkt = self.get_dpop_thumbprint()

        if request['receipt']:
            session = yield login_whistleblower(self.request.tid, request['receipt'],
                                                self.request.client_using_tor,
                                                dpop_jkt=dpop_jkt)
        else:
            if not self.state.accept_submissions or self.state.tenants[self.request.tid].cache['disable_submissions']:
                raise errors.SubmissionDisabled

            session = initialize_submission_session(self.request.tid, dpop_jkt=dpop_jkt)

        if self.session and self.session.role == 'whistleblower':
            # The new session replaces the presented one so that a single
            # whistleblower session cannot be used to accumulate others
            del Sessions[self.session.id]

        return session.serialize()


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
            self.session.token.validate(request['token'].encode().split(b":")[1])
            Sessions.reset_timeout(self.session)
        except Exception:
            log.debug("Session refresh: token validation failed; keeping the existing token")
        else:
            self.session.token = self.state.tokens.new(self.request.tid)

        return self.session.serialize()

    @inlineCallbacks
    def delete(self):
        """
        Logout
        """
        if self.session.role == 'whistleblower':
            yield tw(db_log, tid=self.session.tid,  type='whistleblower_logout')
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
                               self.session.role,
                               self.session.cc,
                               self.session.ek,
                               dpop_jkt=self.get_dpop_thumbprint())

        session.properties['management_session'] = True
        session.properties['authtoken'] = True

        return {'redirect': '/t/%s/#/login?token=%s' % (State.tenants[tid].cache.uuid, session.id)}
