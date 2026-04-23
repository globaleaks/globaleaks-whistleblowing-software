from twisted.trial import unittest
from twisted.internet import reactor, protocol, defer, ssl
from twisted.internet.interfaces import IListeningPort

import socket
import os

from globaleaks.utils.sock import (
    isIPAddress,
    listen_tcp_on_sock,
    listen_tls_on_sock,
    open_socket_listen,
    reserve_tcp_socket,
    parse_endpoint
)


class DummyFactory(protocol.Factory):
    def buildProtocol(self, addr):
        return protocol.Protocol()


class SocketUtilsTests(unittest.TestCase):
    def test_is_ip_address(self):
        self.assertTrue(isIPAddress("127.0.0.1"))
        self.assertTrue(isIPAddress("::1"))
        self.assertFalse(isIPAddress("localhost"))
        self.assertFalse(isIPAddress("example.com"))

    def test_open_socket_listen_ipv4(self):
        sock = open_socket_listen("127.0.0.1", 0)
        self.assertIsInstance(sock, socket.socket)
        self.assertIn(sock.family, (socket.AF_INET, socket.AF_INET6))
        sock.close()

    def test_open_socket_listen_ipv6(self):
        sock = open_socket_listen("::1", 0)
        self.assertIsInstance(sock, socket.socket)
        self.assertEqual(sock.family, socket.AF_INET6)
        sock.close()

    def test_reserve_tcp_socket_success(self):
        sock, err = reserve_tcp_socket("127.0.0.1", 0)
        self.assertIsNone(err)
        self.assertIsInstance(sock, socket.socket)
        sock.close()

    def test_reserve_tcp_socket_failure(self):
        # bind to an invalid address
        sock, err = reserve_tcp_socket("256.256.256.256", 0)
        self.assertIsNone(sock)
        self.assertIsInstance(err, Exception)

    def test_parse_endpoint_tcp(self):
        result = parse_endpoint("tcp://127.0.0.1:1234")
        self.assertEqual(result, {'type': 'tcp', 'host': '127.0.0.1', 'port': 1234})

    def test_parse_endpoint_unix(self):
        result = parse_endpoint("unix:///tmp/test.sock")
        self.assertEqual(result, {'type': 'unix', 'path': '/tmp/test.sock'})

    def test_parse_endpoint_invalid(self):
        with self.assertRaises(ValueError):
            parse_endpoint("http://localhost")
