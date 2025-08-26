# Handlers dealing with platform authentication
import json
from datetime import timedelta
from random import SystemRandom
from sqlalchemy import exists, func, or_, and_
from sqlalchemy.orm import joinedload
from nacl.encoding import Base64Encoder
from twisted.internet.defer import inlineCallbacks, returnValue

import globaleaks.handlers.auth.token
from globaleaks.handlers.base import connection_check, BaseHandler
from globaleaks.handlers.user import user_permissions
from globaleaks.models import InternalTip, User, UserProfile, UserProfilePermission
from globaleaks.models.config import ConfigFactory
from globaleaks.orm import db_log, transact, tw
from globaleaks.rest import errors, requests
from globaleaks.sessions import initialize_submission_session, Sessions
from globaleaks.settings import Settings
from globaleaks.state import State
from globaleaks.utils.crypto import GCE, sha256
from globaleaks.utils.objectdict import ObjectDict
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
    try:
        if not session.query(exists().where(and_(InternalTip.tid == tid, func.length(InternalTip.receipt_hash) < 64))).scalar():
            key = Base64Encoder.decode(receipt.encode())
            hash = sha256(key).decode()
        else:
            salt = ConfigFactory(session, tid).get_val('receipt_salt')
            key, hash = GCE.calculate_key_and_hash(receipt, salt)
    except:
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
    if operator_id is not None:
        itip.receipt_change_needed = True
        itip.operator_id = operator_id

    db_log(session, tid=tid, type='whistleblower_login', user_id=operator_id, object_id=itip.id)

    session = Sessions.new(tid, itip.id, tid, itip.id, 'whistleblower', crypto_prv_key)

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
        user = session.query(User) \
                      .options(joinedload(User.profile).joinedload(UserProfile.permissions),
                               joinedload(User.profile).joinedload(UserProfile.roles)) \
                      .filter(or_(User.id == username, User.username == username),
                                  User.enabled.is_(True), User.tid == tid).one_or_none()
    else:
        user = session.query(User) \
                      .options(joinedload(User.profile).joinedload(UserProfile.permissions),
                               joinedload(User.profile).joinedload(UserProfile.roles)) \
                      .filter(or_(User.username == username),
                                  User.enabled.is_(True), User.tid == tid).one_or_none()

    if user is None:
        db_login_failure(session, tid, 0)

    try:
        if len(user.hash) == 64:
            key = Base64Encoder.decode(password.encode())
            hash = sha256(key).decode()
        else:
            key, hash = GCE.calculate_key_and_hash(password, user.salt)
    except:
        db_login_failure(session, tid, 0)

    if not password or not GCE.check_equality(hash, user.hash):
        db_login_failure(session, tid, 0)

    connection_check(tid, user.role, client_ip, client_using_tor)

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

    permissions = ObjectDict()
    for r in user_permissions:
        permissions[r] = r in user.profile.permissions_list

    return Sessions.new(tid, user.id, user.tid, user.username, user.role, crypto_prv_key, user.crypto_escrow_prv_key, user.profile.roles_list, permissions)


@transact
def get_auth_type(session, tid, username):
    salt = ConfigFactory(session, tid).get_val('receipt_salt')

    if not username: # whistleblower
        if not session.query(exists().where(and_(InternalTip.tid == tid, func.length(InternalTip.receipt_hash) < 64))).scalar():
            return {'type': 'key', 'salt': salt}

    else:
        user = session.query(User).filter(User.tid == tid, or_(User.username == username, User.id == username)).one_or_none()

        # Always calculate the user salt to not disclose if the user exists or not
        salt = GCE.generate_salt(salt + ":" + username)

        salt = salt if not user else user.salt

        if not user or len(user.hash) == 64:
            return {'type': 'key', 'salt': salt}

    return {'type': 'password'}


@transact
def get_user_roles(session, tid, user_id):
    return session.query(User).filter(User.tid == tid, User.id == user_id).one().profile.roles_list


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

        yield login_delay(tid)

        if State.tenants[tid].cache.idp:
            if self.request.oidc_token:
                preferred_username = self.request.oidc_token.get('preferred_username')
                email = self.request.oidc_token.get('email')

                def ensure_user(session):
                    user = session.query(User).filter(User.username == preferred_username, User.mail_address == email, User.tid == tid).one_or_none()
                    if not user:
                       raise errors.InvalidAuthentication
                    
                    return user.username
                
                request['username'] = yield tw(ensure_user)
            else:
                raise errors.InvalidAuthentication

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

        connection_check(self.request.tid, session.role,
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

        # Check if the configuration requires authentication via the IDP
        if State.tenants[self.request.tid].cache.idp:
            # If the configuration requires authentication via the IDP session renewal requires valid IDP token
            if not self.request.oidc_token or self.request.oidc_token['preferred_username'] != self.session.username:
                raise errors.InvalidAuthentication

        try:
            self.session.token.validate(request['token'].encode().split(b":")[1])
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
        if self.session.role == 'whistleblower':
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
                               self.session.username,
                               self.session.role,
                               self.session.cc,
                               self.session.ek,
                               self.session.permissions)

        session.properties['management_session'] = True

        return {'redirect': '/t/%s/#/login?token=%s' % (State.tenants[tid].cache.uuid, session.id)}


class RoleAuthSwitchHandler(BaseHandler):
    """
    Login handler for switching tenant
    """
    check_roles = 'any'

    @inlineCallbacks
    def get(self, role):
        roles = yield get_user_roles(self.request.tid, self.session.user_id)

        if role not in roles:
            raise errors.InvalidAuthentication

        session = Sessions.new(self.session.tid,
                               self.session.user_id,
                               self.session.user_tid,
                               self.session.username,
                               role,
                               self.session.cc,
                               self.session.ek,
                               self.session.permissions)

        returnValue({'redirect': '/#/login?token=%s' % (session.id)})


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
                               "whistleblower",
                               self.session.cc,
                               self.session.ek,
                               self.session.permissions)

        session.properties['operator_session'] = self.session.user_id

        return {'redirect': '/#/login?token=%s' % session.id}
