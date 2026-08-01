# Handlers dealing with platform authentication
import json
from datetime import timedelta
from sqlalchemy import exists, func, or_, and_
from sqlalchemy.orm import joinedload
from nacl.encoding import Base64Encoder
from twisted.internet.defer import inlineCallbacks, returnValue

import globaleaks.handlers.auth.token
from globaleaks.handlers.base import connection_check, BaseHandler
from globaleaks.handlers.user import db_reconcile_statistical_key, user_permissions
from globaleaks.models import InternalTip, User, UserProfile
from globaleaks.models.config import ConfigFactory
from globaleaks.orm import db_log, transact, tw
from globaleaks.rest import errors, requests
from globaleaks.sessions import initialize_submission_session, Sessions
from globaleaks.settings import Settings
from globaleaks.state import State
from globaleaks.utils.crypto import GCE, sha256
from globaleaks.utils.objectdict import ObjectDict
from globaleaks.utils.utility import datetime_now, uuid4


def db_bind_idp_identity(session, tid, user, subject):
    """
    Bind a user to the identity of the identity provider

    The accounts created via signup are bound to the identity that performed the
    registration; the accounts already existing when the identity provider is
    configured are bound to the identity that first authenticates on them, along
    the credentials of the account (trust on first use). No claim published by
    the identity provider is matched against the account, as the providers
    implementing a national digital identity publish pseudonymous subjects and
    personal data that a platform for whistleblowing does not hold. Any
    following authentication requires the identity bound to the account.

    :param session: An ORM session
    :param tid: A tenant ID
    :param user: The user being authenticated
    :param subject: The subject of the token issued by the identity provider
    """
    if not subject:
        raise errors.InvalidAuthentication

    if user.idp_id:
        if user.idp_id != subject:
            raise errors.InvalidAuthentication

        return

    # An identity is bound to a single account, so that the accounts of a
    # platform cannot be accumulated under the same identity
    if session.query(User).filter(User.tid == tid, User.idp_id == subject).count():
        raise errors.InvalidAuthentication

    user.idp_id = subject

    db_log(session, tid=user.tid, type='idp_identity_binding', user_id=user.id, object_id=user.id)


def db_login_failure(session, tid, whistleblower=False):
    Settings.failed_login_attempts[tid] = Settings.failed_login_attempts.get(tid, 0) + 1

    db_log(session, tid=tid, type='whistleblower_login_failure' if whistleblower else 'login_failure')


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
        raise errors.InvalidAuthentication

    itip = session.query(InternalTip) \
                  .filter(InternalTip.tid == tid,
                          InternalTip.receipt_hash == hash).one_or_none()

    if itip is None:
        raise errors.InvalidAuthentication

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
def login(session, tid, username, password, authcode, client_using_tor, client_ip, idp_subject=None):
    """
    Login transaction for users' access

    :param session: An ORM session
    :param tid: A tenant ID
    :param username: A provided username
    :param password: A provided password
    :param authcode: A provided authcode
    :param client_using_tor: A boolean signaling Tor usage
    :param client_ip:  The client IP
    :param idp_subject: The subject of the token issued by the identity provider
    :return: Returns a user session in case of success
    """
    query = session.query(User) \
                   .options(joinedload(User.profile).joinedload(UserProfile.permissions),
                            joinedload(User.profile).joinedload(UserProfile.roles)) \
                   .filter(User.enabled.is_(True), User.tid == tid)

    user = None

    # An account already bound to an identity of the identity provider is
    # resolved via the identity itself, that identifies it better than any
    # username; the username is required only to bind an identity not bound yet
    if tid in State.tenants and State.tenants[tid].cache.idp and idp_subject:
        user = query.filter(User.idp_id == idp_subject).one_or_none()

    if user is None:
        if tid in State.tenants and State.tenants[tid].cache.simplified_login:
            user = query.filter(or_(User.id == username, User.username == username)).one_or_none()
        else:
            user = query.filter(User.username == username).one_or_none()

    if user is None:
        raise errors.InvalidAuthentication

    try:
        if len(user.hash) == 64:
            key = Base64Encoder.decode(password.encode())
            hash = sha256(key).decode()
        else:
            key, hash = GCE.calculate_key_and_hash(password, user.salt)
    except:
        raise errors.InvalidAuthentication

    if not password or not GCE.check_equality(hash, user.hash):
        raise errors.InvalidAuthentication

    connection_check(tid, user.role, client_ip, client_using_tor)

    if user.two_factor_secret:
        if authcode == '':
            raise errors.TwoFactorAuthCodeRequired

        State.totp_verify(user.two_factor_secret, authcode)

    # The identity of the identity provider is bound to the account only once
    # the authentication has succeeded, so that a third party holding a token
    # of the identity provider cannot pin an identity on somebody else account
    if State.tenants[tid].cache.idp:
        db_bind_idp_identity(session, tid, user, idp_subject)

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

    # A logging-in holder propagates the statistical key to any admin/analyst
    # still missing it (covers activation-link and legacy accounts)
    if State.tenants[tid].cache.encryption and crypto_prv_key and user.crypto_global_stat_prv_key:
        db_reconcile_statistical_key(session, tid, user, crypto_prv_key)

    db_log(session, tid=tid, type='login', user_id=user.id)

    permissions = ObjectDict()
    for r in user_permissions:
        permissions[r] = r in user.profile.permissions_list

    user_session = Sessions.new(tid, user.id, user.tid, user.username, user.role, crypto_prv_key, user.crypto_escrow_prv_key, user.profile.roles_list, permissions)

    user_session.idp_id = user.idp_id

    return user_session


