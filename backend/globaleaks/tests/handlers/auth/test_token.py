from twisted.internet.defer import inlineCallbacks

from globaleaks.handlers.auth import token
from globaleaks.jobs import anomalies
from globaleaks.tests import helpers


class Test_Token(helpers.TestHandlerWithPopulatedDB):
    _handler = token.TokenHandler

    @inlineCallbacks
    def test_post(self):
        yield anomalies.Anomalies().run()

        handler = self.request({})

        handler.request.client_using_tor = True

        yield handler.post()
