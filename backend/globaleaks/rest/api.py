#   API
#   ***
#
#   This file defines the URI mapping for the GlobaLeaks API and its factory
import base64
import inspect
import json
import re
import secrets

from functools import lru_cache
from typing import List, Tuple

from sqlalchemy.orm.exc import NoResultFound

from twisted.internet import defer
from twisted.python.failure import Failure
from twisted.web.resource import Resource
from twisted.web.server import NOT_DONE_YET

from globaleaks import LANGUAGES_SUPPORTED_CODES
from globaleaks.handlers import admin, \
                                analyst, \
                                auth, \
                                custodian, \
                                file, \
                                health, \
                                l10n, \
                                public, \
                                recipient, \
                                redirect, \
                                report, \
                                robots, \
                                security, \
                                signup, \
                                sitemap, \
                                staticfile, \
                                support, \
                                user, \
                                wizard, \
                                whistleblower

from globaleaks.rest import decorators, errors
from globaleaks.state import State, extract_exception_traceback_and_schedule_email
from globaleaks.utils.json import JSONEncoder
from globaleaks.utils.sock import isIPAddress

tid_regexp = r'([0-9]+)'
uuid_regexp = r'([a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12})'
uuid_regexp_or_closed = r'([a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}|closed)'
key_regexp = r'([a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}|[a-z_]{0,100})'

COMPILED_RE_MOBILE_UA = re.compile(br'Mobi|Android', re.IGNORECASE)
COMPILED_RE_TID_UUID = re.compile(br'^/t/([a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12})(/.*)$')
COMPILED_RE_TID_SUB = re.compile(br'^/t/([0-9a-z-]+)(/.*)$')

