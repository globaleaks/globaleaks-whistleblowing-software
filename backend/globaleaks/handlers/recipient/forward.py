# Handlers dealing with report forwarding for receivers
import copy
import json

from nacl.encoding import Base64Encoder

from globaleaks import models
from globaleaks.handlers.admin.questionnaire import db_get_questionnaire
from globaleaks.handlers.base import BaseHandler
from globaleaks.handlers.whistleblower.submission import data_hashes, \
                                                         db_archive_questionnaire_schema, \
                                                         db_assign_submission_progressive, \
                                                         db_create_receivertip, \
                                                         db_validate_answers
from globaleaks.models.config import ConfigFactory, db_get_own_config_variable
from globaleaks.orm import db_get, db_log, transact
from globaleaks.rest import errors, requests
from globaleaks.state import State
from globaleaks.utils.crypto import GCE, generateRandomKey, sha256
from globaleaks.utils.json import JSONEncoder
from globaleaks.utils.utility import datetime_now, datetime_null, get_expiration


def _tenant_list_allows(values, uuid):
    values = values or []
    return '*' in values or uuid in values


def db_get_tenant_uuid(session, tid):
    """
    Return the UUID a tenant is designated by in the forwarding relationships

    The tenant IDs are assigned by a counter and are therefore reused over the
    life of a platform: the relationships are held by UUID, that is generated
    once and never changes.

    :param session: An ORM session
    :param tid: The tenant ID
    :return: The UUID of the tenant
    """
    return ConfigFactory(session, tid).get_val('uuid')


def db_get_forwarding_relationships(session):
    """
    Return the forwarding relationships of the platform

    The relationships put the tenants in relation and are therefore decided by
    the administrators of the platform and held by the root tenant alone: each
    one names the tenants allowed to forward (from) and the tenants they are
    allowed to forward to (to), by UUID or by the wildcard *.

    :param session: An ORM session
    :return: The list of the relationships
    """
    return ConfigFactory(session, 1).get_val('forwarding_relationships') or []


def db_forwarding_incoming_enabled(session, tid):
    """
    Check whether any relationship lets a tenant receive the reports of another

    :param session: An ORM session
    :param tid: The tenant ID
    :return: True when the tenant receives forwards from at least one tenant
    """
    uuid = db_get_tenant_uuid(session, tid)

    return any(_tenant_list_allows(relationship.get('to'), uuid)
               for relationship in db_get_forwarding_relationships(session))


def db_forwarding_outgoing_enabled(session, tid):
    """
    Check whether any relationship lets a tenant forward its own reports

    :param session: An ORM session
    :param tid: The tenant ID
    :return: True when the tenant forwards to at least one tenant
    """
    uuid = db_get_tenant_uuid(session, tid)

    return any(_tenant_list_allows(relationship.get('from'), uuid)
               for relationship in db_get_forwarding_relationships(session))


def db_forwarding_pair_allowed(session, source_tid, target_tid):
    """
    Check whether the administrators of the platform related two tenants

    :param session: An ORM session
    :param source_tid: The tenant ID of the tenant that forwards
    :param target_tid: The tenant ID of the tenant that receives
    :return: True when a relationship runs from the former to the latter
    """
    if source_tid == target_tid:
        return False

    source_uuid = db_get_tenant_uuid(session, source_tid)
    target_uuid = db_get_tenant_uuid(session, target_tid)

    return any(_tenant_list_allows(relationship.get('from'), source_uuid) and
               _tenant_list_allows(relationship.get('to'), target_uuid)
               for relationship in db_get_forwarding_relationships(session))


def db_forward_request_required(session, tid):
    """
    Check whether a tenant accepts forwards only upon an authorized request

    :param session: An ORM session
    :param tid: The tenant ID
    :return: True when the tenant requires a request of forward
    """
    return db_forwarding_incoming_enabled(session, tid) and \
        ConfigFactory(session, tid).get_val('require_forward_requests')


def db_access_source_rtip(session, tid, user_id, itip_id):
    return db_get(session,
                  (models.User, models.ReceiverTip, models.InternalTip),
                  (models.User.id == user_id,
                   models.User.tid == tid,
                   models.InternalTip.id == itip_id,
                   models.ReceiverTip.receiver_id == models.User.id,
                   models.ReceiverTip.internaltip_id == models.InternalTip.id))


def db_get_designated_channel(session, tid, var_name):
    """
    Return the channel designated by a tenant to receive forwards or requests of forward

    :param session: An ORM session
    :param tid: The tenant ID of the channel
    :param var_name: The configuration variable designating the channel
    :return: The designated channel or None when the tenant designated none
    """
    channel_id = db_get_own_config_variable(session, tid, var_name)
    if not channel_id:
        return None

    return session.query(models.Context) \
                  .filter(models.Context.id == channel_id,
                          models.Context.tid == tid) \
                  .one_or_none()


