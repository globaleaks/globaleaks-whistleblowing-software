# -*- coding: utf-8
#   API
#   ***
#
#   This file defines the URI mapping for the GlobaLeaks API and its factory
import inspect
import json
import re

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
    robots, \
    security, \
    signup, \
    sitemap, \
    support, \
    staticfile, \
    support, \
    user, \
    viewer, \
    wizard, \
    whistleblower, accreditation

from globaleaks.rest import decorators, errors
from globaleaks.state import State, extract_exception_traceback_and_schedule_email
from globaleaks.utils.json import JSONEncoder
from globaleaks.utils.sock import isIPAddress

tid_regexp = r'([0-9]+)'
uuid_regexp = r'([a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12})'
key_regexp = r'([a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}|[a-z_]{0,100})'

api_spec = [
    (r'/api/health', health.HealthStatusHandler),

    # Public API
    (r'/api/public', public.PublicResource),

    # Authentication Handlers
    (r'/api/auth/token', auth.token.TokenHandler),
    (r'/api/auth/authentication', auth.AuthenticationHandler),
    (r'/api/auth/tokenauth', auth.TokenAuthHandler),
    (r'/api/auth/receiptauth', auth.ReceiptAuthHandler),
    (r'/api/auth/session', auth.SessionHandler),
    (r'/api/auth/tenantauthswitch/' + tid_regexp, auth.TenantAuthSwitchHandler),
    (r'/api/auth/operatorauthswitch', auth.OperatorAuthSwitchHandler),

    # User Preferences Handler
    (r'/api/user/preferences', user.UserInstance),
    (r'/api/user/operations', user.operation.UserOperationHandler),
    (r'/api/user/reset/password', user.reset_password.PasswordResetHandler),
    (r'/api/user/reset/password/(.+)', user.reset_password.PasswordResetHandler),
    (r'/api/user/validate/email/(.+)', user.validate_email.EmailValidation),

    # Receiver Handlers
    (r'/api/recipient/operations', recipient.Operations),
    (r'/api/recipient/rtips', recipient.TipsCollection),
    (r'/api/recipient/rtips/' + uuid_regexp, recipient.rtip.RTipInstance),
    (r'/api/recipient/rtips/' + uuid_regexp + r'/comments', recipient.rtip.RTipCommentCollection),
    (r'/api/recipient/rtips/' + uuid_regexp + r'/iars', recipient.rtip.IdentityAccessRequestsCollection),
    (r'/api/recipient/rtips/' + uuid_regexp + r'/export', recipient.export.ExportHandler),
    (r'/api/recipient/rtips/' + uuid_regexp + r'/rfiles', recipient.rtip.ReceiverFileUpload),
    (r'/api/recipient/redactions', recipient.rtip.RTipRedactionCollection),
    (r'/api/recipient/redactions/' + uuid_regexp, recipient.rtip.RTipRedactionCollection),
    (r'/api/recipient/rfiles/' + uuid_regexp, recipient.rtip.ReceiverFileDownload),
    (r'/api/recipient/wbfiles/' + uuid_regexp, recipient.rtip.WhistleblowerFileDownload),

    # Whistleblower Handlers
    (r'/api/whistleblower/operations', whistleblower.wbtip.Operations),
    (r'/api/whistleblower/submission', whistleblower.submission.SubmissionInstance),
    (r'/api/whistleblower/submission/attachment', whistleblower.attachment.SubmissionAttachment),
    (r'/api/whistleblower/wbtip', whistleblower.wbtip.WBTipInstance),
    (r'/api/whistleblower/wbtip/comments', whistleblower.wbtip.WBTipCommentCollection),
    (r'/api/whistleblower/wbtip/rfiles/' + uuid_regexp, whistleblower.wbtip.ReceiverFileDownload),
    (r'/api/whistleblower/wbtip/wbfiles', whistleblower.attachment.PostSubmissionAttachment),
    (r'/api/whistleblower/wbtip/wbfiles/' + uuid_regexp, whistleblower.wbtip.WhistleblowerFileDownload),
    (r'/api/whistleblower/wbtip/identity', whistleblower.wbtip.WBTipIdentityHandler),
    (r'/api/whistleblower/wbtip/fillform', whistleblower.wbtip.WBTipAdditionalQuestionnaire),

    # Custodian Handlers
    (r'/api/custodian/iars', custodian.IdentityAccessRequestsCollection),
    (r'/api/custodian/iars/' + uuid_regexp, custodian.IdentityAccessRequestInstance),

    # Analyst Handlers
    (r'/api/analyst/stats', analyst.Statistics),

    # Admin Handlers
    (r'/api/admin/node', admin.node.NodeInstance),
    (r'/api/admin/network', admin.network.NetworkInstance),
    (r'/api/admin/users', admin.user.UsersCollection),
    (r'/api/admin/users/' + uuid_regexp, admin.user.UserInstance),
    (r'/api/admin/contexts', admin.context.ContextsCollection),
    (r'/api/admin/contexts/' + uuid_regexp, admin.context.ContextInstance),
    (r'/api/admin/questionnaires', admin.questionnaire.QuestionnairesCollection),
    (r'/api/admin/questionnaires/duplicate', admin.questionnaire.QuestionnareDuplication),
    (r'/api/admin/questionnaires/' + key_regexp, admin.questionnaire.QuestionnaireInstance),
    (r'/api/admin/notification', admin.notification.NotificationInstance),
    (r'/api/admin/fields', admin.field.FieldsCollection),
    (r'/api/admin/fields/' + key_regexp, admin.field.FieldInstance),
    (r'/api/admin/steps', admin.step.StepCollection),
    (r'/api/admin/steps/' + uuid_regexp, admin.step.StepInstance),
    (r'/api/admin/fieldtemplates', admin.field.FieldTemplatesCollection),
    (r'/api/admin/fieldtemplates/' + key_regexp, admin.field.FieldTemplateInstance),
    (r'/api/admin/redirects', admin.redirect.RedirectCollection),
    (r'/api/admin/redirects/' + uuid_regexp, admin.redirect.RedirectInstance),
    (r'/api/admin/auditlog', admin.auditlog.AuditLog),
    (r'/api/admin/auditlog/access', admin.auditlog.AccessLog),
    (r'/api/admin/auditlog/debug', admin.auditlog.DebugLog),
    (r'/api/admin/auditlog/jobs', admin.auditlog.JobsTiming),
    (r'/api/admin/auditlog/tips', admin.auditlog.TipsCollection),
    (r'/api/admin/l10n/(' + '|'.join(LANGUAGES_SUPPORTED_CODES) + ')', admin.l10n.AdminL10NHandler),
    (r'/api/admin/config', admin.operation.AdminOperationHandler),
    (r'/api/admin/config/csr/gen', admin.https.CSRHandler),
    (r'/api/admin/config/acme/run', admin.https.AcmeHandler),
    (r'/api/admin/config/tls', admin.https.ConfigHandler),
    (r'/api/admin/config/tls/files/(cert|chain|key)', admin.https.FileHandler),
    (r'/api/admin/files', admin.file.FileCollection),
    (r'/api/admin/files/(.+)', admin.file.FileInstance),
    (r'/api/admin/tenants', admin.tenant.TenantCollection),
    (r'/api/admin/tenants/' + '([0-9]{1,20})', admin.tenant.TenantInstance),
    (r'/api/admin/statuses', admin.submission_statuses.SubmissionStatusCollection),
    (r'/api/admin/statuses/' + r'(closed)' + r'/substatuses', admin.submission_statuses.SubmissionSubStatusCollection),
    (r'/api/admin/statuses/' + uuid_regexp, admin.submission_statuses.SubmissionStatusInstance),
    (r'/api/admin/statuses/' + uuid_regexp + r'/substatuses', admin.submission_statuses.SubmissionSubStatusCollection),
    (r'/api/admin/statuses/' + r'(closed)' + r'/substatuses/' + uuid_regexp, admin.submission_statuses.SubmissionSubStatusInstance),
    (r'/api/admin/statuses/' + uuid_regexp + r'/substatuses/' + uuid_regexp, admin.submission_statuses.SubmissionSubStatusInstance),

    # Accreditation
    (r'/api/accreditation/request', accreditation.SubmitAccreditationHandler),
    (r'/api/accreditation/all', accreditation.GetAllAccreditationHandler),
    (r'/api/accreditation/request/' + uuid_regexp, accreditation.AccreditationHandler),
    (r'/api/accreditation/request/' + uuid_regexp + r'/accredited', accreditation.AccreditationConfirmHandler),

    # Services
    (r'/api/support', support.SupportHandler),
    (r'/api/signup', signup.Signup),
    (r'/api/signup/([a-zA-Z0-9_\-]{64})', signup.SignupActivation),
    (r'/api/wizard', wizard.Wizard),

    # Well known path
    (r'/.well-known/acme-challenge/([a-zA-Z0-9_\-]{42,44})', admin.https.AcmeChallengeHandler),
    (r'/.well-known/security.txt', security.SecuritytxtHandler),

    # Special Files Handlers
    (r'/robots.txt', robots.RobotstxtHandler),
    (r'/sitemap.xml', sitemap.SitemapHandler),
    (r'/s/(.+)', file.FileHandler),
    (r'/l10n/(' + '|'.join(LANGUAGES_SUPPORTED_CODES) + ')', l10n.L10NHandler),

    # Path alias
    (r'^(/admin|/login|/submission)$', redirect.SpecialRedirectHandler),

    # File viewer app
    (r'/(viewer/[a-zA-Z0-9_\-\/\.\@]*)', viewer.ViewerHandler),

    # This handler attempts to route all non routed get requests
    (r'/([a-zA-Z0-9_\-\/\.\@]*)', staticfile.StaticFileHandler)
]


