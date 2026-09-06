from twisted.internet.defer import Deferred, fail, succeed
from twisted.internet.protocol import Factory, Protocol
from twisted.internet.ssl import optionsForClientTLS
from twisted.internet.task import Clock
from twisted.internet.testing import StringTransportWithDisconnection
from twisted.protocols import tls
from twisted.python.failure import Failure
from twisted.trial import unittest
from twisted.web.client import BrowserLikePolicyForHTTPS, URI

from globaleaks.utils.socks import SOCKS5Agent, SOCKS5ClientEndpoint, SOCKS5ClientFactory, SOCKS5ClientProtocol, \
    TLSWrapClientEndpoint

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
        self.wrapped_protocol = DummyProtocol()
        self.deferred = Deferred()
        self.factory = DummyFactory()
        self.factory.registerProtocol = lambda _: None
        self.protocol = SOCKS5ClientProtocol(self.factory, self.wrapped_protocol, self.deferred, b"example.com", 80)
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
        self.assertEqual(self.wrapped_protocol.data, b"hello")

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
        self.deferred.addCallback(results.append)
        self.protocol.state = 3
        self.protocol.dataReceived(b"\x00" * 8)
        self.assertEqual(results, [self.wrapped_protocol])

    def test_transport_disconnection(self):
        """Test that the transport is properly disconnected on error."""
        self.protocol.error()
        self.assertIsNone(self.protocol.transport)  # Transport should be set to None

    def test_data_following_the_reply_is_passed_through(self):
        self.protocol.state = 3
        self.protocol.dataReceived(b"\x00" * 8 + b"hello")
        self.assertEqual(self.protocol.state, 4)
        self.assertEqual(self.wrapped_protocol.data, b"hello")
        self.assertEqual(self.protocol._buf, b"")

    def test_the_error_state_aborts_the_connection(self):
        self.protocol.state = 0
        self.protocol.dataReceived(b"\x05")
        self.assertIsNone(self.protocol.transport)


class FakeProxyEndpoint:
    def __init__(self):
        self.factories = []
        self.transport = StringTransportWithDisconnection()

    def connect(self, factory):
        self.factories.append(factory)
        protocol = factory.buildProtocol(None)
        self.transport.protocol = protocol
        protocol.makeConnection(self.transport)
        return succeed(protocol)


class TestSOCKS5ClientFactory(unittest.TestCase):
    def setUp(self):
        self.wrapped_factory = Factory.forProtocol(DummyProtocol)
        self.factory = SOCKS5ClientFactory(b"example.com", 80, self.wrapped_factory)

    def test_the_protocol_wraps_the_one_of_the_wrapped_factory(self):
        protocol = self.factory.buildProtocol(None)

        self.assertIsInstance(protocol, SOCKS5ClientProtocol)
        self.assertIs(protocol.wrappedProtocol, self.factory.proto)
        self.assertIsInstance(self.factory.proto, DummyProtocol)
        self.assertEqual(protocol._host, b"example.com")
        self.assertEqual(protocol._port, 80)

    def test_a_wrapped_factory_that_fails_to_build_fails_the_connection(self):
        def failing(addr):
            raise ValueError("no protocol")

        self.wrapped_factory.buildProtocol = failing

        self.assertIsNone(self.factory.buildProtocol(None))

        return self.assertFailure(self.factory.deferred, ValueError)

    def test_a_failed_connection_fails_the_connection(self):
        self.factory.clientConnectionFailed(None, Failure(ConnectionRefusedError()))

        return self.assertFailure(self.factory.deferred, ConnectionRefusedError)

    def test_a_canceled_connection_aborts_the_transport_and_is_not_reported(self):
        transport = StringTransportWithDisconnection()
        self.factory.proto = DummyProtocol()
        self.factory.proto.sender = DummyProtocol()
        self.factory.proto.sender.transport = transport
        transport.protocol = self.factory.proto.sender

        self.factory.deferred.cancel()

        self.assertTrue(self.factory.canceled)
        self.assertFalse(transport.connected)

        self.factory.clientConnectionFailed(None, Failure(ConnectionRefusedError()))
        self.factory.clientConnectionLost(None, None)

        return self.assertFailure(self.factory.deferred, Exception)

    def test_a_protocol_is_unregistered_once_and_harmlessly_twice(self):
        protocol = self.factory.buildProtocol(None)
        self.factory.registerProtocol(protocol)
        self.assertIn(protocol, self.factory.protocols)

        self.factory.unregisterProtocol(protocol)
        self.factory.unregisterProtocol(protocol)
        self.assertNotIn(protocol, self.factory.protocols)


