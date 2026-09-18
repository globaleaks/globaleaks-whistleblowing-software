# Handlers dealing with the reports the sites of a platform exchange
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
from globaleaks.models import get_localized_values
from globaleaks.models.config import ConfigFactory
from globaleaks.models.exchanges import db_exchange_outgoing_enabled, \
                                        db_get_exchange_channel, \
                                        db_get_exchange_owner_tid, \
                                        db_match_exchange, \
                                        db_match_exchanges
from globaleaks.orm import db_get, db_log, transact
from globaleaks.rest import errors, requests
from globaleaks.state import State
from globaleaks.utils.crypto import GCE, generateRandomKey, sha256
from globaleaks.utils.json import JSONEncoder
from globaleaks.utils.utility import datetime_now, datetime_null, get_expiration


def db_exchange_enabled(session, type, tid):
    """
    Check whether any exchange of a type lets a tenant file towards another

    :param session: An ORM session
    :param type: The type of the exchanges
    :param tid: The tenant ID
    :return: True when the tenant files towards at least one tenant
    """
    return db_exchange_outgoing_enabled(session, type, tid)


def db_get_presented_context_id(session, tid, itip):
    """
    Return the channel a report is presented on to the recipients of a site

    :param session: An ORM session
    :param tid: The tenant ID of the recipient reading the report
    :param itip: The internaltip of the report
    :return: The context ID to present
    """
    if itip.is_owned_by(tid):
        return itip.context_id

    exchange = db_get_report_exchange(session, itip)
    channel = db_get_exchange_channel(session, exchange, tid) if exchange is not None else None

    return channel.id if channel is not None else itip.context_id


def db_get_report_exchange(session, itip):
    """
    Return the exchange a report was created by

    :param session: An ORM session
    :param itip: The internaltip of the report
    :return: The exchange or None
    """
    recorded = session.query(models.InternalTipData.value) \
                      .filter(models.InternalTipData.internaltip_id == itip.id,
                              models.InternalTipData.key.in_(['request', 'transmitted_from'])) \
                      .first()

    exchange_id = recorded[0].get('exchange_id') if recorded else None
    if not exchange_id:
        return None

    return session.query(models.Exchange) \
                  .filter(models.Exchange.id == exchange_id) \
                  .one_or_none()


def db_access_source_rtip(session, tid, user_id, itip_id):
    return db_get(session,
                  (models.User, models.ReceiverTip, models.InternalTip),
                  (models.User.id == user_id,
                   models.User.tid == tid,
                   models.InternalTip.id == itip_id,
                   models.ReceiverTip.receiver_id == models.User.id,
                   models.ReceiverTip.internaltip_id == models.InternalTip.id))


def db_origin_report(session, itip):
    """
    Return the report a report was handed over from, if it was handed over

    :param session: An ORM session
    :param itip: The internaltip of the report
    :return: The internaltip it was handed over from or None
    """
    transmission = db_get_transmission(session, itip.id)
    if transmission is None:
        return None

    origin = session.query(models.InternalTip) \
                    .filter(models.InternalTip.id == transmission.internaltip_id) \
                    .one_or_none()

    return origin if origin is not None and origin.type != 'request' else None


# Carrying a report to another site is a permission of the recipient; filing on another site is the
# transmitter role
EXCHANGE_PERMISSIONS = {
    'communication': 'can_send_communications'
}


def db_is_communicable_report(session, tid, itip):
    """
    Check whether a report can be communicated to another site

    :param session: An ORM session
    :param tid: The tenant ID of the tenant that would communicate
    :param itip: The internaltip of the report
    :return: True when the report can be communicated
    """
    if itip.type != 'submission' or itip.tid != tid:
        return False

    return db_origin_report(session, itip) is None


def db_can_communicate_report(session, tid, itip):
    """
    Check whether a report can be communicated by the site that holds it

    :param session: An ORM session
    :param tid: The tenant ID of the tenant that would communicate
    :param itip: The internaltip of the report
    :return: True when the report is communicable and the site communicates
    """
    return db_is_communicable_report(session, tid, itip) and \
        db_exchange_enabled(session, 'communication', tid)


def db_can_transmit(session, tid):
    """
    Check whether a site files its reports on another site of the platform

    :param session: An ORM session
    :param tid: The tenant ID
    :return: True when at least one exchange of transmission runs from the site
    """
    return db_exchange_enabled(session, 'transmission', tid)