def db_get_presented_context_id(session, tid, itip):
    """
    Return the channel a report is presented on to the recipients of a tenant

    The report created by a forward and the request of forward are filed on the
    channel of the tenant they belong to: the recipients of the other tenant are
    presented instead the channel their own tenant designated to the matter, the
    one channel of the exchange they know.

    :param session: An ORM session
    :param tid: The tenant ID of the recipient reading the report
    :param itip: The internaltip of the report
    :return: The context ID to present
    """
    if itip.is_owned_by(tid):
        return itip.context_id

    var_name = 'forward_request_channel' if itip.type == 'forward-request' else 'forward_channel'

    return db_get_own_config_variable(session, tid, var_name) or itip.context_id


def db_get_forward_channel(session, target_tid):
    channel = db_get_designated_channel(session, target_tid, 'forward_channel')
    if channel is None:
        raise errors.InputValidationError("Target tenant has no forward channel configured")

    return channel


def db_get_forward_request_channel(session, target_tid):
    channel = db_get_designated_channel(session, target_tid, 'forward_request_channel')
    if channel is None:
        raise errors.InputValidationError("Target tenant has no forward request channel configured")

    return channel


def db_get_channel_questionnaire(session, target_tid, channel, language):
    return db_get_questionnaire(session, target_tid, channel.questionnaire_id, language, True)


def db_tenant_forward_request_pending(session, source_tid, target_tid):
    requests_ = session.query(models.InternalTip, models.InternalTipData) \
                       .filter(models.InternalTip.tid == target_tid,
                               models.InternalTip.type == 'forward-request',
                               models.InternalTip.allow_forward == False,
                               models.InternalTip.status != 'closed',
                               models.InternalTipData.internaltip_id == models.InternalTip.id,
                               models.InternalTipData.key == 'forward_request') \
                       .all()

    for _, data in requests_:
        try:
            if int(data.value.get('source_tid')) == source_tid:
                return True
        except (AttributeError, TypeError, ValueError):
            continue

    return False


def db_get_authorized_forward_request(session, source_tid, target_tid):
    """
    Return the request of forward authorized to a tenant and not used yet

    Every authorization enables a single forward: a request is spent as soon as
    a report is forwarded under it, and the forward stays linked to it.

    :param session: An ORM session
    :param source_tid: The tenant ID of the tenant that issued the request
    :param target_tid: The tenant ID of the tenant that received the request
    :return: The internaltip of the request or None when the tenant has none
    """
    requests_ = session.query(models.InternalTip, models.InternalTipData) \
                       .filter(models.InternalTip.tid == target_tid,
                               models.InternalTip.type == 'forward-request',
                               models.InternalTip.allow_forward == True,
                               models.InternalTipData.internaltip_id == models.InternalTip.id,
                               models.InternalTipData.key == 'forward_request') \
                       .order_by(models.InternalTip.creation_date) \
                       .all()

    for itip, data in requests_:
        try:
            if int(data.value.get('source_tid')) != source_tid:
                continue
        except (AttributeError, TypeError, ValueError):
            continue

        if not session.query(models.InternalTipForwarding) \
                      .filter(models.InternalTipForwarding.internaltip_id == itip.id) \
                      .count():
            return itip

    return None


def db_get_forward_request_source_tid(session, itip):
    """
    Return the tenant that issued a request of forward

    :param session: An ORM session
    :param itip: The internaltip of the request
    :return: The tenant ID of the tenant that issued it or None
    """
    data = session.query(models.InternalTipData) \
                  .filter(models.InternalTipData.internaltip_id == itip.id,
                          models.InternalTipData.key == 'forward_request') \
                  .one_or_none()

    try:
        return int(data.value.get('source_tid'))
    except (AttributeError, TypeError, ValueError):
        return None


def db_forward_request_is_spent(session, itip):
    """
    Check whether the forward enabled by a request of forward has been performed

    :param session: An ORM session
    :param itip: The internaltip of the request
    :return: True when a report has already been forwarded under the request
    """
    return session.query(models.InternalTipForwarding) \
                  .filter(models.InternalTipForwarding.internaltip_id == itip.id) \
                  .count() > 0


def db_is_forwardable_report(session, source_tid, source_itip):
    """
    Check whether a report can be the source of a forward

    Only original reports are forwardable: the report created by a forward is
    not, so that a report never travels further than the tenant its recipients
    chose to forward it to.
    """
    if source_itip.type == 'submission':
        return True

    # An authorized request of forward is itself forwarded by the tenant that
    # issued it: the forward performed on it is the one that it asked for
    return source_itip.type == 'forward-request' and \
        source_itip.allow_forward and \
        db_get_forward_request_source_tid(session, source_itip) == source_tid and \
        not db_forward_request_is_spent(session, source_itip)


def db_can_forward_report(session, source_tid, source_itip):
    if not db_is_forwardable_report(session, source_tid, source_itip):
        return False

    return db_forwarding_outgoing_enabled(session, source_tid)