class TestSOCKS5ClientEndpoint(unittest.TestCase):
    def test_the_connection_is_established_through_the_proxy(self):
        proxy = FakeProxyEndpoint()
        endpoint = SOCKS5ClientEndpoint(b"example.com", 80, proxy)

        d = endpoint.connect(Factory.forProtocol(DummyProtocol))

        self.assertEqual(len(proxy.factories), 1)
        self.assertIsInstance(proxy.factories[0], SOCKS5ClientFactory)
        self.assertEqual(proxy.transport.value()[:3], b"\x05\x01\x00")

        return d.addCallback(lambda protocol: self.assertIsInstance(protocol, DummyProtocol))


class TestTLSWrapClientEndpoint(unittest.TestCase):
    def test_the_factory_is_wrapped_in_tls_and_the_protocol_unwrapped(self):
        wrapped = []

        class WrappedEndpoint:
            def connect(self, factory):
                wrapped.append(factory)
                protocol = DummyProtocol()
                protocol.wrappedProtocol = DummyProtocol()
                return succeed(protocol)

        factory = Factory.forProtocol(DummyProtocol)
        endpoint = TLSWrapClientEndpoint(optionsForClientTLS("example.com"), WrappedEndpoint())

        d = endpoint.connect(factory)

        self.assertIsInstance(wrapped[0], tls.TLSMemoryBIOFactory)
        self.assertIs(wrapped[0].wrappedFactory, factory)

        return d.addCallback(lambda protocol: self.assertIsInstance(protocol, DummyProtocol))


class TestSOCKS5Agent(unittest.TestCase):
    def setUp(self):
        self.proxy = FakeProxyEndpoint()
        self.agent = SOCKS5Agent(Clock(), proxy_endpoint=self.proxy)

    def test_the_context_factory_is_required_to_be_a_policy(self):
        self.assertIsInstance(self.agent._policy_for_https, BrowserLikePolicyForHTTPS)
        self.assertEqual(self.agent.endpoint_args, {})

        self.assertRaises(NotImplementedError, SOCKS5Agent, Clock(), context_factory=object())

    def test_a_plaintext_uri_is_reached_through_the_proxy(self):
        endpoint = self.agent.endpointForURI(URI.fromBytes(b"http://example.com:8080/path"))

        self.assertIsInstance(endpoint, SOCKS5ClientEndpoint)
        self.assertEqual(endpoint.host, b"example.com")
        self.assertEqual(endpoint.port, 8080)
        self.assertIs(endpoint.proxy_endpoint, self.proxy)

    def test_a_protected_uri_is_reached_through_the_proxy_under_tls(self):
        endpoint = self.agent.endpointForURI(URI.fromBytes(b"https://example.com/path"))

        self.assertIsInstance(endpoint, TLSWrapClientEndpoint)
        self.assertIsInstance(endpoint.wrapped_endpoint, SOCKS5ClientEndpoint)
        self.assertEqual(endpoint.wrapped_endpoint.host, b"example.com")
        self.assertEqual(endpoint.wrapped_endpoint.port, 443)

    def test_the_requests_are_delegated_to_the_wrapped_agent(self):
        requests = []

        class WrappedAgent:
            def request(self, *args, **kwargs):
                requests.append((args, kwargs))
                return fail(Exception("no network"))

        self.agent._wrapped_agent = WrappedAgent()

        d = self.agent.request(b"GET", b"http://example.com/", headers=None)

        self.assertEqual(requests, [((b"GET", b"http://example.com/"), {"headers": None})])

        return self.assertFailure(d, Exception)
