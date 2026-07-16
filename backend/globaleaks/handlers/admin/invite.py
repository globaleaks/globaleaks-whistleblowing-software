from datetime import timedelta

from globaleaks import models
from globaleaks.handlers.admin.tenant import db_create as db_create_tenant
from globaleaks.handlers.admin.node import db_admin_serialize_node
from globaleaks.handlers.admin.notification import db_get_notification
from globaleaks.handlers.base import BaseHandler
from globaleaks.models.config import ConfigFactory
from globaleaks.models.enums import EnumSubscriberStatus
from globaleaks.orm import db_del
from globaleaks.orm import transact
from globaleaks.rest import requests, errors
from globaleaks.state import State
from globaleaks.utils.crypto import generateRandomKey
from globaleaks.utils.utility import datetime_now


INVITE_EXPIRATION = timedelta(hours=24)


def _invite_status(subscriber, tenant):
    if subscriber.activation_token is None and tenant.active:
        return 'accepted'
    if subscriber.state == EnumSubscriberStatus.rejected.value:
        return 'denied'
    if subscriber.state == EnumSubscriberStatus.invited.value and not _is_registered(subscriber):
        return 'invited'
    return 'pending'


def _is_registered(subscriber):
    return bool(subscriber.name or subscriber.surname)


def serialize_invite(subscriber, tenant):
    return {
        'id': subscriber.id,
        'token': subscriber.activation_token,
        'organization_name': subscriber.organization_name,
        'organization_tax_code': subscriber.organization_tax_code,
        'organization_vat_code': subscriber.organization_vat_code,
        'organization_location': subscriber.organization_location,
        'name': subscriber.name,
        'surname': subscriber.surname,
        'email': subscriber.email,
        'phone': subscriber.phone,
        'language': subscriber.language,
        'status': _invite_status(subscriber, tenant),
        'registered': _is_registered(subscriber),
        'tid': subscriber.tid,
        'creation_date': subscriber.creation_date,
        'registration_date': subscriber.registration_date,
        'expiration_date': subscriber.registration_date + INVITE_EXPIRATION,
        'acceptance_date': subscriber.accreditation_date
    }


def _registrations(session):
    return session.query(models.Subscriber, models.Tenant) \
                  .filter(models.Tenant.id == models.Subscriber.tid)


def _invited_subscribers(session):
    return _registrations(session) \
        .filter(models.Subscriber.state == EnumSubscriberStatus.invited.value)


def db_delete_expired_invites(session):
    expired = _invited_subscribers(session) \
        .filter(models.Subscriber.activation_token.isnot(None),
                models.Subscriber.state == EnumSubscriberStatus.invited.value,
                models.Subscriber.registration_date < datetime_now() - INVITE_EXPIRATION) \
        .all()

    if expired:
        db_del(session, models.Tenant, models.Tenant.id.in_([tenant.id for _, tenant in expired]))


@transact
def create_invite(session, request, language):
    db_delete_expired_invites(session)

    config = ConfigFactory(session, 1)
    token = generateRandomKey()
    tenant = db_create_tenant(session, {'active': False,
                                        'name': request['organization_name'],
                                        'subdomain': token,
                                        'mode': config.get_val('mode'),
                                        'profile': config.get_val('profile')})

    invite = models.Subscriber({
        'tid': tenant.id,
        'subdomain': token,
        'language': language,
        'name': '',
        'surname': '',
        'phone': '',
        'email': request['email'],
        'organization_name': request['organization_name'],
        'organization_tax_code': None,
        'organization_vat_code': None,
        'organization_location': '',
        'activation_token': token,
        'client_ip_address': '',
        'client_user_agent': '',
        'tos1': False,
        'tos2': False,
        'state': EnumSubscriberStatus.invited.value
    })

    session.add(invite)
    session.flush()

    template_vars = {
        'type': 'signup_invite',
        'invite': serialize_invite(invite, tenant),
        'node': db_admin_serialize_node(session, 1, language),
        'notification': db_get_notification(session, 1, language)
    }

    State.format_and_send_mail(session, 1, invite.email, template_vars)

    return serialize_invite(invite, tenant)


@transact
def get_invite(session, token):
    db_delete_expired_invites(session)

    ret = _invited_subscribers(session) \
        .filter(models.Subscriber.activation_token == token,
                models.Subscriber.state == EnumSubscriberStatus.invited.value) \
        .one_or_none()

    if ret is None:
        raise errors.ForbiddenOperation

    invite, tenant = ret

    return {
        'organization_name': invite.organization_name,
        'email': invite.email,
        'expiration_date': invite.registration_date + INVITE_EXPIRATION
    }


@transact
def db_get_invites(session):
    db_delete_expired_invites(session)
    return [serialize_invite(invite, tenant) for invite, tenant in _registrations(session)
                             .order_by(models.Subscriber.creation_date.desc())
                             .all()]


class InvitesCollection(BaseHandler):
    check_roles = 'admin'
    root_tenant_only = True

    def get(self):
        return db_get_invites()

    def post(self):
        request = self.validate_request(self.request.content.read(), requests.TenantInviteDesc)

        return create_invite(request, self.request.language)


@transact
def delete_invite(session, invite_id):
    ret = _registrations(session).filter(models.Subscriber.id == invite_id).one_or_none()

    if ret is None:
        raise errors.ForbiddenOperation

    invite, tenant = ret

    if _invite_status(invite, tenant) == 'accepted':
        raise errors.ForbiddenOperation

    db_del(session, models.Tenant, models.Tenant.id == tenant.id)


@transact
def update_invite(session, invite_id, request, language):
    ret = _registrations(session).filter(models.Subscriber.id == invite_id).one_or_none()

    if ret is None:
        raise errors.ForbiddenOperation

    invite, tenant = ret
    action = request['action']

    if action == 'accept':
        if _invite_status(invite, tenant) != 'pending':
            raise errors.ForbiddenOperation
        if invite.activation_token is None:
            raise errors.ForbiddenOperation

        from globaleaks.handlers.signup import db_signup_activation
        db_signup_activation(session, invite.activation_token, '', language)
        invite.state = EnumSubscriberStatus.approved.value
        invite.accreditation_date = datetime_now()
    elif action == 'deny':
        if _invite_status(invite, tenant) != 'pending':
            raise errors.ForbiddenOperation
        invite.state = EnumSubscriberStatus.rejected.value
    else:
        raise errors.InputValidationError

    return serialize_invite(invite, tenant)


class AdminInviteInstance(BaseHandler):
    check_roles = 'admin'
    root_tenant_only = True

    def delete(self, invite_id):
        return delete_invite(invite_id)

    def put(self, invite_id):
        return update_invite(invite_id, self.validate_request(self.request.content.read(), requests.TenantInviteUpdateDesc), self.request.language)


class InviteInstance(BaseHandler):
    check_roles = 'any'
    root_tenant_only = True

    def get(self, token):
        return get_invite(token)
