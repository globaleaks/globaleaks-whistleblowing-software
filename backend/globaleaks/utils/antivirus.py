import pyclamd
import os

from twisted.internet import defer, protocol, reactor, threads

from globaleaks.utils.sock import parse_endpoint

class FileAnalysis:
    def __init__(self, endpoint='unix:///var/globaleaks/antivirus/clamd.sock'):
        self._endpoint = parse_endpoint(endpoint)

    def _scan_file_blocking(self, file_obj) -> str:
        try:
            if self._endpoint['type'] == 'unix':
                cd = pyclamd.ClamdUnixSocket(self._endpoint['path'])
            elif self._endpoint['type'] == 'tcp':
                cd = pyclamd.ClamdNetworkSocket(self._endpoint['host'], self._endpoint['port'])
            else:
                cd = pyclamd.ClamdUnixSocket('/var/globaleaks/antivirus/clamd.sock')

            result = cd.scan_stream(file_obj)
            return 'unsafe' if result else 'safe'
        except Exception as e:
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
        pass

    def outReceived(self, data):
        pass

    def processEnded(self, reason):
        if not self.deferred.called:
            self.deferred.callback(None)

    def processExited(self, reason):
        pass


def launch_clamd(conf, unconfined=False):
    if unconfined:
        # Development
        args = ["aa-exec", "-p", "unconfined", "--", "/usr/sbin/clamd", "--foreground", f"--config-file={conf}"]
    else:
        # Production
        args = ["/usr/sbin/clamd", "--foreground", f"--config-file={conf}"]

    pp = ProcessProtocol(name='clamd', launcher=launch_clamd)
    reactor.spawnProcess(pp, executable=args[0], args=args)
    return pp.deferred


def launch_freshclam(conf, unconfined=False):
    if unconfined:
        # Development
        args = ["aa-exec", "-p", "unconfined", "--", "/usr/bin/freshclam", "--foreground", f"--config-file={conf}"]
    else:
        # Production
        args = ["/usr/bin/freshclam", "--foreground", f"--config-file={conf}"]

    pp = ProcessProtocol(name='freshclam', launcher=launch_freshclam)
    reactor.spawnProcess(pp, executable=args[0], args=args)
    return pp.deferred
