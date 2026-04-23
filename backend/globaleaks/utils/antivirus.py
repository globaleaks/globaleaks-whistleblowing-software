import os
import socket
import time
from datetime import datetime, timedelta, timezone

import pyclamd

from twisted.internet import defer, protocol, reactor, threads
from globaleaks.models import EnumStateFile
from globaleaks.rest import errors
from globaleaks.state import State
from globaleaks.utils.sock import parse_endpoint
from globaleaks.settings import Settings
from globaleaks.utils.log import log

LOCAL_CLAMD_HOSTS = {'', 'localhost', '127.0.0.1', '::1'}
ANTIVIRUS_RECHECK_DAYS = 90


def needs_antivirus_recheck(file_obj):
    validation_date = file_obj.verification_date
    if validation_date and validation_date.tzinfo is None:
        validation_date = validation_date.replace(tzinfo=timezone.utc)

    cutoff = datetime.now(timezone.utc) - timedelta(days=ANTIVIRUS_RECHECK_DAYS)

    if file_obj.state == EnumStateFile.pending.name:
        return True

    return not validation_date or validation_date < cutoff


def prepare_file_download(file_obj, antivirus_enabled):
    if antivirus_enabled and needs_antivirus_recheck(file_obj):
        file_obj.state = EnumStateFile.pending.name
        return True

    return False


def enqueue_antivirus_scan(file_id, tip_prv_key):
    if not tip_prv_key:
        return

    if file_id in State.antivirus_file_ids:
        return

    State.antivirus_files.append((file_id, tip_prv_key))
    State.antivirus_file_ids.add(file_id)


def get_av_result(state):
    if state == EnumStateFile.infected.name:
        return 'UNSAFE'

    if state == EnumStateFile.pending.name:
        return 'PENDING'

    return 'SAFE'


def is_local_clamd_host(host):
    return (host or '').strip().lower() in LOCAL_CLAMD_HOSTS


def get_default_clamd_socket_path():
    sock_path = getattr(Settings, 'antivirus_sock_path', None)
    if sock_path:
        return sock_path

    return os.path.join(Settings.working_path, 'antivirus', 'clamd.sock')


def get_configured_clamd_connection():
    clamd_ip = 'localhost'
    clamd_port = 3310

    try:
        from globaleaks.state import State

        tenant = State.tenants.get(1)
        tenant_cache = getattr(tenant, 'cache', None)

        if tenant_cache is not None:
            clamd_ip = (getattr(tenant_cache, 'antivirus_clamd_ip', clamd_ip) or clamd_ip).strip()
            clamd_port = getattr(tenant_cache, 'antivirus_clamd_port', clamd_port) or clamd_port
    except Exception:
        pass

    return clamd_ip, clamd_port


def get_clamd_endpoint(clamd_ip=None, clamd_port=None):
    if clamd_ip is None or clamd_port is None:
        configured_ip, configured_port = get_configured_clamd_connection()
        clamd_ip = configured_ip if clamd_ip is None else clamd_ip
        clamd_port = configured_port if clamd_port in [None, 0] else clamd_port

    if is_local_clamd_host(clamd_ip):
        return f"unix://{get_default_clamd_socket_path()}"

    return f"tcp://{clamd_ip}:{clamd_port}"


def wait_for_socket(path, timeout=10):
    """Wait for the ClamAV UNIX socket to be ready."""
    end_time = time.time() + timeout
    while time.time() < end_time:
        if os.path.exists(path):
            try:
                sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
                sock.connect(path)
                sock.close()
                return True
            except socket.error:
                time.sleep(0.5)
        else:
            time.sleep(0.5)
    return False


class FileAnalysis:
    def __init__(self, endpoint=None):
        if endpoint is None:
            endpoint = get_clamd_endpoint()
        self._endpoint = parse_endpoint(endpoint)
        self._socket_not_ready_logged = False
        self._scan_error_logged = False

    def _scan_file_blocking(self, file_obj) -> str:
        try:
            if self._endpoint['type'] == 'unix':
                socket_path = self._endpoint['path']
                if not wait_for_socket(socket_path):
                    if not self._socket_not_ready_logged:
                        log.err("Clamd socket not ready: %s", socket_path)
                        self._socket_not_ready_logged = True
                cd = pyclamd.ClamdUnixSocket(socket_path)
            elif self._endpoint['type'] == 'tcp':
                cd = pyclamd.ClamdNetworkSocket(self._endpoint['host'], self._endpoint['port'])
            else:
                return 'error'

            result = cd.scan_stream(file_obj)
            return 'unsafe' if result else 'safe'
        except Exception as e:
            if not self._scan_error_logged:
                log.err("ClamAV scan failed: %s", e)
                self._scan_error_logged = True
            return 'error'

    def scan_file(self, file_obj) -> defer.Deferred:
        return threads.deferToThread(self._scan_file_blocking, file_obj)


class ProcessProtocol(protocol.ProcessProtocol):
    def __init__(self, name, launcher):
        self.name = name
        self.launcher = launcher
        self.deferred = defer.Deferred()
        self.transport = None
        self._ended = False
        print(f"[INFO] Launching {self.name}")

    def errReceived(self, data):
        print(f"[STDERR:{self.name}] {data.decode().strip()}")

    def outReceived(self, data):
        print(f"[STDOUT:{self.name}] {data.decode().strip()}")

    def processEnded(self, reason):
        self._ended = True
        self.transport = None
        if not self.deferred.called:
            self.deferred.callback(None)

    def processExited(self, reason):
        pass

    def stop(self):
        if self._ended or self.transport is None:
            return defer.succeed(None)

        try:
            self.transport.signalProcess('TERM')
        except Exception:
            if not self.deferred.called:
                self.deferred.callback(None)

        return self.deferred


def launch_clamd(conf, unconfined=False):
    if unconfined:
        # Production"
        args = ["aa-exec", "-p", "unconfined", "--", "/usr/sbin/clamd", "--foreground", f"--config-file={conf}"]
    else:
        # Development
        args = ["/usr/sbin/clamd", "--foreground", f"--config-file={conf}"]

    pp = ProcessProtocol(name='clamd', launcher=launch_clamd)
    reactor.spawnProcess(pp, executable=args[0], args=args)
    return pp


def launch_freshclam(conf, unconfined=False):
    if unconfined:
        # Production
        args = ["aa-exec", "-p", "unconfined", "--", "/usr/bin/freshclam", "--foreground", f"--config-file={conf}"]
    else:
        # Development
        args = ["/usr/bin/freshclam", "--foreground", f"--config-file={conf}"]

    pp = ProcessProtocol(name='freshclam', launcher=launch_freshclam)
    reactor.spawnProcess(pp, executable=args[0], args=args)
    return pp
