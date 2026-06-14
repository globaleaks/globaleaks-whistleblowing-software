import json
from twisted.internet import defer
from twisted.internet.threads import deferToThread

from globaleaks.db import sync_refresh_tenant_cache
from globaleaks.handlers.base import connection_check
from globaleaks.rest import errors
from globaleaks.rest.cache import Cache
from globaleaks.state import State
from globaleaks.utils.ip import get_ip_identity
from globaleaks.utils.json import JSONEncoder
from globaleaks.utils.utility import deferred_sleep


USERS_ROLES = {'any', 'admin', 'analyst', 'custodian', 'receiver'}
BYPASS_PATHS = {b"/api/auth/token", b"/api/auth/type", b"/api/report"}

# A session pending a mandatory step (reset-token password change, forced
# password change, password-age expiry, or mandatory two-factor enrollment) is
# confined to this minimal set of endpoints: read its own preferences, perform
# the change/enrollment through operations, and refresh or close the session.
# The operations endpoint is further restricted to the allowed operation by
# UserOperationHandler.
ENFORCED_LIMITED_APIS = {b"/api/user/preferences", b"/api/user/operations", b"/api/auth/session"}

def has_session_or_token(self):
    return self.token or self.session


def check_session_or_token(self):
    # Ensures a token or a session is included in the request
    if self.request.path not in BYPASS_PATHS and not has_session_or_token(self):
        raise errors.InternalServerError("Invalid request: No token and no session")


def check_authentication(self, roles):
    # Performs role checks on the user session
    if isinstance(roles, str):
        roles = {roles}
    else:
        roles = set(roles)

    if 'any' in roles:
        return

    if self.session and self.session.tid == self.request.tid:
        if (self.session.properties.get('reset_token') or
            self.session.properties.get('password_change_needed') or
            self.session.properties.get('require_two_factor')) and \
           self.request.path not in ENFORCED_LIMITED_APIS:
            raise errors.ForbiddenOperation

        if ('user' in roles and self.session.role in USERS_ROLES) or \
           self.session.role in roles:
            # Enforce the session-owning tenant's connection policy on every
            # authenticated request, so that a session cannot be used from a
            # network or transport (e.g. non-Tor) that the tenant rejects,
            # regardless of how or where the session was originally minted.
            connection_check(self.session.tid, self.session.role,
                             self.request.client_ip, self.request.client_using_tor)
            return

    raise errors.NotAuthenticated


def decorator_require_session_or_token(f):
    # Decorator that ensures a token or a session is included in the request
    def wrapper(self, *args, **kwargs):
        check_session_or_token(self)
        return f(self, *args, **kwargs)

    return wrapper


def decorator_authentication(f, roles):
    # Decorator that performs role checks on the user session
    def wrapper(self, *args, **kwargs):
        check_authentication(self, roles)
        return f(self, *args, **kwargs)

    return wrapper


def decorator_cache_get(f):
    # Decorator that checks if the requests resource is cached
    def wrapper(self, *args, **kwargs):
        c = Cache.get(self.request.tid, self.request.path, self.request.language)
        if c is None:
            d = defer.maybeDeferred(f, self, *args, **kwargs)
            d.addCallback(lambda data: Cache.set(self.request.tid, self.request.path, self.request.language, b'application/json', json.dumps(data, cls=JSONEncoder))[1])
            return d
        self.request.setHeader(b'Content-type', c[0])
        return c[1]

    return wrapper


def decorator_cache_invalidate(f):
    def wrapper(self, *args, **kwargs):
        d = defer.maybeDeferred(f, self, *args, **kwargs)

        if self.invalidate_cache:
            def callback(result):
                Cache.invalidate(self.request.tid)
                deferToThread(sync_refresh_tenant_cache, self.request.tid)
                return result

            d.addCallback(callback)

        return d

    return wrapper

