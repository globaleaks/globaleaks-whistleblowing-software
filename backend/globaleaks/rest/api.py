#   API
#   ***
#
#   This file defines the URI mapping for the GlobaLeaks API and its factory
import base64
import inspect
import json
import re
import secrets

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
role_regexp = r'(admin|analyst|custodian|receiver)'
uuid_regexp = r'([a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12})'
uuid_regexp_or_closed = r'([a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}|closed)'
key_regexp = r'([a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}|[a-z_]{0,100})'

api_spec = [
    ('/api/health', health.HealthStatusHandler),
    ('/api/public', public.PublicResource),
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
    ('/api/auth/roleauthswitch/', auth.RoleAuthSwitchHandler, r'/api/auth/roleauthswitch/' + role_regexp),
    ('/api/auth/operatorauthswitch', auth.OperatorAuthSwitchHandler),

    # User Preferences Handler
    ('/api/user/preferences', user.UserInstance),
    ('/api/user/operations', user.operation.UserOperationHandler),
    ('/api/user/reset/password', user.reset_password.PasswordResetHandler),
    ('/api/user/reset/password', user.reset_password.PasswordResetHandler, r'/api/user/reset/password/(.+)'),
    ('/api/user/validate/email', user.validate_email.EmailValidation, r'/api/user/validate/email/(.+)'),

    # Receiver Handlers
    ('/api/recipient/operations', recipient.Operations),
    ('/api/recipient/rtips', recipient.TipsCollection),
    ('/api/recipient/rtips', recipient.rtip.RTipInstance, r'/api/recipient/rtips/' + uuid_regexp),
    ('/api/recipient/rtips', recipient.rtip.ReportAuditLog, r'/api/recipient/rtips/' + uuid_regexp  + r'/auditlog'),
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
    ('/api/whistleblower/wbtip/auditlog', whistleblower.wbtip.ReportAuditLog),
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
    ('/api/admin/users/profiles', admin.user_profile.UserProfilesCollection),
    ('/api/admin/users/profiles', admin.user_profile.UserProfileInstance, r'/api/admin/users/profiles/' + uuid_regexp),
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
        node.descriptors.append((re.compile(regexp), handler))

    def search(self, path):
        """
        Search for a matching handler based on the path.
        """
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

        for prefix, handler, regexp in api_spec:
            if not hasattr(handler, '_decorated'):
                handler._decorated = True
                for m in ['delete', 'get', 'put', 'post']:
                    # head and options method are intentionally not considered here
                    if hasattr(handler, m):
                        decorators.decorate_method(handler, m)

            if not regexp.startswith("^"):
                regexp = "^" + regexp

            if not regexp.endswith("$"):
                regexp += "$"

            self.registry.insert(prefix, re.compile(regexp), handler)

    def resolve_handler(self, path):
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

        request.client_using_mobile = re.search(b'Mobi|Android', request.client_ua, re.IGNORECASE) is not None

        if not State.tenants[1].cache.wizard_done or \
          request.hostname == b'127.0.0.1' or \
          (State.tenants[1].cache.hostname == '' and isIPAddress(request.hostname)):
            request.tid = 1
        else:
            request.tid = State.tenant_hostname_id_map.get(request.hostname)

        if request.tid == 1:
            try:
                match1 = re.match(b'^/t/([a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12})(/.*)', request.path)
                match2 = re.match(b'^/t/([0-9a-z-]+)(/.*)$', request.path)

                if match1 is not None:
                    groups = match1.groups()
                    tid = State.tenant_uuid_id_map[groups[0].decode()]
                    request.tid, request.path = tid, groups[1]
                elif match2 is not None:
                    groups = match2.groups()
                    tid = State.tenant_subdomain_id_map[groups[0].decode()]
                    request.tid, request.path = tid, groups[1]
            except:
                pass

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

        self.handler = handler(State, request)

        request.setResponseCode(self.method_map[method])

        if self.handler.root_tenant_only and \
                request.tid != 1:
            self.handle_exception(errors.ForbiddenOperation, request)
            return b''

        if self.handler.root_tenant_or_management_only and \
                request.tid != 1 and \
                  (not self.handler.session or
                   not self.handler.session.properties.get('management_session', False)):
            self.handle_exception(errors.ForbiddenOperation, request)
            return b''

        if self.handler.upload_handler and method == 'post':
            try:
                self.handler.process_file_upload()
            except Exception as e:
                self.handle_exception(e, request)
                return b''

            if self.handler.uploaded_file is None:
                return b''

        @defer.inlineCallbacks
        def concludeHandlerFailure(err):
            yield self.handler.check_execution_time()
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
            yield self.handler.check_execution_time()

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

        d = defer.maybeDeferred(f, self.handler, *groups).addCallbacks(concludeHandlerSuccess, concludeHandlerFailure)

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
                              b"img-src 'self' data:;"
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
        locales = []

        # Retrieve and decode the 'accept-language' header
        accept_language = request.headers.get(b'accept-language', b'').decode()

        # Get the tenant data once to avoid redundant lookups
        tenant_cache = State.tenants.get(request.tid)

        # Check if tenant exists and is cached
        if tenant_cache:
            enabled_languages = tenant_cache.cache.languages_enabled
            default_language = tenant_cache.cache.default_language

            for language in accept_language.split(","):
                parts = language.strip().split(";")
                score = 1.0  # Default score

                if len(parts) > 1 and parts[1].startswith("q="):
                    try:
                        score = float(parts[1][2:])
                    except (ValueError, TypeError):
                        score = 0  # Fallback if q-value is invalid

                # Append language with score if it's enabled for the tenant
                if parts[0] in enabled_languages:
                    locales.append((parts[0], score))

            if locales:
               # Use max() to pick the language with the highest score
               request.language = max(locales, key=lambda pair: pair[1])[0]
            else:
               # Fallback to default language if no matching locale found
                request.language = default_language
        else:
            # Fallback to default 'en' if tenant doesn't exist or no valid languages enabled
            request.language = 'en'

        return request.language