def db_get_exchange_requests(session, exchange_id, source_tid, target_tid):
    """
    Return the requests filed under an exchange, the oldest one first

    :param session: An ORM session
    :param exchange_id: The exchange the requests were filed under
    :param source_tid: The tenant ID of the tenant that asked
    :param target_tid: The tenant ID of the tenant that decides
    :return: The list of the internaltips of the requests
    """
    found = []
    for itip, data in session.query(models.InternalTip, models.InternalTipData) \
                             .filter(models.InternalTip.tid == target_tid,
                                     models.InternalTip.type == 'request',
                                     models.InternalTipData.internaltip_id == models.InternalTip.id,
                                     models.InternalTipData.key == 'request') \
                             .order_by(models.InternalTip.creation_date):
        try:
            if int(data.value.get('source_tid')) != source_tid:
                continue
        except (AttributeError, TypeError, ValueError):
            continue

        if data.value.get('exchange_id') not in ['', None, exchange_id]:
            continue

        found.append(itip)

    return found


def db_request_is_spent(session, itip):
    """
    Check whether the report a request authorized has been entered

    :param session: An ORM session
    :param itip: The internaltip of the request
    :return: True when a report has already been entered under the request
    """
    return session.query(models.InternalTipTransmission) \
                  .filter(models.InternalTipTransmission.internaltip_id == itip.id) \
                  .count() > 0


def db_get_authorized_request(session, exchange_id, source_tid, target_tid):
    """
    Return the request authorized to a tenant and not spent yet

    :param session: An ORM session
    :param exchange_id: The exchange the request was filed under
    :param source_tid: The tenant ID of the tenant that asked
    :param target_tid: The tenant ID of the tenant that decides
    :return: The internaltip of the request or None
    """
    for itip in db_get_exchange_requests(session, exchange_id, source_tid, target_tid):
        if itip.allow_transmission and not db_request_is_spent(session, itip):
            return itip

    return None


def db_request_pending(session, exchange_id, source_tid, target_tid):
    """
    Check whether a request filed under an exchange has yet to be decided

    :param session: An ORM session
    :param exchange_id: The exchange the request was filed under
    :param source_tid: The tenant ID of the tenant that asked
    :param target_tid: The tenant ID of the tenant that decides
    :return: True when a request is waiting to be decided
    """
    return any(not itip.allow_transmission and itip.status != 'closed'
               for itip in db_get_exchange_requests(session, exchange_id,
                                                    source_tid, target_tid))


def db_get_request_source_tid(session, itip):
    """
    Return the tenant that filed a request

    :param session: An ORM session
    :param itip: The internaltip of the request
    :return: The tenant ID of the tenant that filed it or None
    """
    data = session.query(models.InternalTipData) \
                  .filter(models.InternalTipData.internaltip_id == itip.id,
                          models.InternalTipData.key == 'request') \
                  .one_or_none()

    try:
        return int(data.value.get('source_tid'))
    except (AttributeError, TypeError, ValueError):
        return None


def db_exchange_stage(session, exchange, source_tid, target_tid):
    """
    Return what filing under an exchange composes at this moment

    :param session: An ORM session
    :param exchange: The exchange
    :param source_tid: The tenant ID of the tenant that files
    :param target_tid: The tenant ID of the tenant that receives
    :return: Either 'report', 'request' or None when a request is pending
    """
    if exchange.type != 'transmission' or not exchange.request_questionnaire:
        return 'report'

    if db_get_authorized_request(session, exchange.id, source_tid, target_tid) is not None:
        return 'report'

    if db_request_pending(session, exchange.id, source_tid, target_tid):
        return None

    return 'request'


def db_get_exchange_questionnaire_id(session, exchange, channel, stage):
    """
    Return the questionnaire what an exchange creates is composed with

    :param session: An ORM session
    :param exchange: The exchange
    :param channel: The channel the report is filed on
    :param stage: What is being composed
    :return: The id of the questionnaire
    """
    if stage == 'request':
        return exchange.request_questionnaire

    return exchange.questionnaire or channel.questionnaire_id


