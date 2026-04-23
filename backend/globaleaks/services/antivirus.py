# Implements Clamd service
import shutil
import time

from twisted.internet.defer import Deferred, DeferredList, maybeDeferred, succeed
from twisted.internet import reactor, protocol

from globaleaks.state import State
from globaleaks.services.service import Service
from globaleaks.utils.antivirus import is_local_clamd_host, launch_clamd
from globaleaks.utils.log import log

__all__ = ['Clamd', 'sync_antivirus_runtime']

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
        self.process = None
        self.connector = None
        super().__init__()

    def _clear_process(self, _):
        self.process = None
        return _

    def stop(self):
        super().stop()

        if self.connector is not None:
            self.connector.disconnect()
            self.connector = None

        if self.process is None:
            return succeed(None)

        process = self.process
        self.process = None
        return process.stop()

    def operation(self):
        """
        Launch clamd, then attempt to connect via the configured local socket or TCP endpoint.
        """
        if shutil.which("clamd"):
            self.process = launch_clamd(self.state.settings.conf_clamd, self.state.settings.devel_mode)
            self.process.deferred.addBoth(self._clear_process)
            reactor.callLater(0, self.wait_for_clamd, self.process.deferred)
            return self.process.deferred
        else:
            return Deferred()

    def wait_for_clamd(self, restart_deferred, start_time=None):
        if not self.running or self.process is None or self.process.deferred is not restart_deferred:
            return restart_deferred

        if start_time is None:
            start_time = time.time()

        def retry():
            if not self.running or self.process is None or self.process.deferred is not restart_deferred:
                return
            self.wait_for_clamd(restart_deferred, start_time)

        d = Deferred()

        def handle_result(ready):
            self.connector = None

            if not self.running or self.process is None or self.process.deferred is not restart_deferred:
                return

            if ready:
                log.err("clamd is ready and listening.")
            elif time.time() - start_time > STARTUP_TIMEOUT:
                log.err("clamd did not start within timeout.")
                self.process.stop()
            else:
                log.debug("clamd not ready, retrying...")
                reactor.callLater(RETRY_INTERVAL, retry)

        factory = ClamdFactory(d)

        if 1 in self.state.tenants:
            clamd_ip = getattr(self.state.tenants[1].cache, 'antivirus_clamd_ip', 'localhost') or 'localhost'
            clamd_port = getattr(self.state.tenants[1].cache, 'antivirus_clamd_port', 3310) or 3310

            if is_local_clamd_host(clamd_ip):
                self.connector = reactor.connectUNIX(self.state.settings.antivirus_sock_path, factory)
            else:
                self.connector = reactor.connectTCP(clamd_ip, clamd_port, factory)
        else:
            self.connector = reactor.connectUNIX(self.state.settings.antivirus_sock_path, factory)

        d.addCallback(handle_result)

        return restart_deferred


def is_any_tenant_antivirus_enabled():
    return any(bool(getattr(getattr(tenant, 'cache', None), 'antivirus_enabled', False))
               for tenant in State.tenants.values())


def get_runtime_clamd_connection():
    if 1 not in State.tenants:
        return 'localhost', 3310

    tenant_cache = State.tenants[1].cache
    clamd_ip = getattr(tenant_cache, 'antivirus_clamd_ip', 'localhost') or 'localhost'
    clamd_port = getattr(tenant_cache, 'antivirus_clamd_port', 3310) or 3310
    return clamd_ip, clamd_port


def _get_job(job_cls):
    for job in State.jobs:
        if isinstance(job, job_cls):
            return job

    return None


def _start_job(job_cls):
    job = _get_job(job_cls)
    if job is None:
        job = job_cls()
        State.jobs.append(job)

    return job


def _stop_job(job_cls):
    job = _get_job(job_cls)
    if job is None:
        return succeed(None)

    if job in State.jobs:
        State.jobs.remove(job)

    return maybeDeferred(job.stop)


def ensure_antivirus_decryptor_running():
    from globaleaks.jobs.antivirus_decryptor import AntivirusDecryptor

    return _start_job(AntivirusDecryptor)


def stop_antivirus_decryptor():
    from globaleaks.jobs.antivirus_decryptor import AntivirusDecryptor

    return _stop_job(AntivirusDecryptor)


def ensure_antivirus_updater_running():
    from globaleaks.jobs.update_antivirus import UpdateAntivirus

    return _start_job(UpdateAntivirus)


def stop_antivirus_updater():
    from globaleaks.jobs.update_antivirus import UpdateAntivirus

    return _stop_job(UpdateAntivirus)


def ensure_local_clamd_running():
    if getattr(State, 'antivirus', None) is None:
        State.antivirus = Clamd()
        State.services.append(State.antivirus)

    return State.antivirus


def stop_local_clamd():
    service = getattr(State, 'antivirus', None)
    if service is None:
        return succeed(None)

    if service in State.services:
        State.services.remove(service)

    State.antivirus = None
    return maybeDeferred(service.stop)


def sync_antivirus_runtime():
    enabled = is_any_tenant_antivirus_enabled()
    clamd_ip, _ = get_runtime_clamd_connection()
    deferreds = []

    if enabled:
        ensure_antivirus_decryptor_running()

        if is_local_clamd_host(clamd_ip):
            ensure_antivirus_updater_running()
            ensure_local_clamd_running()
        else:
            deferreds.extend([stop_antivirus_updater(), stop_local_clamd()])
    else:
        deferreds.extend([
            stop_antivirus_decryptor(),
            stop_antivirus_updater(),
            stop_local_clamd()
        ])

    if deferreds:
        return DeferredList(deferreds)

    return succeed(None)
