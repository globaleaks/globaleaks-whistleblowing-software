# Handlers dealing with user support requests
from globaleaks.handlers.base import BaseHandler
from globaleaks.utils.log import escape_string


class ReportHandler(BaseHandler):
    """
    This handler is responsible of receiving CSP violation reports
    """
    check_roles = 'any'

    def post(self):
        request = self.request.content.read().decode('utf-8', 'replace')
        self.state.csp_report_log.write((escape_string(request) + "\n").encode())
