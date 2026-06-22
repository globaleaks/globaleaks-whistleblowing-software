# Handlers dealing with report forwarding for receivers
import copy
import json

from nacl.encoding import Base64Encoder

from globaleaks import models
from globaleaks.handlers.admin.questionnaire import db_get_questionnaire
from globaleaks.handlers.admin.tenant import db_ensure_forward_channel, \
                                             db_ensure_forward_questionnaire, \
                                             db_ensure_forward_request_questionnaire, \
                                             db_ensure_forward_request_channel
from globaleaks.handlers.base import BaseHandler
from globaleaks.handlers.whistleblower.submission import db_archive_questionnaire_schema, \
                                                         db_assign_submission_progressive, \
                                                         db_create_receivertip
from globaleaks.models.config import ConfigFactory
from globaleaks.orm import db_get, db_log, transact
from globaleaks.rest import errors, requests
from globaleaks.state import State
from globaleaks.utils.crypto import GCE, generateRandomKey, sha256
from globaleaks.utils.json import JSONEncoder
from globaleaks.utils.utility import datetime_now, datetime_null, get_expiration


def _tenant_list_allows(values, tid):
    values = values or []
    return '*' in values or tid in values or str(tid) in values


def db_access_source_rtip(session, tid, user_id, itip_id):
    return db_get(session,
                  (models.User, models.ReceiverTip, models.InternalTip),
                  (models.User.id == user_id,
                   models.User.tid == tid,
                   models.InternalTip.id == itip_id,
                   models.ReceiverTip.receiver_id == models.User.id,
                   models.ReceiverTip.internaltip_id == models.InternalTip.id))


def db_get_forward_channel(session, target_tid):
    channel = db_ensure_forward_channel(session, target_tid)
    if channel.type != 'forward':
        raise errors.InputValidationError("Target tenant has no forward channel configured")
    return channel


def db_get_forward_request_channel(session, target_tid=1):
    if target_tid == 1:
        return db_ensure_forward_request_channel(session)

    forward_request_channel_id = ConfigFactory(session, target_tid).get_val('forward_request_channel')
    if not forward_request_channel_id:
        raise errors.InputValidationError("Target tenant has no forward request channel configured")

    return db_get(session,
                  models.Context,
                  (models.Context.id == forward_request_channel_id,
                   models.Context.tid == target_tid,
                   models.Context.type == 'forward-request'))


def db_get_forward_questionnaire(session, tid, language):
    forward_questionnaire = db_ensure_forward_questionnaire(session)
    questionnaire_id = forward_questionnaire.id

    return db_get_questionnaire(session, tid, questionnaire_id, language, True)


def db_get_forward_request_questionnaire(session, tid, language):
    forward_request_questionnaire = db_ensure_forward_request_questionnaire(session)
    questionnaire_id = forward_request_questionnaire.id

    return db_get_questionnaire(session, tid, questionnaire_id, language, True)


