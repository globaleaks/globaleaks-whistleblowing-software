import json
from uuid import uuid4

from sqlalchemy import func, distinct
from sqlalchemy.exc import NoResultFound

from globaleaks.handlers.base import BaseHandler
from globaleaks.models import Subscriber, Tenant, EnumSubscriberStatus, config, InternalTip, InternalTipForwarding, User
from globaleaks.models.config import ConfigFactory
from globaleaks.orm import transact
from globaleaks.rest import requests, errors
from globaleaks.state import State
from globaleaks.utils.log import log


def create_tenant():
    t = Tenant()
    t.active = False
    t.external = True
    return t


def save_step(session, obj):
    session.add(obj)
    session.flush()


def send_email(session, tenant_id: int, email: list):
    for user_desc in email:
        template_vars = {
            'type': 'admin_signup_alert',
            'node': '',  # db_admin_serialize_node(session, 1, user_desc['language']),
            'notification': '',  # db_get_notification(session, 1, user_desc['language']),
            'user': user_desc,
            'signup': '',  # signup_dict
        }

        State.format_and_send_mail(session, 1, user_desc['mail_address'], template_vars)


@transact
def accreditation(session, request):
    try:
        sub = Subscriber(request)
        sub.language = ''
        sub.subdomain = str(uuid4())
        sub.state = EnumSubscriberStatus.requested.name
        sub.organization_location = ''
        t = create_tenant()
        save_step(session, t)
        sub.tid = t.id
        save_step(session, sub)
        sub.subdomain = sub.sharing_id
        save_step(session, sub)
        return {'id': sub.sharing_id}
    except Exception as e:
        log.err(f"Error: Accreditation Fail: {e}")
        raise errors.InternalServerError


def count_user_tip(session, accreditation_item):
    count_tip = (
        session.query(
            func.count(distinct(InternalTipForwarding.id))
        )
        .filter(InternalTipForwarding.oe_internaltip_id == accreditation_item.tid)
        .one()
    )
    count_user = (
        session.query(
            func.count(distinct(User.id))
        )
        .filter(User.tid == accreditation_item.tid)
        .filter(User.mail_address not in (accreditation_item.email, accreditation_item.admin_email))
        .one()
    )
    return count_tip, count_user


def serialize_element(accreditation_item, count_tip, count_user, t):
    return {
        'id': accreditation_item.sharing_id,
        'denomination': accreditation_item.organization_name,
        'type': "NOT_AFFILIATED" if t.affiliated is None or t.affiliated == '' else t.affiliated.upper(),
        'accreditation_date': accreditation_item.creation_date,
        'state': accreditation_item.state if isinstance(accreditation_item.state, str) else EnumSubscriberStatus(
            accreditation_item.state).name,
        'num_user_profiled': list(count_user)[0] + 2,
        'num_tip': list(count_tip)[0]
    }


@transact
def get_all_accreditation(session):
    try:
        request_accreditation = []
        for accreditation_item in (session.query(Subscriber).filter(Subscriber.organization_name.isnot(None))):
            t = (session.query(Tenant).filter(Tenant.id == accreditation_item.tid).one())
            count_tip, count_user = count_user_tip(session, accreditation_item)
            element = serialize_element(accreditation_item, count_tip, count_user, t)
            request_accreditation.append(element)
        return request_accreditation
    except Exception as e:
        log.err(f"Error: Accreditation Fail: {e}")
        raise errors.InternalServerError


@transact
def update_accreditation_by_id(session, accreditation_id, data: dict = None):
    try:
        data = data or {}
        accreditation_item = (
            session.query(Subscriber)
            .filter(Subscriber.organization_name.isnot(None))
            .filter(Subscriber.sharing_id == accreditation_id)
            .one()
        )
        if 'denomination' in data:
            accreditation_item.organization_name = data['denomination']
        if 'pec' in data:
            accreditation_item.organization_email = data['pec']
        if 'institutional_site' in data:
            accreditation_item.organization_institutional_site = data['institutional_site']
        save_step(session, accreditation_item)
        return {'id': accreditation_item.sharing_id}
    except NoResultFound:
        log.error(f"Error: Accreditation with ID {accreditation_id} not found")
        raise errors.ResourceNotFound
    except Exception as e:
        log.err(f"Error: Accreditation Fail: {e}")
        raise errors.InternalServerError


@transact
def delete_accreditation_by_id(session, accreditation_id):
    try:
        accreditation_item = (
            session.query(Subscriber)
            .filter(Subscriber.organization_name.isnot(None))
            .filter(Subscriber.sharing_id == accreditation_id)
            .one()
        )
        accreditation_item.state = EnumSubscriberStatus.rejected.value
        save_step(session, accreditation_item)
        return {'id': accreditation_item.sharing_id}
    except NoResultFound:
        log.error(f"Error: Accreditation with ID {accreditation_id} not found")
        raise errors.ResourceNotFound
    except Exception as e:
        log.err(f"Error: Accreditation Fail: {e}")
        raise errors.InternalServerError


@transact
def get_accreditation_by_id(session, accreditation_id):
    try:
        accreditation_item = (
            session.query(Subscriber)
            .filter(Subscriber.organization_name.isnot(None))
            .filter(Subscriber.sharing_id == accreditation_id)
            .one()
        )
        t = (
            session.query(Tenant)
            .filter(Tenant.id == accreditation_item.tid)
            .one()
        )
        count_tip, count_user = count_user_tip(session, accreditation_item)
        element = serialize_element(accreditation_item, count_tip, count_user, t)
        return element
    except NoResultFound:
        log.error(f"Error: Accreditation with ID {accreditation_id} not found")
        raise errors.ResourceNotFound
    except Exception as e:
        log.err(f"Error: Accreditation Fail: {e}")
        raise errors.InternalServerError


class SubmitAccreditationHandler(BaseHandler):
    """
    This manager is responsible for receiving accreditation requests and forwarding them to the accreditation manager
    """
    check_roles = 'any'
    root_tenant_only = True
    invalidate_cache = True

    def post(self):
        fiscal_code = self.request.headers.get(b'x-idp-userid')
        request = self.validate_request(
            self.request.content.read(),
            requests.SubmitAccreditation)
        request['client_ip_address'] = self.request.client_ip
        request['client_user_agent'] = self.request.client_ua
        request['admin_fiscal_code'] = fiscal_code
        return accreditation(request)


class GetAllAccreditationHandler(BaseHandler):
    """
    This manager is responsible for receiving accreditation requests and forwarding them to the accreditation manager
    """
    check_roles = 'any'
    root_tenant_only = True
    invalidate_cache = True

    def get(self):
        return get_all_accreditation()


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
        data = json.loads(payload) if not (payload == '' or payload is None) else {}
        return update_accreditation_by_id(accreditation_id, data)


class AccreditationConfirmHandler(BaseHandler):
    pass


class AccreditationRejectHandler(BaseHandler):
    check_roles = 'any'
    root_tenant_only = True
    invalidate_cache = True

    def delete(self, accreditation_id: str):
        return delete_accreditation_by_id(accreditation_id)
