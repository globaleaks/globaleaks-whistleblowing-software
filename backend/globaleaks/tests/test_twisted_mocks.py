from twisted.trial import unittest
from twisted.web import server
from twisted.web.test.requesthelper import DummyChannel

# Importing the module applies the production request patches, including the
# request-body size cap enforced in gotLength.
import globaleaks.mocks.twisted_mocks  # noqa: F401

from globaleaks.rest.errors import InputValidationError


class TestRequestBodySizeLimit(unittest.TestCase):
    def request(self):
        return server.Request(DummyChannel(), False)

    def test_empty_body_is_accepted(self):
        request = self.request()
        request.gotLength(0)
        self.assertIsNotNone(request.content)

    def test_body_at_limit_is_accepted(self):
        request = self.request()
        request.gotLength(2 * 1024 * 1024)
        self.assertIsNotNone(request.content)

    def test_oversized_content_length_is_rejected(self):
        self.assertRaises(InputValidationError,
                          self.request().gotLength, 2 * 1024 * 1024 + 1)

    def test_chunked_request_is_rejected(self):
        # Transfer-Encoding: chunked surfaces as a None length and would
        # otherwise bypass the size cap and stream unbounded into memory.
        self.assertRaises(InputValidationError, self.request().gotLength, None)