def db_can_send_forward_request_to(session, source_tid, target_tid):
    return db_forwarding_pair_allowed(session, source_tid, target_tid)


def db_accepts_forward(session, target_tid, source_tid, source_itip):
    if not db_forwarding_pair_allowed(session, source_tid, target_tid):
        return False

    # The channel receiving the forwards lives on the tenant that receives them
    if db_get_designated_channel(session, target_tid, 'forward_channel') is None:
        return False

    # The requests of forward are addressed to the tenant that receives the
    # forwards, that accepts them only once it has authorized the request
    if db_forward_request_required(session, target_tid) and \
       db_get_authorized_forward_request(session, source_tid, target_tid) is None:
        return False

    return db_can_forward_report(session, source_tid, source_itip)


def db_get_forward_targets(session, source_tid, source_itip):
    targets = []
    for tenant in session.query(models.Tenant).filter(models.Tenant.active == True,
                                                      models.Tenant.id != source_tid):
        if not db_accepts_forward(session, tenant.id, source_tid, source_itip):
            continue

        tenant_config = ConfigFactory(session, tenant.id).serialize('tenant')
        targets.append({
            'id': tenant.id,
            'name': tenant_config.get('name', ''),
            'subdomain': tenant_config.get('subdomain', '')
        })

    return targets


def db_can_request_forward(session, source_tid, target_tid):
    """
    Check whether a tenant can ask another one to be authorized to forward

    The request of forward is filed on the tenant that receives it, the one
    requiring the authorization and designating the channel carrying it.
    """
    if not db_forward_request_required(session, target_tid):
        return False

    if not db_can_send_forward_request_to(session, source_tid, target_tid):
        return False

    # A tenant spends the request it filed before filing another one
    if db_tenant_forward_request_pending(session, source_tid, target_tid):
        return False

    return db_get_designated_channel(session, target_tid, 'forward_request_channel') is not None


def db_get_forward_request_targets(session, source_tid):
    """
    Return the tenants a tenant can address a request of forward to
    """
    targets = []
    for tenant in session.query(models.Tenant).filter(models.Tenant.active == True,
                                                      models.Tenant.id != source_tid):
        if not db_can_request_forward(session, source_tid, tenant.id):
            continue

        tenant_config = ConfigFactory(session, tenant.id).serialize('tenant')
        targets.append({
            'id': tenant.id,
            'name': tenant_config.get('name', ''),
            'subdomain': tenant_config.get('subdomain', ''),
            'hostname': tenant_config.get('hostname', ''),
            'context_id': db_get_forward_request_channel(session, tenant.id).id,
            'source_tid': source_tid
        })

    return targets


def db_get_forward_request_target(session, source_tid, target_tid):
    if not db_can_request_forward(session, source_tid, target_tid):
        raise errors.ForbiddenOperation

    channel = db_get_forward_request_channel(session, target_tid)
    tenant_config = ConfigFactory(session, target_tid).serialize('tenant')

    return {
        'id': target_tid,
        'name': tenant_config.get('name', ''),
        'subdomain': tenant_config.get('subdomain', ''),
        'hostname': tenant_config.get('hostname', ''),
        'context_id': channel.id,
        'source_tid': source_tid
    }


def db_query_channel_receivers(session, target_tid):
    return session.query(models.User) \
                  .filter(models.User.tid == target_tid,
                          models.User.enabled == True,
                          models.User.role == 'receiver')


def db_get_forward_receivers(session, target_tid, channel_id, crypto_is_available):
    channel = db_get(session,
                     models.Context,
                     (models.Context.id == channel_id,
                      models.Context.tid == target_tid))

    receiver_query = db_query_channel_receivers(session, target_tid)

    receivers = receiver_query \
        .join(models.ReceiverContext,
              models.ReceiverContext.receiver_id == models.User.id) \
        .filter(models.ReceiverContext.context_id == channel_id) \
        .all()

    if not receivers and channel.select_all_receivers:
        receivers = receiver_query.all()

    if crypto_is_available:
        encryption = db_get(session,
                            models.Config,
                            (models.Config.tid == target_tid,
                             models.Config.var_name == 'encryption'))
        eligible_receivers = []
        for receiver in receivers:
            if receiver.crypto_pub_key:
                eligible_receivers.append(receiver)
            elif encryption.update_date != datetime_null():
                eligible_receivers.append(receiver)
                crypto_is_available = False

        receivers = eligible_receivers

    if not receivers:
        raise errors.InputValidationError("Forward has no eligible recipient")

    return receivers, crypto_is_available


