# Handlers dealing with user support requests
from globaleaks.handlers.base import BaseHandler
from globaleaks.rest import errors, requests
from globaleaks.utils.log import log
from globaleaks.utils.defang import defang

# Maximum accepted length of the support request text. The request body is not
# otherwise bounded and its content is persisted verbatim as queued mail bodies.
SUPPORT_TEXT_MAX_LENGTH = 4096

def generate_support_email(mail_address, hostname, request):
    email = "From: %s\n\n" % mail_address         # regexp-validated
    email += "Site: %s\n\n" % hostname            # serverside-generated
    email += "Request:\n%s" % defang(request)     # untrusted
    return email


class SupportHandler(BaseHandler):
    """
    This handler is responsible of receiving support requests and forward them to administrators
    """
    check_roles = 'any'

    def post(self):
        request = self.validate_request(self.request.content.read(),
                                        requests.SupportDesc)

        if len(request['text']) > SUPPORT_TEXT_MAX_LENGTH:
            raise errors.InputValidationError("Support request text too long")

        email = generate_support_email(request['mail_address'],
                                       self.request.hostname,
                                       request['text'])

        self.state.schedule_support_email(self.request.tid, email)
        log.debug("Received support request and forwarded to administrators")