def db_get_exchange_option(session, exchange, source_tid, target_tid,
                           language=None, source_itip=None):
    """
    Return the way of filing an exchange offers, or nothing when it offers none

    :param session: An ORM session
    :param exchange: The exchange
    :param source_tid: The tenant ID of the tenant that files
    :param target_tid: The tenant ID of the tenant that receives
    :param language: The language the channel is named in
    :param source_itip: The report handed over, on an exchange of transmission
    :return: The option offered or None
    """
    exchange_channel = db_get_exchange_channel(session, exchange, target_tid)
    if exchange_channel is None:
        return None

    # a channel nobody receives on carries nothing
    if not session.query(models.ReceiverContext) \
                  .filter(models.ReceiverContext.context_id == exchange_channel.id) \
                  .count():
        return None

    owner_tid = db_get_exchange_owner_tid(session, exchange, source_tid, target_tid)

    # The report the sender keeps lives on the channel of its origin: same recipients and retention
    if owner_tid == target_tid:
        channel = exchange_channel
    elif source_itip is not None:
        channel = session.query(models.Context) \
                         .filter(models.Context.id == source_itip.context_id) \
                         .one_or_none()
    else:
        channel = None

    if channel is None:
        return None

    stage = db_exchange_stage(session, exchange, source_tid, target_tid)
    if stage is None:
        return None

    questionnaire_id = db_get_exchange_questionnaire_id(session, exchange, channel, stage)
    if not questionnaire_id:
        return None

    name = exchange_channel.name
    if language is not None:
        name = get_localized_values({}, exchange_channel, ['name'], language)['name']

    return {
        'id': exchange.id,
        'owner_tid': owner_tid,
        'exchange_channel': exchange_channel,
        'channel': channel,
        'channel_id': exchange_channel.id,
        'channel_name': name,
        'questionnaire_id': questionnaire_id,
        'stage': stage
    }


def db_get_exchange_targets(session, type, source_tid, language, source_itip=None):
    """
    Return the sites a site files towards and the ways it files on each

    :param session: An ORM session
    :param type: The type of the exchanges
    :param source_tid: The tenant ID of the tenant that files
    :param language: The language the channels are named in
    :param source_itip: The report handed over, on an exchange of transmission
    :return: The list of the destinations, each carrying its options
    """
    targets = []
    for tenant in session.query(models.Tenant).filter(models.Tenant.active == True):
        options = []
        for exchange in db_match_exchanges(session, type, source_tid, tenant.id):
            option = db_get_exchange_option(session, exchange, source_tid,
                                            tenant.id, language, source_itip)
            if option is None:
                continue

            options.append({key: option[key] for key in ['id', 'channel_id',
                                                         'channel_name', 'stage']})

        if not options:
            continue

        tenant_config = ConfigFactory(session, tenant.id).serialize('tenant')
        targets.append({
            'id': tenant.id,
            'name': tenant_config.get('name', ''),
            'subdomain': tenant_config.get('subdomain', ''),
            'options': options
        })

    return targets


def db_get_chosen_exchange(session, type, source_tid, target_tid, exchange_id,
                           source_itip=None):
    """
    Return the exchange chosen by the sender and the way it files under it

    :param session: An ORM session
    :param type: The type of the exchange
    :param source_tid: The tenant ID of the tenant that files
    :param target_tid: The tenant ID of the tenant that receives
    :param exchange_id: The exchange chosen by the sender
    :param source_itip: The report handed over, on an exchange of transmission
    :return: The exchange and the option it offers
    """
    if session.query(models.Tenant) \
              .filter(models.Tenant.id == target_tid,
                      models.Tenant.active == True) \
              .one_or_none() is None:
        raise errors.InputValidationError("Invalid target tenant")

    exchange = db_match_exchange(session, type, source_tid, target_tid, exchange_id)
    if exchange is None:
        raise errors.ForbiddenOperation

    option = db_get_exchange_option(session, exchange, source_tid, target_tid,
                                    None, source_itip)
    if option is None:
        raise errors.ForbiddenOperation

    return exchange, option


def db_get_exchange_options(session, type, source_tid, target_tid, exchange_id,
                            language, source_itip=None):
    """
    Return what filing towards the other sites is composed of

    :param session: An ORM session
    :param type: The type of the exchanges
    :param source_tid: The tenant ID of the tenant that files
    :param target_tid: The tenant chosen by the sender, if any
    :param exchange_id: The exchange chosen by the sender, if any
    :param language: The language the questionnaire is presented in
    :param source_itip: The report handed over, on an exchange of transmission
    :return: The destinations offered and the questionnaire to compose
    """
    targets = db_get_exchange_targets(session, type, source_tid, language, source_itip)

    ret = {
        'targets': targets,
        'target_tid': None,
        'exchange_id': '',
        'stage': '',
        'questionnaire': None
    }

    if not targets:
        return ret

    # Destination and channel are chosen before the questionnaire; a single option is chosen
    # implicitly
    if target_tid not in [target['id'] for target in targets]:
        target_tid = targets[0]['id'] if len(targets) == 1 else None

    if target_tid is None:
        return ret

    target = [entry for entry in targets if entry['id'] == target_tid][0]
    options = target['options']

    if exchange_id not in [option['id'] for option in options]:
        exchange_id = options[0]['id'] if len(options) == 1 else ''

    if not exchange_id:
        ret['target_tid'] = target_tid
        return ret

    exchange, option = db_get_chosen_exchange(session, type, source_tid,
                                              target_tid, exchange_id, source_itip)

    ret['target_tid'] = target_tid
    ret['exchange_id'] = exchange_id
    ret['stage'] = option['stage']
    ret['questionnaire'] = db_get_questionnaire(session, option['owner_tid'],
                                                option['questionnaire_id'],
                                                language, True)

    return ret