class APIResourceWrapper(Resource):
    _registry = None
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
        self._registry = []
        self.handler = None

        for tup in api_spec:
            args = {}
            if len(tup) == 2:
                pattern, handler = tup
            else:
                pattern, handler, args = tup

            if not pattern.startswith("^"):
                pattern = "^" + pattern

            if not pattern.endswith("$"):
                pattern += "$"

            if not hasattr(handler, '_decorated'):
                handler._decorated = True
                for m in ['delete', 'get', 'put', 'post']:
                    # head and options method is intentionally not considered here
                    if hasattr(handler, m):
                        decorators.decorate_method(handler, m)

            self._registry.append((re.compile(pattern), handler, args))

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
            request.tid = State.tenant_hostname_id_map.get(request.hostname, None)

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

        match = None
        for regexp, handler, args in self._registry:
            try:
                match = regexp.match(request_path)
            except UnicodeDecodeError:
                match = None
            if match:
                break

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

        self.handler = handler(State, request, **args)

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

        request.setHeader(b'Content-Security-Policy',
                          b"base-uri 'none';"
                          b"default-src 'none';"
                          b"form-action 'none';"
                          b"frame-ancestors 'none';"
                          b"sandbox;")

        request.setHeader(b"Cross-Origin-Embedder-Policy", "require-corp")
        request.setHeader(b"Cross-Origin-Opener-Policy", "same-origin")
        request.setHeader(b"Cross-Origin-Resource-Policy", "same-origin")

        # Disable features that could be used to deanonymize the user
        microphone = False
        if request.tid in State.tenants and getattr(State.tenants[request.tid], 'microphone', False):
            microphone = True

        request.setHeader(b'Permissions-Policy', b"camera=(),"
                                                 b"document-domain=(),"
                                                 b"fullscreen=(),"
                                                 b"geolocation=(),"
                                                 b"microphone=(" + (b"self" if microphone else b"") + b"),"
                                                 b"serial=(),"
                                                 b"usb=(),"
                                                 b"web-share=()")

        # Prevent old browsers not supporting CSP frame-ancestors directive to includes the platform within an iframe
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

        request.setHeader(b'Content-Language', request.language)

    def detect_language(self, request):
        locales = []
        for language in request.headers.get(b'accept-language', b'').decode().split(","):
            parts = language.strip().split(";")
            if len(parts) > 1 and parts[1].startswith("q="):
                try:
                    score = float(parts[1][2:])
                except (ValueError, TypeError):
                    score = 0
            else:
                score = 1.0

            if request.tid in State.tenants and parts[0] in State.tenants[request.tid].cache.languages_enabled:
                locales.append((parts[0], score))

        if locales:
            locales.sort(key=lambda pair: pair[1], reverse=True)
            request.language = locales[0][0]
        elif request.tid in State.tenants:
            request.language = State.tenants[request.tid].cache.default_language
        else:
            request.language = 'en'

        return request.language
