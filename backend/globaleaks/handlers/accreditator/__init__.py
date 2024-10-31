from globaleaks.handlers.accreditator.services import accreditation, get_all_accreditation, persistent_drop, \
    get_accreditation_by_id, update_accreditation_by_id, toggle_status_activate, activate_tenant, \
    from_invited_to_request
from globaleaks.handlers.base import BaseHandler
from globaleaks.rest import requests, errors
import logging
import json

class ConfirmRequestHandler(BaseHandler):
    """
    This manager is responsible for receiving accreditation requests and forwarding them to the accreditation manager
    """
    check_roles = 'any'
    root_tenant_only = True
    invalidate_cache = True

    def post(self, accreditation_id: str):
        body_req = self.request.content.read()
        fiscal_code = self.request.headers.get(b'x-idp-userid')
        request = self.validate_request(body_req,requests.SubmitAccreditation)
        request['client_ip_address'] = self.request.client_ip
        request['client_user_agent'] = self.request.client_ua
        request['admin_fiscal_code'] = fiscal_code
        try:
            request['organization_institutional_site'] = json.loads(body_req).get('organization_institutional_site')
        except Exception as e:
            logging.debug(e)
            request['organization_institutional_site'] = None
        return from_invited_to_request(request, accreditation_id)

class SubmitInstructorRequestHandler(BaseHandler):
    """
    This manager is responsible for receiving accreditation requests and forwarding them to the accreditation manager
    """
    check_roles = 'receiver'
    root_tenant_only = True
    invalidate_cache = True

    def post(self):
        body_req = self.request.content.read()
        request = self.validate_request(
            body_req,
            requests.AccreditationInstructorRequest)
        request['client_ip_address'] = self.request.client_ip
        request['client_user_agent'] = self.request.client_ua
        try:
            request['organization_institutional_site'] = json.loads(body_req).get('organization_institutional_site')
        except Exception as e:
            logging.debug(e)
            request['organization_institutional_site'] = None
        return accreditation(request, is_instructor = True)

class ToggleStatusActiveHandler(BaseHandler):
    check_roles = 'any'
    root_tenant_only = True
    invalidate_cache = True

    def put(self, accreditation_id: str):
        return toggle_status_activate(accreditation_id, is_toggle=True)

class AccreditationConfirmHandler(BaseHandler):
    """
    This manager is responsible for confirm accreditation requests
    """
    check_roles = 'any'
    invalidate_cache = True
    root_tenant_only = True

    def post(self, accreditation_id: str):
        request = self.validate_request(
            self.request.content.read(),
            requests.confirmAccreditation)
        return activate_tenant(accreditation_id, request)

class AccreditationApprovedHandler(BaseHandler):
    """
    This manager is responsible for confirm accreditation requests
    """
    check_roles = 'accreditor'
    root_tenant_only = True

    def post(self, accreditation_id: str):
        return toggle_status_activate(accreditation_id)

class AccreditationHandler(BaseHandler):
    """
    This manager is responsible for receiving accreditation requests and forwarding them to the accreditation manager
    """
    check_roles = 'any'
    root_tenant_only = True
    invalidate_cache = True

    def get(self, accreditation_id: str):
        return get_accreditation_by_id(accreditation_id)

    def put(self, accreditation_id: str):
        payload = self.request.content.read().decode('utf-8')
        data = json.loads(payload) if payload else {}
        return update_accreditation_by_id(accreditation_id, data)

    def delete(self, accreditation_id: str):
        request = self.validate_request(
            self.request.content.read().decode('utf-8'),
            requests.deleteAccreditation)
        return persistent_drop(
            accreditation_id,
            request
        )

class GetAllAccreditationHandler(BaseHandler):
    """
    This manager is responsible for receiving accreditation requests and forwarding them to the accreditation manager
    """
    check_roles = 'accreditor'
    root_tenant_only = True
    invalidate_cache = True

    def get(self):
        return get_all_accreditation()

class SubmitAccreditationHandler(BaseHandler):
    """
    This manager is responsible for receiving accreditation requests and forwarding them to the accreditation manager
    """
    check_roles = 'any'
    root_tenant_only = True
    invalidate_cache = True

    @staticmethod
    def cookies_to_dict(cookie_string):
        cookies = [item.strip() for item in cookie_string.split(';') if item]
        cookie_dict = dict(item.split('=', 1) for item in cookies)
        return cookie_dict

    def get_fiscal_code(self):
        fiscal_code = self.request.headers.get(b'x-idp-userid')
        if fiscal_code:
            return fiscal_code.decode()
        cookies = self.cookies_to_dict(self.request.headers.get(b'cookie', b'').decode())
        return cookies.get('x-idp-userid')

    def post(self):
        fiscal_code = self.get_fiscal_code()
        if not fiscal_code:
            raise errors.ForbiddenOperation
        body_req = self.request.content.read()
        request = self.validate_request(
            body_req,
            requests.SubmitAccreditation)
        request['client_ip_address'] = self.request.client_ip
        request['client_user_agent'] = self.request.client_ua
        request['admin_fiscal_code'] = fiscal_code
        try:
            request['organization_institutional_site'] = json.loads(body_req).get('organization_institutional_site')
        except Exception as e:
            logging.debug(e)
            request['organization_institutional_site'] = None
        return accreditation(request)