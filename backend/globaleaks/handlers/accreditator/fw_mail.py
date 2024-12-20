from globaleaks import models
from globaleaks.handlers.admin.node import db_admin_serialize_node
from globaleaks.handlers.admin.notification import db_get_notification
from globaleaks.models import serializers, EnumSubscriberStatus, EnumUserRole
from globaleaks.state import State

def send_email_accreditation_user(session, emails: list, language, accreditation_item, wizard, is_admin:bool = False):
    """
    Send activation emails to the provided email addresses.

    Args:
        session: The database session.
        emails: List of email addresses to send to.
        language: The language for the email content.
        accreditation_item: The Subscriber object.
        wizard: Dictionary containing setup information.
        is_admin: choose what template send
    """
    eo_uuid = session.query(models.Config).filter(models.Config.tid == accreditation_item.tid, models.Config.var_name == 'uuid').one_or_none()
    node = db_admin_serialize_node(session, 1, language)
    notification = db_get_notification(session, 1, language)
    signup = serializers.serialize_signup(accreditation_item)
    signup['recipient_name'] = accreditation_item.recipient_name
    signup['recipient_surname'] = accreditation_item.recipient_surname
    node['is_eo_admin'] = is_admin
    node['is_eo'] = True
    node['eo_uuid'] = eo_uuid.value if eo_uuid else ''
    admin_pwd = 'None' if not wizard or not wizard.get('admin_password') else wizard.get('admin_password')
    rec_pwd = 'None' if not wizard or not wizard.get('receiver_password') else wizard.get('receiver_password')
    template_vars = {
        'node': node,
        'notification': notification,
        'signup': signup
    }
    if is_admin:
        template_vars['type'] = 'new_user_admin_signup_external_organization_alert'
        template_vars['password_admin'] = admin_pwd
    else:
        template_vars['type'] = 'new_user_recipient_signup_external_organization_alert'
        template_vars['password_recipient'] = rec_pwd

    for email in emails:
        State.format_and_send_mail(session, 1, email, template_vars)

def send_email_request_accreditation(session, language, accreditation_item, notify_email = None, motivation_text=None):
    """
    Send activation emails to the provided email addresses.

    Args:
        session: The database session.
        language: The language for the email content.
        accreditation_item: The Subscriber object.
        notify_email: Email to
        motivation_text: notify motivation
    """
    node = db_admin_serialize_node(session, 1, language)
    notification = db_get_notification(session, 1, language)
    signup = serializers.serialize_signup(accreditation_item)
    status = accreditation_item.state
    signup['status'] = status if isinstance(status, str) else EnumSubscriberStatus(status).name
    signup['status'] = signup['status'] if not motivation_text else 'DELETED'
    signup['motivation_text'] = motivation_text
    template_vars = {
        'type': 'sign_up_external_organization_info',
        'node': node,
        'notification': notification,
        'signup': signup
    }
    if not notify_email:
        notify_email = [{"email": accreditation_item.organization_email, "secondary_smtp": True}]
    if accreditation_item.email:
        notify_email.append({"email": accreditation_item.email, "secondary_smtp": False})

    for notify in notify_email:
        secondary_smtp = True if notify.get('secondary_smtp') else False
        State.format_and_send_mail(session, 1, notify.get('email'), template_vars, secondary_smtp)


def send_email_request_approved(session, language, accreditation_item):
    """
    Send activation emails to the provided email addresses.

    Args:
        session: The database session.
        language: The language for the email content.
        accreditation_item: The Subscriber object.
    """
    node = db_admin_serialize_node(session, 1, language)
    notification = db_get_notification(session, 1, language)
    signup = serializers.serialize_signup(accreditation_item)
    status = accreditation_item.state
    signup['status'] = status if isinstance(status, str) else EnumSubscriberStatus(status).name
    template_vars = {
        'type': 'sign_up_external_organization',
        'node': node,
        'notification': notification,
        'signup': signup
    }
    for email in [accreditation_item.organization_email]:
        State.format_and_send_mail(session, 1, email, template_vars, secondary_smtp = True)

def send_alert_accreditor_incoming_request(session, language, accreditation_item):
    accreditor = (session.query(models.User.mail_address)
                  .filter(models.User.tid == 1)
                  .filter(models.User.role == EnumUserRole.accreditor.name)).all()
    accreditor_email = [user[0] for user in accreditor]
    notification = db_get_notification(session, 1, language)
    node = db_admin_serialize_node(session, 1, language)
    signup = serializers.serialize_signup(accreditation_item)
    status = accreditation_item.state
    signup['status'] = status if isinstance(status, str) else EnumSubscriberStatus(status).name
    template_vars = {
        'type': 'accreditor_signup_external_organization_alert',
        'node': node,
        'notification': notification,
        'signup': signup
    }
    for email in accreditor_email:
        State.format_and_send_mail(session, 1, email, template_vars)