def db_tenant_forward_request_pending(session, source_tid):
    requests_ = session.query(models.InternalTip, models.InternalTipData) \
                       .filter(models.InternalTip.tid == 1,
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


def db_tenant_forward_request_authorized(session, source_tid):
    requests_ = session.query(models.InternalTip, models.InternalTipData) \
                       .filter(models.InternalTip.tid == 1,
                               models.InternalTip.type == 'submission',
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


def db_get_forward_source_tid(session, itip):
    data = session.query(models.InternalTipData) \
                  .filter(models.InternalTipData.internaltip_id == itip.id,
                          models.InternalTipData.key == 'forwarded_from') \
                  .one_or_none()
    if data is None:
        return None

    try:
        return int(data.value.get('source_tid'))
    except (AttributeError, TypeError, ValueError):
        return None


def db_is_forwardable_report(session, source_tid, source_itip):
    if source_itip.type == 'submission':
        return True

    if source_itip.type != 'forward' or source_tid != 1:
        return False

    original_source_tid = db_get_forward_source_tid(session, source_itip)

    return original_source_tid is not None and original_source_tid != 1


def db_can_forward_report(session, source_tid, source_itip):
    if not db_is_forwardable_report(session, source_tid, source_itip):
        return False

    if source_tid != 1 and not db_tenant_forward_request_authorized(session, source_tid):
        return False

    source_config = ConfigFactory(session, source_tid)

    return source_config.get_val('enable_forward_out') and \
        bool(source_config.get_val('send_forwarding'))


def db_can_send_forward_to(session, source_tid, target_tid, source_itip):
    if not db_can_forward_report(session, source_tid, source_itip):
        return False

    source_config = ConfigFactory(session, source_tid)

    return _tenant_list_allows(source_config.get_val('send_forwarding'), target_tid)


def db_can_send_forward_request_to(session, source_tid, target_tid):
    if source_tid == 1:
        return False

    source_config = ConfigFactory(session, source_tid)

    return source_config.get_val('enable_forward_out') and \
        _tenant_list_allows(source_config.get_val('send_forwarding_request'), target_tid)


def db_is_forward_direction_allowed(source_tid, target_tid):
    if source_tid == 1:
        return target_tid != 1

    return target_tid == 1


def db_accepts_forward(session, target_tid, source_tid, source_itip):
    if not db_is_forward_direction_allowed(source_tid, target_tid):
        return False

    target_config = ConfigFactory(session, target_tid)
    if not target_config.get_val('accept_forwarding'):
        return False

    return db_can_send_forward_to(session, source_tid, target_tid, source_itip) and \
        target_config.get_val('enable_forward_in') and \
        _tenant_list_allows(target_config.get_val('accept_forwarding_from'), source_tid)


def db_get_forward_targets(session, source_tid, source_itip):
    targets = []
    for tenant in session.query(models.Tenant).filter(models.Tenant.active == True,
                                                      models.Tenant.id != source_tid):
        if not db_accepts_forward(session, tenant.id, source_tid, source_itip):
            continue

        try:
            db_get_forward_channel(session, tenant.id)
        except errors.GLException:
            continue

        tenant_config = ConfigFactory(session, tenant.id).serialize('tenant')
        targets.append({
            'id': tenant.id,
            'name': tenant_config.get('name', ''),
            'subdomain': tenant_config.get('subdomain', '')
        })

    return targets


def db_can_request_forward(session, source_tid, source_itip=None):
    if source_tid == 1:
        return False

    if source_itip is not None and source_itip.type != 'submission':
        return False

    if db_tenant_forward_request_pending(session, source_tid):
        return False

    if not db_can_send_forward_request_to(session, source_tid, 1):
        return False

    target_config = ConfigFactory(session, 1)
    if not target_config.get_val('accept_forwarding') or \
       not _tenant_list_allows(target_config.get_val('accepts_requests_of_forward_from'), source_tid):
        return False

    try:
        return db_get_forward_request_channel(session, 1) is not None
    except errors.GLException:
        return False


def db_get_forward_request_target(session, source_tid):
    if source_tid == 1:
        raise errors.ForbiddenOperation

    if not db_can_send_forward_request_to(session, source_tid, 1):
        raise errors.ForbiddenOperation

    target_config = ConfigFactory(session, 1)
    if not target_config.get_val('accept_forwarding') or \
       not _tenant_list_allows(target_config.get_val('accepts_requests_of_forward_from'), source_tid):
        raise errors.ForbiddenOperation

    channel = db_get_forward_request_channel(session, 1)
    tenant_config = target_config.serialize('tenant')

    return {
        'id': 1,
        'name': tenant_config.get('name', ''),
        'subdomain': tenant_config.get('subdomain', ''),
        'hostname': tenant_config.get('hostname', ''),
        'context_id': channel.id,
        'source_tid': source_tid
    }


def db_query_forward_receivers(session, target_tid):
    return session.query(models.User) \
                  .join(models.UserProfilePermission,
                        models.UserProfilePermission.profile_id == models.User.profile_id) \
                  .filter(models.User.tid == target_tid,
                          models.User.enabled == True,
                          models.User.role == 'receiver',
                          models.UserProfilePermission.permission == 'can_forward_reports')


def db_query_forward_request_receivers(session, target_tid):
    return session.query(models.User) \
                  .join(models.UserProfilePermission,
                        models.UserProfilePermission.profile_id == models.User.profile_id) \
                  .filter(models.User.tid == target_tid,
                          models.User.enabled == True,
                          models.User.role == 'receiver',
                          models.UserProfilePermission.permission == 'can_request_forward')


def db_get_forward_receivers(session, target_tid, channel_id, crypto_is_available):
    channel = db_get(session,
                     models.Context,
                     (models.Context.id == channel_id,
                      models.Context.tid == target_tid))

    receiver_query = db_query_forward_request_receivers(session, target_tid) \
        if channel.type == 'forward-request' else \
        db_query_forward_receivers(session, target_tid)

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


def sanitize_forward_answers(schema, answers):
    sanitized = copy.deepcopy(answers)

    def sanitize_fields(fields):
        for field in fields:
            field_id = field.get('id')
            if field_id and (field.get('template_id') == 'whistleblower_identity' or
                             field.get('type') in ('fileupload', 'voice')):
                sanitized[field_id] = ''

            sanitize_fields(field.get('children', []))

    for step in schema:
        sanitize_fields(step.get('children', []))

    return sanitized


@transact
def get_forward_options(session, tid, user_session, itip_id, language):
    if not user_session.has_permission('can_forward_reports'):
        raise errors.ForbiddenOperation

    _, _, source_itip = db_access_source_rtip(session, tid, user_session.user_id, itip_id)
    if not db_can_forward_report(session, tid, source_itip):
        raise errors.ForbiddenOperation

    return {
        'questionnaire': db_get_forward_questionnaire(session, tid, language),
        'tenants': db_get_forward_targets(session, tid, source_itip)
    }


@transact
def get_forward_request_options(session, tid, user_session, language):
    if not user_session.has_permission('can_request_forward'):
        raise errors.ForbiddenOperation

    if not db_can_request_forward(session, tid):
        return {'available': False}

    tenant = db_get_forward_request_target(session, tid)
    return {
        'available': True,
        'questionnaire': db_get_forward_request_questionnaire(session, tid, language),
        'tenant': tenant,
        'tenants': [tenant]
    }


@transact
def create_forward_request(session, tid, user_session, request):
    if not user_session.has_permission('can_request_forward'):
        raise errors.ForbiddenOperation

    source_user = db_get(session,
                         models.User,
                         (models.User.id == user_session.user_id,
                          models.User.tid == tid))

    if not db_can_request_forward(session, tid):
        raise errors.ForbiddenOperation

    target_tid = 1
    if int(request['target_tid']) != target_tid:
        raise errors.ForbiddenOperation

    target_config = ConfigFactory(session, target_tid)
    target_tenant = session.query(models.Tenant) \
                           .filter(models.Tenant.id == target_tid,
                                   models.Tenant.active == True) \
                           .one_or_none()
    if target_tenant is None:
        raise errors.InputValidationError("Invalid target tenant")

    target_channel = db_get_forward_request_channel(session, target_tid)
    forward_questionnaire = db_get_forward_request_questionnaire(session, tid, None)

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

    answers = sanitize_forward_answers(forward_questionnaire['steps'], request['answers'])
    questionnaire_hash = db_archive_questionnaire_schema(session, forward_questionnaire['steps'])

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
    session.add(target_answers)

    data = models.InternalTipData()
    data.internaltip_id = target_itip.id
    data.key = 'forward_request'
    data.creation_date = target_itip.creation_date
    data.value = {
        'source_tid': tid,
        'requester_user_id': source_user.id
    }
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
    forward_questionnaire = db_get_forward_questionnaire(session, tid, None)

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

    answers = sanitize_forward_answers(forward_questionnaire['steps'], request['answers'])
    questionnaire_hash = db_archive_questionnaire_schema(session, forward_questionnaire['steps'])

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
    session.add(target_answers)

    forwarding = models.InternalTipForwarding()
    forwarding.internaltip_id = source_itip.id
    forwarding.forwarding_internaltip_id = target_itip.id
    session.add(forwarding)

    data = models.InternalTipData()
    data.internaltip_id = str(target_itip.id)
    data.key = 'forwarded_from'
    data.creation_date = target_itip.creation_date
    data.value = {'source_tid': source_itip.tid}

    session.add(data)

    for receiver in receivers:
        receiver_tip_key = GCE.asymmetric_encrypt(receiver.crypto_pub_key, crypto_tip_prv_key) \
            if target_encryption else b''
        db_create_receivertip(session, receiver, target_itip, receiver_tip_key)

    if source_user.id not in {receiver.id for receiver in receivers}:
        if target_encryption:
            if not source_user.crypto_pub_key:
                raise errors.InputValidationError("Forwarding user has no encryption key")
            receiver_tip_key = GCE.asymmetric_encrypt(source_user.crypto_pub_key, crypto_tip_prv_key)
        else:
            receiver_tip_key = b''
        db_create_receivertip(session, source_user, target_itip, receiver_tip_key)

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
        'privacy': privacy
    }
    target_log_data = {
        'source_tid': source_itip.tid,
        'target_internaltip_id': target_itip.id,
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
        return get_forward_options(self.request.tid,
                                   self.session,
                                   itip_id,
                                   self.request.language)

    def post(self, itip_id):
        request = self.validate_request(self.request.content.read(), requests.ForwardReportDesc)
        return create_forward(self.request.tid,
                              self.session,
                              itip_id,
                              request,
                              self.request.language)


class RTipForwardRequest(BaseHandler):
    """
    Interface used to open the forward request channel on the accepting tenant.
    """
    check_roles = 'receiver'

    def get(self, itip_id):
        return get_forward_request_options(self.request.tid,
                                           self.session,
                                           self.request.language)

    def post(self, itip_id):
        request = self.validate_request(self.request.content.read(), requests.ForwardReportDesc)
        return create_forward_request(self.request.tid,
                                      self.session,
                                      request)


class RTipsForwardRequest(BaseHandler):
    """
    Interface used to create a tenant-level forward request.
    """
    check_roles = 'receiver'

    def get(self):
        return get_forward_request_options(self.request.tid,
                                           self.session,
                                           self.request.language)

    def post(self):
        request = self.validate_request(self.request.content.read(), requests.ForwardReportDesc)
        return create_forward_request(self.request.tid,
                                      self.session,
                                      request)
