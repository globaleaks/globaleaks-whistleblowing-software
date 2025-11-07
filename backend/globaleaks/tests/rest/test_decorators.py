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
    def __init__(self, tid=1, path=b"/test", client_ip="127.0.0.1", language="en"):
        self.tid = tid
        self.path = path
        self.client_ip = client_ip
        self.language = language  # Add this line
        self.responseHeaders = MagicMock()

    def setHeader(self, key, value):
        pass


class FakeSession:
    def __init__(self, role="user", tid=1):
        self.role = role
        self.tid = tid


class FakeHandler:
    upload_handler = False
    invalidate_cache = False
    token = False
    session = False


class TestDecorators(unittest.TestCase):
    def setUp(self):
        State.settings.enable_rate_limiting = True

        # Patch deferred_sleep to immediately succeed (fake no wait)
        self.sleep_patch = patch(
            "globaleaks.rest.decorators.deferred_sleep",
            return_value=defer.succeed(None)
        )
        self.sleep_patch.start()

        root_tenant = MagicMock()
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

    def test_decorator_rate_limit_whistleblower_blocked(self):
        self.handler = FakeHandler()
        self.handler.session = FakeSession()
        self.handler.token = None
        self.handler.request = FakeRequest()

        self.handler.session.role = "whistleblower"
        self.handler.session.user_id = uuid4()
        self.handler.request.tid = 1
        self.handler.request.path = b"/api/whistleblower/submission"

        # Patch RateLimit to simulate rate limit block
        rate_limit_mock = MagicMock()
        rate_limit_mock.check.side_effect = [True]
        State.RateLimit = rate_limit_mock

        @decorator_rate_limit
        def test_func(self): return "Should not run"

        with self.assertRaises(errors.ForbiddenOperation):
            test_func(self.handler)
