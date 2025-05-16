# Implements Clamd service
import shutil
import time

from twisted.internet.defer import Deferred
from twisted.internet import reactor, protocol

from globaleaks.services.service import Service
from globaleaks.utils.antivirus import launch_clamd
from globaleaks.utils.log import log

__all__ = ['Clamd']

STARTUP_TIMEOUT = 120  # seconds
RETRY_INTERVAL = 30    # seconds


class ClamdProtocol(protocol.Protocol):
    def connectionMade(self):
        log.info(f"Successfully connected to clamd")
        self.transport.loseConnection()
        self.factory.deferred.callback(True)


class ClamdFactory(protocol.ClientFactory):
    def __init__(self, deferred):
        self.deferred = deferred

    def buildProtocol(self, addr):
        proto = ClamdProtocol()
        proto.factory = self
        return proto

    def clientConnectionFailed(self, connector, reason):
        log.err(f"Failed to connect to clamd: {reason.getErrorMessage()}")
        self.deferred.callback(False)


class Clamd(Service):
    def __init__(self):
        super().__init__()

    def operation(self):
        """
        Launch clamd, then attempt to connect via TCP with retries for up to 2 minutes.
        """
        if shutil.which("clamd"):
            restart_deferred = launch_clamd(self.state.settings.conf_clamd, self.state.settings.devel_mode)
            reactor.callLater(0, self.wait_for_clamd, restart_deferred)
            return restart_deferred
        else:
            return Deferred()

    def wait_for_clamd(self, restart_deferred, start_time=None):
        if start_time == None:
            start_time = time.time()

        def retry():
            self.wait_for_clamd(restart_deferred, start_time)

        d = Deferred()

        def handle_result(ready):
            if ready:
                log.err("clamd is ready and listening.")
            elif time.time() - start_time > STARTUP_TIMEOUT:
                log.err("clamd did not start within timeout.")
                restart_deferred.callback(None)
            else:
                log.debug("clamd not ready, retrying...")
                reactor.callLater(RETRY_INTERVAL, retry)

        factory = ClamdFactory(d)

        if 1 in self.state.tenants:
            if self.state.tenants[1].cache.antivirus_clamd_ip in ['localhost', '127.0.0.1']:
                reactor.connectUNIX(self.state.settings.antivirus_sock_path, factory)
            else:
                reactor.connectTCP(self.state.tenants[1].cache.antivirus_clamd_ip, self.state.tenans[1].cache.antivirus_clamd_port, factory)
        else:
            reactor.connectUNIX(self.state.settings.antivirus_sock_path, factory)

        d.addCallback(handle_result)

        reactor.callLater(0, wait_for_clamd)
        return restart_deferred