@transact
def get_auth_type(session, tid, username, idp_subject=None):
    """
    Resolve the authentication type and the salt to be applied by a client

    :param session: An ORM session
    :param tid: A tenant ID
    :param username: A provided username
    :param idp_subject: The subject of the token issued by the identity provider
    :return: The authentication type to be performed by the client
    """
    salt = ConfigFactory(session, tid).get_val('receipt_salt')

    if idp_subject:
        # The account bound to an identity of the identity provider is resolved
        # via the identity itself and is presented to its user, that is asked
        # for its password alone; an identity bound to no account requires
        # instead the user to identify the account to be bound to it
        user = session.query(User).filter(User.tid == tid, User.idp_id == idp_subject).one_or_none()

        if user is None:
            return {'type': 'binding'}

        if len(user.hash) == 64:
            return {'type': 'key', 'salt': user.salt, 'username': user.username}

        return {'type': 'password', 'username': user.username}

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

        idp_subject = None

        # A request carrying no username on a tenant configured with an identity
        # provider is resolved via the identity presented on the request itself
        if not username and State.tenants[self.request.tid].cache.idp and self.request.oidc_token:
            idp_subject = self.request.oidc_token.get('sub')

        return get_auth_type(self.request.tid, username, idp_subject)


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

        try:
            idp_subject = None

            if State.tenants[tid].cache.idp:
                if not self.request.oidc_token:
                    raise errors.InvalidAuthentication

                idp_subject = self.request.oidc_token.get('sub')

            session = yield login(tid,
                                  request['username'],
                                  request['password'],
                                  request['authcode'],
                                  self.request.client_using_tor,
                                  self.request.client_ip,
                                  idp_subject)
        except:
            yield tw(db_login_failure, self.request.tid, 0)
            raise

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

        session = Sessions.get(request['authtoken'])
        if session is None:
            yield tw(db_login_failure, self.request.tid, 0)
            raise errors.InvalidAuthentication

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

        connection_check(self.request.tid, 'whistleblower',
                         self.request.client_ip, self.request.client_using_tor)

        operator_id = None
        if self.session and self.session.properties.get('operator_session', False):
            # this is actually a recipient operating on behalf of a whistleblower
            operator_id = self.session.properties.get('operator_session')

        if request['receipt']:
            try:
                session = yield login_whistleblower(self.request.tid, request['receipt'],
                                                    self.request.client_using_tor, operator_id)
            except:
                yield tw(db_login_failure, self.request.tid, 1)
                raise
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
            # If the configuration requires authentication via the IDP session renewal
            # requires a valid token issued for the identity bound to the account
            if not self.request.oidc_token or self.request.oidc_token.get('sub') != self.session.idp_id:
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

        # The session is the one of the same user on the same tenant and
        # therefore keeps the identity bound to its account
        session.idp_id = self.session.idp_id

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
