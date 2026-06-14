import json
import mimetypes
import os
import re

from datetime import datetime

from tempfile import NamedTemporaryFile

from nacl.encoding import Base64Encoder
from twisted.internet import abstract
from twisted.internet.defer import DeferredLock, inlineCallbacks, maybeDeferred
from twisted.internet.threads import deferToThread
from twisted.protocols.basic import FileSender

from globaleaks.utils.ip import get_ip_identity
from globaleaks.orm import transact_sync
from globaleaks.rest import errors
from globaleaks.sessions import Sessions
from globaleaks.settings import Settings
from globaleaks.state import State
from globaleaks.transactions import db_get_user
from globaleaks.utils.crypto import GCE, sha256
from globaleaks.utils.ip import check_ip
from globaleaks.utils.log import log
from globaleaks.utils.pgp import PGPContext
from globaleaks.utils.securetempfile import SecureTemporaryFile
from globaleaks.utils.utility import datetime_now

mimetypes.add_type('text/javascript', '.js')


def decodeString(string):
    string = Base64Encoder.decode(string)
    uint8_array = [c for c in string]
    uint16_array = []
    for i in range(len(uint8_array)):
        if not (i%2):
             uint16_array.append((uint8_array[i] | (uint8_array[i+1] << 8)))
    return ''.join(map(chr, uint16_array))


def serve_file(request, fo):
    filesender = FileSender()

    def on_success(byte):
        fo.close()

    def on_error(error):
        filesender.consumer.unregisterProducer()
        fo.close()

    if request.finished:
        return

    d = filesender.beginFileTransfer(fo, request)
    d.addCallback(on_success)
    d.addErrback(on_error)

    return d


def connection_check(tid, role, client_ip, client_using_tor):
    """
    Accept or refuse a connection in relation to the platform settings

    :param tid: A tenant ID
    :param role: A user role
    :param client_ip: A client IP
    :param client_using_tor: A boolean for signaling Tor use
    """
    cache = State.tenants[tid].cache
    ip_filter_enabled_key = f'ip_filter_{role}_enable'
    ip_filter_key = f'ip_filter_{role}'
    https_allowed_key = f'https_{role}'

    ip_filter_enabled = cache.get(ip_filter_enabled_key)
    if ip_filter_enabled:
        ip_filter = cache.get(ip_filter_key)
        if not check_ip(client_ip, ip_filter):
            raise errors.AccessLocationInvalid

    https_allowed = cache.get(https_allowed_key)
    if not https_allowed and not client_using_tor:
        raise errors.TorNetworkRequired


def db_confirmation_check(session, tid, user_id, secret):
    user = db_get_user(session, tid, user_id)

    if user.two_factor_secret:
        State.totp_verify(user.two_factor_secret, secret)
    else:
        if len(user.hash) == 64:
            hash = sha256(Base64Encoder.decode(secret.encode())).decode()
        else:
            _, hash = GCE.calculate_key_and_hash(secret, user.salt)

        if not GCE.check_equality(hash, user.hash):
            raise errors.InvalidAuthentication


@transact_sync
def sync_confirmation_check(session, tid, user_id, secret):
    return db_confirmation_check(session, tid, user_id, secret)