def db_create_source_tenant_receivertips(session, tid, source_itip, target_itip,
                                         target_receivers, target_encryption, crypto_tip_prv_key):
    """
    Give the recipients of the forwarding tenant access to the report created by a forward

    The report created by the forward is the space where the two tenants talk
    to each other: every recipient the report has on the forwarding tenant
    follows it. The recipients that other tenants may hold on the report
    because of earlier forwards stay out of it, as do the ones that have no
    encryption key the tip key could be wrapped for.

    :param session: An ORM session
    :param tid: The tenant ID of the forwarding tenant
    :param source_itip: The internaltip of the report being forwarded
    :param target_itip: The internaltip created by the forward
    :param target_receivers: The recipients receiving the forward on its channel
    :param target_encryption: Whether the report created by the forward is encrypted
    :param crypto_tip_prv_key: The private key of the report created by the forward
    """
    target_receiver_ids = {receiver.id for receiver in target_receivers}
    source_receivers = session.query(models.User) \
                              .filter(models.User.id == models.ReceiverTip.receiver_id,
                                      models.ReceiverTip.internaltip_id == source_itip.id,
                                      models.User.tid == tid)

    for receiver in source_receivers:
        if receiver.id in target_receiver_ids:
            continue

        if target_encryption:
            if not receiver.crypto_pub_key:
                continue
            receiver_tip_key = GCE.asymmetric_encrypt(receiver.crypto_pub_key, crypto_tip_prv_key)
        else:
            receiver_tip_key = b''

        db_create_receivertip(session, receiver, target_itip, receiver_tip_key)


def db_prepare_forward_answers(session, target_tid, target_channel, answers):
    """
    Validate the answers of a forward and drop the data that is never transferred

    The answers are composed by a recipient of another tenant and are validated
    exactly as the ones of a submission are (see db_validate_answers), so that
    the questionnaire the receiving tenant configured is the only shape the data
    written on it can take, and so that neither the bound on the answers nesting
    depth nor the per field constraints can be escaped by a modified client.

    :param session: An ORM session
    :param target_tid: The tenant ID of the tenant receiving the forward
    :param target_channel: The channel the forward is filed on
    :param answers: The answers composed by the sender
    :return: The steps of the questionnaire and the answers to be stored
    """
    steps, _ = db_validate_answers(session, target_tid,
                                   target_channel.questionnaire_id, answers, True)

    return steps, sanitize_forward_answers(steps, answers)


def sanitize_forward_answers(schema, answers):
    """
    Drop from the answers of a forward the data that is never transferred

    The attachments are instead uploaded by the sender and registered on the
    report created by the forward.
    """
    sanitized = copy.deepcopy(answers)

    def sanitize_fields(fields):
        for field in fields:
            field_id = field.get('id')
            if field_id and field.get('template_id') == 'whistleblower_identity':
                sanitized[field_id] = ''

            sanitize_fields(field.get('children', []))

    for step in schema:
        sanitize_fields(step.get('children', []))

    return sanitized


@transact
def get_forward_options(session, tid, user_session, itip_id, target_tid, language):
    if not user_session.has_permission('can_forward_reports'):
        raise errors.ForbiddenOperation

    _, _, source_itip = db_access_source_rtip(session, tid, user_session.user_id, itip_id)
    if not db_can_forward_report(session, tid, source_itip):
        raise errors.ForbiddenOperation

    # The attachments are held on the session until the forward is performed:
    # opening a new composition drops the ones left over by a previous one
    user_session.files = []

    targets = db_get_forward_targets(session, tid, source_itip)

    # The report is filed on the channel designated by the tenant receiving it
    # and it is therefore its questionnaire that is presented to the sender
    target_tids = [target['id'] for target in targets]
    if target_tid not in target_tids:
        target_tid = target_tids[0] if target_tids else None

    questionnaire = None
    if target_tid is not None:
        channel = db_get_forward_channel(session, target_tid)
        questionnaire = db_get_channel_questionnaire(session, target_tid, channel, language)

    return {
        'target_tid': target_tid,
        'questionnaire': questionnaire,
        'tenants': targets
    }


@transact
def get_forward_request_options(session, tid, user_session, language):
    if not user_session.has_permission('can_forward_reports'):
        raise errors.ForbiddenOperation

    targets = db_get_forward_request_targets(session, tid)
    if not targets:
        return {'available': False}

    # The request is filed on the channel the receiving tenant designated: it is
    # its questionnaire that is presented to the tenant asking for the forward
    target = targets[0]
    channel = db_get_forward_request_channel(session, target['id'])

    return {
        'available': True,
        'questionnaire': db_get_channel_questionnaire(session, target['id'], channel, language),
        'tenant': target,
        'tenants': targets
    }