api_spec = [
    ('/api/health', health.HealthStatusHandler),
    ('/api/public', public.PublicResource),
    ('/api/public/contexts', public.ContextInstance, r'/api/public/contexts/' + uuid_regexp),
    ('/api/report', report.ReportHandler),
    ('/api/support', support.SupportHandler),
    ('/api/wizard', wizard.Wizard),

    # Authentication Handlers
    ('/api/auth/token', auth.token.TokenHandler),
    ('/api/auth/authentication', auth.AuthenticationHandler),
    ('/api/auth/type', auth.AuthTypeHandler),
    ('/api/auth/tokenauth', auth.TokenAuthHandler),
    ('/api/auth/receiptauth', auth.ReceiptAuthHandler),
    ('/api/auth/session', auth.SessionHandler),
    ('/api/auth/tenantauthswitch/', auth.TenantAuthSwitchHandler, r'/api/auth/tenantauthswitch/' + tid_regexp),
    ('/api/auth/operatorauthswitch', auth.OperatorAuthSwitchHandler),

    # User Preferences Handler
    ('/api/user/preferences', user.UserInstance),
    ('/api/user/operations', user.operation.UserOperationHandler),
    ('/api/user/reset/password', user.reset_password.PasswordResetHandler),
    ('/api/user/reset/password', user.reset_password.PasswordResetHandler, r'/api/user/reset/password/(.+)'),
    ('/api/user/validate/email', user.validate_email.EmailValidation, r'/api/user/validate/email/(.+)'),

    # Receiver Handlers
    ('/api/recipient/rtips', recipient.TipsCollection),
    ('/api/recipient/rtips', recipient.rtip.RTipInstance, r'/api/recipient/rtips/' + uuid_regexp),
    ('/api/recipient/rtips', recipient.rtip.RTipCommentCollection, r'/api/recipient/rtips/' + uuid_regexp + r'/comments'),
    ('/api/recipient/rtips', recipient.rtip.IdentityAccessRequestsCollection, r'/api/recipient/rtips/' + uuid_regexp + r'/iars'),
    ('/api/recipient/rtips', recipient.export.ExportHandler, r'/api/recipient/rtips/' + uuid_regexp + r'/export'),
    ('/api/recipient/rtips', recipient.rtip.ReceiverFileUpload, r'/api/recipient/rtips/' + uuid_regexp + r'/rfiles'),
    ('/api/recipient/redactions', recipient.rtip.RTipRedactionCollection),
    ('/api/recipient/redactions', recipient.rtip.RTipRedactionCollection, r'/api/recipient/redactions/' + uuid_regexp),
    ('/api/recipient/rfiles', recipient.rtip.ReceiverFileDownload, r'/api/recipient/rfiles/' + uuid_regexp),
    ('/api/recipient/wbfiles', recipient.rtip.WhistleblowerFileDownload, r'/api/recipient/wbfiles/' + uuid_regexp),

    # Whistleblower Handlers
    ('/api/whistleblower/operations', whistleblower.wbtip.Operations),
    ('/api/whistleblower/submission', whistleblower.submission.SubmissionInstance),
    ('/api/whistleblower/submission/attachment', whistleblower.attachment.SubmissionAttachment),
    ('/api/whistleblower/wbtip', whistleblower.wbtip.WBTipInstance),
    ('/api/whistleblower/wbtip/comments', whistleblower.wbtip.WBTipCommentCollection),
    ('/api/whistleblower/wbtip/rfiles', whistleblower.wbtip.ReceiverFileDownload, r'/api/whistleblower/wbtip/rfiles/' + uuid_regexp),
    ('/api/whistleblower/wbtip/wbfiles',  whistleblower.attachment.PostSubmissionAttachment),
    ('/api/whistleblower/wbtip/wbfiles', whistleblower.wbtip.WhistleblowerFileDownload, r'/api/whistleblower/wbtip/wbfiles/' + uuid_regexp),
    ('/api/whistleblower/wbtip/identity', whistleblower.wbtip.WBTipIdentityHandler),
    ('/api/whistleblower/wbtip/fillform', whistleblower.wbtip.WBTipAdditionalQuestionnaire),

    # Custodian Handlers
    ('/api/custodian/iars', custodian.IdentityAccessRequestsCollection),
    ('/api/custodian/iars', custodian.IdentityAccessRequestInstance, r'/api/custodian/iars/' + uuid_regexp),

    # Analyst Handlers
    ('/api/analyst/stats', analyst.Statistics),

    # Admin Handlers
    ('/api/admin/node', admin.node.NodeInstance),
    ('/api/admin/network', admin.network.NetworkInstance),
    ('/api/admin/users', admin.user.UsersCollection),
    ('/api/admin/users', admin.user.UserInstance, r'/api/admin/users/' + uuid_regexp),
    ('/api/admin/contexts', admin.context.ContextsCollection),
    ('/api/admin/contexts', admin.context.ContextInstance, r'/api/admin/contexts/' + uuid_regexp),
    ('/api/admin/questionnaires', admin.questionnaire.QuestionnairesCollection),
    ('/api/admin/questionnaires', admin.questionnaire.QuestionnaireInstance, r'/api/admin/questionnaires/' + key_regexp),
    ('/api/admin/questionnaires/duplicate', admin.questionnaire.QuestionnareDuplication),
    ('/api/admin/notification', admin.notification.NotificationInstance),
    ('/api/admin/fields', admin.field.FieldsCollection),
    ('/api/admin/fields', admin.field.FieldInstance, r'/api/admin/fields/' + key_regexp),
    ('/api/admin/steps', admin.step.StepCollection),
    ('/api/admin/steps', admin.step.StepInstance, r'/api/admin/steps/' + uuid_regexp),
    ('/api/admin/fieldtemplates', admin.field.FieldTemplatesCollection),
    ('/api/admin/fieldtemplates', admin.field.FieldTemplateInstance, r'/api/admin/fieldtemplates/' + key_regexp),
    ('/api/admin/redirects', admin.redirect.RedirectCollection, r'/api/admin/redirects'),
    ('/api/admin/redirects', admin.redirect.RedirectInstance, r'/api/admin/redirects/' + uuid_regexp),
    ('/api/admin/auditlog', admin.auditlog.AuditLog),
    ('/api/admin/auditlog/access', admin.auditlog.AccessLog),
    ('/api/admin/auditlog/debug', admin.auditlog.DebugLog),
    ('/api/admin/auditlog/jobs', admin.auditlog.JobsTiming),
    ('/api/admin/auditlog/tips', admin.auditlog.TipsCollection),
    ('/api/admin/l10n/', admin.l10n.AdminL10NHandler, r'/api/admin/l10n/(' + '|'.join(LANGUAGES_SUPPORTED_CODES) + ')'),
    ('/api/admin/config', admin.operation.AdminOperationHandler),
    ('/api/admin/config/csr/gen', admin.https.CSRHandler),
    ('/api/admin/config/acme/run', admin.https.AcmeHandler),
    ('/api/admin/config/tls', admin.https.ConfigHandler),
    ('/api/admin/config/tls/files/', admin.https.FileHandler, r'/api/admin/config/tls/files/(cert|chain|key)'),
    ('/api/admin/files', admin.file.FileCollection),
    ('/api/admin/files', admin.file.FileInstance, r'/api/admin/files/(.+)'),
    ('/api/admin/tenants', admin.tenant.TenantCollection),
    ('/api/admin/tenants', admin.tenant.TenantInstance, r'/api/admin/tenants/' + '([0-9]{1,20})'),
    ('/api/admin/statuses', admin.submission_statuses.SubmissionStatusCollection),
    ('/api/admin/statuses', admin.submission_statuses.SubmissionStatusInstance, r'/api/admin/statuses/' + uuid_regexp_or_closed),
    ('/api/admin/statuses', admin.submission_statuses.SubmissionSubStatusCollection, r'/api/admin/statuses/' + uuid_regexp_or_closed + r'/substatuses'),
    ('/api/admin/statuses', admin.submission_statuses.SubmissionSubStatusInstance, r'/api/admin/statuses/' + uuid_regexp_or_closed + r'/substatuses/' + uuid_regexp),

    # Signup
    ('/api/signup', signup.Signup),
    ('/api/signup', signup.SignupActivation, r'/api/signup/([a-zA-Z0-9_\-]{64})'),

    # Well known path
    ('/.well-known/acme-challenge', admin.https.AcmeChallengeHandler, r'/\.well-known/acme-challenge/([a-zA-Z0-9_\-]{42,44})'),
    ('/.well-known/security.txt', security.SecuritytxtHandler),

    # Special Files Handlers
    ('/robots.txt', robots.RobotstxtHandler),
    ('/sitemap.xml', sitemap.SitemapHandler),
    ('/s/', file.FileHandler, r'/s/(.+)'),
    ('/l10n/', l10n.L10NHandler, r'/l10n/(' + '|'.join(LANGUAGES_SUPPORTED_CODES) + ')'),

    # Path alias
    ('/admin', redirect.SpecialRedirectHandler, r'(/admin)'),
    ('/login', redirect.SpecialRedirectHandler, r'(/login)'),
    ('/submission', redirect.SpecialRedirectHandler, r'(/submission)'),
]

