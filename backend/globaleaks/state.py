# -*- coding: utf-8
import os
import re
import sys
import traceback

from acme.errors import ValidationError

from txtorcon.torcontrolprotocol import TorProtocolError
from sqlalchemy.exc import OperationalError
from twisted.internet.defer import succeed, AlreadyCalledError, CancelledError
from twisted.internet.error import ConnectionLost, ConnectionRefusedError, DNSLookupError, NoRouteError, TimeoutError
from twisted.mail.smtp import SMTPError
from twisted.python.failure import Failure
from twisted.python.threadpool import ThreadPool
from twisted.web.client import ResponseNeverReceived

from globaleaks import __version__, orm
from globaleaks.orm import tw
from globaleaks.rest import errors
from globaleaks.settings import Settings
from globaleaks.transactions import db_schedule_email
from globaleaks.utils.agent import get_tor_agent, get_web_agent
from globaleaks.utils.crypto import sha256, totpVerify
from globaleaks.utils.log import log
from globaleaks.utils.mail import sendmail
from globaleaks.utils.objectdict import ObjectDict
from globaleaks.utils.pgp import PGPContext
from globaleaks.utils.singleton import Singleton
from globaleaks.utils.sni import SNIMap
from globaleaks.utils.sock import reserve_tcp_socket
from globaleaks.utils.tempdict import TempDict
from globaleaks.utils.templating import Templating
from globaleaks.utils.token import TokenList
from globaleaks.utils.tor_exit_set import TorExitSet
from globaleaks.utils.utility import datetime_now, datetime_null


silenced_exceptions = (
  AlreadyCalledError,
  CancelledError,
  ConnectionLost,
  ConnectionRefusedError,
  DNSLookupError,
  GeneratorExit,
  OperationalError,
  NoRouteError,
  ResponseNeverReceived,
  SMTPError,
  TimeoutError,
  TorProtocolError,
  ValidationError
)


class RateLimitingStatus(object):
    def __init__(self):
        self.counter = 0


class RateLimitingDict(TempDict):
    def check(self, key, limit):
        if key not in self:
            self[key] = RateLimitingStatus()

        status = self[key]

        if status.counter >= limit:
            raise errors.ForbiddenOperation()

        status.counter += 1


RateLimitingTable = RateLimitingDict(3600)


class TenantState(object):
    def __init__(self):
        self.cache = ObjectDict()

        # An ACME challenge will have 5 minutes to resolve
        self.acme_tmp_chall_dict = TempDict(300)

        self.reset_events()

    def reset_events(self):
        from globaleaks.anomaly import Alarm

        self.RecentEventQ = []
        self.EventQ = []
        self.AnomaliesQ = []
        self.Alarm = Alarm()


