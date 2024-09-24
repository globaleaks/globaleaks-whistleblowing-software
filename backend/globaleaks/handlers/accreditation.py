import json
from typing import Dict, Optional
from uuid import uuid4

from sqlalchemy import func, distinct, or_
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
    """Create a new inactive, external tenant."""
    t = Tenant()
    t.active = False
    t.external = True
    return t


def revert_tenant(session, accreditation_id: str):
    t = (
        session.query(Tenant)
        .join(Subscriber, Tenant.id == Subscriber.tid)  # Correzione join tra Tenant e Subscriber
        .filter(Subscriber.sharing_id == accreditation_id)  # Corretto 'fileter' in 'filter'
        .one()
    )
    t.active = not t.active


@transact
def toggle_status_activate(session, accreditation_id: str, is_toggle=False):
    accreditation_item = (
        session.query(Subscriber)
        .filter(Subscriber.sharing_id == accreditation_id)
        .one()
    )
    status = accreditation_item.state if isinstance(accreditation_item.state, str) else EnumSubscriberStatus(
        accreditation_item.state).name

    status_mapping = {
        'accredited': EnumSubscriberStatus.suspended,
        'suspended': EnumSubscriberStatus.accredited,
    }
    if not is_toggle:
        status_mapping['requested'] = EnumSubscriberStatus.approved

    if status not in status_mapping:
        raise errors.ForbiddenOperation

    if is_toggle:
        revert_tenant(session, accreditation_id)

    return _change_status(
        session,
        accreditation_id,
        status,
        status_mapping[status].value
    )


def save_step(session, obj):
    """Save an object to the database session and flush changes."""
    session.add(obj)
    session.flush()


def send_email(session, emails: list, language, accreditation_item, wizard):
    """
    Send activation emails to the provided email addresses.

    Args:
        session: The database session.
        emails: List of email addresses to send to.
        language: The language for the email content.
        accreditation_item: The Subscriber object.
        wizard: Dictionary containing setup information.
    """
    node = db_admin_serialize_node(session, 1, language)
    notification = db_get_notification(session, 1, language)
    signup = serializers.serialize_signup(accreditation_item)

    template_vars = {
        'type': 'activation',
        'node': node,
        'notification': notification,
        'signup': signup,
        'password_admin': wizard['admin_password'],
        'password_recipient': wizard['receiver_password']
    }

    for email in emails:
        State.format_and_send_mail(session, 1, email, template_vars)


@transact
def accreditation(session, request):
    """
    Process an accreditation request.

    Args:
        session: The database session.
        request: The accreditation request data.

    Returns:
        A dictionary containing the new subscriber's sharing ID.

    Raises:
        InternalServerError: If the accreditation process fails.
    """
    try:
        request['name'] = request['recipient_name']
        request['surname'] = request['recipient_surname']
        request['email'] = request['recipient_email']
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
    """
    Count the number of tips and users for a given accreditation item.

    Args:
        session: The database session.
        accreditation_item: The Subscriber object.

    Returns:
        A tuple containing the count of tips and users.
    """
    count_tip = (
        session.query(func.count(distinct(InternalTipForwarding.id)))
        .filter(InternalTipForwarding.oe_internaltip_id == accreditation_item.tid)
        .scalar()
    )
    count_user = (
        session.query(
            func.count(distinct(User.id))
        )
        .filter(User.tid == accreditation_item.tid)
        .filter(User.mail_address.notin_([accreditation_item.email, accreditation_item.admin_email]))
        .scalar()
    )
    return count_tip, count_user


def add_user_primary(accreditation_item, dict_element):
    """
    Add primary user information to the dictionary element.

    Args:
        accreditation_item: The Subscriber object.
        dict_element: The dictionary to update.

    Returns:
        The updated dictionary.
    """
    dict_element.update({
        'organization_email': accreditation_item.organization_email,
        'organization_institutional_site': accreditation_item.organization_institutional_site,
        'admin_name': accreditation_item.admin_name,
        'admin_surname': accreditation_item.admin_surname,
        'admin_fiscal_code': accreditation_item.admin_fiscal_code,
        'admin_email': accreditation_item.admin_email,
        'recipient_name': accreditation_item.name,
        'recipient_surname': accreditation_item.surname,
        'recipient_fiscal_code': accreditation_item.recipient_fiscal_code,
        'recipient_email': accreditation_item.email,
        'tos1': accreditation_item.tos1,
        'tos2': accreditation_item.tos2,
        'closed_tips': 0
    })
    return dict_element


