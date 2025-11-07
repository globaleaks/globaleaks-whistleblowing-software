import json
from twisted.internet import defer
from twisted.internet.threads import deferToThread

from globaleaks.db import sync_refresh_tenant_cache
from globaleaks.rest import errors
from globaleaks.rest.cache import Cache
from globaleaks.state import State
from globaleaks.utils.ip import get_ip_identity
from globaleaks.utils.json import JSONEncoder
from globaleaks.utils.utility import deferred_sleep


USERS_ROLES = {'any', 'admin', 'analyst', 'custodian', 'receiver'}
BYPASS_PATHS = {b"/api/auth/token", b"/api/auth/type", b"/api/report"}

def has_session_or_token(self):
    return self.token or self.session


def decorator_require_session_or_token(f):
    # Decorator that ensures a token or a session is included in the request
    def wrapper(self, *args, **kwargs):
        if self.request.path not in BYPASS_PATHS and not has_session_or_token(self):
            raise errors.InternalServerError("Invalid request: No token and no session")

        return f(self, *args, **kwargs)

    return wrapper


def decorator_authentication(f, roles):
    # Decorator that performs role checks on the user session
    def wrapper(self, *args, **kwargs):
        user_roles = set(roles)  # Convert roles to set
        if 'any' in user_roles:
            return f(self, *args, **kwargs)
        if self.session and self.session.tid == self.request.tid:
            if 'user' in user_roles and self.session.role in USERS_ROLES:
                return f(self, *args, **kwargs)
            if self.session.role in user_roles:
                return f(self, *args, **kwargs)

        raise errors.NotAuthenticated

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
        if self.session:
            user_id = self.session.user_id.encode()

            if self.session.role == 'whistleblower' and path.startswith(b'/api/whistleblower/'):
                if self.request.path == b'/api/whistleblower/submission':
                    block = State.RateLimit.check(b"reports_per_hour_per_tenant_per_ip:" + tid,
                                                  root_tenant.cache.threshold_reports_per_hour_per_tenant_per_ip,
                                                  3600) > 0

                    block = block or \
                            State.RateLimit.check(b"reports_per_hour_per_ip:" + tid + b":" + client_ip,
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
        else:
            if self.request.path in [b'/api/auth/authentication', b'/api/auth/receiptauth', b'/api/auth/authentication']:
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
        f = decorator_require_session_or_token(f)
        if State.settings.enable_rate_limiting:
            f = decorator_rate_limit(f)

    f = decorator_authentication(f, roles)

    setattr(h, method, f)
