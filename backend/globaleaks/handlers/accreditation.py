from globaleaks.handlers.base import BaseHandler
from globaleaks.rest import requests


class SubmitAccreditationHandler(BaseHandler):
    """
    This manager is responsible for receiving accreditation requests and forwarding them to the accreditation manager
    """
    check_roles = 'any'
    root_tenant_only = True
    invalidate_cache = True

    def post(self):
        self.request.headers.get(b'x-fiscalcode')
        request = self.validate_request(
            self.request.content.read(),
            requests.SubmitAccreditation)