@transact
def create_forward_request(session, tid, user_session, request):
    if not user_session.has_permission('can_forward_reports'):
        raise errors.ForbiddenOperation

    source_user = db_get(session,
                         models.User,
                         (models.User.id == user_session.user_id,
                          models.User.tid == tid))

    target_tid = int(request['target_tid'])
    if not db_can_request_forward(session, tid, target_tid):
        raise errors.ForbiddenOperation

    target_config = ConfigFactory(session, target_tid)
    target_tenant = session.query(models.Tenant) \
                           .filter(models.Tenant.id == target_tid,
                                   models.Tenant.active == True) \
                           .one_or_none()
    if target_tenant is None:
        raise errors.InputValidationError("Invalid target tenant")

    target_channel = db_get_forward_request_channel(session, target_tid)
    steps, answers = db_prepare_forward_answers(session, target_tid, target_channel,
                                                request['answers'])

    target_state = State.tenants.get(target_tid)
    target_encryption = target_state.cache.encryption if target_state is not None else \
        target_config.get_val('encryption')
    receivers, target_encryption = db_get_forward_receivers(session, target_tid,
                                                            target_channel.id, target_encryption)

    target_itip = models.InternalTip()
    target_itip.tid = target_tid
    target_itip.status = 'new'
    target_itip.type = 'forward-request'
    target_itip.allow_forward = False

    # The recipient that issued the request is the operator of it: the
    # notification of the request reaches the recipients that decide on it
    target_itip.operator_id = source_user.id
    target_itip.creation_date = datetime_now()
    target_itip.update_date = target_itip.creation_date
    target_itip.last_access = target_itip.creation_date
    target_itip.context_id = target_channel.id
    target_itip.progressive = db_assign_submission_progressive(session, target_tid)
    target_itip.score = 0
    target_itip.receipt_hash = sha256(generateRandomKey()).decode()

    if target_channel.tip_timetolive > 0:
        target_itip.expiration_date = get_expiration(target_channel.tip_timetolive)

    if target_channel.tip_reminder > 0:
        target_itip.reminder_date = get_expiration(target_channel.tip_reminder)

    if target_encryption:
        crypto_tip_prv_key, target_itip.crypto_tip_pub_key = GCE.generate_keypair()
    else:
        crypto_tip_prv_key = b''

    session.add(target_itip)
    session.flush()

    questionnaire_hash = db_archive_questionnaire_schema(session, steps)

    plaintext_answers = answers
    if target_itip.crypto_tip_pub_key:
        answers = Base64Encoder.encode(
            GCE.asymmetric_encrypt(target_itip.crypto_tip_pub_key,
                                   json.dumps(answers, cls=JSONEncoder).encode())
        ).decode()

    target_answers = models.InternalTipAnswers()
    target_answers.internaltip_id = target_itip.id
    target_answers.questionnaire_hash = questionnaire_hash
    target_answers.creation_date = target_itip.creation_date
    target_answers.answers = answers
    target_answers.stat_answers = {}
    target_answers.hash_sha256, target_answers.hash_sha512 = data_hashes(plaintext_answers, target_itip.crypto_tip_pub_key)
    session.add(target_answers)

    data = models.InternalTipData()
    data.internaltip_id = target_itip.id
    data.key = 'forward_request'
    data.creation_date = target_itip.creation_date
    data.value = {
        'source_tid': tid,
        'requester_user_id': source_user.id
    }
    data.hash_sha256, data.hash_sha512 = data_hashes(data.value)
    session.add(data)

    for receiver in receivers:
        receiver_tip_key = GCE.asymmetric_encrypt(receiver.crypto_pub_key, crypto_tip_prv_key) \
            if target_encryption else b''
        db_create_receivertip(session, receiver, target_itip, receiver_tip_key)

    source_receiver_tip_key = GCE.asymmetric_encrypt(source_user.crypto_pub_key, crypto_tip_prv_key) \
        if target_encryption and source_user.crypto_pub_key else b''
    db_create_receivertip(session, source_user, target_itip, source_receiver_tip_key)

    source_log_data = {
        'target_internaltip_id': target_itip.id,
        'target_tid': target_tid,
        'target_channel_id': target_channel.id
    }
    target_log_data = {
        'source_tid': tid,
        'target_internaltip_id': target_itip.id,
        'requester_user_id': source_user.id
    }

    db_log(session, tid=tid, type='report_forward_request_created',
           user_id=user_session.user_id, object_id=target_itip.id, data=source_log_data)
    db_log(session, tid=target_tid, type='report_forward_request_received',
           user_id=None, object_id=target_itip.id, data=target_log_data)

    return {
        'id': target_itip.id,
        'target_tid': target_tid,
        'target_channel_id': target_channel.id,
        'progressive': target_itip.progressive,
        'status': target_itip.status
    }


