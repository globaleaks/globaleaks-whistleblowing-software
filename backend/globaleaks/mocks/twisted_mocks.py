import hmac
import hashlib

from io import BytesIO as StringIO

from twisted import version as _twisted_version
from twisted.internet import address
from twisted.logger import ILogObserver, Logger
from twisted.mail._cred import CramMD5ClientAuthenticator
from twisted.python import log
from twisted.web import http_headers
from twisted.web.http import HTTPChannel, Request
from twisted.web.http_headers import Headers

from zope.interface import implementer

from globaleaks.rest.errors import InputValidationError


def null_function(*args, **kw):
    pass


def mock_Request_getClientIP(self):
    if isinstance(self.client, (address.IPv4Address, address.IPv6Address)):
        return self.client.host

    return None


def mock_Request_gotLength(self, length):
    # length is None only for Transfer-Encoding: chunked requests, which the
    # application never issues; rejecting them keeps the size cap below from
    # being bypassed by a body streamed without a declared Content-Length.
    if length is None or length > 2 * 1024 * 1024:
        raise InputValidationError("Request exceeding max size of 2MB")

    self.content = StringIO()


def mock_Request_redirect(self, url):
    self.setResponseCode(301)
    self.setHeader(b"location", url)


_orig_request_write = Request.write
def mock_Request_write(self, data):
    # Backport Twisted #9410 from  19.7.0
    if self._disconnected:
        return

    return _orig_request_write(self, data)


def mock_CramMD5ClientAuthenticator_challengeResponse(self, secret, chal):
    response = hmac.HMAC(secret, chal, digestmod=hashlib.md5).hexdigest()
    return self.user + b' ' + response.encode('ascii')


def mock_HTTPChannel_finishRequestBody(self, data):
    # Backport CVE-2024-41671 (GHSA-c8m8-j448-xjx7) from Twisted 24.7.0.
    # In affected versions (<= 24.3.0) allContentReceived() was invoked
    # before the body was appended to the buffer, which under HTTP/1.1
    # pipelining could cause responses to be returned out of order.
    # Swapping the two calls makes the response order deterministic.
    self._dataBuffer.append(data)
    self.allContentReceived()


def _sanitize_linear_whitespace(value):
    # Backport of twisted.web.http_headers._sanitizeLinearWhitespace (21.2.0).
    # Collapses CR/LF (and the other line boundaries splitlines() recognizes)
    # into a single space so a client-controlled header value cannot inject
    # additional response headers (CWE-113 / response splitting).
    if isinstance(value, str):
        return " ".join(value.splitlines())

    return b" ".join(value.splitlines())


_orig_Headers_setRawHeaders = Headers.setRawHeaders
def mock_Headers_setRawHeaders(self, name, values):
    return _orig_Headers_setRawHeaders(self, name, [_sanitize_linear_whitespace(v) for v in values])


_orig_Headers_addRawHeader = Headers.addRawHeader
def mock_Headers_addRawHeader(self, name, value):
    return _orig_Headers_addRawHeader(self, name, _sanitize_linear_whitespace(value))


Request.getClientIP = mock_Request_getClientIP
Request.gotLength = mock_Request_gotLength
Request.parseCookies = null_function
Request.redirect = mock_Request_redirect
Request.write = mock_Request_write

if (_twisted_version.major, _twisted_version.minor) < (24, 7):
    HTTPChannel._finishRequestBody = mock_HTTPChannel_finishRequestBody

if not hasattr(http_headers, "_sanitizeLinearWhitespace"):
    Headers.setRawHeaders = mock_Headers_setRawHeaders
    Headers.addRawHeader = mock_Headers_addRawHeader

CramMD5ClientAuthenticator.challengeResponse = mock_CramMD5ClientAuthenticator_challengeResponse


@implementer(ILogObserver)
class NullObserver(object):
    def __call__(self, event):
        pass


log.msg = log.info = log.err = null_function


null_logger = Logger(observer=NullObserver())
Request._log = null_logger
HTTPChannel._log = null_logger
