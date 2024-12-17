import logging
from typing import Dict, Optional

from sqlalchemy.exc import NoResultFound

from globaleaks.handlers.accreditator.fw_mail import send_email_request_approved
from globaleaks.utils.log import log
from globaleaks.models import Tenant, User, InternalTipForwarding, Subscriber, EnumSubscriberStatus
from globaleaks.rest import errors
from sqlalchemy import func, distinct, or_

def create_tenant():
    """Create a new inactive, external tenant."""
    t = Tenant()
    t.active = False
    t.external = True
    return t

def revert_tenant(session, accreditation_id: str):
    """
    Toggles the activation status of a Tenant object associated with a given accreditation_id.

    Args:
        session: The database session (typically an instance of SQLAlchemy Session) used to execute the query.
        accreditation_id (str): The accreditation ID used to filter the corresponding Subscriber.

    Raises:
        sqlalchemy.orm.exc.NoResultFound: If no Tenant is found associated with the provided accreditation_id.
        sqlalchemy.orm.exc.MultipleResultsFound: If more than one Tenant is found associated with the provided accreditation_id.
    """
    t = (
        session.query(Tenant)
        .join(Subscriber, Tenant.id == Subscriber.tid)
        .filter(Subscriber.id == accreditation_id)
        .one()
    )
    t.active = not t.active

def save_step(session, obj):
    """Save an object to the database session and flush changes."""
    session.add(obj)
    session.flush()

def is_call_from_instructor(from_request: bool) -> str:
    """is_instructor: is a request of instructor"""
    if from_request:
        return EnumSubscriberStatus.instructor_request.name
    return EnumSubscriberStatus.requested.name

def count_user_tip(session, accreditation_item: Subscriber):
    """
    Count the number of tips and users for a given accreditation item.
    Args:
        session: The database session.
        accreditation_item: The Subscriber object.
    Returns:
        A tuple containing the count of tips and users.
    """
    status = accreditation_item.state if isinstance(accreditation_item.state, str) else EnumSubscriberStatus(
        accreditation_item.state).name
    if status != EnumSubscriberStatus.accredited.name:
        return {}, 2
    count_user = (
        session.query(
            func.count(distinct(User.id))
        )
        .filter(User.tid == accreditation_item.tid)
        .scalar()
    )
    count_tip = (
        session.query(
            InternalTipForwarding.state,
            func.count(distinct(InternalTipForwarding.id))
        )
        .filter(InternalTipForwarding.tid == accreditation_item.tid)
        .group_by(InternalTipForwarding.state)
        .all()
    )
    return dict(count_tip), count_user

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
        'id': accreditation_item.id,
        'organization_name': accreditation_item.organization_name,
        'organization_institutional_site': accreditation_item.organization_institutional_site,
        'type': "AFFILIATED" if t.affiliated else 'NOT_AFFILIATED',
        'accreditation_date': accreditation_item.creation_date,
        'state': accreditation_item.state if isinstance(accreditation_item.state, str) else EnumSubscriberStatus(
            accreditation_item.state).name,
        'num_user_profiled': count_user,
        'opened_tips': count_tip
    }

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
        'admin_name': accreditation_item.name,
        'admin_surname': accreditation_item.surname,
        'admin_tax_code': accreditation_item.tax_code,
        'admin_email': accreditation_item.email,
        'recipient_name': accreditation_item.recipient_name,
        'recipient_surname': accreditation_item.recipient_surname,
        'recipient_tax_code': accreditation_item.recipient_tax_code,
        'recipient_email': accreditation_item.recipient_email,
        'tos1': accreditation_item.tos1,
        'tos2': accreditation_item.tos2
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
             .filter(User.mail_address.notin_([accreditation_item.email, accreditation_item.recipient_email]))).all()
    return [
        {
            'id': user.id,
            'name': user.name,
            'surname': None,
            'email': user.mail_address,
            'idp_id': None,
            'role': user.role,
            'creation_date': user.creation_date,
            'last_access': user.last_login,
            'assigned_tips': 0,
            'closed_tips': 0
        }
        for user in query
    ]