@transact
def create_forward(session, tid, user_session, itip_id, request, language):
    if not user_session.has_permission('can_forward_reports'):
        raise errors.ForbiddenOperation

    source_user, _, source_itip = db_access_source_rtip(session, tid, user_session.user_id, itip_id)
    if not db_can_forward_report(session, tid, source_itip):
        raise errors.ForbiddenOperation

    target_tid = int(request['target_tid'])
    if target_tid == tid:
        raise errors.InputValidationError("Target tenant must differ from source tenant")

    target_tenant = session.query(models.Tenant) \
                           .filter(models.Tenant.id == target_tid,
                                   models.Tenant.active == True) \
                           .one_or_none()
    if target_tenant is None:
        raise errors.InputValidationError("Invalid target tenant")

    if not db_accepts_forward(session, target_tid, tid, source_itip):
        raise errors.ForbiddenOperation

    target_config = ConfigFactory(session, target_tid)
    target_channel = db_get_forward_channel(session, target_tid)
    steps, answers = db_prepare_forward_answers(session, target_tid, target_channel,
                                                request['answers'])

    target_state = State.tenants.get(target_tid)
    target_encryption = target_state.cache.encryption if target_state is not None else \
        target_config.get_val('encryption')
    receivers, target_encryption = db_get_forward_receivers(session, target_tid,
                                                            target_channel.id, target_encryption)

    target_itip = models.InternalTip()
    target_itip.tid = target_tid
    target_itip.status = 'new'
    target_itip.type = 'forward'
    target_itip.allow_forward = False

    # The recipient that performed the forward is the operator of the report it
    # created: the announcement of the forward reaches the recipients of the two
    # tenants and never the one that performed it
    target_itip.operator_id = source_user.id
    target_itip.creation_date = datetime_now()
    target_itip.update_date = target_itip.creation_date
    target_itip.last_access = target_itip.creation_date
    target_itip.context_id = target_channel.id
    target_itip.progressive = db_assign_submission_progressive(session, target_tid)
    target_itip.score = 0
    target_itip.receipt_hash = sha256(generateRandomKey()).decode()

    if target_channel.tip_timetolive > 0:
        target_itip.expiration_date = get_expiration(target_channel.tip_timetolive)

    if target_channel.tip_reminder > 0:
        target_itip.reminder_date = get_expiration(target_channel.tip_reminder)

    if target_encryption:
        crypto_tip_prv_key, target_itip.crypto_tip_pub_key = GCE.generate_keypair()
    else:
        crypto_tip_prv_key = b''

    # The report forwarded upon a request of forward is made accessible to the
    # whistleblower of the tenant that performed it through a receipt issued
    # here and kept, encrypted, on the request itself
    receipt = ''
    if source_itip.type == 'forward-request':
        receipt = GCE.generate_receipt()
        wb_key, target_itip.receipt_hash = GCE.calculate_key_and_hash(
            receipt, State.tenants[target_tid].cache.receipt_salt)
        target_itip.receipt_change_needed = True

        if target_encryption:
            cc, target_itip.crypto_pub_key = GCE.generate_keypair()
            target_itip.crypto_prv_key = Base64Encoder.encode(GCE.symmetric_encrypt(wb_key, cc))
            target_itip.crypto_tip_prv_key = Base64Encoder.encode(
                GCE.asymmetric_encrypt(target_itip.crypto_pub_key, crypto_tip_prv_key))

    session.add(target_itip)
    session.flush()

    if receipt:
        receipt_data = models.InternalTipData()
        receipt_data.internaltip_id = source_itip.id
        receipt_data.key = 'forward_receipt'
        receipt_data.creation_date = target_itip.creation_date
        receipt_data.value = Base64Encoder.encode(
            GCE.asymmetric_encrypt(source_itip.crypto_tip_pub_key, receipt.encode())).decode() \
            if source_itip.crypto_tip_pub_key else receipt
        receipt_data.hash_sha256, receipt_data.hash_sha512 = data_hashes(receipt, source_itip.crypto_tip_pub_key)
        session.add(receipt_data)

    questionnaire_hash = db_archive_questionnaire_schema(session, steps)

    plaintext_answers = answers
    if target_itip.crypto_tip_pub_key:
        answers = Base64Encoder.encode(
            GCE.asymmetric_encrypt(target_itip.crypto_tip_pub_key,
                                   json.dumps(answers, cls=JSONEncoder).encode())
        ).decode()

    target_answers = models.InternalTipAnswers()
    target_answers.internaltip_id = target_itip.id
    target_answers.questionnaire_hash = questionnaire_hash
    target_answers.creation_date = target_itip.creation_date
    target_answers.answers = answers
    target_answers.stat_answers = {}
    target_answers.hash_sha256, target_answers.hash_sha512 = data_hashes(plaintext_answers, target_itip.crypto_tip_pub_key)
    session.add(target_answers)

    # The attachments uploaded while composing the forward become attachments of
    # the report created by it and are delivered by the ordinary delivery job
    for uploaded_file in user_session.files:
        if target_encryption:
            for k in ['name', 'type', 'size', 'hash_sha256', 'hash_sha512']:
                uploaded_file[k] = Base64Encoder.encode(
                    GCE.asymmetric_encrypt(target_itip.crypto_tip_pub_key, str(uploaded_file[k])))

        new_file = models.InternalFile()
        new_file.id = uploaded_file['filename']
        new_file.name = uploaded_file['name']
        new_file.content_type = uploaded_file['type']
        new_file.size = uploaded_file['size']
        new_file.internaltip_id = target_itip.id
        new_file.reference_id = uploaded_file['reference_id']
        new_file.creation_date = target_itip.creation_date
        new_file.hash_sha256 = uploaded_file['hash_sha256']
        new_file.hash_sha512 = uploaded_file['hash_sha512']
        session.add(new_file)

    user_session.files = []

    forwarding = models.InternalTipForwarding()
    forwarding.internaltip_id = source_itip.id
    forwarding.forwarding_internaltip_id = target_itip.id

    # The key of the report created by the forward is handed over to the
    # whistleblower, wrapped with the key of the report forwarded, so that the
    # whistleblower can exchange messages with the recipients of the tenant
    # that received the forward
    if source_itip.type != 'forward-request' and \
            target_encryption and source_itip.crypto_tip_pub_key:
        forwarding.crypto_tip_prv_key = Base64Encoder.encode(
            GCE.asymmetric_encrypt(source_itip.crypto_tip_pub_key, crypto_tip_prv_key)).decode()

    session.add(forwarding)

    # The forward performed by a tenant spends the request of forward that
    # authorized it and stays linked to it; the forward performed on the request
    # itself is already linked to it by the link written above. A tenant that
    # accepts the forwards without a request is instead forwarded to directly,
    # and there is no authorization to spend
    forward_request_id = ''
    forward_request = source_itip if source_itip.type == 'forward-request' else \
        db_get_authorized_forward_request(session, tid, target_tid)

    if forward_request is None and db_forward_request_required(session, target_tid):
        raise errors.ForbiddenOperation

    if forward_request is not None:
        forward_request_id = forward_request.id
        forward_request.update_date = target_itip.creation_date

        if forward_request.id != source_itip.id:
            request_forwarding = models.InternalTipForwarding()
            request_forwarding.internaltip_id = forward_request.id
            request_forwarding.forwarding_internaltip_id = target_itip.id
            session.add(request_forwarding)

    data = models.InternalTipData()
    data.internaltip_id = str(target_itip.id)
    data.key = 'forwarded_from'
    data.creation_date = target_itip.creation_date
    # The origin is the tenant that performed the forward: on a forward
    # performed upon a request of forward the source report is the request
    # itself, which is filed on the receiving tenant and does not name the
    # sender
    data.value = {'source_tid': tid,
                  'forward_request_internaltip_id': forward_request_id}
    data.hash_sha256, data.hash_sha512 = data_hashes(data.value)

    session.add(data)

    for receiver in receivers:
        receiver_tip_key = GCE.asymmetric_encrypt(receiver.crypto_pub_key, crypto_tip_prv_key) \
            if target_encryption else b''
        db_create_receivertip(session, receiver, target_itip, receiver_tip_key)

    # Whether the tenant that performed the forward keeps accessing the report
    # it created is decided by the tenant that receives it: a forward carrying
    # a question keeps the two teams talking on it, one handing a content over
    # leaves the sender without access
    if target_config.get_val('forward_source_access'):
        if target_encryption and not source_user.crypto_pub_key:
            raise errors.InputValidationError("Forwarding user has no encryption key")

        db_create_source_tenant_receivertips(session, tid, source_itip, target_itip,
                                             receivers, target_encryption, crypto_tip_prv_key)

    source_itip.update_date = target_itip.creation_date

    privacy = {
        'forward_questionnaire_filed': True,
        'source_answers_copied': False,
        'identity_copied': False,
        'files_copied': False,
        'comments_copied': False,
        'private_notes_copied': False
    }
    source_log_data = {
        'source_internaltip_id': source_itip.id,
        'target_internaltip_id': target_itip.id,
        'target_tid': target_tid,
        'target_channel_id': target_channel.id,
        'forward_request_internaltip_id': forward_request_id,
        'privacy': privacy
    }
    target_log_data = {
        'source_tid': source_itip.tid,
        'target_internaltip_id': target_itip.id,
        'forward_request_internaltip_id': forward_request_id,
        'privacy': privacy
    }

    db_log(session, tid=tid, type='report_forward_created',
           user_id=user_session.user_id, object_id=source_itip.id, data=source_log_data)
    db_log(session, tid=target_tid, type='report_forward_received',
           user_id=None, object_id=target_itip.id, data=target_log_data)

    return {
        'id': target_itip.id,
        'source_id': source_itip.id,
        'target_tid': target_tid,
        'target_channel_id': target_channel.id
    }