def extract_user(session, accreditation_item):
    """
    Extract user information for a given accreditation item.

    Args:
        session: The database session.
        accreditation_item: The Subscriber object.

    Returns:
        A list of dictionaries containing user information.
    """
    query = (session.query(User)
             .filter(User.tid == accreditation_item.tid)
             .filter(User.mail_address.notin_([accreditation_item.email, accreditation_item.admin_email])))
    return [
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
        for user in query
    ]


def serialize_element(accreditation_item, count_tip, count_user, t):
    """
    Serialize an accreditation item into a dictionary.

    Args:
        accreditation_item: The Subscriber object.
        count_tip: The number of tips.
        count_user: The number of users.
        t: The Tenant object.

    Returns:
        A dictionary containing serialized accreditation information.
    """
    return {
        'id': accreditation_item.sharing_id,
        'organization_name': accreditation_item.organization_name,
        'type': "AFFILIATED" if t.affiliated else 'NOT_AFFILIATED',
        'accreditation_date': accreditation_item.creation_date,
        'state': accreditation_item.state if isinstance(accreditation_item.state, str) else EnumSubscriberStatus(
            accreditation_item.state).name,
        'num_user_profiled': count_user + 2,
        'opened_tips': count_tip
    }


@transact
def get_all_accreditation(session):
    """
    Retrieve all accreditation items.

    Args:
        session: The database session.

    Returns:
        A list of dictionaries containing accreditation information.

    Raises:
        InternalServerError: If the retrieval process fails.
    """
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


def determine_type(data: Dict[str, Optional[str]]) -> bool:
    type_value = data.get('type')
    return (
            isinstance(type_value, bool) and type_value or
            isinstance(type_value, str) and type_value.upper() == 'AFFILIATED'
    )


@transact
def update_accreditation_by_id(session, accreditation_id, data: dict = None):
    """
    Update an accreditation item by its ID.

    Args:
        session: The database session.
        accreditation_id: The ID of the accreditation to update.
        data: A dictionary containing the fields to update.

    Returns:
        A dictionary containing the updated accreditation's sharing ID.

    Raises:
        ResourceNotFound: If the accreditation item is not found.
        InternalServerError: If the update process fails.
    """
    data = data or {}
    try:
        accreditation_item = (
            session.query(Subscriber)
            .filter(Subscriber.organization_name.isnot(None), Subscriber.sharing_id == accreditation_id)
            .one()
        )
        if accreditation_item.state == EnumSubscriberStatus.requested.name:
            updated_fields = ['organization_name', 'organization_email', 'organization_institutional_site']
            for key, value in data.items():
                if key in updated_fields:
                    setattr(accreditation_item, key, value)
        if 'type' in data:
            tenant = session.query(Tenant).filter(Tenant.id == accreditation_item.tid).one()
            tenant.affiliated = determine_type(data)
        return {'id': accreditation_item.sharing_id}
    except NoResultFound:
        log.error(f"Error: Accreditation with ID {accreditation_id} not found")
        raise errors.ResourceNotFound
    except Exception as e:
        log.err(f"Error: Accreditation Fail: {e}")
        raise errors.InternalServerError


@transact
def persistent_drop(session, accreditation_id: str):
    try:
        accreditation_item = accreditation_by_id(session, accreditation_id)
        status = accreditation_item.get('state')
        status = status if isinstance(status, str) else EnumSubscriberStatus(status).name
        status_mapping = {
            'requested': EnumSubscriberStatus.requested,
            'suspended': EnumSubscriberStatus.suspended,
            'instructor_request': EnumSubscriberStatus.instructor_request
        }
        if status not in status_mapping:
            raise errors.ForbiddenOperation
        elif status == 'suspended' and accreditation_item.get('num_user_profiled') > 1 and accreditation_item.get('opened_tips') > 0:
            raise errors.ForbiddenOperation
        else:
            tenant_item = (
                session.query(Tenant)
                .join(Subscriber, Tenant.id == Subscriber.tid)  # Correzione join tra Tenant e Subscriber
                .filter(Subscriber.sharing_id == accreditation_id)  # Corretto 'fileter' in 'filter'
                .one()
            )
            session.delete(tenant_item)
        return {'id': accreditation_item.get('id')}
    except NoResultFound:
        log.err(f"Error: Accreditation with ID {accreditation_id} not found")
        raise errors.ResourceNotFound
    except Exception as e:
        log.err(f"Error: Accreditation Fail: {e}")
        raise errors.InternalServerError