def add_instructor_info(session, accreditation_item):
    """
    Extract instructor user information for a given accreditation item, if exists.

    Args:
        session: The database session.
        accreditation_item: The Subscriber object.

    Returns:
        A dictionaries containing instructor user information, if exists else None
    """
    if not accreditation_item.requestor_id:
        return None
    try:
        user = (session.query(User).filter(User.id == accreditation_item.requestor_id)).one_or_none()
        return {
            'id': user.id,
            'username': user.username
        }
    except Exception as e:
        logging.debug(e)
        return None

def find_mail_for_persistent_drop(session, status, accreditation_obj) -> dict:
    if status == EnumSubscriberStatus.instructor_request.name and accreditation_obj.requestor_id:
        user = (session.query(User).filter(User.id == accreditation_obj.requestor_id)).one_or_none()
        if user.mail_address:
            return {"email": user.mail_address, "secondary_smtp": False}
    return {"email": accreditation_obj.organization_email, "secondary_smtp": True}

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
            .filter(Subscriber.id == accreditation_id)
            .one()
        )
        t = (
            session.query(Tenant)
            .filter(Tenant.id == accreditation_item.tid)
            .one()
        )
        count_tip, count_user = count_user_tip(session, accreditation_item)
        element = serialize_element(accreditation_item, count_tip.get('open', 0), count_user, t)
        element = add_user_primary(accreditation_item, element)
        element['closed_tips'] = count_tip.get('closed', 0)
        element['users'] = extract_user(session, accreditation_item)
        element['requestor_id'] = add_instructor_info(session, accreditation_item)
        return element
    except NoResultFound:
        logging.debug(f"Error: Accreditation with ID {accreditation_id} not found")
        raise errors.ResourceNotFound
    except Exception as e:
        log.err(f"Error: Accreditation Fail: {e}")
        raise errors.InternalServerError

def determine_type(data: Dict[str, Optional[any]]) -> bool:
    type_value = data.get('type')
    return (
            isinstance(type_value, bool) and type_value or
            isinstance(type_value, str) and type_value.upper() == 'AFFILIATED'
    )

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
            .filter(Subscriber.id == accreditation_id)
            .filter(
                or_(
                    Subscriber.state == from_status,
                    Subscriber.state == EnumSubscriberStatus[from_status].value
                )
            )
            .one()
        )
        accreditation_item.state = to_status
        if to_status in [EnumSubscriberStatus['approved'].value, EnumSubscriberStatus['invited'].value]:
            send_email_request_approved(
                session=session,
                language='en',
                accreditation_item=accreditation_item
            )
        return {'id': accreditation_item.id}
    except NoResultFound:
        log.err(f"Error: Accreditation with ID {accreditation_id} not found")
        raise errors.ResourceNotFound
    except Exception as e:
        log.err(f"Error: Accreditation Fail: {e}")
        raise errors.InternalServerError

def add_users_id_to_subscriber(session, accreditation_item):
    """
    Updates the subscriber object setting admin's and recipient's id.

    Args:
        session: The database session.
        accreditation_item: The Subscriber object.

    Returns:
        dict: A dictionary containing the `id` of the subscriber whose status was successfully updated.
    """
    admin_user = (session.query(User)
             .filter(User.tid == accreditation_item.tid)
             .filter(User.mail_address == accreditation_item.email)
             .filter(User.role == 0)).one_or_none()
    recipient_user = (session.query(User)
             .filter(User.tid == accreditation_item.tid)
             .filter(User.mail_address == accreditation_item.recipient_email)
             .filter(User.role == 1)).one_or_none()
    if admin_user:
        accreditation_item.user_id = admin_user.id
    if recipient_user:
        accreditation_item.recipient_user_id = recipient_user.id

    return accreditation_item