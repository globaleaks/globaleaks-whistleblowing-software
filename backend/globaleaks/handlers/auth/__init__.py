# Handlers dealing with platform authentication
import json
from datetime import timedelta
from sqlalchemy import exists, func, or_, and_
from sqlalchemy.orm import joinedload
from nacl.encoding import Base64Encoder
from twisted.internet.defer import inlineCallbacks

import globaleaks.handlers.auth.token  # noqa: F401
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
from globaleaks.utils.utility import datetime_now
from globaleaks.db import refresh_tenant_cache


def db_receipt_auth_is_legacy(session, tid):
    # Legacy server-hashed mode while any pre-key receipt_hash (length < 64) remains.
    return session.query(exists().where(and_(InternalTip.tid == tid,
                                              func.length(InternalTip.receipt_hash) < 64))).scalar()


def db_bind_idp_identity(session, tid, user, subject):
    """
    Bind a user to the identity of the identity provider

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

    # An identity binds to a single account
    if session.query(User).filter(User.tid == tid, User.idp_id == subject).count():
        raise errors.InvalidAuthentication

    user.idp_id = subject

    db_log(session, tid=user.tid, type='idp_identity_binding', user_id=user.id, object_id=user.id)


def db_idp_username(session, tid, claims):
    """
    Resolve the username to be assigned to the account provisioned for an

    :param session: An ORM session
    :param tid: A tenant ID
    :param claims: The claims of the token issued by the identity provider
    :return: The username to be assigned to the account, empty when the
    """
    username = ''

    for claim in ['preferred_username', 'email', 'sub']:
        username = str(claims.get(claim) or '').strip()
        if username:
            break

    if not username:
        return ''

    # An existing username is never reassigned: the identity binds to it through its own credentials
    if session.query(User).filter(User.tid == tid, User.username == username).count():
        return ''

    return username


def db_provision_idp_user(session, tid, claims, username):
    """
    Provision the account of an identity authenticated by the identity provider

    :param session: An ORM session
    :param tid: A tenant ID
    :param claims: The claims of the token issued by the identity provider
    :param username: The username to be assigned to the account
    :return: The provisioned user
    """
    # An identity binds to a single account, disabled ones included
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
    user_desc['password'] = ''  # nosec B105
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

    session = Sessions.new(tid, itip.id, tid, itip.id, 'whistleblower', crypto_prv_key, dpop_jkt=dpop_jkt)


    session.properties["receipt_change_needed"] = itip.receipt_change_needed

    return session


def db_resolve_login_user(session, tid, username, idp_subject):
    """
    Resolve the account that logs in: an account already bound to the identity is resolved by it;
    the username only binds a new one

    :param session: An ORM session
    :param tid: A tenant ID
    :param username: A provided username
    :param idp_subject: The subject of the token issued by the identity provider
    :return: The account, or None
    """
    query = session.query(User) \
                   .options(joinedload(User.profile).joinedload(UserProfile.permissions),
                            joinedload(User.profile).joinedload(UserProfile.roles)) \
                   .filter(User.enabled.is_(True), User.tid == tid)

    tenant_cache = State.tenants[tid].cache if tid in State.tenants else None

    user = None
    if tenant_cache is not None and tenant_cache.idp and idp_subject:
        user = query.filter(User.idp_id == idp_subject).one_or_none()

    if user is not None:
        return user

    if tenant_cache is not None and tenant_cache.simplified_login:
        return query.filter(or_(User.id == username, User.username == username)).one_or_none()

    return query.filter(User.username == username).one_or_none()


def db_check_password(session, tid, user, password):
    """
    Check the password of an account, failing the login on a mismatch

    :param session: An ORM session
    :param tid: A tenant ID
    :param user: The account
    :param password: A provided password
    :return: The key derived from the password
    """
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

    return key


def db_unlock_private_key(session, tid, user, key):
    """
    Unlock the private key of an account; an account holding none on a site that encrypts is given
    one and has to change its password

    :param session: An ORM session
    :param tid: A tenant ID
    :param user: The account
    :param key: The key derived from the password
    :return: The private key, empty when the account holds none
    """
    if user.crypto_prv_key:
        return GCE.symmetric_decrypt(key, Base64Encoder.decode(user.crypto_prv_key))

    if State.tenants[tid].cache.encryption or \
       ConfigFactory(session, tid).get_val('crypto_support_pub_key'):
        crypto_prv_key, _ = GCE.generate_keypair()

        user.password_change_needed = True

        return crypto_prv_key

    return ''


def db_propagate_login_keys(session, tid, user, crypto_prv_key):
    """
    A logging-in holder propagates the statistical key to any admin/analyst still missing it
    (covers activation-link and legacy accounts), and the support key alike

    :param session: An ORM session
    :param tid: A tenant ID
    :param user: The account
    :param crypto_prv_key: The private key of the account
    """
    if State.tenants[tid].cache.encryption and crypto_prv_key and user.crypto_global_stat_prv_key:
        db_reconcile_statistical_key(session, tid, user, crypto_prv_key)

    if crypto_prv_key and user.crypto_support_prv_key:
        db_reconcile_support_key(session, tid, user, crypto_prv_key)


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
    user = db_resolve_login_user(session, tid, username, idp_subject)

    if user is None:
        db_login_failure(session, tid, 0)

    # An account provisioned by the identity provider without a password is accessible via the
    # identity only
    if not user.hash:
        raise errors.InvalidAuthentication

    connection_check(tid, user.role, client_ip, client_using_tor)

    key = db_check_password(session, tid, user, password)

    if user.two_factor_secret:
        if authcode == '':
            raise errors.TwoFactorAuthCodeRequired

        State.totp_verify(user.two_factor_secret, authcode)

    # Bound only after a successful authentication, so that a third party holding a token cannot pin
    # an identity on someone else's account
    if State.tenants[tid].cache.idp:
        db_bind_idp_identity(session, tid, user, idp_subject)

    if len(user.hash) != 64:
        user.password_change_needed = True

    crypto_prv_key = db_unlock_private_key(session, tid, user, key)

    if State.tenants[tid].cache.password_change_period > 0 and \
       user.password_change_date < datetime_now() - timedelta(days=State.tenants[tid].cache.password_change_period):
        user.password_change_needed = True

    user.last_login = datetime_now()

    db_propagate_login_keys(session, tid, user, crypto_prv_key)

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

    # An account holding a password is accessed via the password, never via the identity alone
    if user is not None and user.hash:
        raise errors.InvalidAuthentication

    if user is None:
        if not State.tenants[tid].cache.idp_provisioning:
            raise errors.InvalidAuthentication

        username = db_idp_username(session, tid, claims)

        # An existing username binds to the identity via its own credentials
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

    # No password yet: the session carries the obligation, as on a forced password change
    user_session.properties['password_change_needed'] = True
    user_session.properties['require_two_factor'] = State.tenants[tid].cache.two_factor and not user.two_factor_secret

    return user_session


def db_idp_auth_type(session, tid, idp_claims):
    """
    Resolve the authentication type of an identity: resolved by the identity and asked for the
    password alone; an unbound identity is bound through the username and the credentials

    :param session: An ORM session
    :param tid: A tenant ID
    :param idp_claims: The claims of the token issued by the identity provider
    :return: The authentication type to be performed by the client
    """
    user = session.query(User).filter(User.tid == tid, User.idp_id == idp_claims.get('sub')).one_or_none()

    if user is None:
        if State.tenants[tid].cache.idp_provisioning and db_idp_username(session, tid, idp_claims):
            return {'type': 'provisioning'}

        return {'type': 'binding'}

    # Setup not completed: resumed instead of asking for a password never set
    if not user.hash:
        return {'type': 'provisioning'}

    if len(user.hash) == 64:
        return {'type': 'key', 'salt': user.salt, 'username': user.username}

    return {'type': 'password', 'username': user.username}


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
    if idp_claims:
        return db_idp_auth_type(session, tid, idp_claims)

    salt = ConfigFactory(session, tid).get_val('receipt_salt')

    if not username: # whistleblower
        if not db_receipt_auth_is_legacy(session, tid):
            return {'type': 'key', 'salt': salt}

        return {'type': 'password'}

    user = session.query(User).filter(User.tid == tid, or_(User.username == username, User.id == username)).one_or_none()

    # Always calculate the user salt to not disclose if the user exists or not
    salt = GCE.generate_salt(salt + ":" + username)

    salt = salt if not user else user.salt

    # Presented as any other account, so that the accounts still to be set up are not disclosed
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

        # No username with an identity provider configured: resolved by the identity on the request
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

            # No password: the account was provisioned by the identity provider and the user must
            # set one
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
                'redirect': f'https://{State.tenants[tid].cache.hostname}/#/login?token={session.id}'
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

        # With an identity provider configured the renewal requires a valid token for the
        # identity bound to the account
        if State.tenants[self.request.tid].cache.idp and \
                (not self.request.oidc_token or self.request.oidc_token.get('sub') != self.session.idp_id):
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
            yield tw(db_log, tid=self.session.tid,  type='whistleblower_logout')
        else:
            yield tw(db_log, tid=self.session.tid,  type='logout', user_id=self.session.user_id)

        del Sessions[self.session.id]


class TenantAuthSwitchHandler(BaseHandler):
    """
    Login handler for switching tenant
    """
    check_roles = 'admin'

    @inlineCallbacks
    def get(self, tid):
        if self.request.tid != 1:
            raise errors.InvalidAuthentication

        tid = int(tid)

        # A site created a moment ago is not in the state yet: the answer to
        # its creation returns before the reload of the cache, and until then
        # the site has no name to be addressed by. It is loaded here, so that
        # the address handed back names the site instead of nothing.
        if not State.tenants.get(tid) or not State.tenants[tid].cache.uuid:
            # Local import: the database module reaches the handlers
            yield refresh_tenant_cache(tid)

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

        return {'redirect': f'/t/{State.tenants[tid].cache.uuid}/#/login?token={session.id}'}


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

        # Same user on the same tenant: the identity binding is kept
        session.idp_id = self.session.idp_id

        # Spent through the token login, which binds the session to the key of the client
        session.properties['authtoken'] = True

        return {'redirect': f'/#/login?token={session.id}'}
