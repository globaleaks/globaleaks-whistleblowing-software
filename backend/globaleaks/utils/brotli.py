import brotli
import re

from twisted.web import iweb
from zope.interface import implementer


@implementer(iweb._IRequestEncoder)
class BrotliEncoder:
    def __init__(self, request) -> None:
        self._request = request
        self._compressor = brotli.Compressor(quality=5)

    def encode(self, data):
        """
        Write to the request, compressing data on the fly with Brotli if supported.
        """
        if self._request.compressed:
            return data

        return self._compressor.process(data)

    def finish(self):
        """
        Finish handling the request, flushing any remaining compressed data.
        """
        if self._request.compressed:
            return b''

        return self._compressor.finish()


@implementer(iweb._IRequestEncoderFactory)
class BrotliEncoderFactory:
    _brotli_check_regex = re.compile(rb"(:?^|[\s,])br(:?$|[\s,])")

    def encoderForRequest(self, request):
        """
        Check the headers if the client accepts Brotli encoding, and return an encoder if so.
        """
        accept_headers = b",".join(request.requestHeaders.getRawHeaders(b"accept-encoding", []))
        if self._brotli_check_regex.search(accept_headers) and not request.path.endswith((b".woff", b".woff2")):
            request.responseHeaders.setRawHeaders(b"content-encoding", [b"br"])
            return BrotliEncoder(request)

        return None