def decorator_rate_limit(f):
    def wrapper(self, *args, **kwargs):
        root_tenant = State.tenants.get(1)
        if not root_tenant:
            return

        delay = False
        block = False
        client_ip = get_ip_identity(self.request.client_ip).encode()
        tid = str(self.request.tid).encode()
        path = self.request.path
        if path in (b'/api/auth/authentication', b'/api/auth/tokenauth', b'/api/auth/receiptauth'):
            # Login endpoints are throttled regardless of any presented session:
            # a session must not exempt the caller from the login thresholds
            # (e.g. minting unlimited submission sessions via empty receipts)
            if not self.request.client_using_tor:
                delay = State.RateLimit.check(b"logins_per_minute_per_tenant_per_ip:" + tid + b":" + client_ip,
                                              root_tenant.cache.threshold_logins_per_minute_per_tenant_per_ip,
                                              60)

                delay = delay or \
                        State.RateLimit.check(b"logins_per_minute_per_ip:" + client_ip,
                                              root_tenant.cache.threshold_logins_per_minute_per_ip,
                                              60)

            delay = delay or \
                    State.RateLimit.check(b"logins_per_minute_per_tenant:" + tid,
                                          root_tenant.cache.threshold_logins_per_minute_per_tenant,
                                          60)

            delay = delay or \
                    State.RateLimit.check(b"logins_per_minute_per_system",
                                          root_tenant.cache.threshold_logins_per_minute_per_system,
                                          60)
        elif path == b'/api/support':
            # Support requests are throttled regardless of any presented
            # session or token: a token-only caller must not be able to
            # enqueue unbounded administrator notification mail.
            if not self.request.client_using_tor:
                block = State.RateLimit.check(b"support_per_hour_per_tenant_per_ip:" + tid + b":" + client_ip,
                                              root_tenant.cache.threshold_support_per_hour_per_tenant_per_ip,
                                              3600) > 0

                block = block or \
                        State.RateLimit.check(b"support_per_hour_per_ip:" + client_ip,
                                              root_tenant.cache.threshold_support_per_hour_per_ip,
                                              3600) > 0

            block = block or \
                    State.RateLimit.check(b"support_per_hour_per_tenant:" + tid,
                                          root_tenant.cache.threshold_support_per_hour_per_tenant,
                                          3600) > 0

            block = block or \
                    State.RateLimit.check(b"support_per_hour_per_system",
                                          root_tenant.cache.threshold_support_per_hour_per_system,
                                          3600) > 0

        elif path == b'/api/signup':
            # Signup is public and allocates persistent tenant state plus
            # administrator notification mail: a token-only caller must not be
            # able to register unbounded tenants. Signup is served only on the
            # root tenant, so per-IP limits are enforced (skipped on Tor, where
            # the client IP is not meaningful) together with a per-system
            # backstop that also bounds Tor traffic.
            if not self.request.client_using_tor:
                block = State.RateLimit.check(b"signups_per_minute_per_ip:" + client_ip,
                                              root_tenant.cache.threshold_signups_per_minute_per_ip,
                                              60) > 0

                block = block or \
                        State.RateLimit.check(b"signups_per_hour_per_ip:" + client_ip,
                                              root_tenant.cache.threshold_signups_per_hour_per_ip,
                                              3600) > 0

            block = block or \
                    State.RateLimit.check(b"signups_per_hour_per_system",
                                          root_tenant.cache.threshold_signups_per_hour_per_system,
                                          3600) > 0

        elif self.session:
            user_id = self.session.user_id.encode()

            if self.session.role == 'whistleblower' and path.startswith(b'/api/whistleblower/'):
                if self.request.path == b'/api/whistleblower/submission':
                    if not self.request.client_using_tor:
                        block = State.RateLimit.check(b"reports_per_hour_per_tenant_per_ip:" + tid + b":" + client_ip,
                                                      root_tenant.cache.threshold_reports_per_hour_per_tenant_per_ip,
                                                      3600) > 0

                        block = block or \
                                State.RateLimit.check(b"reports_per_hour_per_ip:" + client_ip,
                                                      root_tenant.cache.threshold_reports_per_hour_per_ip,
                                                      3600) > 0

                    block = block or \
                            State.RateLimit.check(b"reports_per_hour_per_tenant:" + tid,
                                                  root_tenant.cache.threshold_reports_per_hour_per_tenant,
                                                  3600) > 0

                    block = block or \
                            State.RateLimit.check(b"reports_per_hour_per_system",
                                                  root_tenant.cache.threshold_reports_per_hour_per_system,
                                                  3600) > 0
                else:
                    if not self.upload_handler:
                        delay = State.RateLimit.check(b"operations_per_second_per_report:" + user_id,
                                                      root_tenant.cache.threshold_operations_per_second_per_report,
                                                      1)

                        delay = delay or \
                                State.RateLimit.check(b"operations_per_minute_per_report:" + user_id,
                                                      root_tenant.cache.threshold_operations_per_minute_per_report,
                                                      60)

                        delay = delay or \
                                State.RateLimit.check(b"operations_per_hour_per_report:" + user_id,
                                                      root_tenant.cache.threshold_operations_per_hour_per_report,
                                                      3600)

        if block:
            raise errors.ForbiddenOperation()

        elif delay:
            d = deferred_sleep(min(60, 0.2 * 2 ** delay))
            d.addCallback(lambda _: f(self, *args, **kwargs))
            return d

        return f(self, *args, **kwargs)

    return wrapper


def decorate_method(h, method):
    roles = getattr(h, 'check_roles')
    if isinstance(roles, str):
        roles = {roles}

    f = getattr(h, method)

    if State.settings.enable_api_cache:
        if method == 'get':
            if h.cache_resource:
                f = decorator_cache_get(f)
        elif method in ['delete', 'post', 'put']:
            if h.invalidate_cache:
                f = decorator_cache_invalidate(f)

    if method in ['delete', 'post', 'put']:
        f = decorator_rate_limit(f)
        f = decorator_require_session_or_token(f)

    f = decorator_authentication(f, roles)

    setattr(h, method, f)
