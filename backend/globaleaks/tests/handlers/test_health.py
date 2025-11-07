from twisted.internet.defer import inlineCallbacks
from globaleaks.handlers import health
from globaleaks.tests import helpers


class TestHealthHandler(helpers.TestHandler):
    _handler = health.HealthStatusHandler

    @inlineCallbacks
    def test_get(self):
        result = yield self.request().get()
        self.assertEqual(result, "OK")

