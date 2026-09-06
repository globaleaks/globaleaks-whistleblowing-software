# Minimal SOCKS5 implementation
# The implementation supports:
# - Plaintexts connections
# - HTTPS connections
# - The implementation perform optimistic data connection
#   as supported by Tor spec: https://gitweb.torproject.org/torspec.git/tree/socks-extensions.txt
# - No authentication is implented as it is not required
#   in the context of GlobaLeaks
#
# code concept from https://github.com/habnabit/txsocksx

import contextlib
import struct

from twisted.internet import defer, interfaces
from twisted.internet.protocol import Protocol
from twisted.protocols import tls
from twisted.protocols.policies import ProtocolWrapper, WrappingFactory
from twisted.web.client import Agent, BrowserLikePolicyForHTTPS
from twisted.web.iweb import IAgentEndpointFactory, IAgent, IPolicyForHTTPS
from zope.interface import implementer, directlyProvides, providedBy


class SOCKS5ClientProtocol(ProtocolWrapper):
    def __init__(self, factory, wrapped_protocol, connected_deferred, host, port):
        ProtocolWrapper.__init__(self, factory, wrapped_protocol)
        self._connectedDeferred = connected_deferred
        self._host = host
        self._port = port
        self._buf = b''
        self.state = 0

    def error(self):
        self.transport.abortConnection()
        self.transport = None

    def socks_state_0(self):
        # error state
        self.error()

    def socks_state_1(self):
        if len(self._buf) < 2:
            return

        if self._buf[:2] != b"\x05\x00":
            # Anonymous access denied
            self.error()
            return

        self._buf = self._buf[2:]

        self.state = 2
        getattr(self, f'socks_state_{self.state}')()

    def socks_state_2(self):
        if len(self._buf) < 2:
            return

        if self._buf[:2] != b"\x05\x00":
            self.error()
            return

        self._buf = self._buf[2:]

        self.state = 3
        getattr(self, f'socks_state_{self.state}')()

    def socks_state_3(self):
        if len(self._buf) < 8:
            return

        self._buf = self._buf[8:]

        if self._buf:
            self.wrappedProtocol.dataReceived(self._buf)

        self._buf = b''

        self.state = 4

    def makeConnection(self, transport):
        directlyProvides(self, providedBy(transport))
        Protocol.makeConnection(self, transport)
        self.factory.registerProtocol(self)

        # We implement only Anonymous access
        self.transport.write(struct.pack("!BB", 5, len(b"\x00")) + b"\x00")

        self.transport.write(struct.pack("!BBBBB", 5, 1, 0, 3, len(self._host)) + self._host + struct.pack("!H", self._port))
        self.wrappedProtocol.makeConnection(self)

        with contextlib.suppress(defer.AlreadyCalledError):
            self._connectedDeferred.callback(self.wrappedProtocol)

        self.state = 1

    def dataReceived(self, data):
        if self.state != 4:
            self._buf = b''.join([self._buf, data])
            getattr(self, f'socks_state_{self.state}')()
        else:
            self.wrappedProtocol.dataReceived(data)


class SOCKS5ClientFactory(WrappingFactory):
    protocol = SOCKS5ClientProtocol
    proto = None
    canceled = False

    def __init__(self, host, port, wrapped_factory):
        self.host = host
        self.port = port
        self.deferred = defer.Deferred(self._cancel)
        WrappingFactory.__init__(self, wrapped_factory)

    def buildProtocol(self, addr):
        try:
            self.proto = self.wrappedFactory.buildProtocol(addr)
        except Exception:
            self.deferred.errback()
        else:
            return self.protocol(self, self.proto, self.deferred, self.host, self.port)

    def clientConnectionFailed(self, connector, reason):
        if not self.canceled:
            self.deferred.errback(reason)

    def clientConnectionLost(self, connector, reason):
        pass

    def unregisterProtocol(self, p):
        self.protocols.pop(p, None)

    def _cancel(self, d):
        self.proto.sender.transport.abortConnection()
        self.canceled = True


@implementer(interfaces.IStreamClientEndpoint)
class SOCKS5ClientEndpoint:
    def __init__(self, host, port, proxy_endpoint):
        self.host = host
        self.port = port
        self.proxy_endpoint = proxy_endpoint

    def connect(self, protocol_factory):
        proxy_factory = SOCKS5ClientFactory(self.host, self.port, protocol_factory)
        return self.proxy_endpoint.connect(proxy_factory).addCallback(lambda proto: proxy_factory.deferred)


@implementer(interfaces.IStreamClientEndpoint)
class TLSWrapClientEndpoint:
    _wrapper = tls.TLSMemoryBIOFactory

    def __init__(self, context_factory, wrapped_endpoint):
        self.context_factory = context_factory
        self.wrapped_endpoint = wrapped_endpoint

    def connect(self, fac):
        fac = self._wrapper(self.context_factory, True, fac)
        return self.wrapped_endpoint.connect(fac).addCallback(self._unwrap_protocol)

    def _unwrap_protocol(self, proto):
        return proto.wrappedProtocol


_Agent = Agent


@implementer(IAgentEndpointFactory, IAgent)
class SOCKS5Agent:
    endpoint_factory = SOCKS5ClientEndpoint
    _tls_wrapper = TLSWrapClientEndpoint

    def __init__(self, reactor, context_factory=None,
                 connect_timeout=None, bind_address=None, pool=None, proxy_endpoint=None, endpoint_args=None):
        if context_factory is None:
            context_factory = BrowserLikePolicyForHTTPS()
        if endpoint_args is None:
            endpoint_args = {}
        if not IPolicyForHTTPS.providedBy(context_factory):
            raise NotImplementedError(
                'context_factory must implement IPolicyForHTTPS')
        self.proxy_endpoint = proxy_endpoint
        self.endpoint_args = endpoint_args
        self._policy_for_https = context_factory
        self._wrapped_agent = _Agent.usingEndpointFactory(
            reactor, self, pool=pool)

    def request(self, *a, **kw):
        return self._wrapped_agent.request(*a, **kw)

    def _get_endpoint(self, scheme, host, port):
        endpoint = self.endpoint_factory(host, port, self.proxy_endpoint, **self.endpoint_args)

        if scheme == b'https':
            tls_policy = self._policy_for_https.creatorForNetloc(host, port)
            endpoint = self._tls_wrapper(tls_policy, endpoint)

        return endpoint

    def endpointForURI(self, uri):
        return self._get_endpoint(uri.scheme, uri.host, uri.port)
