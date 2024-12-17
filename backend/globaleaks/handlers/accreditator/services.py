import logging
from sqlalchemy.exc import NoResultFound

from globaleaks.handlers.accreditator.fw_mail import send_email_request_accreditation, \
    send_alert_accreditor_incoming_request, send_email_accreditation_user
from globaleaks.models.config import ConfigFactory
from globaleaks.handlers.accreditator.utils import add_users_id_to_subscriber, is_call_from_instructor, \
    create_tenant, save_step, count_user_tip, \
    serialize_element, accreditation_by_id, determine_type, revert_tenant, _change_status, find_mail_for_persistent_drop
from globaleaks.models import Subscriber, Tenant, EnumSubscriberStatus
from globaleaks.orm import transact
from uuid import uuid4
from globaleaks.utils.log import log
from globaleaks.rest import errors
from globaleaks.db.appdata import load_appdata
from globaleaks.handlers.wizard import db_wizard
from twisted.internet.threads import deferToThread
from globaleaks.db import sync_refresh_tenant_cache
from globaleaks.utils.crypto import generateRandomPassword
from globaleaks import models
from globaleaks.handlers.admin.tenant import db_initialize_tenant_submission_statuses



@transact
def accreditation(session, request, is_instructor=False):
    """
    Process an accreditation request.
    Args:
        session: The database session.
        request: The accreditation request data.
        is_instructor: is a request of instructor
    Returns:
        A dictionary containing the new subscriber's sharing ID.
    Raises:
        InternalServerError: If the accreditation process fails.
    """
    try:
        request['name'] = request.get('admin_name', '')
        request['surname'] = request.get('admin_surname', '')
        request['email'] = request.get('admin_email', '')
        request['organization_institutional_site'] = request.get('organization_institutional_site')
        sub = Subscriber(request)
        sub.language = ''
        sub.subdomain = str(uuid4())
        sub.state = is_call_from_instructor(is_instructor)
        sub.organization_location = ''

        t = create_tenant()
        save_step(session, t)

        sub.tid = t.id
        save_step(session, sub)

        sub.subdomain = sub.id

        save_step(session, sub)
        try:
            send_email_request_accreditation(
                session=session,
                language='en',
                accreditation_item=sub
            )

            send_alert_accreditor_incoming_request(
                session=session,
                language='en',
                accreditation_item=sub
            )
        except Exception as e:
            logging.debug(e)

        return {'id': sub.id}
    except Exception as e:
        log.err(f"Error: Accreditation Fail: {e}")
        raise errors.InternalServerError

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
            element = serialize_element(accreditation_item, count_tip.get('open', 0), count_user, t)
            element['closed_tips'] = count_tip.get('closed', 0)
            request_accreditation.append(element)
        return request_accreditation
    except Exception as e:
        log.err(f"Error: Accreditation Fail: {e}")
        raise errors.InternalServerError

@transact
def persistent_drop(session, accreditation_id: str, request):
    try:
        accreditation_item = accreditation_by_id(session, accreditation_id)
        aux_acc = (
            session.query(Subscriber)
            .filter(Subscriber.organization_name.isnot(None))
            .filter(Subscriber.id == accreditation_id)
            .one()
        )
        status = accreditation_item.get('state')
        status = status if isinstance(status, str) else EnumSubscriberStatus(status).name
        status_mapping = {
            'requested': EnumSubscriberStatus.requested,
            'suspended': EnumSubscriberStatus.suspended,
            'instructor_request': EnumSubscriberStatus.instructor_request,
            'accredited': EnumSubscriberStatus.accredited
        }
        if status not in status_mapping:
            raise errors.ForbiddenOperation
        elif status in ['suspended', 'accredited']  and accreditation_item.get('num_user_profiled') > 2 and accreditation_item.get('opened_tips') > 0:
            raise errors.ForbiddenOperation
        else:
            tenant_item = (
                session.query(Tenant)
                .join(Subscriber, Tenant.id == Subscriber.tid)
                .filter(Subscriber.id == accreditation_id)
                .one()
            )
            session.delete(tenant_item)
            try:
                send_email_request_accreditation(
                    session,
                    'en',
                    accreditation_item=aux_acc,
                    notify_email=[find_mail_for_persistent_drop(session, status=status, accreditation_obj=aux_acc)],
                    motivation_text=request['motivation_text']
                )
            except Exception as e:
                logging.debug(e)
        return {'id': accreditation_item.get('id')}
    except NoResultFound:
        log.err(f"Error: Accreditation with ID {accreditation_id} not found")
        raise errors.ResourceNotFound
    except Exception as e:
        log.err(f"Error: Accreditation Fail: {e}")
        raise errors.InternalServerError

@transact
def get_accreditation_by_id(session, accreditation_id):
    return accreditation_by_id(session, accreditation_id)

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
            .filter(Subscriber.organization_name.isnot(None), Subscriber.id == accreditation_id)
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
        return {'id': accreditation_item.id}
    except NoResultFound:
        log.error(f"Error: Accreditation with ID {accreditation_id} not found")
        raise errors.ResourceNotFound
    except Exception as e:
        log.err(f"Error: Accreditation Fail: {e}")
        raise errors.InternalServerError