class RTipForward(BaseHandler):
    """
    Interface used to create a linked InternalTip through the forward questionnaire.
    """
    check_roles = 'receiver'

    def get(self, itip_id):
        try:
            target_tid = int(self.request.args.get(b'target_tid', [b''])[0])
        except (IndexError, TypeError, ValueError):
            target_tid = None

        return get_forward_options(self.request.tid,
                                   self.session,
                                   itip_id,
                                   target_tid,
                                   self.request.language)

    def post(self, itip_id):
        request = self.validate_request(self.request.content.read(), requests.ForwardReportDesc)
        return create_forward(self.request.tid,
                              self.session,
                              itip_id,
                              request,
                              self.request.language)


class RTipForwardAttachment(BaseHandler):
    """
    Interface used to upload the attachments of a forward being composed.

    The files are held on the session of the sender and registered on the report
    as soon as the forward is performed.
    """
    check_roles = 'receiver'
    upload_handler = True

    def post(self, itip_id):
        if not self.session.has_permission('can_forward_reports'):
            raise errors.ForbiddenOperation

        self.uploaded_file['submission'] = True
        self.session.files.append(self.uploaded_file)


class RTipsForwardRequest(BaseHandler):
    """
    Interface used to open the forward request channel on the accepting tenant.

    The request is issued by the tenant and not by one of its reports: it is
    reachable from a report as well as from the list of them, and the report it
    is reached from bears no part in it.
    """
    check_roles = 'receiver'

    def get(self, itip_id=None):
        return get_forward_request_options(self.request.tid,
                                           self.session,
                                           self.request.language)

    def post(self, itip_id=None):
        request = self.validate_request(self.request.content.read(), requests.ForwardReportDesc)
        return create_forward_request(self.request.tid,
                                      self.session,
                                      request)


