# Handlers dealing with platform authentication
import json
from datetime import timedelta
from sqlalchemy import exists, func, or_, and_
from sqlalchemy.orm import joinedload
from nacl.encoding import Base64Encoder
from twisted.internet.defer import inlineCallbacks

import globaleaks.handlers.auth.token
from globaleaks.handlers.admin.user import db_create_user
from globaleaks.handlers.admin.user_profile import db_resolve_default_user_profile
from globaleaks.handlers.base import connection_check, BaseHandler
from globaleaks.handlers.support import db_reconcile_support_key
from globaleaks.handlers.user import db_reconcile_statistical_key, user_permissions
from globaleaks.models import InternalTip, User, UserProfile

from globaleaks.models.config import ConfigFactory
from globaleaks.orm import db_log, transact, tw
from globaleaks.rest import errors, requests
from globaleaks.sessions import initialize_submission_session, Sessions
from globaleaks.state import State
from globaleaks.utils.crypto import GCE, sha256
from globaleaks.utils.log import log
from globaleaks.utils.objectdict import ObjectDict
from globaleaks.utils.utility import datetime_now, uuid4


def db_receipt_auth_is_legacy(session, tid):
    # Legacy server-hashed mode while any pre-key receipt_hash (length < 64) remains.
    return session.query(exists().where(and_(InternalTip.tid == tid,
                                              func.length(InternalTip.receipt_hash) < 64))).scalar()


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


def db_idp_username(session, tid, claims):
    """
    Resolve the username to be assigned to the account provisioned for an
    identity of the identity provider

    :param session: An ORM session
    :param tid: A tenant ID
    :param claims: The claims of the token issued by the identity provider
    :return: The username to be assigned to the account, empty when the
             identity provider publishes no usable username or when the
             username is already in use on the tenant
    """
    username = ''

    for claim in ['preferred_username', 'email', 'sub']:
        username = str(claims.get(claim) or '').strip()
        if username:
            break

    if not username:
        return ''

    # An username already in use is never reassigned: the identity is bound to
    # the account holding it via the credentials of the account itself
    if session.query(User).filter(User.tid == tid, User.username == username).count():
        return ''

    return username


def db_provision_idp_user(session, tid, claims, username):
    """
    Provision the account of an identity authenticated by the identity provider

    The account is created with the profile configured by default on the tenant
    and holds no password: its user is required to set one before proceeding,
    the encryption material of the account being generated at that point.

    :param session: An ORM session
    :param tid: A tenant ID
    :param claims: The claims of the token issued by the identity provider
    :param username: The username to be assigned to the account
    :return: The provisioned user
    """
    # An identity is bound to a single account, so that the accounts of a
    # platform cannot be accumulated under the same identity; the accounts
    # disabled in the meantime are taken into account as well
    if session.query(User).filter(User.tid == tid, User.idp_id == claims['sub']).count():
        raise errors.InvalidAuthentication

    role, profile_id = db_resolve_default_user_profile(session, tid)

    # A tenant creating no user by default provisions no account
    if not role:
        raise errors.InvalidAuthentication

    language = State.tenants[tid].cache.default_language

    user_desc = User().dict(language)
    user_desc['username'] = username
    user_desc['name'] = str(claims.get('name') or '').strip() or username
    user_desc['mail_address'] = str(claims.get('email') or '').strip()
    user_desc['language'] = language
    user_desc['role'] = role
    user_desc['profile_id'] = profile_id
    user_desc['idp_id'] = claims['sub']
    user_desc['password'] = ''
    user_desc['pgp_key_remove'] = False
    user_desc = user_desc | user_permissions

    user = db_create_user(session, tid, None, user_desc, language, defer_password_setup=True)

    db_log(session, tid=tid, type='idp_user_provisioning', user_id=user.id, object_id=user.id)

    return user





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
def login_whistleblower(session, tid, receipt, client_using_tor, operator_id=None, dpop_jkt=''):
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
    if operator_id is not None:
        itip.receipt_change_needed = True
        itip.operator_id = operator_id

    db_log(session, tid=tid, type='whistleblower_login', user_id=operator_id, object_id=itip.id)

    session = Sessions.new(tid, itip.id, tid, itip.id, 'whistleblower', crypto_prv_key, dpop_jkt=dpop_jkt)


    session.properties["receipt_change_needed"] = itip.receipt_change_needed

    return session


