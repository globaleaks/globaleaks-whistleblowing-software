import copy
import re

from twisted.internet.defer import inlineCallbacks, maybeDeferred

from globaleaks import models
from globaleaks.db import refresh_tenant_cache
from globaleaks.handlers.admin.node import db_update_enabled_languages
from globaleaks.handlers.admin.user_profile import user_permissions
from globaleaks.orm import tw
from globaleaks.rest import api, errors
from globaleaks.rest.decorators import USERS_ROLES
from globaleaks.tests import helpers
from globaleaks.tests.helpers import TestGL, forge_request


# What a route may ask for: one of the roles an account holds, the whistleblower,
# or one of the two keywords that stand for a set of them - 'user' for every
# account and 'any' for whoever asks
DECLARABLE_ROLES = USERS_ROLES | {'user', 'whistleblower'}


# The routes an administrator reaches without holding any permission. Each is a
# deliberate exception and is named here so that a new one cannot be introduced
# without this test being updated on purpose:
#
#   - entering a site one administers is not the management of an area;
#   - the catalog of the metrics and the options offered when choosing carry no
#     value of their own, only names to pick from;
#   - the operations on the configuration declare a permission of their own, one
#     per operation, inside the handler;
#   - the files of a site are served to whoever administers it.
ROUTES_OPEN_TO_EVERY_ADMINISTRATOR = {
    "AdminOperationHandler",
    "FileCollection",
    "FileInstance",
    "MetricCatalog",
    "SelectablesCollection",
    "TenantAuthSwitchHandler"
}


# The routes served to whoever asks, without a session. Each is a deliberate
# opening of the platform to the outside, and is named here so that a route
# cannot become public by the slip of a declaration:
#
#   - what a site publishes of itself, and what tells it is alive;
#   - the ways of authenticating, and the ones of recovering an access;
#   - what a reporting person and a registering organization submit;
#   - what a browser fetches on its own: files, translations, redirects and the
#     documents a domain is expected to serve.
ROUTES_OPEN_TO_ANYONE = {
    "admin.https.AcmeChallengeHandler",
    "admin.invite.InviteInstance",
    "auth.AuthTypeHandler",
    "auth.AuthenticationHandler",
    "auth.ReceiptAuthHandler",
    "auth.TokenAuthHandler",
    "auth.token.TokenHandler",
    "file.FileHandler",
    "health.HealthStatusHandler",
    "l10n.L10NHandler",
    "public.ContextInstance",
    "public.PublicResource",
    "redirect.SpecialRedirectHandler",
    "report.ReportHandler",
    "robots.RobotstxtHandler",
    "security.SecuritytxtHandler",
    "signup.Signup",
    "signup.SignupActivation",
    "sitemap.SitemapHandler",
    "support.SupportHandler",
    "user.reset_password.PasswordResetHandler",
    "user.validate_email.EmailValidation",
    "wizard.Wizard",
}


def handler_name(handler):
    return handler.__module__.replace('globaleaks.handlers.', '') + '.' + handler.__name__


def declared_permissions(handler, method):
    """
    Return the permissions a handler demands on one of its methods
    """
    permission = getattr(handler, 'require_permission', None)

    if isinstance(permission, dict):
        permission = permission.get(method)

    if permission is None:
        return ()

    return (permission,) if isinstance(permission, str) else tuple(permission)


def declared_methods(handler):
    return [m for m in ['delete', 'get', 'put', 'post'] if hasattr(handler, m)]


def route_arguments(spec):
    """
    Return the number of arguments the route of a spec carries
    """
    return re.compile(spec[2]).groups if len(spec) > 2 else 0


