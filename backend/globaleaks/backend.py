#   backend
#   *******
import sys
import traceback

from twisted.application import service
from twisted.internet import reactor, defer
from twisted.python.log import ILogObserver
from twisted.python.log import addObserver
from twisted.web import resource, server

from globaleaks.jobs import job, jobs_list
from globaleaks.services import tor

from globaleaks.db import create_db, initialize_db, update_db, \
    sync_refresh_tenant_cache, sync_initialize_snimap
from globaleaks.rest.api import APIResourceWrapper
from globaleaks.settings import Settings
from globaleaks.state import State
from globaleaks.utils.brotli import BrotliEncoderFactory
from globaleaks.utils.log import log, openLogFile, logFormatter, LogObserver
from globaleaks.utils.sock import listen_tcp_on_sock, listen_tls_on_sock


def fail_startup(excep):
    log.err("ERROR: Cannot start GlobaLeaks. Please manually examine the exception.")
    log.err("EXCEPTION: %s", excep)
    log.debug('TRACE: %s', traceback.format_exc(excep))
    if reactor.running:
        reactor.stop()


class Request(server.Request):
    log_ip_and_ua = False


class Site(server.Site):
    requestFactory = Request

    def _openLogFile(self, path):
        return openLogFile(path, Settings.log_file_size, Settings.num_log_files)


class Service(service.Service):
    _shutdown = False

    def __init__(self):
        self.state = State
        self.arw = resource.EncodingResourceWrapper(APIResourceWrapper(), [BrotliEncoderFactory()])
        self.api_factory = Site(self.arw, logPath=Settings.accesslogfile, logFormatter=logFormatter)
        self.api_factory.displayTracebacks = False

    def start_jobs(self):
        for j in jobs_list:
            self.state.jobs.append(j())

        self.state.tor = tor.Tor()
        self.state.services.append(self.state.tor)

        self.state.jobs_monitor = job.JobsMonitor(self.state.jobs)

    def stop_jobs(self):
        deferred_list = []

        for job in self.state.jobs + self.state.services:
            deferred_list.append(defer.maybeDeferred(job.stop))

        if self.state.jobs_monitor is not None:
            deferred_list.append(self.state.jobs_monitor.stop())
            self.state.jobs_monitor = None

        return defer.DeferredList(deferred_list)

    def deferred_start(self):
        try:
            ret = update_db()

            if ret == -1 or self.state.settings.migrate_only:
                reactor.stop()
                return

            if ret == 0:
                create_db()
                initialize_db()

            for sock in self.state.http_socks:
                listen_tcp_on_sock(reactor, sock.fileno(), self.api_factory)

            for sock in self.state.https_socks:
                listen_tls_on_sock(reactor,
                                   fd=sock.fileno(),
                                   contextFactory=self.state.snimap,
                                   factory=self.api_factory)

            sync_refresh_tenant_cache()
            sync_initialize_snimap()
            self.state.orm_tp.start()
            self.start_jobs()
            self.state.print_listening_interfaces()

        except Exception as excep:
            fail_startup(excep)

    def startService(self):
        reactor.callLater(0, self.deferred_start)

    @defer.inlineCallbacks
    def stopService(self):
        yield self.state.orm_tp.stop()
        yield self.stop_jobs()


try:
    application = service.Application('GlobaLeaks')

    logfile = openLogFile(Settings.logfile, Settings.log_file_size, Settings.num_log_files)

    if Settings.nodaemon:
        addObserver(LogObserver(logfile).emit)
    else:
         application.setComponent(ILogObserver, LogObserver(logfile).emit)

    Service().setServiceParent(application)
except Exception as excep:
    fail_startup(excep)
    # Exit with non-zero exit code to signal systemd/systemV
    sys.exit(55)