@transact
def login(session, tid, username, password, authcode, client_using_tor, client_ip, dpop_jkt='', idp_subject=None):

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
        db_login_failure(session, tid, 0)

    # An account provisioned by the identity provider and whose user has not
    # set a password yet is accessible only via the identity bound to it
    if not user.hash:
        raise errors.InvalidAuthentication

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
    elif State.tenants[tid].cache.encryption or \
         ConfigFactory(session, tid).get_val('crypto_support_pub_key'):
        crypto_prv_key, _ = GCE.generate_keypair()

        user.password_change_needed = True

    if State.tenants[tid].cache.password_change_period > 0 and \
       user.password_change_date < datetime_now() - timedelta(days=State.tenants[tid].cache.password_change_period):
        user.password_change_needed = True

    user.last_login = datetime_now()

    # A logging-in holder propagates the statistical key to any admin/analyst
    # still missing it (covers activation-link and legacy accounts)
    if State.tenants[tid].cache.encryption and crypto_prv_key and user.crypto_global_stat_prv_key:
        db_reconcile_statistical_key(session, tid, user, crypto_prv_key)

    if crypto_prv_key and user.crypto_support_prv_key:
        db_reconcile_support_key(session, tid, user, crypto_prv_key)

    db_log(session, tid=tid, type='login', user_id=user.id)

    permissions = ObjectDict()
    for r in user_permissions:
        permissions[r] = r in user.profile.permissions_list

    user_session = Sessions.new(tid, user.id, user.tid, user.username, user.role, crypto_prv_key, user.crypto_escrow_prv_key, user.profile.roles_list, permissions, sk=user.crypto_support_prv_key, dpop_jkt=dpop_jkt)

    user_session.properties['password_change_needed'] = user.password_change_needed
    user_session.properties['require_two_factor'] = State.tenants[tid].cache.two_factor and not user.two_factor_secret

    user_session.idp_id = user.idp_id

    return user_session


@transact
def login_idp(session, tid, claims, client_using_tor, client_ip, dpop_jkt=''):
    """
    Login transaction for the accounts provisioned by the identity provider

    The tenants configured to provision the accounts create an account for every
    identity that is not bound to any account yet; the account is created with
    no password and its user is required to set one before proceeding, so that
    the encryption material of the account is generated and held by its user
    alone. An account whose setup has not been completed keeps being accessible
    via its identity, so that an interrupted setup can be resumed.

    :param session: An ORM session
    :param tid: A tenant ID
    :param claims: The claims of the token issued by the identity provider
    :param client_using_tor: A boolean signaling Tor usage
    :param client_ip: The client IP
    :return: Returns a user session in case of success
    """
    subject = claims.get('sub')
    if not subject:
        raise errors.InvalidAuthentication

    user = session.query(User) \
                  .options(joinedload(User.profile).joinedload(UserProfile.permissions),
                           joinedload(User.profile).joinedload(UserProfile.roles)) \
                  .filter(User.enabled.is_(True),
                          User.tid == tid,
                          User.idp_id == subject).one_or_none()

    # An account holding a password is accessed via the password itself and
    # never via the identity provider alone
    if user is not None and user.hash:
        raise errors.InvalidAuthentication

    if user is None:
        if not State.tenants[tid].cache.idp_provisioning:
            raise errors.InvalidAuthentication

        username = db_idp_username(session, tid, claims)

        # An username already in use identifies an account of the platform that
        # is bound to the identity via its own credentials
        if not username:
            raise errors.InvalidAuthentication

        user = db_provision_idp_user(session, tid, claims, username)

    connection_check(tid, user.role, client_ip, client_using_tor)

    crypto_prv_key = ''
    if State.tenants[tid].cache.encryption or \
       ConfigFactory(session, tid).get_val('crypto_support_pub_key'):
        crypto_prv_key, _ = GCE.generate_keypair()

    user.password_change_needed = True
    user.last_login = datetime_now()

    db_log(session, tid=tid, type='login', user_id=user.id)

    permissions = ObjectDict()
    for r in user_permissions:
        permissions[r] = r in user.profile.permissions_list

    user_session = Sessions.new(tid, user.id, user.tid, user.username, user.role, crypto_prv_key, user.crypto_escrow_prv_key, user.profile.roles_list, permissions, sk=user.crypto_support_prv_key, dpop_jkt=dpop_jkt)

    user_session.idp_id = user.idp_id

    # The account is accessed before a password exists: the session carries the
    # obligation so that the client confines the user on setting one, exactly
    # as it does on the sessions opened with a password to be changed
    user_session.properties['password_change_needed'] = True
    user_session.properties['require_two_factor'] = State.tenants[tid].cache.two_factor and not user.two_factor_secret

    return user_session