class StateClass(ObjectDict, metaclass=Singleton):
    def __init__(self):
        self.reset_cache = False
        self.start_time = datetime_now()
        self.settings = Settings

        self.tor_exit_set = TorExitSet()

        self.https_socks = []
        self.http_socks = []

        self.snimap = SNIMap()

        self.jobs = []
        self.jobs_monitor = None
        self.services = []
        self.tor = None

        self.exceptions = {}
        self.exceptions_email_count = 0
        self.stats_collection_start_time = datetime_now()

        self.accept_submissions = True

        self.tenants = {}

        self.tenant_uuid_id_map = {}
        self.tenant_hostname_id_map = {}
        self.tenant_subdomain_id_map = {}

        self.orm_tp = None
        self.set_orm_tp(ThreadPool(4, 16))

        self.tokens = TokenList(60)
        self.TempKeys = TempDict(3600 * 72)
        self.TwoFactorTokens = TempDict(120)
        self.TempUploadFiles = TempDict(3600)
        self.RateLimitingTable = RateLimitingDict(3600)

        self.shutdown = False

    def init_environment(self):
        os.umask(0o77)
        self.settings.eval_paths()
        self.create_directories()

    def set_orm_tp(self, orm_tp):
        self.orm_tp = orm_tp
        orm.set_thread_pool(orm_tp)

    def get_agent(self):
        if 1 not in self.tenants or self.tenants[1].cache.anonymize_outgoing_connections:
            return get_tor_agent(self.settings.socks_port)

        return get_web_agent()

    def create_directory(self, path):
        """
        Create the specified directory;
        Returns True on success, False if the directory was already existing
        """
        if os.path.exists(path):
            return False

        log.debug("Creating directory: %s", path)

        try:
            os.mkdir(path)
        except OSError as excep:
            log.debug("Error in creating directory: %s (%s)",
                      path, excep.strerror)
            raise excep

        return True

    def create_directories(self):
        """
        Creates directories tree for the software data dir
        """
        for dirpath in [self.settings.working_path,
                        self.settings.files_path,
                        self.settings.attachments_path,
                        self.settings.ramdisk_path,
                        self.settings.tmp_path,
                        self.settings.log_path]:
            self.create_directory(dirpath)

    def bind_tcp_ports(self):
        # Allocate local ports
        for port in self.settings.bind_local_ports:
            sock, fail = reserve_tcp_socket('127.0.0.1', port)
            if fail is not None:
                log.err("Could not reserve socket for %s (error: %s)",
                        fail.args[0], fail.args[1])
                continue

            if port == 8443:
                self.https_socks += [sock]
            else:
                self.http_socks += [sock]

        # Allocate remote ports
        for port in self.settings.bind_remote_ports:
            sock, fail = reserve_tcp_socket(self.settings.bind_address, port)
            if fail is not None:
                log.err("Could not reserve socket for %s (error: %s)",
                        fail.args[0], fail.args[1])
                continue

            if port == 8443:
                self.https_socks += [sock]
            else:
                self.http_socks += [sock]

    def print_listening_interfaces(self):
        print("GlobaLeaks is now running and accessible at the following urls:")

        tenant_cache = self.tenants[1].cache

        if self.settings.devel_mode:
            print("- [HTTPS]: https://127.0.0.1:8443")

        elif tenant_cache.reachable_via_web:
            hostname = tenant_cache.hostname or '0.0.0.0'
            print("- [HTTPS]: https://%s" % hostname)

        if tenant_cache.onionservice:
            print("- [Tor]:  http://%s" % tenant_cache.onionservice)

    def reset_minutely(self):
        self.exceptions.clear()
        self.exceptions_email_count = 0

    def reset_hourly(self):
        for tid in self.tenants:
            self.tenants[tid].reset_events()

        self.stats_collection_start_time = datetime_now()

    def sendmail(self, tid, to_address, subject, body):
        if self.settings.disable_notifications:
            return succeed(True)

        if self.tenants[tid].cache.mode != 'default':
            tid = 1

        return sendmail(tid,
                        self.tenants[tid].cache.notification.smtp_server,
                        self.tenants[tid].cache.notification.smtp_port,
                        self.tenants[tid].cache.notification.smtp_security,
                        self.tenants[tid].cache.notification.smtp_authentication,
                        self.tenants[tid].cache.notification.smtp_username,
                        self.tenants[tid].cache.notification.smtp_password,
                        self.tenants[tid].cache.name,
                        self.tenants[tid].cache.notification.smtp_source_email,
                        to_address,
                        self.tenants[tid].cache.name + ' - ' + subject,
                        body,
                        self.tenants[1].cache.anonymize_outgoing_connections,
                        self.settings.socks_port)

    def schedule_support_email(self, tid, text):
        subject = "Support request"
        delivery_list = set.union(set(self.tenants[1].cache.notification.admin_list),
                                  set(self.tenants[tid].cache.notification.admin_list))

        for mail_address, pgp_key_public in delivery_list:
            body = text

            # Opportunisticly encrypt the mail body. NOTE that mails will go out
            # unencrypted if one address in the list does not have a public key set.
            if pgp_key_public:
                try:
                    body = PGPContext(pgp_key_public).encrypt_message(mail_body)
                except:
                    continue

            # avoid waiting for the notification to send and instead rely on threads to handle it
            tw(db_schedule_email, tid, mail_address, subject, body)

    def schedule_exception_email(self, tid, exception_text, *args):
        if not hasattr(self.tenants[tid].cache, 'notification'):
            log.err("Error: Cannot send mail exception before complete initialization.")
            return

        if self.exceptions_email_count >= self.settings.exceptions_email_minutely_limit:
            return

        exception_text = (exception_text % args) if args else exception_text

        sha256_hash = sha256(exception_text.encode())

        if sha256_hash not in self.exceptions:
            self.exceptions[sha256_hash] = 0

        self.exceptions[sha256_hash] += 1
        if self.exceptions[sha256_hash] > 5:
            log.err("Exception mail suppressed for (%s) [reason: threshold exceeded]", sha256_hash)
            return

        self.exceptions_email_count += 1

        mail_subject = "GlobaLeaks Exception"
        delivery_list = self.tenants[1].cache.notification.admin_list + \
                        self.tenants[tid].cache.notification.admin_list

        if self.tenants[1].cache.enable_developers_exception_notification:
            delivery_list.append(('exceptions@globaleaks.org', ''))

        for mail_address, pgp_key_public in delivery_list:
            mail_body = "Platform: %s\nHost: %s (%s)\nVersion: %s\n\n%s" % (self.tenants[tid].cache.name,
                                                                            self.tenants[tid].cache.hostname,
                                                                            self.tenants[tid].cache.onionservice,
                                                                            __version__,
                                                                            exception_text)

            # Opportunisticly encrypt the mail body. NOTE that mails will go out
            # unencrypted if one address in the list does not have a public key set.
            if pgp_key_public:
                mail_body = PGPContext(pgp_key_public).encrypt_message(mail_body)

            # avoid waiting for the notification to send and instead rely on threads to handle it
            tw(db_schedule_email, 1, mail_address, mail_subject, mail_body)

    def format_and_send_mail(self, session, tid, mail_address, template_vars):
        mail_subject, mail_body = Templating().get_mail_subject_and_body(template_vars)

        db_schedule_email(session, tid, mail_address, mail_subject, mail_body)

    def get_tmp_file_by_name(self, filename):
        for k, v in self.TempUploadFiles.items():
            if os.path.basename(v.filepath) == filename:
                return self.TempUploadFiles.pop(k)

    def update_tor_exits_list(self):
        net_agent = self.get_agent()
        log.debug('Fetching list of Tor exit nodes')
        return self.tor_exit_set.update(net_agent)

    def totp_verify(self, secret, token):
        class UsedToken(object):
            def __init__(self, token):
               self.token = token

        # Check token reuse
        previous_token = self.TwoFactorTokens.get(secret)
        if previous_token and previous_token.token == token:
            raise errors.InvalidTwoFactorAuthCode

        try:
            totpVerify(secret, token)
        except:
            raise errors.InvalidTwoFactorAuthCode

        # Register last used valid token
        self.TwoFactorTokens[secret] = UsedToken(token)