def db_query_channel_receivers(session, tid):
    return session.query(models.User) \
                  .filter(models.User.tid == tid,
                          models.User.enabled == True,
                          models.User.role == 'receiver')


def db_get_channel_receivers(session, tid, channel_id):
    """
    Return the recipients a channel of a site hands its reports to

    :param session: An ORM session
    :param tid: The tenant ID of the tenant the channel belongs to
    :param channel_id: The channel
    :return: The recipients of the channel
    """
    channel = db_get(session,
                     models.Context,
                     (models.Context.id == channel_id,
                      models.Context.tid == tid))

    receiver_query = db_query_channel_receivers(session, tid)

    receivers = receiver_query \
        .join(models.ReceiverContext,
              models.ReceiverContext.receiver_id == models.User.id) \
        .filter(models.ReceiverContext.context_id == channel_id) \
        .all()

    if not receivers and channel.select_all_receivers:
        receivers = receiver_query.all()

    return receivers


def db_filter_eligible_receivers(session, owner_tid, receivers, crypto_is_available):
    """
    Drop the recipients the report could not be handed to, and tell the encryption

    :param session: An ORM session
    :param owner_tid: The tenant ID of the tenant the report belongs to
    :param receivers: The recipients the report is handed to
    :param crypto_is_available: Whether the report is encrypted
    :return: The eligible recipients and whether the report is encrypted
    """
    if not crypto_is_available:
        return receivers, crypto_is_available

    encryption = db_get(session,
                        models.Config,
                        (models.Config.tid == owner_tid,
                         models.Config.var_name == 'encryption'))

    eligible_receivers = []
    for receiver in receivers:
        if receiver.crypto_pub_key:
            eligible_receivers.append(receiver)
        elif encryption.update_date != datetime_null():
            eligible_receivers.append(receiver)
            crypto_is_available = False

    return eligible_receivers, crypto_is_available


def db_create_source_tenant_receivertips(session, tid, source_itip, target_itip,
                                         target_receivers, target_encryption, crypto_tip_prv_key):
    """
    Give the recipients of the filing tenant access to the report it created

    :param session: An ORM session
    :param tid: The tenant ID of the transmission tenant
    :param source_itip: The internaltip of the report being transmitted
    :param target_itip: The internaltip created by the transmission
    :param target_receivers: The recipients receiving the transmission on its channel
    :param target_encryption: Whether the report created by the transmission is encrypted
    :param crypto_tip_prv_key: The private key of the report created by the transmission
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


def db_prepare_answers(session, tid, questionnaire_id, answers):
    """
    Validate the answers composed by a recipient and drop what is never transferred

    :param session: An ORM session
    :param tid: The tenant ID of the tenant the questionnaire belongs to
    :param questionnaire_id: The questionnaire the answers are shaped by
    :param answers: The answers composed by the sender
    :return: The steps of the questionnaire and the answers to be stored
    """
    steps, _ = db_validate_answers(session, tid, questionnaire_id, answers, True)

    return steps, sanitize_transmission_answers(steps, answers)


def sanitize_transmission_answers(schema, answers):
    """
    Drop from the answers composed for another site the data that is never transferred
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


