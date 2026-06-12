from globaleaks.utils.socks import SOCKS5Agent

from twisted.internet import reactor
from twisted.internet.endpoints import UNIXClientEndpoint
from twisted.web.client import Agent, readBody


def get_tor_agent(socks_socket):
    """
    An HTTP agent that uses SOCKS5 to proxy all requests through the socks_socket

    The SOCKS listener is exposed by the locally launched tor daemon as a
    unix-domain socket protected by filesystem permissions, so that no other
    local process can impersonate it by pre-binding a fixed TCP port.
    :param socks_socket: the path of the tor SOCKS unix-domain socket
    :return: an initialized agent using the specified socks config
    """
    torServerEndpoint = UNIXClientEndpoint(reactor, socks_socket)

    return SOCKS5Agent(reactor, proxyEndpoint=torServerEndpoint)


def get_web_agent():
    """An HTTP agent that connects to the web without using Tor
    :return: A simple initialized agent
    """
    return Agent(reactor, connectTimeout=5)


def get_page(agent, url):
    """Perform a get request to the specified url and return response content
    :param agent: An agent to be used to issue the request
    :param url: A url to be fetched
    :return: A content returned by the url resource
    """
    return agent.request(b'GET', url).addCallback(readBody)
