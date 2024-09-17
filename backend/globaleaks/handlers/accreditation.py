import json
from uuid import uuid4

from sqlalchemy import func, distinct
from sqlalchemy.exc import NoResultFound
from twisted.internet.threads import deferToThread

from globaleaks import models
from globaleaks.db import sync_refresh_tenant_cache
from globaleaks.db.appdata import load_appdata
from globaleaks.handlers.admin.node import db_admin_serialize_node
from globaleaks.handlers.admin.notification import db_get_notification
from globaleaks.handlers.admin.tenant import db_initialize_tenant_submission_statuses
from globaleaks.handlers.base import BaseHandler
from globaleaks.handlers.wizard import db_wizard
from globaleaks.models import Subscriber, Tenant, EnumSubscriberStatus, config, InternalTip, InternalTipForwarding, \
    User, serializers
from globaleaks.models.config import ConfigFactory
from globaleaks.orm import transact
from globaleaks.rest import requests, errors
from globaleaks.state import State
from globaleaks.utils.crypto import generateRandomKey, generateRandomPassword
from globaleaks.utils.log import log


def create_tenant():
    t = Tenant()
    t.active = False
    t.external = True
    return t


def save_step(session, obj):
    session.add(obj)
    session.flush()


def send_email(session, email: list, language, accreditation_item, wizard):
    for user_desc in email:
        template_vars = {
            'type': 'activation',
            'node': db_admin_serialize_node(session, 1, language),
            'notification': db_get_notification(session, 1, language),
            'signup': serializers.serialize_signup(accreditation_item),
            'password_admin': wizard['admin_password'],
            'password_recipient': wizard['receiver_password']
        }

        State.format_and_send_mail(session, 1, user_desc, template_vars)


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
        .filter(User.mail_address.notin_([accreditation_item.email, accreditation_item.admin_email]))
        .one()
    )
    return count_tip, count_user


def add_user_primary(session, accreditation_item, dict_element):
    dict_element['organization_email'] = accreditation_item.organization_email
    dict_element['organization_institutional_site'] = accreditation_item.organization_institutional_site
    dict_element['admin_name'] = accreditation_item.admin_name
    dict_element['admin_surname'] = accreditation_item.admin_surname
    dict_element['admin_fiscal_code'] = accreditation_item.admin_fiscal_code
    dict_element['admin_email'] = accreditation_item.admin_email
    dict_element['recipient_name'] = accreditation_item.name
    dict_element['recipient_surname'] = accreditation_item.surname
    dict_element['recipient_fiscal_code'] = accreditation_item.recipient_fiscal_code
    dict_element['recipient_email'] = accreditation_item.email
    dict_element['tos1'] = accreditation_item.tos1
    dict_element['tos2'] = accreditation_item.tos2
    dict_element['closed_tips'] = 0
    return dict_element


def extract_user(session, accreditation_item):
    user_list = []
    query = (session.query(User)
             .filter(User.tid == accreditation_item.tid)
             .filter(User.mail_address.notin_([accreditation_item.email, accreditation_item.admin_email]))
             ).all()
    for user in query:
        user_list.append(
            {
                'id': user.id,
                'name': user.name,
                'surname': None,
                'email': user.mail_address,
                'fiscal_code': None,
                'role': user.role,
                'creation_date': user.creation_date,
                'last_access': user.last_login,
                'assigned_tips': 0,
                'closed_tips': 0
            }
        )
    return user_list


def serialize_element(accreditation_item, count_tip, count_user, t):
    return {
        'id': accreditation_item.sharing_id,
        'organization_name': accreditation_item.organization_name,
        'type': "NOT_AFFILIATED" if t.affiliated is None or t.affiliated == '' else t.affiliated.upper(),
        'accreditation_date': accreditation_item.creation_date,
        'state': accreditation_item.state if isinstance(accreditation_item.state, str) else EnumSubscriberStatus(
            accreditation_item.state).name,
        'num_user_profiled': list(count_user)[0] + 2,
        'opened_tips': list(count_tip)[0]
    }


@transact
def get_all_accreditation(session):
    try:
        request_accreditation = []
        for accreditation_item in (session.query(Subscriber).filter(Subscriber.organization_name.isnot(None))):
            t = (session.query(Tenant).filter(Tenant.id == accreditation_item.tid).one())
            count_tip, count_user = count_user_tip(session, accreditation_item)
            element = serialize_element(accreditation_item, count_tip, count_user, t)
            element['closed_tips'] = 0
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
        element = add_user_primary(session, accreditation_item, element)
        element['users'] = extract_user(session, accreditation_item)
        return element
    except NoResultFound:
        log.error(f"Error: Accreditation with ID {accreditation_id} not found")
        raise errors.ResourceNotFound
    except Exception as e:
        log.err(f"Error: Accreditation Fail: {e}")
        raise errors.InternalServerError


@transact
def activate_tenant(session, accreditation_id):
    config_element = ConfigFactory(session, 1)
    accreditation_item = (
        session.query(Subscriber)
        .filter(Subscriber.organization_name.isnot(None))
        .filter(Subscriber.sharing_id == accreditation_id)
        .one()
    )
    accreditation_item.activation_token = generateRandomKey()
    t = (session.query(Tenant).filter(Tenant.id == accreditation_item.tid).one())
    mode = config_element.get_val('mode')
    language = config_element.get_val('default_language')
    appdata = load_appdata()
    models.config.initialize_config(session, t.id, mode)
    models.config.add_new_lang(session, t.id, language, appdata)
    db_initialize_tenant_submission_statuses(session, t.id)
    t.active = True
    accreditation_item.activation_token = generateRandomKey()
    password_admin = generateRandomPassword(16)
    password_receiver = generateRandomPassword(16)
    node_name = accreditation_item.organization_name
    wizard = {
        'node_language': language,
        'node_name': node_name,
        'admin_username': 'admin',
        'admin_name': accreditation_item.admin_name + ' ' + accreditation_item.admin_surname,
        'admin_password': password_admin,
        'admin_mail_address': accreditation_item.admin_email,
        'admin_escrow': config_element.get_val('escrow'),
        'receiver_username': 'recipient',
        'receiver_name': accreditation_item.name + ' ' + accreditation_item.surname,
        'receiver_password': password_receiver,
        'receiver_mail_address': accreditation_item.email,
        'profile': 'default',
        'skip_admin_account_creation': False,
        'skip_recipient_account_creation': False,
        'enable_developers_exception_notification': True
    }
    db_wizard(session, accreditation_item.tid, '', wizard)
    deferToThread(sync_refresh_tenant_cache, t)
    """
    send_email(
        session, 
        [accreditation_item.admin_email, accreditation_item.email], 
        language, 
        accreditation_item,
        wizard
    )
    """
    accreditation_item.state = 1
    return {'id': accreditation_item.sharing_id}


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
    """
    This manager is responsible for confirm accreditation requests
    """
    check_roles = 'any'
    root_tenant_only = True

    def post(self, accreditation_id: str):
        return activate_tenant(accreditation_id)


class AccreditationRejectHandler(BaseHandler):
    check_roles = 'any'
    root_tenant_only = True
    invalidate_cache = True

    def delete(self, accreditation_id: str):
        return delete_accreditation_by_id(accreditation_id)