def mail_exception_handler(etype, value, tback):
    """
    Formats traceback and exception data and emails the error,
    This would be enabled only in the testing phase and testing release,
    not in production release.
    """
    if isinstance(value, silenced_exceptions) or \
        (etype == AssertionError and value.message == "Request closed"):
        # we need to bypass email notification for some exception that:
        # 1) raise frequently or lie in a twisted bug;
        # 2) lack of useful stacktraces;
        # 3) can be cause of email storm amplification
        #
        # this kind of exception can be simply logged error logs.
        log.err("exception mail suppressed for exception (%s) [reason: special exception]", str(etype))
        return

    mail_body = ""

    # collection of the stacktrace info
    exc_type = re.sub("(<(type|class ')|'exceptions.|'>|__main__.)",
                      "", str(etype))

    mail_body += "%s %s\n\n" % (exc_type.strip(), etype.__doc__)

    mail_body += '\n'.join(traceback.format_exception(etype, value, tback))

    log.err("Unhandled exception raised:")
    log.err(mail_body)

    State.schedule_exception_email(1, mail_body)


def extract_exception_traceback_and_schedule_email(e):
    if isinstance(e, Failure):
        type, value, traceback = e.type, e.value, e.getTracebackObject()
    else:
        type, value, traceback = sys.exc_info()

    mail_exception_handler(type, value, traceback)


# State is a singleton class exported once
State = StateClass()
