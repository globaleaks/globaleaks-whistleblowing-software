from twisted.internet.defer import inlineCallbacks

from globaleaks.handlers.staticfile import StaticFileHandler
from globaleaks.rest import errors
from globaleaks.tests import helpers

class TestStaticFileHandler(helpers.TestHandler):
    _handler = StaticFileHandler

    @inlineCallbacks
    def test_get_existent(self):
        handler = self.request()

        # Mock the nonce used for this request
        handler.request.nonce = b'secureNonce123'

        # Call the handler
        yield handler.get('index.html')

        # Get response body and decode
        body = handler.request.getResponseBody().decode()

        # Ensure it's HTML and the nonce was injected
        self.assertIn('nonce="secureNonce123"', body)

    def test_get_unexistent(self):
        handler = self.request()
        return self.assertRaises(errors.ResourceNotFound, handler.get, 'unexistent')