@transact
def toggle_status_activate(session, accreditation_id: str, is_toggle=False):
    accreditation_item = (
        session.query(Subscriber)
        .filter(Subscriber.id == accreditation_id)
        .one()
    )
    status = accreditation_item.state if isinstance(accreditation_item.state, str) else EnumSubscriberStatus(
        accreditation_item.state).name

    if not is_toggle:
        status_mapping = {
            'requested': EnumSubscriberStatus.approved,
            'instructor_request': EnumSubscriberStatus.invited,
            'invited': EnumSubscriberStatus.invited

        }
    else:
        status_mapping = {
            'accredited': EnumSubscriberStatus.suspended,
            'suspended': EnumSubscriberStatus.accredited,
        }

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

@transact
def activate_tenant(session, accreditation_id, request):
    """
    Activate a tenant based on the accreditation ID.

    Args:
        session: The database session.
        accreditation_id: The ID of the accreditation to activate.
        request: dict of input request

    Returns:
        A dictionary containing the activated accreditation's sharing ID.
    """
    config_element = ConfigFactory(session, 1)
    accreditation_item = (
        session.query(Subscriber)
        .filter(Subscriber.organization_name.isnot(None))
        .filter(Subscriber.id == accreditation_id)
        .one()
    )
    status = accreditation_item.state if isinstance(accreditation_item.state, str) else EnumSubscriberStatus(
        accreditation_item.state).name

    if status !=  EnumSubscriberStatus.approved.name:
        raise errors.ResourceNotFound

    accreditation_item.activation_token = None
    t = (session.query(Tenant).filter(Tenant.id == accreditation_item.tid).one())
    mode = config_element.get_val('mode')
    language = config_element.get_val('default_language')
    appdata = load_appdata()

    models.config.initialize_config(session, t.id, mode)
    models.config.add_new_lang(session, t.id, language, appdata)
    db_initialize_tenant_submission_statuses(session, t.id)

    t.active = True
    accreditation_item.tos2 = str(request['tos2'])

    wizard = {
        'node_language': language,
        'node_name': accreditation_item.organization_name,
        'admin_username': 'admin',
        'admin_name': f"{accreditation_item.name} {accreditation_item.surname}",
        'admin_password': generateRandomPassword(16),
        'admin_mail_address': accreditation_item.email,
        'admin_tax_code': accreditation_item.tax_code,
        'admin_escrow': config_element.get_val('escrow'),
        'receiver_username': 'recipient',
        'receiver_name': f"{accreditation_item.recipient_name} {accreditation_item.recipient_surname}",
        'receiver_password': generateRandomPassword(16),
        'receiver_mail_address': accreditation_item.recipient_email,
        'receiver_tax_code': accreditation_item.recipient_tax_code,
        'profile': 'default',
        'skip_admin_account_creation': False,
        'skip_recipient_account_creation': False,
        'enable_developers_exception_notification': True
    }
    db_wizard(session, accreditation_item.tid, '', wizard)
    add_users_id_to_subscriber(session, accreditation_item)
    deferToThread(sync_refresh_tenant_cache, t)
    send_email_request_accreditation(
        session,
        language,
        accreditation_item,
        notify_email=[{"email": accreditation_item.organization_email, "secondary_smtp": True}]
    )
    send_email_accreditation_user(
        session=session,
        emails=[accreditation_item.email],
        language=language,
        accreditation_item=accreditation_item,
        wizard=wizard,
        is_admin = True
    )
    send_email_accreditation_user(
        session,
        [accreditation_item.recipient_email],
        language,
        accreditation_item,
        wizard
    )
    accreditation_item.state = EnumSubscriberStatus.accredited.value
    return {'id': accreditation_item.id}

@transact
def from_invited_to_request(session, request, accreditation_id: str):
    try:
        accreditation_item = (
            session.query(Subscriber)
            .filter(Subscriber.id == accreditation_id)
            .one()
        )
        accreditation_item.organization_name = request.get('organization_name')
        accreditation_item.organization_email = request.get('organization_email')
        accreditation_item.organization_institutional_site = request.get('organization_institutional_site')
        accreditation_item.name = request.get('admin_name')
        accreditation_item.surname = request.get('admin_surname')
        accreditation_item.email = request.get('admin_email')
        accreditation_item.tax_code = request.get('admin_tax_code')
        accreditation_item.recipient_name = request.get('recipient_name')
        accreditation_item.recipient_surname = request.get('recipient_surname')
        accreditation_item.recipient_email = request.get('recipient_email')
        accreditation_item.recipient_tax_code = request.get('recipient_tax_code')
        accreditation_item.tos1 = request.get('tos1', False)
        accreditation_item.tos2 = request.get('tos2', False)
        accreditation_item.state = EnumSubscriberStatus.requested.name
        save_step(session, accreditation_item)
        try:
            send_alert_accreditor_incoming_request(
                session=session,
                language='en',
                accreditation_item=accreditation_item
            )
        except Exception as e:
            logging.debug(e)
        return {'id': accreditation_item.id}
    except Exception as e:
        log.err(f"Error: Accreditation Fail: {e}")
        raise errors.InternalServerError