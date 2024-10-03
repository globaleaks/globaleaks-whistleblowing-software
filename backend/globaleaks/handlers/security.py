# -*- coding: utf-8 -*-
#
# Implementation of security.txt resource
from datetime import timedelta

from globaleaks.handlers.base import BaseHandler
from globaleaks.utils.utility import datetime_now, datetime_to_ISO8601


class SecuritytxtHandler(BaseHandler):
    """
    Handler that implements the Robot.txt api
    """
    check_roles = 'any'

    def get(self):
        """
        Get the robots.txt
        """
        self.request.setHeader(b'Content-Type', b'text/plain')

        date = datetime_now() + timedelta(days=365)

        data = "Policy: https://github.com/globaleaks/whistleblowing-software/security/policy\n" \
               "Contact: https://github.com/globaleaks/whistleblowing-software/security/advisories/new\n" \
               "Expires: " + datetime_to_ISO8601(date)

        return data
