import os
import socket
import time
import pyclamd

from twisted.internet import defer, protocol, reactor, threads
from globaleaks.utils.sock import parse_endpoint


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
    def __init__(self, endpoint='unix:///run/clamav/clamd.ctl'):
        self._endpoint = parse_endpoint(endpoint)

    def _scan_file_blocking(self, file_obj) -> str:
        try:
            if self._endpoint['type'] == 'unix':
                socket_path = self._endpoint['path']
                if not wait_for_socket(socket_path):
                    print(f"[ERROR] Clamd socket not ready: {socket_path}")
                    return 'error'
                cd = pyclamd.ClamdUnixSocket(socket_path)
            elif self._endpoint['type'] == 'tcp':
                cd = pyclamd.ClamdNetworkSocket(self._endpoint['host'], self._endpoint['port'])
            else:
                return 'error'

            result = cd.scan_stream(file_obj)
            return 'unsafe' if result else 'safe'
        except Exception as e:
            print(f"[ERROR] ClamAV scan failed: {e}")
            return 'error'

    def scan_file(self, file_obj) -> defer.Deferred:
        return threads.deferToThread(self._scan_file_blocking, file_obj)


class ProcessProtocol(protocol.ProcessProtocol):
    def __init__(self, name, launcher):
        self.name = name
        self.launcher = launcher
        self.deferred = defer.Deferred()
        print(f"[INFO] Launching {self.name}")

    def errReceived(self, data):
        print(f"[STDERR:{self.name}] {data.decode().strip()}")

    def outReceived(self, data):
        print(f"[STDOUT:{self.name}] {data.decode().strip()}")

    def processEnded(self, reason):
        if not self.deferred.called:
            self.deferred.callback(None)

    def processExited(self, reason):
        pass


def launch_clamd(conf, unconfined=False):
    if unconfined:
        args = ["aa-exec", "-p", "unconfined", "--", "/usr/sbin/clamd", "--foreground", f"--config-file={conf}"]
    else:
        args = ["/usr/sbin/clamd", "--foreground", f"--config-file={conf}"]

    pp = ProcessProtocol(name='clamd', launcher=launch_clamd)
    reactor.spawnProcess(pp, executable=args[0], args=args)
    return pp.deferred


def launch_freshclam(conf, unconfined=False):
    # if unconfined:
    #     args = ["aa-exec", "-p", "unconfined", "--", "/usr/bin/freshclam", "--foreground", f"--config-file={conf}"]
    # else:
    #     args = ["/usr/bin/freshclam", "--foreground", f"--config-file={conf}"]
    #
    # pp = ProcessProtocol(name='freshclam', launcher=launch_freshclam)
    # reactor.spawnProcess(pp, executable=args[0], args=args)
    return None