def db_new_exchange_report(session, owner_tid, channel, source_user, stage, encryption):
    """
    Compose the report an exchange files, on the site that owns it

    :param session: An ORM session
    :param owner_tid: The tenant ID of the site the report lives on
    :param channel: The channel the report is filed on
    :param source_user: The recipient that files
    :param stage: The stage of the exchange
    :param encryption: Whether the site encrypts its reports
    :return: The report and the private key of its encryption, empty when the site does not encrypt
    """
    itip = models.InternalTip()
    itip.tid = owner_tid
    itip.status = 'new'
    # A request is decided before the report is entered; what a site files on itself is an ordinary
    # report
    itip.type = 'request' if stage == 'request' else 'exchange'
    itip.allow_transmission = False

    # The operator never receives the announcement of what it filed
    itip.operator_id = source_user.id
    itip.creation_date = datetime_now()
    itip.update_date = itip.creation_date
    itip.last_access = itip.creation_date
    itip.context_id = channel.id
    itip.progressive = db_assign_submission_progressive(session, owner_tid)
    itip.score = 0
    itip.receipt_hash = sha256(generateRandomKey()).decode()

    if channel.tip_timetolive > 0:
        itip.expiration_date = get_expiration(channel.tip_timetolive)

    if channel.tip_reminder > 0:
        itip.reminder_date = get_expiration(channel.tip_reminder)

    if not encryption:
        return itip, b''

    crypto_tip_prv_key, itip.crypto_tip_pub_key = GCE.generate_keypair()

    return itip, crypto_tip_prv_key


def db_issue_receipt(session, itip, authorization, encryption, crypto_tip_prv_key):
    """
    Make a report accessible to the whistleblower through a receipt issued here and kept encrypted
    on the request that granted it

    :param session: An ORM session
    :param itip: The report filed
    :param authorization: The request that granted the report
    :param encryption: Whether the report is encrypted
    :param crypto_tip_prv_key: The private key of the report
    """
    receipt = GCE.generate_receipt()
    wb_key, itip.receipt_hash = GCE.calculate_key_and_hash(
        receipt, State.tenants[itip.tid].cache.receipt_salt)
    itip.receipt_change_needed = True

    if encryption:
        cc, itip.crypto_pub_key = GCE.generate_keypair()
        itip.crypto_prv_key = Base64Encoder.encode(GCE.symmetric_encrypt(wb_key, cc))
        itip.crypto_tip_prv_key = Base64Encoder.encode(
            GCE.asymmetric_encrypt(itip.crypto_pub_key, crypto_tip_prv_key))

    receipt_data = models.InternalTipData()
    receipt_data.internaltip_id = authorization.id
    receipt_data.key = 'receipt'
    receipt_data.creation_date = itip.creation_date
    receipt_data.value = Base64Encoder.encode(
        GCE.asymmetric_encrypt(authorization.crypto_tip_pub_key, receipt.encode())).decode() \
        if authorization.crypto_tip_pub_key else receipt
    receipt_data.hash_sha256, receipt_data.hash_sha512 = \
        data_hashes(receipt, authorization.crypto_tip_pub_key)
    session.add(receipt_data)


def db_store_exchange_answers(session, itip, steps, answers):
    """
    Archive the questionnaire a report is composed with and store its answers

    :param session: An ORM session
    :param itip: The report filed
    :param steps: The steps of the questionnaire
    :param answers: The answers given
    """
    questionnaire_hash = db_archive_questionnaire_schema(session, steps)

    plaintext_answers = answers
    if itip.crypto_tip_pub_key:
        answers = Base64Encoder.encode(
            GCE.asymmetric_encrypt(itip.crypto_tip_pub_key,
                                   json.dumps(answers, cls=JSONEncoder).encode())
        ).decode()

    itip_answers = models.InternalTipAnswers()
    itip_answers.internaltip_id = itip.id
    itip_answers.questionnaire_hash = questionnaire_hash
    itip_answers.creation_date = itip.creation_date
    itip_answers.answers = answers
    itip_answers.stat_answers = {}
    itip_answers.hash_sha256, itip_answers.hash_sha512 = \
        data_hashes(plaintext_answers, itip.crypto_tip_pub_key)
    session.add(itip_answers)


def db_store_exchange_files(session, itip, user_session, encryption):
    """
    Attach to a report the files uploaded while composing it; the ordinary delivery job delivers
    them

    :param session: An ORM session
    :param itip: The report filed
    :param user_session: The session of the recipient that files
    :param encryption: Whether the report is encrypted
    """
    for uploaded_file in user_session.files:
        if encryption:
            for k in ['name', 'type', 'size', 'hash_sha256', 'hash_sha512']:
                uploaded_file[k] = Base64Encoder.encode(
                    GCE.asymmetric_encrypt(itip.crypto_tip_pub_key, str(uploaded_file[k])))

        new_file = models.InternalFile()
        new_file.id = uploaded_file['filename']
        new_file.name = uploaded_file['name']
        new_file.content_type = uploaded_file['type']
        new_file.size = uploaded_file['size']
        new_file.internaltip_id = itip.id
        new_file.reference_id = uploaded_file['reference_id']
        new_file.creation_date = itip.creation_date
        new_file.hash_sha256 = uploaded_file['hash_sha256']
        new_file.hash_sha512 = uploaded_file['hash_sha512']
        session.add(new_file)

    user_session.files = []