@transact
def get_auth_type(session, tid, username, idp_claims=None):
    """
    Resolve the authentication type and the salt to be applied by a client

    :param session: An ORM session
    :param tid: A tenant ID
    :param username: A provided username
    :param idp_claims: The claims of the token issued by the identity provider
    :return: The authentication type to be performed by the client
    """
    salt = ConfigFactory(session, tid).get_val('receipt_salt')

    if idp_claims:
        # The account bound to an identity of the identity provider is resolved
        # via the identity itself and is presented to its user, that is asked
        # for its password alone; an identity bound to no account requires
        # instead the user to identify the account to be bound to it, unless the
        # tenant is configured to provision an account for every identity
        user = session.query(User).filter(User.tid == tid, User.idp_id == idp_claims.get('sub')).one_or_none()

        if user is None:
            if State.tenants[tid].cache.idp_provisioning and db_idp_username(session, tid, idp_claims):
                return {'type': 'provisioning'}

            return {'type': 'binding'}

        # The account has been provisioned and its user has not completed its
        # setup: the setup is resumed instead of asking for a password that
        # has never been set
        if not user.hash:
            return {'type': 'provisioning'}

        if len(user.hash) == 64:
            return {'type': 'key', 'salt': user.salt, 'username': user.username}

        return {'type': 'password', 'username': user.username}

    if not username: # whistleblower
        if not db_receipt_auth_is_legacy(session, tid):
            return {'type': 'key', 'salt': salt}

    else:
        user = session.query(User).filter(User.tid == tid, or_(User.username == username, User.id == username)).one_or_none()

        # Always calculate the user salt to not disclose if the user exists or not
        salt = GCE.generate_salt(salt + ":" + username)

        salt = salt if not user else user.salt

        # An account holding no password is presented as any other account, so
        # that the accounts still to be set up are not disclosed
        if not user or not user.hash or len(user.hash) == 64:
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

        idp_claims = None

        # A request carrying no username on a tenant configured with an identity
        # provider is resolved via the identity presented on the request itself
        if not username and State.tenants[self.request.tid].cache.idp and self.request.oidc_token:
            idp_claims = self.request.oidc_token

        return get_auth_type(self.request.tid, username, idp_claims)


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

        idp_subject = None
        session = None

        if State.tenants[tid].cache.idp:
            if not self.request.oidc_token:
                raise errors.InvalidAuthentication

            idp_subject = self.request.oidc_token.get('sub')

            # An authentication carrying no password is the one of an account
            # provisioned by the identity provider, whose user is required to
            # set a password before proceeding
            if not request['password']:
                session = yield login_idp(tid,
                                          self.request.oidc_token,
                                          self.request.client_using_tor,
                                          self.request.client_ip,
                                          self.get_dpop_thumbprint())

        if session is None:
            session = yield login(tid,
                                  request['username'],
                                  request['password'],
                                  request['authcode'],
                                  self.request.client_using_tor,
                                  self.request.client_ip,
                                  self.get_dpop_thumbprint(),
                                  idp_subject)


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

        operator_id = None
        if self.session and self.session.properties.get('operator_session', False):
            # this is actually a recipient operating on behalf of a whistleblower
            operator_id = self.session.properties.get('operator_session')

        dpop_jkt = self.get_dpop_thumbprint()

        if request['receipt']:
            session = yield login_whistleblower(self.request.tid, request['receipt'],
                                                self.request.client_using_tor, operator_id,
                                                dpop_jkt=dpop_jkt)

        else:
            if not self.state.accept_submissions or self.state.tenants[self.request.tid].cache['disable_submissions']:
                raise errors.SubmissionDisabled

            session = initialize_submission_session(self.request.tid, dpop_jkt=dpop_jkt)

        if operator_id:
            session.properties["operator_session"] = self.session.user_id

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

        # Check if the configuration requires authentication via the IDP
        if State.tenants[self.request.tid].cache.idp:
            # If the configuration requires authentication via the IDP session renewal
            # requires a valid token issued for the identity bound to the account
            if not self.request.oidc_token or self.request.oidc_token.get('sub') != self.session.idp_id:
                raise errors.InvalidAuthentication

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
                               permissions=self.session.permissions,
                               sk=self.session.sk,
                               dpop_jkt=self.get_dpop_thumbprint())


        session.properties['management_session'] = True
        session.properties['authtoken'] = True

        return {'redirect': '/t/%s/#/login?token=%s' % (State.tenants[tid].cache.uuid, session.id)}


class RoleAuthSwitchHandler(BaseHandler):
    """
    Login handler for switching role
    """
    check_roles = 'user'

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
                               permissions=self.session.permissions,
                               sk=self.session.sk)

        # The session is the one of the same user on the same tenant and
        # therefore keeps the identity bound to its account
        session.idp_id = self.session.idp_id

        # The redirect is spent through the token login, that alone can adopt
        # the session and bind it to the key of the client presenting it
        session.properties['authtoken'] = True

        return {'redirect': '/#/login?token=%s' % (session.id)}


class OperatorAuthSwitchHandler(BaseHandler):
    """
    Login handler for switching tenant
    """
    check_roles = 'receiver'

    def get(self):
        prv_key, _ = GCE.generate_keypair()

        session = Sessions.new(self.session.user_tid,
                               uuid4(),
                               self.session.user_tid,
                               "whistleblower",
                               "whistleblower",
                               self.session.cc,
                               self.session.ek,
                               permissions=self.session.permissions,
                               dpop_jkt=self.get_dpop_thumbprint())


        session.properties['operator_session'] = self.session.user_id
        session.properties['authtoken'] = True

        return {'redirect': '/#/login?token=%s' % session.id}