class TestAPI(TestGL):
    @inlineCallbacks
    def setUp(self):
        yield TestGL.setUp(self)

        self.api = api.APIResourceWrapper()

        yield tw(db_update_enabled_languages, 1, ['en', 'ar', 'it', 'pt_PT'], 'en')
        yield refresh_tenant_cache()

    def test_resolve_handler(self):
        testcases = [
            ('/api/public', api.public.PublicResource),
            ('/', api.staticfile.StaticFileHandler),
            ('/l10n/en', api.l10n.L10NHandler),
            ('/api/signup/cHa6qFmw89vyzOsY8JZjcKaBzXYWuZNMbiDwlYcCVYmIfLTBi0re_rzttIwcunEt', api.signup.SignupActivation)
        ]

        for testcase in testcases:
            match, handler = self.api.resolve_handler(testcase[0])
            self.assertEqual(handler, testcase[1])

    def test_api_spec(self):
        for spec in api.api_spec:
            check_roles = spec[1].check_roles
            self.assertIsNotNone(check_roles)

            if isinstance(check_roles, str):
                check_roles = {check_roles}

            self.assertTrue(len(check_roles) >= 1)
            self.assertTrue('any' not in check_roles or len(check_roles) == 1)

            rest = list(filter(lambda a: a not in ['any',
                                                   'user',
                                                   'whistleblower',
                                                   'admin',
                                                   'analyst',
                                                   'auditor',
                                                   'receiver',
                                                   'transmitter',
                                                   'custodian'], check_roles))
            self.assertTrue(len(rest) == 0)

    def test_every_administrative_route_declares_the_permission_of_its_area(self):
        """
        The routes are walked, not listed: a handler added tomorrow is checked
        """
        known = set(user_permissions) | set(models.admin_permissions)

        undeclared = set()

        for spec in api.api_spec:
            handler = spec[1]
            roles = handler.check_roles
            roles = {roles} if isinstance(roles, str) else set(roles)

            if 'admin' not in roles:
                continue

            demanded = set()
            for method in declared_methods(handler):
                demanded.update(declared_permissions(handler, method))

            if not demanded:
                undeclared.add(handler.__name__)
                continue

            # What is demanded is a permission the platform knows: a typo in a
            # declaration would otherwise leave the area open to everybody
            self.assertTrue(demanded.issubset(known),
                            f"{handler.__name__} demands {sorted(demanded - known)}, which is not a permission")

        self.assertEqual(undeclared, ROUTES_OPEN_TO_EVERY_ADMINISTRATOR)

    def test_get_with_no_accept_language_header(self):
        request = forge_request()
        self.assertEqual(self.api.detect_language(request), 'en')

    def test_get_with_accept_language_header_1(self):
        request = forge_request(headers={'Accept-Language': 'ar;q=0.8,it;q=0.6'})
        self.assertEqual(self.api.detect_language(request), 'ar')

    def test_get_with_accept_language_header_2(self):
        request = forge_request(headers={'Accept-Language': 'pt-PT,en;it;q=0.6'})
        self.assertEqual(self.api.detect_language(request), 'pt_PT')

    def test_get_with_accept_language_header_3(self):
        request = forge_request(headers={'Accept-Language': 'antani1,antani2;q=0.8,antani3;q=0.6'})
        self.assertEqual(self.api.detect_language(request), 'en')

    def test_status_codes_and_headers(self):
        test_cases = [
            (b'', 501),
            (b'DELETE', 501),
            (b'GET', 200),
            (b'HEAD', 200),
            (b'OPTIONS', 200),
            (b'POST', 501),
            (b'PUT', 501),
            (b'XXX', 501)
        ]

        default_server_headers = {
            'Cache-control': 'no-store',
            'Cross-Origin-Embedder-Policy': 'require-corp',
            'Cross-Origin-Opener-Policy': 'same-origin',
            'Cross-Origin-Resource-Policy': 'same-origin',
            'Origin-Agent-Cluster': '?1',
            'Permissions-Policy': 'accelerometer=(),'
                                  'ambient-light-sensor=(),'
                                  'bluetooth=(),'
                                  'camera=(),'
                                  'clipboard-read=(),'
                                  'clipboard-write=(self),'
                                  'document-domain=(),'
                                  'display-capture=(),'
                                  'fullscreen=(),'
                                  'geolocation=(),'
                                  'gyroscope=(),'
                                  'idle-detection=(self),'
                                  'keyboard-map=(),'
                                  'local-fonts=(),'
                                  'magnetometer=(),'
                                  'microphone=(),'
                                  'midi=(),'
                                  'notifications=(),'
                                  'payment=(),'
                                  'push=(),'
                                  'screen-wake-lock=(),'
                                  'serial=(),'
                                  'speaker-selection=(),'
                                  'usb=(),'
                                  'web-share=(),'
                                  'xr-spatial-tracking=()',
            'Content-Security-Policy': 'base-uri \'none\';'
                                       'default-src \'none\';'
                                       'form-action \'none\';'
                                       'frame-ancestors \'none\';'
                                       'sandbox;'
                                       'trusted-types;'
                                       'require-trusted-types-for \'script\';'
                                       'report-to csp-endpoint',
            'Reporting-Endpoints': 'csp-endpoint="/api/report"',
            'Referrer-Policy': 'no-referrer',
            'Server': 'GlobaLeaks',
            'X-Content-Type-Options': 'nosniff',
            'X-Check-Tor': 'False',
            'X-Frame-Options': 'deny'
        }

        server_headers = copy.copy(default_server_headers)
        server_headers['Content-Security-Policy'] = 'base-uri \'none\';' \
                                                    'connect-src \'self\';' \
                                                    'default-src \'none\';' \
                                                    'font-src \'self\';' \
                                                    'form-action \'none\';' \
                                                    'frame-ancestors \'none\';' \
                                                    'frame-src \'self\';' \
                                                    'img-src \'self\';' \
                                                    'media-src \'self\';' \
                                                    'script-src \'self\';' \
                                                    'style-src \'self\' \'random-nonce\';' \
                                                    'trusted-types angular angular#bundler dompurify default;' \
                                                    'require-trusted-types-for \'script\';' \
                                                    'report-to csp-endpoint'

        # '/' and '/index.html' are both served as the entry point: '/index.html'
        # is canonicalized to '/' and must not redirect.
        for entrypoint in (b"https://globaleaks.org/", b"https://globaleaks.org/index.html"):
            for method, status_code in test_cases:
                request = forge_request(uri=entrypoint, method=method)
                self.api.render(request)
                self.assertEqual(request.responseCode, status_code)
                self.assertEqual(request.path, b'/')
                for headerName, expectedHeaderValue in server_headers.items():
                    returnedHeaderValue = request.responseHeaders.getRawHeaders(headerName)[-1]

                    if headerName == 'Content-Security-Policy':
                        expectedHeaderValue = expectedHeaderValue.replace('random-nonce', f"nonce-{request.nonce.decode()}")  # noqa: PLW2901
                    self.assertEqual(returnedHeaderValue, expectedHeaderValue)

        server_headers = copy.copy(default_server_headers)
        server_headers['Content-Security-Policy'] = 'base-uri \'none\';' \
                                                    'default-src \'none\';' \
                                                    'form-action \'none\';' \
                                                    'frame-ancestors \'none\';' \
                                                    'script-src \'wasm-unsafe-eval\';' \
                                                    'sandbox;' \
                                                    'trusted-types;' \
                                                    'require-trusted-types-for \'script\';' \
                                                    'report-to csp-endpoint'

        for method, status_code in test_cases:
            request = forge_request(uri=b"https://globaleaks.org/workers/crypto.worker.js", method=method)
            self.api.render(request)
            self.assertEqual(request.responseCode, status_code)
            for headerName, expectedHeaderValue in server_headers.items():
                returnedHeaderValue = request.responseHeaders.getRawHeaders(headerName)[-1]
                self.assertEqual(returnedHeaderValue, expectedHeaderValue)

        server_headers = copy.copy(default_server_headers)

        for method, status_code in test_cases:
            request = forge_request(uri=b"https://globaleaks.org/api/public", method=method)
            self.api.render(request)
            self.assertEqual(request.responseCode, status_code)
            for headerName, expectedHeaderValue in server_headers.items():
                returnedHeaderValue = request.responseHeaders.getRawHeaders(headerName)[-1]
                self.assertEqual(returnedHeaderValue, expectedHeaderValue)

        server_headers = copy.copy(default_server_headers)
        server_headers['Content-Security-Policy'] = 'base-uri \'none\';' \
                                                    'default-src \'none\';' \
                                                    'connect-src blob:;' \
                                                    'form-action \'none\';' \
                                                    'frame-ancestors \'self\';' \
                                                    'img-src blob:;' \
                                                    'media-src blob:;' \
                                                    'script-src \'self\';' \
                                                    'style-src \'self\';' \
                                                    'sandbox allow-scripts;' \
                                                    'trusted-types;' \
                                                    'require-trusted-types-for \'script\';' \
                                                    'report-to csp-endpoint'

        server_headers['Cross-Origin-Resource-Policy'] = 'cross-origin'

        for method, status_code in test_cases:
            request = forge_request(uri=b"https://globaleaks.org/viewer/index.html", method=method)
            self.api.render(request)
            self.assertEqual(request.responseCode, status_code)
            for headerName, expectedHeaderValue in server_headers.items():
                returnedHeaderValue = request.responseHeaders.getRawHeaders(headerName)[-1]
                self.assertEqual(returnedHeaderValue, expectedHeaderValue)

        server_headers = copy.copy(default_server_headers)
        server_headers['Access-Control-Allow-Origin'] = 'null'

        for method, status_code in test_cases:
            request = forge_request(uri=b"https://globaleaks.org/viewer/script.js", method=method)
            self.api.render(request)
            self.assertEqual(request.responseCode, status_code)
            for headerName, expectedHeaderValue in server_headers.items():
                returnedHeaderValue = request.responseHeaders.getRawHeaders(headerName)[-1]
                self.assertEqual(returnedHeaderValue, expectedHeaderValue)

    def test_request_state_and_redirects(self):
        # Remote HTTP connection is always redirected to HTTPS
        request = forge_request(uri=b'http://globaleaks.org/')
        self.api.render(request)
        self.assertFalse(request.client_using_tor)
        self.assertEqual(request.responseCode, 302)

        # Local HTTP connection on port 8082 should be marked as not coming from Tor
        request = forge_request(uri=b'http://127.0.0.1:8082/', client_addr=b'127.0.0.1')
        self.api.render(request)
        self.assertFalse(request.client_using_tor)
        self.assertEqual(request.responseCode, 302)

        # Local HTTP connection on port 8083 should be marked as coming from Tor
        request = forge_request(uri=b'http://127.0.0.1:8083/', client_addr=b'127.0.0.1')
        self.api.render(request)
        self.assertTrue(request.client_using_tor)
        self.assertEqual(request.responseCode, 302)

        # Remote HTTP connection not coming from Tor should be redirected to HTTPS
        request = forge_request(uri=b'http://globaleaks.org/', client_addr=b'8.8.8.8')
        self.api.render(request)
        self.assertFalse(request.client_using_tor)
        self.assertEqual(request.responseCode, 302)
        self.assertEqual(request.responseHeaders.getRawHeaders('location')[0], 'https://globaleaks.org/')