def db_record_exchange_origin(session, itip, stage, tid, target_tid, exchange, source_user,
                              authorization, source_itip):
    """
    Record on a report the exchange it was filed by and name its origin: the report handed over,
    or the request that granted it

    :param session: An ORM session
    :param itip: The report filed
    :param stage: The stage of the exchange
    :param tid: The tenant ID of the tenant that files
    :param target_tid: The tenant ID of the destination
    :param exchange: The exchange
    :param source_user: The recipient that files
    :param authorization: The request that granted the report, if any
    :param source_itip: The report handed over, if any
    """
    data = models.InternalTipData()
    data.internaltip_id = itip.id
    data.key = 'request' if stage == 'request' else 'transmitted_from'
    data.creation_date = itip.creation_date
    data.value = {
        'source_tid': tid,
        'target_tid': target_tid,
        'exchange_id': exchange.id,
        'requester_user_id': source_user.id,
        'request_internaltip_id': authorization.id if authorization is not None else ''
    }
    data.hash_sha256, data.hash_sha512 = data_hashes(data.value)
    session.add(data)

    origin = source_itip if source_itip is not None else authorization
    if origin is None:
        return

    transmission = models.InternalTipTransmission()
    transmission.internaltip_id = origin.id
    transmission.transmitting_internaltip_id = itip.id
    session.add(transmission)

    origin.update_date = itip.creation_date


def db_create_exchange_receivertips(session, receivers, itip, encryption, crypto_tip_prv_key):
    """
    Give some recipients access to a report

    :param session: An ORM session
    :param receivers: The recipients
    :param itip: The report
    :param encryption: Whether the report is encrypted
    :param crypto_tip_prv_key: The private key of the report
    """
    for receiver in receivers:
        receiver_tip_key = GCE.asymmetric_encrypt(receiver.crypto_pub_key, crypto_tip_prv_key) \
            if encryption else b''
        db_create_receivertip(session, receiver, itip, receiver_tip_key)


def db_create_exchange_report(session, tid, user_session, type, request, language,
                              source_itip=None):
    """
    File on another site of the platform the report an exchange composes

    :param session: An ORM session
    :param tid: The tenant ID of the tenant that files
    :param user_session: The session of the recipient that files
    :param type: The type of the exchange
    :param request: The request data
    :param language: The language the report is composed in
    :param source_itip: The report handed over, on an exchange of transmission
    :return: A descriptor of what has been filed
    """
    source_user = db_get(session,
                         models.User,
                         (models.User.id == user_session.user_id,
                          models.User.tid == tid))

    target_tid = int(request['target_tid'])
    exchange, option = db_get_chosen_exchange(session, type, tid, target_tid,
                                              request.get('exchange_id', ''),
                                              source_itip)

    stage = option['stage']
    owner_tid = option['owner_tid']
    channel = option['channel']

    steps, answers = db_prepare_answers(session, owner_tid,
                                        option['questionnaire_id'], request['answers'])

    # The report belongs to one site and follows its encryption
    owner_state = State.tenants.get(owner_tid)
    encryption = owner_state.cache.encryption if owner_state is not None else \
        ConfigFactory(session, owner_tid).get_val('encryption')

    # The participants are the recipients of the channel on the destination
    exchange_receivers = db_get_channel_receivers(session, target_tid,
                                                  option['exchange_channel'].id)
    exchange_receivers, encryption = db_filter_eligible_receivers(session, owner_tid,
                                                                  exchange_receivers,
                                                                  encryption)
    if not exchange_receivers:
        raise errors.InputValidationError("Exchange has no eligible recipient")

    if owner_tid == target_tid:
        # filed on the channel of the exchange: its recipients hold it
        receivers, participants = exchange_receivers, []
    else:
        # lives on the sender, on the channel of origin: its recipients hold it and the recipients
        # of the exchange take part
        receivers, participants = [], exchange_receivers

    itip, crypto_tip_prv_key = db_new_exchange_report(session, owner_tid, channel, source_user,
                                                      stage, encryption)

    # Accessible to the whistleblower through a receipt issued here and kept encrypted on the
    # request
    authorization = None
    if stage == 'report' and exchange.type == 'transmission' and exchange.request_questionnaire:
        authorization = db_get_authorized_request(session, exchange.id, tid, target_tid)

    if authorization is not None:
        db_issue_receipt(session, itip, authorization, encryption, crypto_tip_prv_key)

    session.add(itip)
    session.flush()

    db_store_exchange_answers(session, itip, steps, answers)

    db_store_exchange_files(session, itip, user_session, encryption)

    db_record_exchange_origin(session, itip, stage, tid, target_tid, exchange, source_user,
                              authorization, source_itip)

    db_create_exchange_receivertips(session, receivers, itip, encryption, crypto_tip_prv_key)
    db_create_exchange_receivertips(session, participants, itip, encryption, crypto_tip_prv_key)

    db_grant_source_access(session, tid, itip, source_itip, source_user, receivers,
                           encryption, crypto_tip_prv_key)

    log_data = {
        'source_tid': tid,
        'target_tid': target_tid,
        'exchange_id': exchange.id,
        'internaltip_id': itip.id,
        'request_internaltip_id': authorization.id if authorization is not None else '',
        'source_internaltip_id': source_itip.id if source_itip is not None else ''
    }

    db_log(session, tid=tid, type=f'report_{itip.type}_created',
           user_id=user_session.user_id, object_id=itip.id, data=log_data)

    if target_tid != tid:
        db_log(session, tid=target_tid, type=f'report_{itip.type}_received',
               user_id=None, object_id=itip.id, data=log_data)

    return {
        'id': itip.id,
        'type': itip.type,
        'stage': stage,
        'source_id': source_itip.id if source_itip is not None else '',
        'target_tid': target_tid,
        'target_channel_id': channel.id,
        'progressive': itip.progressive,
        'status': itip.status,
        # The sender follows a request, and what it files on itself; a transmission is handed over
        'accessible': itip.tid == tid or stage == 'request'
    }


