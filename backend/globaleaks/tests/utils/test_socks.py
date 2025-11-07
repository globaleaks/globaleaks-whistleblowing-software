from twisted.internet.defer import Deferred
from twisted.internet.protocol import Factory, Protocol
from twisted.test.proto_helpers import StringTransportWithDisconnection
from twisted.trial import unittest

from globaleaks.utils.socks import SOCKS5ClientProtocol

class DummyFactory(Factory):
    def __init__(self):
        # Initialize your factory with necessary attributes
        pass

    def unregisterProtocol(self, protocol):
        # Add logic to unregister protocol if needed
        pass

class DummyProtocol(Protocol):
    def __init__(self):
        self.data = b""

    def dataReceived(self, data):
        self.data += data

class TestSOCKS5ClientProtocol(unittest.TestCase):
    def setUp(self):
        self.wrappedProtocol = DummyProtocol()
        self.deferred = Deferred()
        self.factory = DummyFactory()
        self.factory.registerProtocol = lambda _: None
        self.protocol = SOCKS5ClientProtocol(self.factory, self.wrappedProtocol, self.deferred, b"example.com", 80)
        self.transport = StringTransportWithDisconnection()
        self.transport.protocol = self.protocol  # This line ensures the transport has a protocol attached
        self.protocol.makeConnection(self.transport)

    def test_socks5_handshake(self):
        """Test that SOCKS5 handshake is initiated correctly."""
        expected_request = b"\x05\x01\x00" + b"\x05\x01\x00\x03\x0bexample.com\x00P"
        self.assertEqual(self.transport.value(), expected_request)

    def test_socks5_response(self):
        """Test that the protocol correctly handles a SOCKS5 response."""
        self.protocol.dataReceived(b"\x05\x00")
        self.assertEqual(self.protocol.state, 2)

        self.protocol.dataReceived(b"\x05\x00")
        self.assertEqual(self.protocol.state, 3)

    def test_data_passthrough(self):
        """Test that data is correctly passed through after connection."""
        self.protocol.state = 4  # Simulate a successful handshake
        self.protocol.dataReceived(b"hello")
        self.assertEqual(self.wrappedProtocol.data, b"hello")

    def test_invalid_auth_response(self):
        """Test that an invalid authentication response results in error."""
        self.protocol.dataReceived(b"\x05\x02")  # Invalid response
        self.assertIsNone(self.protocol.transport)  # Transport should be aborted

    def test_invalid_connection_response(self):
        """Test that an invalid connection response results in error."""
        self.protocol.state = 2
        self.protocol.dataReceived(b"\x05\x01")  # Invalid response
        self.assertIsNone(self.protocol.transport)  # Transport should be aborted

    def test_partial_data(self):
        """Test that partial data does not cause state corruption."""
        self.protocol.dataReceived(b"\x05")
        self.assertEqual(self.protocol.state, 1)  # Should not advance state prematurely

    def test_deferred_callback(self):
        """Test that the deferred callback is fired upon successful connection."""
        results = []
        self.deferred.addCallback(lambda x: results.append(x))
        self.protocol.state = 3
        self.protocol.dataReceived(b"\x00" * 8)
        self.assertEqual(results, [self.wrappedProtocol])

    def test_transport_disconnection(self):
        """Test that the transport is properly disconnected on error."""
        self.protocol.error()
        self.assertIsNone(self.protocol.transport)  # Transport should be set to None