def db_get_forwarding(session, forwarded_itip_id):
    """
    Return the forwarding a report was created by

    :param session: An ORM session
    :param forwarded_itip_id: The internaltip ID of the report created by the forward
    :return: The forwarding or None when the report was not created by one
    """
    return session.query(models.InternalTipForwarding) \
                  .filter(models.InternalTipForwarding.forwarding_internaltip_id == forwarded_itip_id) \
                  .one_or_none()


def serialize_forward_message(session, comment, viewer_tid):
    """
    Transaction returning a serialized descriptor of a forward message

    The messages exchanged with the whistleblower are the public comments of
    the report created by the forward: the space where the whistleblower is
    keeps the public visibility on every kind of report.
    The author of a message is presented to the other tenant of the forward by
    the name of its tenant, mirroring the masking of the recipients identities.

    :param session: An ORM session
    :param comment: A model to be serialized
    :param viewer_tid: The tenant ID of the user the message is serialized for
    :return: A serialized description of the model specified
    """
    author_name = ''
    if comment.author_id:
        author = session.query(models.User).get(comment.author_id)
        if author is not None:
            author_name = author.name if author.tid == viewer_tid else \
                ConfigFactory(session, author.tid).get_val('name')

    return {
        'id': comment.id,
        'creation_date': comment.creation_date,
        'author_id': comment.author_id,
        'author_name': author_name,
        'content': comment.content
    }


def db_get_forward_messages(session, forwarded_itip_id, viewer_tid, tip_prv_key):
    messages = []
    for comment in session.query(models.Comment) \
                          .filter(models.Comment.internaltip_id == forwarded_itip_id,
                                  models.Comment.visibility == models.EnumVisibility.public.value) \
                          .order_by(models.Comment.creation_date):
        entry = serialize_forward_message(session, comment, viewer_tid)
        if tip_prv_key:
            entry['content'] = GCE.asymmetric_decrypt(
                tip_prv_key, Base64Encoder.decode(entry['content'].encode())).decode()
        messages.append(entry)

    return messages


def db_access_forwarding_as_whistleblower(session, wb_itip_id, forwarded_itip_id):
    """
    Retrieve a forwarding on behalf of the whistleblower of the report it forwarded
    """
    source_itip = db_get(session, models.InternalTip, models.InternalTip.id == wb_itip_id)

    forwarding = db_get_forwarding(session, forwarded_itip_id)
    if forwarding is None or forwarding.internaltip_id != source_itip.id:
        raise errors.ForbiddenOperation

    forwarded_itip = db_get(session, models.InternalTip,
                            models.InternalTip.id == forwarded_itip_id)

    if not forwarding.messages_enabled(forwarded_itip):
        raise errors.ForbiddenOperation

    return source_itip, forwarded_itip, forwarding


def db_whistleblower_forward_key(user_session, source_itip, forwarding, forwarded_itip):
    if not forwarded_itip.crypto_tip_pub_key:
        return b''

    source_tip_key = GCE.asymmetric_decrypt(user_session.cc,
                                            Base64Encoder.decode(source_itip.crypto_tip_prv_key))

    return GCE.asymmetric_decrypt(source_tip_key,
                                  Base64Encoder.decode(forwarding.crypto_tip_prv_key))


@transact
def get_forward_messages_as_whistleblower(session, user_session, forwarded_itip_id):
    source_itip, forwarded_itip, forwarding = \
        db_access_forwarding_as_whistleblower(session, user_session.user_id, forwarded_itip_id)

    tip_prv_key = db_whistleblower_forward_key(user_session, source_itip,
                                               forwarding, forwarded_itip)

    return db_get_forward_messages(session, forwarded_itip.id, source_itip.tid, tip_prv_key)