def db_grant_source_access(session, tid, itip, source_itip, source_user, receivers,
                           encryption, crypto_tip_prv_key):
    """
    Give the site that files the access it keeps on what it files: a communication is held by the
    recipients of the report it carries, a request is followed by the recipient that presented it,
    what is filed upon a request is handed over to the whistleblower and the receiving site

    :param session: An ORM session
    :param tid: The tenant ID of the tenant that files
    :param itip: The internaltip filed
    :param source_itip: The report carried, on a communication
    :param source_user: The recipient that files
    :param receivers: The recipients that hold the report on the site it lives on
    :param encryption: Whether the report is encrypted
    :param crypto_tip_prv_key: The private key of the report
    """
    if source_itip is not None:
        db_create_source_tenant_receivertips(session, tid, source_itip, itip,
                                             receivers, encryption, crypto_tip_prv_key)
        return

    if itip.type != 'request':
        return

    if encryption and not source_user.crypto_pub_key:
        raise errors.InputValidationError("Filing user has no encryption key")

    receiver_tip_key = GCE.asymmetric_encrypt(source_user.crypto_pub_key, crypto_tip_prv_key) \
        if encryption else b''

    db_create_receivertip(session, source_user, itip, receiver_tip_key)


@transact
def get_exchange_options(session, tid, user_session, type, target_tid, exchange_id,
                         language, itip_id=None):
    """
    Return what filing towards the other sites of the platform is composed of
    """
    unavailable = {'available': False, 'targets': [], 'target_tid': None,
                   'exchange_id': '', 'stage': '', 'questionnaire': None}

    permission = EXCHANGE_PERMISSIONS.get(type)
    if permission is not None and not user_session.has_permission(permission):
        return unavailable

    source_itip = None
    if itip_id is not None:
        _, _, source_itip = db_access_source_rtip(session, tid, user_session.user_id, itip_id)
        if not db_can_communicate_report(session, tid, source_itip):
            return unavailable
    elif not db_can_transmit(session, tid):
        return unavailable

    # Attachments are held on the session until filed: a new composition drops the leftovers
    user_session.files = []

    ret = db_get_exchange_options(session, type, tid, target_tid, exchange_id,
                                  language, source_itip)
    ret['available'] = True

    return ret


@transact
def create_exchange_report(session, tid, user_session, type, request, language,
                           itip_id=None):
    """
    File towards another site of the platform the report composed by a sender
    """
    permission = EXCHANGE_PERMISSIONS.get(type)
    if permission is not None and not user_session.has_permission(permission):
        raise errors.ForbiddenOperation

    source_itip = None
    if itip_id is not None:
        _, _, source_itip = db_access_source_rtip(session, tid, user_session.user_id, itip_id)
        if not db_can_communicate_report(session, tid, source_itip):
            raise errors.ForbiddenOperation
    elif not db_can_transmit(session, tid):
        raise errors.ForbiddenOperation

    return db_create_exchange_report(session, tid, user_session, type, request,
                                     language, source_itip)