# Extend the tuples in the API spec that have 2 elements with None
api_spec = [t if len(t) == 3 else (*t, re.escape(t[0])) for t in api_spec]


default_api = staticfile.StaticFileHandler
default_regexp = re.compile(r'/([a-zA-Z0-9_\-\/\.\@]*)')


@lru_cache(maxsize=128)
def expand_language(lang: str):
    parts = lang.split('_')
    return [
        '_'.join(parts[:i])
        for i in range(len(parts), 0, -1)
    ]

@lru_cache(maxsize=512)
def parse_accept_language(raw_header: str) -> List[str]:
    """
    Parse Accept-Language according to RFC.
    Returns language tags ordered by preference.
    """
    if not raw_header:
        return []

    parsed: List[Tuple[str, float, int]] = []

    for index, item in enumerate(raw_header.split(',')):
        parts = item.strip().split(';')
        lang = parts[0].replace('-', '_')

        if not lang:
            continue

        q = 1.0
        for param in parts[1:]:
            param = param.strip()  # noqa: PLW2901
            if param.startswith('q='):
                try:
                    q = float(param[2:])
                except ValueError:
                    q = 0.0

        parsed.append((lang, q, index))

    # Order by:
    # 1. highest q-value
    # 2. original order (stable)
    parsed.sort(key=lambda x: (-x[1], x[2]))

    return [lang for lang, _, _ in parsed]


class TrieNode:
    def __init__(self):
        self.children = {}
        self.descriptors = []  # List of tuples (regexp, handler)