class TestPermissionEnforcement(helpers.TestHandler):
    """
    Every permission a route declares is enforced on every one of its methods,
    """
    # A method that refuses for a reason of its own even when the permission is
    # held: the deletion of an invitation refuses one that does not exist, and
    # the identifier this test hands over is a made up one.
    REFUSING_FOR_THEIR_OWN_REASONS = {"AdminInviteInstance.delete"}

    @inlineCallbacks
    def test_the_declared_permission_is_demanded_by_every_method(self):
        exercised = 0

        for spec in api.api_spec:
            handler = spec[1]
            roles = handler.check_roles
            roles = {roles} if isinstance(roles, str) else set(roles)

            if 'admin' not in roles:
                continue

            arguments = ['x' * 36] * route_arguments(spec)

            for method in declared_methods(handler):
                demanded = declared_permissions(handler, method)
                if not demanded:
                    continue

                # The session holds every permission but the ones the method
                # demands: what is refused is refused for that reason alone
                request = self.request(role='admin',
                                       handler_cls=handler,
                                       permissions={p: False for p in demanded})

                yield self.assertFailure(
                    maybeDeferred(getattr(request, method), *arguments),
                    errors.ForbiddenOperation)

                # The counter-proof, without which the check above would pass
                # on a method that refuses everything: holding the permission,
                # the same call is no longer refused for lack of it.
                granted = self.request(role='admin',
                                       handler_cls=handler,
                                       permissions={p: True for p in demanded})

                try:
                    yield maybeDeferred(getattr(granted, method), *arguments)
                except errors.ForbiddenOperation:
                    self.assertIn(f"{handler.__name__}.{method}",
                                  self.REFUSING_FOR_THEIR_OWN_REASONS,
                                  f"{handler.__name__}.{method} refuses even to whoever holds {sorted(demanded)}")
                except Exception:  # noqa: S110
                    # Refused for anything else - a made up identifier, an empty
                    # body: what matters is that it is not the permission
                    pass

                exercised += 1

        # The walk found what it was supposed to: a change that emptied
        # api_spec, or that stopped declaring permissions altogether, would
        # otherwise leave this test green over nothing
        self.assertEqual(exercised, 93)


class TestPublicSurface(TestGL):
    """
    What the platform serves without a session is the surface it exposes to
    the outside: it is stated here in full, so that a route cannot join it
    without the decision being taken here as well.
    """

    def test_only_the_declared_routes_are_served_without_a_session(self):
        public = {handler_name(spec[1]) for spec in api.api_spec
                  if spec[1].check_roles == 'any'}

        self.assertEqual(public, ROUTES_OPEN_TO_ANYONE)

    def test_every_route_says_who_reaches_it(self):
        # A route that declares nothing inherits the default of the base
        # handler, which asks for an administrator: the platform fails closed,
        # and this states it rather than leaving it to be discovered
        for spec in api.api_spec:
            handler = spec[1]
            roles = handler.check_roles
            roles = {roles} if isinstance(roles, str) else set(roles)

            self.assertTrue(roles, f"{handler_name(handler)} declares no role")
            self.assertTrue(roles <= DECLARABLE_ROLES,
                            f"{handler_name(handler)} declares an unknown role: {sorted(roles)}")
