import fcntl
import socket

from twisted.internet import abstract
from twisted.protocols import tls
from urllib.parse import urlparse

def is_ip_address(hostname):
    return abstract.isIPAddress(hostname) or abstract.isIPv6Address(hostname)


def listen_tcp_on_sock(reactor, fd, factory):
    return reactor.adoptStreamPort(fd, socket.AF_INET6, factory)


def listen_tls_on_sock(reactor, fd, context_factory, factory):
    tls_factory = tls.TLSMemoryBIOFactory(context_factory, False, factory)
    port = listen_tcp_on_sock(reactor, fd, tls_factory)
    port._type = 'TLS'
    return port


def open_socket_listen(ip, port):
    if abstract.isIPv6Address(ip):
        s = socket.socket(socket.AF_INET6, socket.SOCK_STREAM)
    else:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.setblocking(False)

    flags = fcntl.fcntl(s, fcntl.F_GETFD)
    fcntl.fcntl(s, fcntl.F_SETFD, flags | fcntl.FD_CLOEXEC)

    s.bind((ip, port))
    s.listen(4096)

    return s

def parse_endpoint(endpoint):
    parsed = urlparse(endpoint)
    if parsed.scheme == 'unix':
        return {'type': 'unix', 'path': parsed.path}
    elif parsed.scheme == 'tcp':
        return {'type': 'tcp', 'host': parsed.hostname, 'port': parsed.port}
    else:
        raise ValueError(f"Unsupported socket type: {parsed.scheme}")

def reserve_tcp_socket(ip, port):
    try:
        sock = open_socket_listen(ip, port)
        return [sock, None]
    except Exception as err:
        return [None, err]