class BaseHandler(object):
    check_roles = 'admin'
    handler_exec_time_threshold = 120
    cache_resource = False
    invalidate_cache = False
    root_tenant_only = False
    root_tenant_or_management_only = False
    upload_handler = False
    uploaded_file = None
    allowed_mimetypes = []

    def __init__(self, state, request):
        self.name = type(self).__name__
        self.state = state
        self.request = request
        self.request.start_time = datetime.now()
        self.token = None

        self.session = self.get_session()

    def get_session(self):
        if hasattr(self, 'session'):
            return self.session

        session = None

        # Check token header and arg
        token = self.request.headers.get(b'x-token')
        token_arg = self.request.args.get(b"token")
        if token_arg:
            token = token_arg[0]

        if token:
            # Throttle token validation per client IP before the proof-of-work
            # verification so that a burst of invalid redemptions cannot
            # monopolize the reactor with synchronous Argon2 work. Tor clients
            # share an exit identity and are excluded to avoid penalizing them.
            if not self.request.client_using_tor and \
               State.RateLimit.check(b"token_validations_per_minute_per_ip:" + get_ip_identity(self.request.client_ip).encode(), 100, 60) > 0:
                return

            try:
                self.token = self.state.tokens.validate(token)
                if self.token.session is not None:
                    session = self.token.session
            except Exception:
                return

        # Check session header
        session_id = self.request.headers.get(b'x-session')
        if session_id:
            session = Sessions.get(session_id.decode())

        if session is None or session.tid != self.request.tid:
            return

        if session.role != 'whistleblower' and \
           self.state.tenants[1].cache.get('log_accesses_of_internal_users', False):
             self.request.log_ip_and_ua = True

        return session

    @staticmethod
    def validate_python_type(value, python_type):
        """
        Return True if the python class instantiates the specified python_type.
        """
        if value is None:
            return True

        if python_type == int:
            try:
                int(value)
                return True
            except Exception:
                return False

        if python_type == bool:
            if value == 'true' or value == 'false':
                return True

        return isinstance(value, python_type)

    @staticmethod
    def validate_regexp(value, type):
        """
        Return True if the python class matches the given regexp.
        """
        return bool(re.match(type, value))

    @staticmethod
    def validate_type(value, type):
        retval = False

        if value is None:
            log.err("-- Invalid python_type, in [%s] expected %s", value, type)

        # if it's callable, than assumes is a primitive class
        elif callable(type):
            retval = BaseHandler.validate_python_type(value, type)
            if not retval:
                log.err("-- Invalid python_type, in [%s] expected %s", value, type)

        # value as "{foo:bar}"
        elif isinstance(type, dict):
            retval = BaseHandler.validate_request(value, type)
            if not retval:
                log.err("-- Invalid JSON/dict [%s] expected %s", value, type)

        # regexp
        elif isinstance(type, str):
            retval = BaseHandler.validate_regexp(value, type)
            if not retval:
                log.err("-- Failed Match in regexp [%s] against %s", value, type)

        # value as "[ type ]"
        elif isinstance(type, list):
            # empty list is ok
            if not value:
                retval = True

            else:
                retval = all(BaseHandler.validate_type(x, type[0]) for x in value)
                if not retval:
                    log.err("-- List validation failed [%s] of %s", value, type)

        return retval

    @staticmethod
    def validate_request(request, request_template):
        """
        Takes a string that represents a JSON requests and checks to see if it
        conforms to the request type it is supposed to be.

        This request must be either a dict or a list. This function may be called
        recursively to validate sub-parameters that are also go GLType.
        """
        if not isinstance(request, (dict, list)):
            try:
                request = json.loads(request)
            except Exception:
                raise errors.InputValidationError

        if isinstance(request_template, dict):
            success_check = 0
            keys_to_strip = []
            for key, value in request.items():
                if key not in request_template:
                    # strip whatever is not validated
                    #
                    # reminder: it's not possible to raise an exception for the
                    # in case more values are present because it's normal that the
                    # client will send automatically more data.
                    #
                    # e.g. the client will always send 'creation_date' attributes of
                    #      objects and attributes like this are present generally only
                    #      from the second request on.
                    #
                    keys_to_strip.append(key)
                    continue

                if not BaseHandler.validate_type(value, request_template[key]):
                    log.err("Received key %s: type validation fail", key)
                    raise errors.InputValidationError("Key (%s) type validation failure" % key)
                success_check += 1

            for key in keys_to_strip:
                del request[key]

            for key, value in request_template.items():
                if key not in request:
                    log.debug("Key %s expected but missing!", key)
                    log.debug("Received schema %s - Expected %s",
                              request.keys(), request_template.keys())
                    raise errors.InputValidationError("Missing key %s" % key)

                if not BaseHandler.validate_type(request[key], value):
                    log.err("Expected key: %s type validation failure", key)
                    raise errors.InputValidationError("Key (%s) double validation failure" % key)

                if isinstance(request_template[key], (dict, list)) and request_template[key]:
                    BaseHandler.validate_request(request[key], request_template[key])

                success_check += 1

            if success_check != len(request_template) * 2:
                log.err("Success counter double check failure: %d", success_check)
                raise errors.InputValidationError("Success counter double check failure")

        elif isinstance(request_template, list):
            if not all(BaseHandler.validate_type(x, request_template[0]) for x in request):
                raise errors.InputValidationError("Not every element in %s is %s" %
                                                  (request, request_template[0]))

        return request

    def redirect(self, url):
        self.request.setResponseCode(301)
        self.request.setHeader(b'location', url)

    def check_file_presence(self, filepath):
        if not os.path.exists(filepath) or not os.path.isfile(filepath):
            raise errors.ResourceNotFound

    def check_confirmation(self):
        user_id = self.session.user_id

        secret = decodeString(self.request.headers.get(b'x-confirmation', b''))

        try:
            sync_confirmation_check(self.session.user_tid, user_id, secret)
        except (errors.InvalidAuthentication, errors.InvalidTwoFactorAuthCode):
            # Count consecutive failed confirmations and drop the session once
            # the budget is exhausted: this prevents a session-holding attacker
            # from brute forcing the six-digit TOTP or the password used to
            # authorize sensitive operations (e.g. disable_2fa, get_recovery_key).
            failures = self.session.properties.get('confirmation_failures', 0) + 1
            if failures >= 5:
                Sessions.revoke(self.session.tid, self.session.user_id)
            else:
                self.session.properties['confirmation_failures'] = failures

            raise

        self.session.properties.pop('confirmation_failures', None)

    def open_file(self, filepath):
        self.check_file_presence(filepath)

        return open(filepath, 'rb')

    def write_file(self, filename, filepath):
        if isinstance(filepath, str):
            compressed_path = filepath + '.br'

            accept_encoding = self.request.getHeader('Accept-Encoding')
            if accept_encoding and 'br' in accept_encoding and os.path.exists(compressed_path):
                self.request.compressed = True
                filepath = compressed_path

            fp = self.open_file(filepath)
        else:
            fp = filepath

        mimetype, _ = mimetypes.guess_type(filename)

        if mimetype not in self.allowed_mimetypes:
            mimetype = 'application/octet-stream'

        self.request.setHeader(b'Content-Type', mimetype)

        return serve_file(self.request, fp)

    def write_file_as_download(self, filename, fp, pgp_key=''):
        if isinstance(fp, str):
            fp = self.open_file(fp)

        if pgp_key:
            filename += '.pgp'
            _fp = fp
            out = NamedTemporaryFile()  # noqa: SIM115 - handle is returned to serve_file for streaming
            # PGP encryption of a whole file is CPU-heavy; run it off the
            # reactor thread so large downloads/exports cannot stall the
            # single-threaded event loop. The response is served once the
            # encryption completes.
            d = deferToThread(PGPContext(pgp_key).encrypt_file, _fp, out.name)
            d.addCallback(lambda _: self._serve_download(filename, out))
            return d

        return self._serve_download(filename, fp)

    def _serve_download(self, filename, fp):
        self.request.setHeader(b'Content-Type', 'application/octet-stream')
        self.request.setHeader(b'Content-Disposition',
                               'attachment; filename="%s"' % filename)

        return serve_file(self.request, fp)

    @inlineCallbacks
    def serialize_download(self, fn, *args):
        # Serialize CPU-heavy downloads per user (report exports and PGP-wrapped
        # attachment downloads): a user runs at most one at a time and the rest
        # queue rather than being rejected, so a single user cannot multiply the
        # decrypt/compress/encrypt cost. The lock is dropped once idle so
        # download_locks stays bounded.
        key = self.session.user_id
        lock = self.state.download_locks.get(key)
        if lock is None:
            lock = DeferredLock()
            self.state.download_locks[key] = lock

        yield lock.acquire()
        try:
            ret = yield maybeDeferred(fn, *args)
            return ret
        finally:
            lock.release()
            if not lock.locked and not lock.waiting:
                self.state.download_locks.pop(key, None)

    def process_file_upload(self):
        if b'flowFilename' not in self.request.args:
            return

        total_file_size = int(self.request.args[b'flowTotalSize'][0])
        file_id = self.request.args[b'flowIdentifier'][0].decode()

        if file_id not in self.state.TempUploadFiles:
            if self.session and self.session.role == 'whistleblower':
                tid = str(self.request.tid).encode()
                path = self.request.path
                user_id = self.session.user_id.encode()
                client_ip = get_ip_identity(self.request.client_ip).encode()

                block = State.RateLimit.check(b"attachments_per_hour_per_report:" + user_id,
                                              State.tenants[1].cache.threshold_attachments_per_hour_per_report,
                                              3600)
                if block:
                    raise errors.ForbiddenOperation()

            self.state.TempUploadFiles[file_id] = SecureTemporaryFile(Settings.tmp_path)

        f = self.state.TempUploadFiles[file_id]

        max_file_size = self.state.tenants[self.request.tid].cache.maximum_filesize
        max_file_size_bytes = max_file_size * 1024 * 1024

        chunk_size = len(self.request.args[b'file'][0])
        if (chunk_size > max_file_size_bytes or
            total_file_size > max_file_size_bytes or
            f.size + chunk_size > max_file_size_bytes):
            log.err("File upload request rejected: file too big", tid=self.request.tid)
            raise errors.FileTooBig(max_file_size)

        chunk_number = int(self.request.args[b'flowChunkNumber'][0])

        with f.open('w') as f:
            # Chunks are uploaded strictly in order (simultaneousUploads: 1). Anything that
            # is not the next expected chunk is a re-send of one already received (its
            # response was lost, e.g. on a connection the server closed after its idle
            # timeout): acknowledge it with the regular 201 without rewriting or
            # re-finalizing. Rewriting would duplicate bytes and desync the ChaCha20
            # keystream, while re-finalizing the last chunk would attach the file twice.
            # process_file_upload runs synchronously on the reactor thread, so this
            # check-and-write needs no lock.
            if chunk_number != f.written_chunks + 1:
                return None

            f.write(self.request.args[b'file'][0])
            f.written_chunks += 1

            if self.request.args[b'flowChunkNumber'][0] != self.request.args[b'flowTotalChunks'][0]:
                return None

        filename = os.path.basename(self.request.args[b'flowFilename'][0].decode())
        mime_type, _ = mimetypes.guess_type(filename)
        mime_type = mime_type or 'application/octet-stream'  # Default MIME type if None

        # Prepare the uploaded file metadata
        self.uploaded_file = {
            'id': file_id,
            'date': datetime_now(),
            'name': filename,
            'type': mime_type,
            'size': total_file_size,
            'filename': os.path.basename(f.filepath),
            'body': f,
            'description': self.request.args.get(b'description', [''])[0],
            'reference_id': self.request.args.get(b'reference_id', [''])[0],
            'visibility': self.request.args.get(b'visibility', [''])[0]
        }

    def write_upload_plaintext_to_disk(self, destination):
        """
        :param destination: the path where to store the file
        :return: a descriptor dictionary for the saved file
        """
        try:
            log.debug('Creating file %s with %d bytes', destination, self.uploaded_file['size'])

            with self.uploaded_file['body'].open('r') as encrypted_file, open(destination, 'wb') as plaintext_file:
                while True:
                    chunk = encrypted_file.read(abstract.FileDescriptor.bufferSize)
                    if not chunk:
                        break

                    plaintext_file.write(chunk)

        finally:
            self.uploaded_file['path'] = destination

    def check_root_or_management_session(self):
        if self.request.tid != 1 and not (self.session and self.session.properties and self.session.properties.get('management_session', False)):
            raise errors.ForbiddenOperation

    def check_execution_time(self):
        self.request.execution_time = datetime.now() - self.request.start_time

        if self.request.execution_time.seconds > self.handler_exec_time_threshold:
            err_tup = ("Handler [%s] exceeded execution threshold (of %d secs) with an execution time of %.2f seconds",
                       self.name, self.handler_exec_time_threshold, self.request.execution_time.seconds)
            log.err(*err_tup, tid=self.request.tid)