class Trie:
    def __init__(self):
        self.root = TrieNode()

    def insert(self, prefix, regexp, handler):
        """
        Insert a route prefix into the Trie.
        """
        node = self.root
        parts = prefix.strip('/').split('/')

        for part in parts:
            if part not in node.children:
                node.children[part] = TrieNode()
            node = node.children[part]

        # Attach the full regexp and handler at the leaf node
        node.descriptors.append((regexp, handler))

    def search(self, path):
        """
        Search for a matching handler based on the path.
        """
        match = None
        node = self.root
        parts = path.strip('/').split('/')

        for part in parts:
            if part in node.children:
                node = node.children[part]
            else:
                break

        for regexp, handler in node.descriptors:
            match = regexp.match(path)
            if match:
                return match, handler

        return default_regexp.match(path), default_api


class APIResourceWrapper(Resource):
    isLeaf = True
    method_map = {
      'delete': 200,
      'head': 200,
      'get': 200,
      'options': 200,
      'post': 201,
      'put': 202
    }

    def __init__(self):
        Resource.__init__(self)
        self.registry = Trie()
        self.handler = None
        self.static_routes = {}

        for prefix, handler, regexp in api_spec:
            if not hasattr(handler, '_decorated'):
                handler._decorated = True
                for m in ['delete', 'get', 'put', 'post']:
                    # head and options method are intentionally not considered here
                    if hasattr(handler, m):
                        decorators.decorate_method(handler, m)

            if not regexp.startswith("^"):
                regexp = "^" + regexp  # noqa: PLW2901

            if not regexp.endswith("$"):
                regexp += "$"  # noqa: PLW2901

            compiled = re.compile(regexp)
            self.registry.insert(prefix, compiled, handler)

            if compiled.groups == 0:
                m = compiled.match(prefix)
                if m is not None:
                    self.static_routes[prefix] = (m, handler)

    def resolve_handler(self, path):
        hit = self.static_routes.get(path)
        if hit is not None:
            return hit
        return self.registry.search(path)

    def should_redirect_https(self, request):
        if request.isSecure() or \
                request.hostname.endswith(b'.onion') or \
                b'acme-challenge' in request.path:
            return False

        return True

    def should_redirect_tor(self, request):
        if request.client_using_tor and \
           State.tenants[request.tid].cache.onionnames and \
           request.hostname != State.tenants[request.tid].cache.onionnames[0]:
            return True

        return False

    def redirect_https(self, request, hostname=None):
        if hostname is None:
            hostname = request.hostname

        if request.port == 8082:
            hostname += b":8443"

        request.redirect(b'https://' + hostname + request.path)

    def redirect_tor(self, request):
        request.redirect(b'http://' + State.tenants[request.tid].cache.onionnames[0] + request.path)

    def handle_exception(self, exception, request):
        """
        handle_exception is a callback that decorators all deferreds in render

        It responds to properly handled GL Exceptions by pushing the error msgs
        to the client and it spools a mail in the case the exception is unknown
        and unhandled.

        :param exception: A `Twisted.python.Failure` instance that wraps a `GLException`
                  or a normal `Exception`
        :param request: A `twisted.web.Request`
        """
        if request.finished:
            return

        e = exception

        if inspect.isclass(e):
            e = e()

        if isinstance(e, Failure):
            e = e.value

        if isinstance(e, NoResultFound):
            e = errors.ResourceNotFound
        elif isinstance(e, errors.GLException):
            pass
        else:
            e = errors.InternalServerError('Unexpected')
            e.tid = request.tid
            e.url = request.hostname + request.path
            extract_exception_traceback_and_schedule_email(exception)

        if isinstance(e, errors.GLException):
          request.setResponseCode(e.status_code)
          request.setHeader(b'content-type', b'application/json')

          response = json.dumps({
              'error_message': e.reason,
              'error_code': e.error_code,
              'arguments': getattr(e, 'arguments', [])
          })

          request.write(response.encode())

    def render(self, request):
        """
        :param request: `twisted.web.Request`

        :return: empty `str` or `NOT_DONE_YET`
        """
        request.compressed = False
        request.hostname = request.getRequestHostname()
        request.port = request.getHost().port
        request.headers = request.getAllHeaders()
        request.client_ip = b''
        request.client_ua = b''
        request.client_using_mobile = False
        request.client_using_tor = False
        request.language = 'en'
        request.multilang = False
        request.finished = False
        request.nonce = base64.b64encode(secrets.token_bytes(16))

        request.client_ip = request.getClientIP()
        if isinstance(request.client_ip, bytes):
            request.client_ip = request.client_ip.decode()

        # Handle IPv4 mapping on IPv6
        if request.client_ip.startswith('::ffff:'):
            request.client_ip = request.client_ip[7:]

        request.client_using_tor = request.client_ip in State.tor_exit_set or \
                                   request.port == 8083

        request.client_ua = request.headers.get(b'user-agent', b'')

        request.client_using_mobile = COMPILED_RE_MOBILE_UA.search(request.client_ua) is not None

        if not State.tenants[1].cache.wizard_done or \
          request.hostname.lower() in (b'127.0.0.1', b'localhost') or \
          (State.tenants[1].cache.hostname == '' and isIPAddress(request.hostname)):
            request.tid = 1
        else:
            request.tid = State.tenant_hostname_id_map.get(request.hostname)

        if request.tid == 1:
            try:
                m = COMPILED_RE_TID_UUID.match(request.path)
                if m:
                    tid_bytes, rest = m.groups()
                    tid = State.tenant_uuid_id_map.get(tid_bytes.decode())
                    if tid is not None:
                        request.tid = tid
                        request.path = rest
                else:
                    m = COMPILED_RE_TID_SUB.match(request.path)
                    if m:
                        sub_bytes, rest = m.groups()
                        tid = State.tenant_subdomain_id_map.get(sub_bytes.decode())
                        if tid is not None:
                            request.tid = tid
                            request.path = rest
            except Exception:
                pass

        if request.path == b'/index.html':
            request.redirect(b'/')
            return b''

        if request.path == b'/':
            request.path = b'/index.html'

        if request.tid is None:
            # Tentative domain correction in relation to presence / absence of 'www.' prefix
            if not request.hostname.startswith(b'www.'):
                tentative_hostname = b'www.' + request.hostname
            else:
                tentative_hostname = request.hostname[4:]

            if tentative_hostname in State.tenant_hostname_id_map:
                request.redirect(b'https://' + tentative_hostname + b'/')
                return b''
            else:
                # Fallback on root tenant with error 400
                request.tid = None

        self.detect_language(request)
        if b'multilang' in request.args:
            request.multilang = True

        self.set_headers(request)

        if isIPAddress(request.hostname) and 1 in State.tenants:
            hostname = State.tenants[1].cache['hostname']
            https_enabled = State.tenants[1].cache['https_enabled']
            if hostname and https_enabled:
                request.tid = 1
                self.redirect_https(request, hostname.encode())
                return b''

        if request.tid is None or request.tid not in State.tenants:
            request.tid = None
            request.setResponseCode(400)
            return b''

        if self.should_redirect_tor(request):
            self.redirect_tor(request)
            return b''

        if self.should_redirect_https(request):
            self.redirect_https(request)
            return b''

        request_path = request.path.decode()

        if request_path in State.tenants[request.tid].cache['redirects']:
            request.redirect(State.tenants[request.tid].cache['redirects'][request_path])
            return b''

        match, handler = self.resolve_handler(request_path)
        if match is None:
            self.handle_exception(errors.ResourceNotFound, request)
            return b''

        method = request.method.lower().decode()

        if method == 'head':
            method = 'get'
        elif method == 'options':
            request.setResponseCode(200)
            return b''

        if method not in self.method_map.keys() or not hasattr(handler, method):
            self.handle_exception(errors.MethodNotImplemented, request)
            return b''

        f = getattr(handler, method)
        groups = match.groups()

        # The instance is bound to a local: APIResourceWrapper is a single
        # shared (isLeaf) Resource, so storing it on self would be overwritten
        # by any concurrent in-flight request before this request's deferred
        # callbacks run. The conclude callbacks below close over this local.
        h = handler(State, request)

        request.setResponseCode(self.method_map[method])

        if h.root_tenant_only and \
                request.tid != 1:
            self.handle_exception(errors.ForbiddenOperation, request)
            return b''

        if h.root_tenant_or_management_only and \
                request.tid != 1 and \
                  (not h.session or
                   not h.session.properties.get('management_session', False)):
            self.handle_exception(errors.ForbiddenOperation, request)
            return b''

        if h.upload_handler and method == 'post':
            try:
                # Enforce the same session/token and role checks that gate the
                # decorated handler method before processing any upload body, so
                # that unauthenticated or unauthorized requests cannot allocate
                # and fill temporary files.
                decorators.check_session_or_token(h)
                decorators.check_authentication(h, h.check_roles)

                h.process_file_upload()
            except Exception as e:
                self.handle_exception(e, request)
                return b''

            if h.uploaded_file is None:
                return b''

        @defer.inlineCallbacks
        def concludeHandlerFailure(err):
            yield h.check_execution_time()
            self.handle_exception(err, request)

            if request.finished:
                return

            request.finish()

        @defer.inlineCallbacks
        def concludeHandlerSuccess(ret):
            """
            Concludes successful execution of a `BaseHandler` instance

            :param ret: A `dict`, `list`, `str`, `None` or something unexpected
            """
            yield h.check_execution_time()

            if request.finished:
                return

            if ret is not None:
                if isinstance(ret, (dict, list)):
                    ret = json.dumps(ret, cls=JSONEncoder, separators=(',', ':'))
                    request.setHeader(b'content-type', b'application/json')

                if isinstance(ret, str):
                    ret = ret.encode()

                request.write(ret)

            request.finish()

        d = defer.maybeDeferred(f, h, *groups).addCallbacks(concludeHandlerSuccess, concludeHandlerFailure)

        def _finish(_ret):
            request.finished = True

        request.notifyFinish().addBoth(_finish)
        request.notifyFinish().addErrback(lambda _: d.cancel())

        return NOT_DONE_YET

    def set_headers(self, request):
        request.setHeader(b'Server', b'GlobaLeaks')

        if request.isSecure():
            request.setHeader(b'Strict-Transport-Security',
                              b'max-age=31536000; includeSubDomains; preload')

            if request.tid in State.tenants and State.tenants[request.tid].cache.onionservice:
                request.setHeader(b'Onion-Location', b'http://' + State.tenants[request.tid].cache.onionservice.encode() + request.path)

        request.setHeader(b"Cross-Origin-Embedder-Policy", "require-corp")
        request.setHeader(b"Cross-Origin-Opener-Policy", "same-origin")
        request.setHeader(b"Cross-Origin-Resource-Policy", "same-origin")
        request.setHeader(b"Origin-Agent-Cluster", "?1")

        # Default CSP Policy with reporting of any violation
        request.setHeader(b'Content-Security-Policy',
                          b"base-uri 'none';"
                          b"default-src 'none';"
                          b"form-action 'none';"
                          b"frame-ancestors 'none';"
                          b"sandbox;"
                          b"trusted-types;"
                          b"require-trusted-types-for 'script';"
                          b"report-to csp-endpoint")

        # CSP Policy on the entry point
        if request.path == b'/index.html':
            request.setHeader(b'Content-Security-Policy',
                              b"base-uri 'none';"
                              b"connect-src 'self';"
                              b"default-src 'none';"
                              b"font-src 'self';"
                              b"form-action 'none';"
                              b"frame-ancestors 'none';"
                              b"frame-src 'self';"
                              b"img-src 'self';"
                              b"media-src 'self';"
                              b"script-src 'self';"
                              b"style-src 'self' 'nonce-" + request.nonce + b"';"
                              b"trusted-types angular angular#bundler dompurify default;"
                              b"require-trusted-types-for 'script';"
                              b"report-to csp-endpoint")

        # CSP Policy for the crypto worker with reporting of any violation
        elif request.path == b'/workers/crypto.worker.js':
            request.setHeader(b'Content-Security-Policy',
                              b"base-uri 'none';"
                              b"default-src 'none';"
                              b"form-action 'none';"
                              b"frame-ancestors 'none';"
                              b"script-src 'wasm-unsafe-eval';"
                              b"sandbox;"
                              b"trusted-types;"
                              b"require-trusted-types-for 'script';"
                              b"report-to csp-endpoint")

        # CSP Policy for the file viewer
        elif request.path.startswith(b'/viewer'):
            if request.path == b'/viewer/index.html':
                request.setHeader(b'Content-Security-Policy',
                                  b"base-uri 'none';"
                                  b"default-src 'none';"
                                  b"connect-src blob:;"
                                  b"form-action 'none';"
                                  b"frame-ancestors 'self';"
                                  b"img-src blob:;"
                                  b"media-src blob:;"
                                  b"script-src 'self';"
                                  b"style-src 'self';"
                                  b"sandbox allow-scripts;"
                                  b"trusted-types;"
                                  b"require-trusted-types-for 'script';"
                                  b"report-to csp-endpoint")

                request.setHeader(b"Cross-Origin-Resource-Policy", "cross-origin")
            else:
                request.setHeader(b'Access-Control-Allow-Origin', "null")

        request.setHeader(b'Reporting-Endpoints', "csp-endpoint=\"/api/report\"")

        # Disable features that could be used to deanonymize the user
        microphone = False
        if request.tid in State.tenants and getattr(State.tenants[request.tid], 'microphone', False):
            microphone = True

        # Prevent usage of the unused permissions listed in: https://developer.mozilla.org/en-US/docs/Web/API/Permissions
        request.setHeader(b'Permissions-Policy', b"accelerometer=(),"
                                                 b"ambient-light-sensor=(),"
                                                 b"bluetooth=(),"
                                                 b"camera=(),"
                                                 b"clipboard-read=(),"
                                                 b"clipboard-write=(self),"
                                                 b"document-domain=(),"
                                                 b"display-capture=(),"
                                                 b"fullscreen=(),"
                                                 b"geolocation=(),"
                                                 b"gyroscope=(),"
                                                 b"idle-detection=(self),"
                                                 b"keyboard-map=(),"
                                                 b"local-fonts=(),"
                                                 b"magnetometer=(),"
                                                 b"microphone=(" + (b"self" if microphone else b"") + b"),"
                                                 b"midi=(),"
                                                 b"notifications=(),"
                                                 b"payment=(),"
                                                 b"push=(),"
                                                 b"screen-wake-lock=(),"
                                                 b"serial=(),"
                                                 b"speaker-selection=(),"
                                                 b"usb=(),"
                                                 b"web-share=(),"
                                                 b"xr-spatial-tracking=()")

        # Defense in depth against clickjacking; on modern browsers framing is
        # already prevented by the CSP frame-ancestors 'none' directive above.
        request.setHeader(b'X-Frame-Options', b'deny')

        # Prevent the browsers to implement automatic mime type detection and execution.
        request.setHeader(b'X-Content-Type-Options', b'nosniff')

        # Disable caching
        # As by RFC 7234 Cache-control: no-store is the main directive instructing to not
        # store any entry to be used for caching; this settings make it not necessary to
        # use any other headers like Pragma and Expires.
        # This is described in section "3. Storing Responses in Caches"
        request.setHeader(b'Cache-control', b'no-store')

        # Avoid information leakage via referrer
        # This header instruct the browser to never inject the Referrer header in any
        # of the requests performed by xhr and via click on user links
        request.setHeader(b'Referrer-Policy', b'no-referrer')

        # to avoid Robots spidering, indexing, caching
        if request.tid in State.tenants and State.tenants[request.tid].cache.allow_indexing:
            request.setHeader(b'X-Robots-Tag', b'noarchive')
        else:
            request.setHeader(b'X-Robots-Tag', b'noindex')

        if request.client_using_tor is True:
            request.setHeader(b'X-Check-Tor', b'True')
        else:
            request.setHeader(b'X-Check-Tor', b'False')

    def detect_language(self, request):
        tenant = State.tenants.get(request.tid)
        if not tenant:
            request.language = 'en'
            return request.language

        cache = tenant.cache

        raw_header = request.headers.get(
            b'accept-language', b''
        ).decode()

        for lang in parse_accept_language(raw_header):
            for candidate in expand_language(lang):
                if candidate in cache.languages_enabled:
                    request.language = candidate
                    return request.language

        request.language = cache.default_language
        return request.language
