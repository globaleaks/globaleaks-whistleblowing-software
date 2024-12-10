from globaleaks.handlers.accreditator.services import accreditation, get_all_accreditation, persistent_drop, \
    get_accreditation_by_id, update_accreditation_by_id, toggle_status_activate, activate_tenant, \
    from_invited_to_request
from globaleaks.handlers.base import BaseHandler
from globaleaks.models.config import ConfigFactory
from globaleaks.orm import transact
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
        admin_tax_code = self.request.headers.get(b'x-idp-userid')
        request = self.validate_request(body_req,requests.SubmitAccreditation)
        request['client_ip_address'] = self.request.client_ip
        request['client_user_agent'] = self.request.client_ua
        request['admin_tax_code'] = admin_tax_code
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
    check_roles = 'accreditor'
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

class AccreditationDeleteHandler(BaseHandler):
    check_roles = 'accreditor'
    root_tenant_only = True
    invalidate_cache = True

    def delete(self, accreditation_id: str):
        request = self.validate_request(
            self.request.content.read().decode('utf-8'),
            requests.deleteAccreditation)
        return persistent_drop(
            accreditation_id,
            request
        )

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
    @transact
    def check_request_tax_code(session):
        if ConfigFactory(session, 1).get_val('mode') == 'accreditation':
            raise errors.ForbiddenOperation
        if ConfigFactory(session, 1).get_val('proxy_idp_enabled'):
            raise errors.ForbiddenOperation
        return True

    def get_tax_code(self):
        tax_code = self.request.headers.get(b'x-idp-userid')
        if tax_code:
            return tax_code.decode()
        self.check_request_tax_code()
        return None

    def post(self):
        tax_code = self.get_tax_code()
        body_req = self.request.content.read()
        request = self.validate_request(
            body_req,
            requests.SubmitAccreditation)
        request['client_ip_address'] = self.request.client_ip
        request['client_user_agent'] = self.request.client_ua
        request['tax_code'] = tax_code
        try:
            request['organization_institutional_site'] = json.loads(body_req).get('organization_institutional_site')
        except Exception as e:
            logging.debug(e)
            request['organization_institutional_site'] = None
        return accreditation(request)