def _change_status(session, accreditation_id: str, from_status: str, to_status: int):
    """
    Updates the accreditation status of a subscriber in the database.

    This function searches for a subscriber with the given `accreditation_id` and current
    status `from_status`. If found, it updates the subscriber's status (`state`) to `to_status`.
    If no subscriber is found or an error occurs, appropriate exceptions are raised.

    Parameters:
        session (Session): The current database session used to query and commit changes.
        accreditation_id (str): The unique identifier of the accreditation whose status is to be updated.
        from_status (str): The current status of the accreditation. The update will only occur if this matches.
        to_status (int): The new status value to which the accreditation will be updated.

    Returns:
        dict: A dictionary containing the `id` of the subscriber whose status was successfully updated.

    Raises:
        ResourceNotFound: Raised if no subscriber with the given `accreditation_id` and `from_status` is found.
        InternalServerError: Raised if any other error occurs during the process.

    Exceptions:
        NoResultFound: Raised when the query does not find a matching subscriber.
        Exception: Generic exceptions are caught, logged, and raise an `InternalServerError`.
    """
    try:
        accreditation_item = (
            session.query(Subscriber)
            .filter(Subscriber.organization_name.isnot(None))
            .filter(Subscriber.sharing_id == accreditation_id)
            .filter(
                or_(
                    Subscriber.state == from_status,
                    Subscriber.state == EnumSubscriberStatus[from_status].value
                )
            )
            .one()
        )
        accreditation_item.state = to_status
        return {'id': accreditation_item.sharing_id}
    except NoResultFound:
        log.err(f"Error: Accreditation with ID {accreditation_id} not found")
        raise errors.ResourceNotFound
    except Exception as e:
        log.err(f"Error: Accreditation Fail: {e}")
        raise errors.InternalServerError


@transact
def get_accreditation_by_id(session, accreditation_id):
    return accreditation_by_id(session, accreditation_id)


def accreditation_by_id(session, accreditation_id):
    """
    Retrieve an accreditation item by its ID.

    Args:
        session: The database session.
        accreditation_id: The ID of the accreditation to retrieve.

    Returns:
        A dictionary containing the accreditation information.

    Raises:
        ResourceNotFound: If the accreditation item is not found.
        InternalServerError: If the retrieval process fails.
    """
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
        element = add_user_primary(accreditation_item, element)
        element['users'] = extract_user(session, accreditation_item)
        return element
    except NoResultFound:
        log.err(f"Error: Accreditation with ID {accreditation_id} not found")
        raise errors.ResourceNotFound
    except Exception as e:
        log.err(f"Error: Accreditation Fail: {e}")
        raise errors.InternalServerError


@transact
def activate_tenant(session, accreditation_id):
    """
    Activate a tenant based on the accreditation ID.

    Args:
        session: The database session.
        accreditation_id: The ID of the accreditation to activate.

    Returns:
        A dictionary containing the activated accreditation's sharing ID.
    """
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

    wizard = {
        'node_language': language,
        'node_name': accreditation_item.organization_name,
        'admin_username': 'admin',
        'admin_name': f"{accreditation_item.admin_name} {accreditation_item.admin_surname}",
        'admin_password': generateRandomPassword(16),
        'admin_mail_address': accreditation_item.admin_email,
        'admin_escrow': config_element.get_val('escrow'),
        'receiver_username': 'recipient',
        'receiver_name': f"{accreditation_item.name} {accreditation_item.surname}",
        'receiver_password': generateRandomPassword(16),
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
    accreditation_item.state = EnumSubscriberStatus.accredited.value
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
        data = json.loads(payload) if payload else {}
        return update_accreditation_by_id(accreditation_id, data)

    def delete(self, accreditation_id: str):
        return persistent_drop(
            accreditation_id
        )

class AccreditationApprovedHandler(BaseHandler):
    """
    This manager is responsible for confirm accreditation requests
    """
    check_roles = 'any'
    root_tenant_only = True

    def post(self, accreditation_id: str):
        return toggle_status_activate(accreditation_id)

class AccreditationConfirmHandler(BaseHandler):
    """
    This manager is responsible for confirm accreditation requests
    """
    check_roles = 'any'
    root_tenant_only = True

    def post(self, accreditation_id: str):
        return activate_tenant(accreditation_id)


class ToggleStatusActiveHandler(BaseHandler):
    check_roles = 'any'
    root_tenant_only = True
    invalidate_cache = True

    def put(self, accreditation_id: str):
        return toggle_status_activate(accreditation_id, is_toggle=True)
