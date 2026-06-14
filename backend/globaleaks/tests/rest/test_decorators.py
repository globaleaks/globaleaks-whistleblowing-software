from twisted.trial import unittest
from twisted.internet import defer
from unittest.mock import MagicMock, patch
from globaleaks.rest import errors
from globaleaks.state import State
from globaleaks.rest.cache import Cache
from globaleaks.rest.decorators import (decorator_rate_limit, decorator_require_session_or_token,
                                        decorator_authentication, decorator_cache_get, decorator_cache_invalidate)
from globaleaks.utils.utility import uuid4


class FakeRequest:
    def __init__(self, tid=1, path=b"/test", language="en", client_ip="127.0.0.1", client_using_tor=True):
        self.tid = tid
        self.path = path
        self.client_ip = client_ip
        self.client_using_tor = client_using_tor
        self.language = language  # Add this line
        self.responseHeaders = MagicMock()

    def setHeader(self, key, value):
        pass


class FakeSession:
    def __init__(self, role="user", tid=1, properties=None):
        self.role = role
        self.tid = tid
        self.properties = properties if properties is not None else {}


class FakeHandler:
    upload_handler = False
    invalidate_cache = False
    token = False
    session = False


class TestDecorators(unittest.TestCase):
    def setUp(self):
        State.RateLimit.enabled = True

        # Patch deferred_sleep to immediately succeed (fake no wait)
        self.sleep_patch = patch(
            "globaleaks.rest.decorators.deferred_sleep",
            return_value=defer.succeed(None)
        )
        self.sleep_patch.start()

        root_tenant = MagicMock()
        # connection_check (run by decorator_authentication) reads connection
        # policy via cache.get; default to a permissive policy for these tests
        root_tenant.cache.get.return_value = False
        root_tenant.cache.threshold_reports_per_hour_per_system = 50
        root_tenant.cache.threshold_reports_per_hour_per_tenant = 10
        root_tenant.cache.threshold_reports_per_hour_per_ip = 10
        root_tenant.cache.threshold_reports_per_hour_per_tenant_per_ip = 5
        root_tenant.cache.threshold_attachments_per_hour_per_report = 30
        root_tenant.cache.threshold_operations_per_hour_per_report = 50
        root_tenant.cache.threshold_operations_per_minute_per_report = 10
        root_tenant.cache.threshold_operations_per_second_per_report = 1

        State.tenants[1] = root_tenant

    def tearDown(self):
        # Stop patches after each test
        self.sleep_patch.stop()

    def test_decorator_require_session_or_token(self):
        self.handler = FakeHandler()
        self.handler.session = FakeSession()
        self.handler.token = None
        self.handler.request = FakeRequest()

        @decorator_require_session_or_token
        def test_func(self): return "Authenticated"

        self.handler.session = None
        self.handler.request.token = None
        self.handler.request.path = b"/forbidden"

        with self.assertRaises(errors.InternalServerError):
            test_func(self.handler)

    def test_decorator_authentication(self):
        self.handler = FakeHandler()
        self.handler.session = FakeSession()
        self.handler.session.role = "user"
        self.handler.token = None
        self.handler.request = FakeRequest()

        def test_func(self):
            return "Authorized"

        decorated_func = decorator_authentication(test_func, ["admin"])

        with self.assertRaises(errors.NotAuthenticated):
            decorated_func(self.handler)

        self.handler.session.role = "admin"
        self.assertEqual(decorated_func(self.handler), "Authorized")

    def test_decorator_authentication_reset_token_confined(self):
        self.handler = FakeHandler()
        self.handler.session = FakeSession(role="receiver",
                                           properties={"reset_token": "x"})
        self.handler.token = None
        self.handler.request = FakeRequest()

        def test_func(self):
            return "Authorized"

        decorated_func = decorator_authentication(test_func, ["receiver"])

        # While the reset token is held every other endpoint is forbidden
        self.handler.request.path = b"/api/recipient/rtips"
        with self.assertRaises(errors.ForbiddenOperation):
            decorated_func(self.handler)

        # The endpoints needed to complete the password change stay reachable
        for path in (b"/api/user/preferences",
                     b"/api/user/operations",
                     b"/api/auth/session"):
            self.handler.request.path = path
            self.assertEqual(decorated_func(self.handler), "Authorized")

        # Once the reset token is cleared the session regains full access
        self.handler.session.properties = {}
        self.handler.request.path = b"/api/recipient/rtips"
        self.assertEqual(decorated_func(self.handler), "Authorized")

    def test_decorator_authentication_password_change_confined(self):
        self.handler = FakeHandler()
        self.handler.session = FakeSession(role="receiver",
                                           properties={"password_change_needed": True})
        self.handler.token = None
        self.handler.request = FakeRequest()

        def test_func(self):
            return "Authorized"

        decorated_func = decorator_authentication(test_func, ["receiver"])

        # While the forced password change is pending every other endpoint is forbidden
        self.handler.request.path = b"/api/recipient/rtips"
        with self.assertRaises(errors.ForbiddenOperation):
            decorated_func(self.handler)

        # The endpoints needed to complete the password change stay reachable
        for path in (b"/api/user/preferences",
                     b"/api/user/operations",
                     b"/api/auth/session"):
            self.handler.request.path = path
            self.assertEqual(decorated_func(self.handler), "Authorized")

        # Once the password change is completed the session regains full access
        self.handler.session.properties = {}
        self.handler.request.path = b"/api/recipient/rtips"
        self.assertEqual(decorated_func(self.handler), "Authorized")

    def test_decorator_authentication_require_two_factor_confined(self):
        self.handler = FakeHandler()
        self.handler.session = FakeSession(role="receiver",
                                           properties={"require_two_factor": True})
        self.handler.token = None
        self.handler.request = FakeRequest()

        def test_func(self):
            return "Authorized"

        decorated_func = decorator_authentication(test_func, ["receiver"])

        # While the mandatory 2fa enrollment is pending every other endpoint is forbidden
        self.handler.request.path = b"/api/recipient/rtips"
        with self.assertRaises(errors.ForbiddenOperation):
            decorated_func(self.handler)

        # The endpoints needed to complete the enrollment stay reachable
        for path in (b"/api/user/preferences",
                     b"/api/user/operations",
                     b"/api/auth/session"):
            self.handler.request.path = path
            self.assertEqual(decorated_func(self.handler), "Authorized")

        # Once the enrollment is completed the session regains full access
        self.handler.session.properties = {}
        self.handler.request.path = b"/api/recipient/rtips"
        self.assertEqual(decorated_func(self.handler), "Authorized")

    def test_decorator_authentication_enforces_tor_policy(self):
        # A session whose role is restricted to Tor must be rejected per-request
        # when presented over a non-Tor connection, even though the session was
        # authorized once at login.
        self.handler = FakeHandler()
        self.handler.session = FakeSession(role="receiver")
        self.handler.token = None
        self.handler.request = FakeRequest()

        State.tenants[1].cache.get.side_effect = \
            lambda key, default=None: {'https_receiver': False}.get(key, False)

        def test_func(self):
            return "Authorized"

        decorated_func = decorator_authentication(test_func, ["receiver"])

        self.handler.request.client_using_tor = False
        with self.assertRaises(errors.TorNetworkRequired):
            decorated_func(self.handler)

        # Over Tor the same session is authorized
        self.handler.request.client_using_tor = True
        self.assertEqual(decorated_func(self.handler), "Authorized")

    def test_decorator_authentication_enforces_ip_filter(self):
        # A session whose role is IP-filtered must be rejected per-request when
        # presented from an address outside the configured range.
        self.handler = FakeHandler()
        self.handler.session = FakeSession(role="receiver")
        self.handler.token = None
        self.handler.request = FakeRequest()

        policy = {'ip_filter_receiver_enable': True,
                  'ip_filter_receiver': '192.0.2.0/24',
                  'https_receiver': True}
        State.tenants[1].cache.get.side_effect = \
            lambda key, default=None: policy.get(key, False)

        def test_func(self):
            return "Authorized"

        decorated_func = decorator_authentication(test_func, ["receiver"])

        self.handler.request.client_ip = "198.51.100.5"
        with self.assertRaises(errors.AccessLocationInvalid):
            decorated_func(self.handler)

        # From an allowed address the same session is authorized
        self.handler.request.client_ip = "192.0.2.10"
        self.assertEqual(decorated_func(self.handler), "Authorized")

    @defer.inlineCallbacks
    def test_decorator_cache_get(self):
        self.handler = FakeHandler()
        self.handler.session = FakeSession()
        self.handler.token = None
        self.handler.request = FakeRequest()

        Cache.set(1, b"/test", "en", b"application/json", "cached_response")

        @decorator_cache_get
        def test_func(self): return defer.succeed({"message": "fresh_response"})

        result = yield test_func(self.handler)
        self.assertEqual(result, "cached_response")

    @defer.inlineCallbacks
    def test_decorator_cache_invalidate(self):
        self.handler = FakeHandler()
        self.handler.session = FakeSession()
        self.handler.token = None
        self.handler.request = FakeRequest()
        self.handler.invalidate_cache = True

        Cache.set(1, b"/test", "en", b"application/json", "cached_response")

        @decorator_cache_invalidate
        def test_func(self):
            return defer.succeed("Updated")

        result = yield test_func(self.handler)
        self.assertEqual(result, "Updated")

    @defer.inlineCallbacks
    def test_decorator_rate_limit_no_limit(self):
        self.handler = FakeHandler()
        self.handler.session = FakeSession()
        self.handler.token = None
        self.handler.request = FakeRequest()

        self.handler.session.role = "whistleblower"
        self.handler.session.user_id = uuid4()
        self.handler.request.tid = 1
        self.handler.request.path = b"/api/whistleblower/submission"

        @decorator_rate_limit
        def test_func(self): return defer.succeed("Passed")
        result = yield test_func(self.handler)
        self.assertEqual(result, "Passed")

    def test_decorator_rate_limit_login_throttled_with_session(self):
        self.handler = FakeHandler()
        self.handler.session = FakeSession(role="whistleblower")
        self.handler.session.user_id = uuid4()
        self.handler.token = None
        self.handler.request = FakeRequest(path=b"/api/auth/receiptauth")

        rate_limit_mock = MagicMock()
        rate_limit_mock.check.return_value = 0
        State.RateLimit = rate_limit_mock

        @decorator_rate_limit
        def test_func(self): return "Passed"

        self.assertEqual(test_func(self.handler), "Passed")

        # Holding a session must not exempt login endpoints from login throttling
        checked_keys = [call.args[0] for call in rate_limit_mock.check.call_args_list]
        self.assertTrue(any(key.startswith(b"logins_per_minute") for key in checked_keys))

    # Contract for every endpoint throttled by decorator_rate_limit: the buckets
    # it must consult, whether each is skipped on Tor (per-IP buckets, where the
    # client IP is shared and not meaningful), and the effect of tripping a
    # bucket ('block' -> ForbiddenOperation, 'delay' -> deferred execution).
    RATE_LIMIT_CONTRACT = [
        {"paths": [b"/api/auth/authentication",
                   b"/api/auth/tokenauth",
                   b"/api/auth/receiptauth"],
         "role": None, "action": "delay",
         "buckets": [(b"logins_per_minute_per_tenant_per_ip", True),
                     (b"logins_per_minute_per_ip", True),
                     (b"logins_per_minute_per_tenant", False),
                     (b"logins_per_minute_per_system", False)]},
        {"paths": [b"/api/support"],
         "role": None, "action": "block",
         "buckets": [(b"support_per_hour_per_tenant_per_ip", True),
                     (b"support_per_hour_per_ip", True),
                     (b"support_per_hour_per_tenant", False),
                     (b"support_per_hour_per_system", False)]},
        {"paths": [b"/api/signup"],
         "role": None, "action": "block",
         "buckets": [(b"signups_per_minute_per_ip", True),
                     (b"signups_per_hour_per_ip", True),
                     (b"signups_per_hour_per_system", False)]},
        {"paths": [b"/api/whistleblower/submission"],
         "role": "whistleblower", "action": "block",
         "buckets": [(b"reports_per_hour_per_tenant_per_ip", True),
                     (b"reports_per_hour_per_ip", True),
                     (b"reports_per_hour_per_tenant", False),
                     (b"reports_per_hour_per_system", False)]},
        {"paths": [b"/api/whistleblower/operations"],
         "role": "whistleblower", "action": "delay",
         "buckets": [(b"operations_per_second_per_report", False),
                     (b"operations_per_minute_per_report", False),
                     (b"operations_per_hour_per_report", False)]},
    ]

    def test_decorator_rate_limit_contract(self):
        # Each bucket is tripped in isolation, on and off Tor, so the test fails
        # if an endpoint loses its limiting, swaps block for delay, or stops
        # honouring the Tor skip on its per-IP buckets.
        for endpoint in self.RATE_LIMIT_CONTRACT:
            for path in endpoint["paths"]:
                for bucket, skipped_on_tor in endpoint["buckets"]:
                    for tor in (False, True):
                        with self.subTest(path=path, bucket=bucket, tor=tor):
                            self.handler = FakeHandler()
                            self.handler.token = "x"
                            self.handler.request = FakeRequest(path=path, client_using_tor=tor)
                            if endpoint["role"]:
                                self.handler.session = FakeSession(role=endpoint["role"])
                                self.handler.session.user_id = uuid4()
                            else:
                                self.handler.session = None

                            rate_limit_mock = MagicMock()
                            rate_limit_mock.check.side_effect = \
                                lambda key, *_, b=bucket: 1 if key.startswith(b) else 0
                            State.RateLimit = rate_limit_mock

                            @decorator_rate_limit
                            def test_func(self): return "Passed"

                            checked = lambda: [c.args[0] for c in rate_limit_mock.check.call_args_list]

                            if tor and skipped_on_tor:
                                # the per-IP bucket must not be consulted over Tor
                                self.assertEqual(test_func(self.handler), "Passed")
                                self.assertFalse(any(k.startswith(bucket) for k in checked()))
                                continue

                            if endpoint["action"] == "block":
                                with self.assertRaises(errors.ForbiddenOperation):
                                    test_func(self.handler)
                            else:
                                self.assertEqual(self.successResultOf(test_func(self.handler)), "Passed")

                            # the tripped bucket must have been consulted
                            self.assertTrue(any(k.startswith(bucket) for k in checked()))
