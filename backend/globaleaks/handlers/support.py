# Handlers dealing with user support requests
from globaleaks.handlers.base import BaseHandler
from globaleaks.rest import requests
from globaleaks.utils.log import log
from globaleaks.utils.defang import defang

def generate_support_email(mail_address, hostname, request):
    email = "From: %s\n\n" % defang(mail_address) # untrusted
    email += "Site: %s\n\n" % hostname            # trusted
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

        email = generate_support_email(request['mail_address'],
                                       self.request.hostname,
                                       request['text'])

        self.state.schedule_support_email(self.request.tid, email)
        log.debug("Received support request and forwarded to administrators")
