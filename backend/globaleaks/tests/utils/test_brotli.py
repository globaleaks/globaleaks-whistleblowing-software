import brotli

from twisted.trial import unittest
from twisted.web import iweb, resource, server
from zope.interface.verify import verifyObject
from twisted.web.static import Data
from twisted.web.test.requesthelper import DummyChannel

from globaleaks.utils.brotli import BrotliEncoderFactory


class BrotliEncoderTests(unittest.TestCase):
    def setUp(self):
        self.channel = DummyChannel()
        staticResource = Data(b"Some data", "text/plain")
        wrapped = resource.EncodingResourceWrapper(
            staticResource, [BrotliEncoderFactory()]
        )
        self.channel.site.resource.putChild(b"foo", wrapped)
        self.channel.site.resource.putChild(b"file.woff2", wrapped)

    def test_interfaces(self):
        """
        L{BrotliEncoderFactory} implements the
        L{iweb._IRequestEncoderFactory} and its C{encoderForRequest} returns an
        instance of L{server._BrotliEncoder} which implements
        L{iweb._IRequestEncoder}.
        """
        request = server.Request(self.channel, False)
        request.compressed = False
        request.gotLength(0)
        request.requestHeaders.setRawHeaders(b"Accept-Encoding", [b"br,gzip,deflate"])
        request.requestReceived(b"GET", b"/foo", b"HTTP/1.0")
        factory = BrotliEncoderFactory()
        self.assertTrue(verifyObject(iweb._IRequestEncoderFactory, factory))

        encoder = factory.encoderForRequest(request)
        self.assertTrue(verifyObject(iweb._IRequestEncoder, encoder))

    def test_encoding(self):
        """
        If the client request passes a I{Accept-Encoding} header which mentions
        Brotli, L{server._BrotliEncoder} automatically compresses the data.
        """
        request = server.Request(self.channel, False)
        request.compressed = False
        request.gotLength(0)
        request.requestHeaders.setRawHeaders(b"Accept-Encoding", [b"br,gzip,deflate"])
        request.requestReceived(b"GET", b"/foo", b"HTTP/1.0")
        data = self.channel.transport.written.getvalue()
        self.assertIn(b"Content-Encoding: br\r\n", data)
        body = data[data.find(b"\r\n\r\n") + 4 :]
        self.assertEqual(b"Some data", brotli.decompress(body))

    def test_unsupported(self):
        """
        L{server.BrotliEncoderFactory} doesn't return a L{server._BrotliEncoder} if
        the I{Accept-Encoding} header doesn't mention Brotli support.
        """
        request = server.Request(self.channel, False)
        request.compressed = False
        request.gotLength(0)
        request.requestHeaders.setRawHeaders(b"Accept-Encoding", [b"foo,bar"])
        request.requestReceived(b"GET", b"/foo", b"HTTP/1.0")
        data = self.channel.transport.written.getvalue()
        self.assertIn(b"Content-Length", data)
        self.assertNotIn(b"Content-Encoding: br\r\n", data)
        body = data[data.find(b"\r\n\r\n") + 4 :]
        self.assertEqual(b"Some data", body)

    def test_passthrough_already_compressed_contents(self):
        """
        L{server.BrotliEncoderFactory} dont encode the data if the data is already compressed.
        """
        request = server.Request(self.channel, False)
        request.compressed = True
        request.gotLength(0)
        request.requestHeaders.setRawHeaders(b"Accept-Encoding", [b"br,foo,bar"])
        request.requestReceived(b"GET", b"/foo", b"HTTP/1.0")
        data = self.channel.transport.written.getvalue()
        self.assertIn(b"Content-Length", data)
        self.assertIn(b"Content-Encoding: br\r\n", data)
        body = data[data.find(b"\r\n\r\n") + 4 :]
        self.assertEqual(b"Some data", body)

    def test_passthrough_woff_and_woff2(self):
        """
        L{server.BrotliEncoderFactory} dont encode woff and woff2 files
        """
        request = server.Request(self.channel, False)
        request.gotLength(0)
        request.requestHeaders.setRawHeaders(b"Accept-Encoding", [b"br,foo,bar"])
        request.requestReceived(b"GET", b"/file.woff2", b"HTTP/1.0")
        data = self.channel.transport.written.getvalue()
        self.assertIn(b"Content-Length", data)
        self.assertNotIn(b"Content-Encoding: br\r\n", data)
        body = data[data.find(b"\r\n\r\n") + 4 :]
        self.assertEqual(b"Some data", body)