class ExchangeHandler(BaseHandler):
    """
    Handler composing and filing what a site files on another site
    """
    check_roles = 'receiver'
    invalidate_cache = True
    exchange_type = 'transmission'

    def parse_choice(self):
        try:
            target_tid = int(self.request.args.get(b'target_tid', [b''])[0])
        except (IndexError, TypeError, ValueError):
            target_tid = None

        try:
            exchange_id = self.request.args.get(b'exchange_id', [b''])[0].decode()
        except (IndexError, TypeError, ValueError, UnicodeDecodeError):
            exchange_id = ''

        return target_tid, exchange_id

    def get(self, itip_id=None):
        target_tid, exchange_id = self.parse_choice()

        return get_exchange_options(self.request.tid, self.session,
                                    self.exchange_type, target_tid, exchange_id,
                                    self.request.language, itip_id)

    def post(self, itip_id=None):
        request = self.validate_request(self.request.content.read(),
                                        requests.ExchangeReportDesc)

        return create_exchange_report(self.request.tid, self.session,
                                      self.exchange_type, request,
                                      self.request.language, itip_id)


@transact
def get_transmissions(session, tid, user_session, language):
    """
    Return what a transmitter has transmitted

    :param session: An ORM session
    :param tid: The tenant ID
    :param user_session: The session of the transmitter
    :param language: The language the channels are named in
    :return: The trace of what the transmitter transmitted
    """
    held = {internaltip_id: rtip_id
            for internaltip_id, rtip_id
            in session.query(models.ReceiverTip.internaltip_id, models.ReceiverTip.id)
                      .filter(models.ReceiverTip.receiver_id == user_session.user_id)}

    ret = []
    for itip in session.query(models.InternalTip) \
                       .filter(models.InternalTip.operator_id == user_session.user_id) \
                       .order_by(models.InternalTip.creation_date.desc()):
        channel = session.query(models.Context) \
                         .filter(models.Context.id == itip.context_id) \
                         .one_or_none()

        ret.append({
            'id': itip.id,
            'creation_date': itip.creation_date,
            'tenant_name': ConfigFactory(session, itip.tid).get_val('name'),
            'exchange_name': get_localized_values({}, channel, ['name'], language)['name'] if channel is not None else '',
            'type': itip.type,
            'status': itip.status,
            'rtip_id': held.get(itip.id, '')
        })

    return ret


class Transmissions(ExchangeHandler):
    """
    Handler listing and filing what a transmitter transmits
    """
    check_roles = 'transmitter'
    exchange_type = 'transmission'

    def get(self, itip_id=None):
        return get_transmissions(self.request.tid, self.session,
                                 self.request.language)


class TransmissionOptions(ExchangeHandler):
    """
    Handler returning the destinations a transmitter may file towards and the
    """
    check_roles = 'transmitter'
    exchange_type = 'transmission'


class RTipCommunication(ExchangeHandler):
    """
    Handler carrying to another site what a report of this one holds
    """
    exchange_type = 'communication'

    def get(self, itip_id):
        return ExchangeHandler.get(self, itip_id)

    def post(self, itip_id):
        return ExchangeHandler.post(self, itip_id)


class ExchangeAttachment(BaseHandler):
    """
    Interface used to upload the attachments of a report being composed.
    """
    upload_handler = True
    exchange_type = 'transmission'

    def post(self, itip_id=None):
        permission = EXCHANGE_PERMISSIONS.get(self.exchange_type)
        if permission is not None and not self.session.has_permission(permission):
            raise errors.ForbiddenOperation

        self.uploaded_file['submission'] = True
        self.session.files.append(self.uploaded_file)


class TransmissionAttachment(ExchangeAttachment):
    """
    Interface used to upload the attachments of a transmission being composed
    """
    check_roles = 'transmitter'
    exchange_type = 'transmission'


class CommunicationAttachment(ExchangeAttachment):
    """
    Interface used to upload the attachments of a communication being composed
    """
    check_roles = 'receiver'
    exchange_type = 'communication'


def db_get_transmission(session, transmitted_itip_id):
    """
    Return the transmission a report was created by

    :param session: An ORM session
    :param transmitted_itip_id: The internaltip ID of the report created by the transmission
    :return: The transmission or None when the report was not created by one
    """
    return session.query(models.InternalTipTransmission) \
                  .filter(models.InternalTipTransmission.transmitting_internaltip_id == transmitted_itip_id) \
                  .one_or_none()

