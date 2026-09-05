# API handling recipient user functionalities
import json

from datetime import datetime

from nacl.encoding import Base64Encoder
from sqlalchemy.orm import aliased
from sqlalchemy.sql.expression import and_, or_

import globaleaks.handlers.recipient.export
import globaleaks.handlers.exchange
import globaleaks.handlers.recipient.insertion

from globaleaks import models
from globaleaks.handlers.base import BaseHandler
from globaleaks.handlers.recipient.rtip import db_grant_tip_access, db_revoke_tip_access, db_notify_grant_access, db_user_can_bypass_masking, redact_answers
from globaleaks.handlers.whistleblower.submission import index_answers
from globaleaks.models import get_localized_values
from globaleaks.orm import db_log, transact
from globaleaks.rest import requests, errors
from globaleaks.utils.crypto import GCE
from globaleaks.utils.utility import datetime_never
from globaleaks.handlers.exchange import db_get_presented_context_id


def _db_context_info(session, context_id, language, context_cache):
    """
    Describe a channel as the list of the reports names it, once per channel
    """
    if context_id in context_cache:
        return context_cache[context_id]

    context = session.query(models.Context).filter(models.Context.id == context_id).one_or_none()
    if context is None:
        context_cache[context_id] = {
            'name': '',
            'order': 0,
            'slug': ''
        }
        return context_cache[context_id]

    name = get_localized_values({}, context, ['name'], language)['name']
    context_cache[context_id] = {
        'name': name,
        'order': context.order or 0,
        'slug': context.slug
    }
    return context_cache[context_id]


def _db_receiver_ids_by_itip(session):
    """
    Return the recipients that have access to each report
    """
    receiver_ids_by_itip = {}

    for itip_id, receiver_id in session.query(models.ReceiverTip.internaltip_id,
                                              models.ReceiverTip.receiver_id) \
                                       .filter(models.User.id == models.ReceiverTip.receiver_id,
                                               models.User.tid == models.InternalTip.tid,
                                               models.InternalTip.id == models.ReceiverTip.internaltip_id):
        receiver_ids_by_itip.setdefault(itip_id, []).append(receiver_id)

    return receiver_ids_by_itip


def _db_listed_reports(session, tid, user_id, updated_after, updated_before):
    """
    Return the reports a recipient is shown: the ones it received and the ones of the channels it
    is on whose recipients are not selectable, paired with their answers and the identity of the
    whistleblower; the report of an exchange is listed to the owning site, and to the other side
    only where it cannot reach it through the origin
    """
    receiver_contexts = [
        context_id[0] for context_id in session.query(models.Context.id)
                                               .join(models.ReceiverContext,
                                                     models.Context.id == models.ReceiverContext.context_id)
                                               .filter(models.Context.allow_recipients_selection == False,
                                                       models.ReceiverContext.receiver_id == user_id
                                                      ).all()
    ]

    # Reached from its origin by whoever holds it: the report it was filed from, or the request
    origin_rtip = aliased(models.ReceiverTip)
    origin_held = session.query(models.InternalTipTransmission) \
                         .filter(models.InternalTipTransmission.transmitting_internaltip_id == models.InternalTip.id,
                                 origin_rtip.internaltip_id == models.InternalTipTransmission.internaltip_id,
                                 origin_rtip.receiver_id == user_id) \
                         .exists()

    return session.query(models.ReceiverTip,
                         models.InternalTip,
                         models.InternalTipAnswers,
                         models.InternalTipData) \
                  .join(models.InternalTipData,
                        and_(models.InternalTipData.internaltip_id == models.InternalTip.id,
                             models.InternalTipData.key == 'whistleblower_identity'),
                        isouter=True) \
                  .filter(or_(models.InternalTip.context_id.in_(receiver_contexts),
                              models.ReceiverTip.receiver_id == user_id),
                          or_(models.InternalTip.type != 'exchange',
                              models.InternalTip.tid == tid,
                              ~origin_held),
                          models.InternalTip.update_date >= updated_after,
                          models.InternalTip.update_date <= updated_before,
                          models.InternalTip.id == models.ReceiverTip.internaltip_id,
                          models.InternalTipAnswers.internaltip_id == models.ReceiverTip.internaltip_id) \
                  .group_by(models.ReceiverTip.id)


def _listed_answers(user_key, rtip, itip, itip_answers, label, accessible):
    """
    Return the answers and the label of a report as listed: decrypted by the key of the recipient
    that holds it, dropped when it holds none
    """
    answers = itip_answers.answers

    if itip.crypto_tip_pub_key and accessible and rtip.crypto_tip_prv_key:
        tip_key = GCE.asymmetric_decrypt(user_key, Base64Encoder.decode(rtip.crypto_tip_prv_key))

        if label:
            label = GCE.asymmetric_decrypt(tip_key, Base64Encoder.decode(label.encode())).decode()

        answers = json.loads(GCE.asymmetric_decrypt(tip_key, Base64Encoder.decode(answers.encode())).decode())
        index_answers(answers)
    elif itip.crypto_tip_pub_key:
        # remove useless and unusable crypted data
        answers = ""
        label = ""

    return answers, label


def _subscription_level(data, itip):
    """
    Return how the whistleblower is identified: not at all, from the filing, or later on
    """
    if data is None:
        return 0

    if data.creation_date == itip.creation_date:
        return 1

    return 2


def _db_redact_listed_answers(session, user_id, dict_ret):
    """
    The list shows the answers: the redactions apply here too
    """
    if not dict_ret or db_user_can_bypass_masking(session, user_id):
        return

    redactions_by_itip = {}
    for redaction in session.query(models.Redaction) \
                            .filter(models.Redaction.internaltip_id.in_(dict_ret.keys())):
        redactions_by_itip.setdefault(redaction.internaltip_id, []).append(redaction)

    for itip_id, entry in dict_ret.items():
        redactions = redactions_by_itip.get(itip_id)
        if redactions and isinstance(entry['answers'], dict):
            redact_answers(entry['answers'], redactions)


def _number_reports_by_channel(session, ret, language, context_cache):
    """
    Number the reports of each channel in the order they were filed
    """
    reports_by_context = {}
    for report in ret:
        reports_by_context.setdefault(report['context_id'], []).append(report)

    for reports in reports_by_context.values():
        reports.sort(key=lambda r: (r['creation_date'], r['progressive']))
        for index, report in enumerate(reports, start=1):
            context_order = _db_context_info(session, report['context_id'], language, context_cache)['order']
            report['channel_progressive'] = index
            report['context_count'] = index
            report['channel_progressive_sort_key'] = f'{context_order:08d}-{index:08d}'


@transact
def get_receivertips(session, tid, user_session, language, args=None):
    """
    Return list of submissions received by the specified receiver

    :param session: An ORM session
    :param tid: The tenant ID
    :param user_session: The user session
    :param language: The language to be used during data serialization
    :return: A list of submissions descriptors
    """
    user_id = user_session.user_id
    user_key = user_session.cc

    args = args or {}
    updated_after = datetime.fromtimestamp(int(args.get(b'updated_after', [b'0'])[0]))
    updated_before = datetime.fromtimestamp(int(args.get(b'updated_before', [b'32503680000'])[0]))

    receiver_ids_by_itip = _db_receiver_ids_by_itip(session)

    dict_ret = dict()
    can_transmit = globaleaks.handlers.exchange.db_can_transmit(session, tid)

    context_cache = {}

    for rtip, itip, itip_answers, data in _db_listed_reports(session, tid, user_id, updated_after, updated_before):
        label = itip.label
        important = itip.important
        reminder_date = itip.reminder_date

        # Importance, label and reminder belong to the owning tenant: not listed to the other side
        if not itip.is_owned_by(tid):
            label = ''
            important = False
            reminder_date = datetime_never()

        # The report of an exchange is presented to the recipients of each of
        # the two sites on the channel their own site knows it by
        context_id = db_get_presented_context_id(session, tid, itip)

        accessible = rtip.receiver_id == user_id
        answers, label = _listed_answers(user_key, rtip, itip, itip_answers, label, accessible)

        can_communicate = globaleaks.handlers.exchange.db_can_communicate_report(session, tid, itip)

        receiver_count = len(receiver_ids_by_itip.get(itip.id, []))
        if itip.type == 'request' and tid != itip.tid:
            receiver_count = 1

        context_info = _db_context_info(session, context_id, language, context_cache)
        if accessible or itip.id not in dict_ret:
            dict_ret[itip.id] = {
                'id': itip.id,
                'creation_date': itip.creation_date,
                'access_date': rtip.access_date,
                'last_access': itip.last_access,
                'update_date': itip.update_date,
                'expiration_date': itip.expiration_date,
                'reminder_date': reminder_date,
                'progressive': itip.progressive,
                'important': important,
                'label': label,
                'updated': rtip.last_access < itip.update_date,
                'context_id': context_id,
                'context_name': context_info['name'],
                'slug': context_info['slug'],
                'type': itip.type,
                'allow_transmission': itip.allow_transmission,
                'can_communicate': can_communicate,
                'can_transmit': can_transmit,
                'tor': itip.tor,
                'answers': answers,
                'score': itip.score,
                'status': itip.status,
                'substatus': itip.substatus,
                'receiver_count': receiver_count,
                'receiver_ids': receiver_ids_by_itip.get(itip.id, []),
                'subscription': _subscription_level(data, itip),
                'accessible': accessible
            }

    _db_redact_listed_answers(session, user_id, dict_ret)

    ret = list(dict_ret.values())

    _number_reports_by_channel(session, ret, language, context_cache)

    return ret


def db_grant_tips_access(session, tid, user_session, tips, receiver_id, log_data):
    """
    Grant a recipient access to some reports, announcing it once

    :param session: An ORM session
    :param tid: A tenant ID
    :param user_session: The session of the recipient that grants
    :param tips: The reports, paired with the access of the recipient that grants
    :param receiver_id: The recipient granted
    :param log_data: The data logged with each grant
    """
    notified = False
    for itip, rtip in tips:
        new_receiver, _ = db_grant_tip_access(session, tid, user_session, itip, rtip, receiver_id)
        if not new_receiver:
            continue

        db_log(session, tid=tid, type='grant_access', user_id=user_session.user_id, object_id=itip.id, data=log_data)

        if not notified:
            db_notify_grant_access(session, new_receiver)
            notified = True


def db_revoke_tips_access(session, tid, user_id, tips, receiver_id, log_data):
    """
    Revoke from a recipient the access to some reports

    :param session: An ORM session
    :param tid: A tenant ID
    :param user_id: The recipient that revokes
    :param tips: The reports, paired with the access of the recipient that revokes
    :param receiver_id: The recipient revoked
    :param log_data: The data logged with each revocation
    """
    for itip, _ in tips:
        if db_revoke_tip_access(session, tid, user_id, itip, receiver_id):
            db_log(session, tid=tid, type='revoke_access', user_id=user_id, object_id=itip.id, data=log_data)


@transact
def perform_tips_operation(session, tid, user_session, user_cc, operation, args):
    """
    Transaction for performing operation on submissions (grant/revoke)

    :param session: An ORM session
    :param tid: A tenant ID
    :param user_session: The session of the recipient
    :param user_cc: A recipient crypto key
    :param operation: An operation command (grant/revoke)
    :param args: The operation arguments
    """
    if operation not in ('grant', 'revoke') or not user_session.permissions.can_grant_access_to_reports:
        raise errors.ForbiddenOperation

    user_id = user_session.user_id

    log_data = {
        'recipient_id': args['receiver']
    }

    tips = session.query(models.InternalTip, models.ReceiverTip) \
                  .filter(models.ReceiverTip.receiver_id == user_id,
                          models.InternalTip.id == models.ReceiverTip.internaltip_id,
                          models.InternalTip.id.in_(args['rtips']))

    if operation == 'grant':
        db_grant_tips_access(session, tid, user_session, tips, args['receiver'], log_data)
    else:
        db_revoke_tips_access(session, tid, user_id, tips, args['receiver'], log_data)


class TipsCollection(BaseHandler):
    """

    Handler dealing with submissions fetch
    """
    check_roles = {'receiver', 'transmitter'}

    def get(self):
        return get_receivertips(self.request.tid,
                                self.session,
                                self.request.language,
                                self.request.args)


class Operations(BaseHandler):
    """
    Handler that enables to issue operations on submissions
    """
    check_roles = {'receiver', 'transmitter'}

    def put(self):
        request = self.validate_request(self.request.content.read(), requests.OpsDesc)

        return perform_tips_operation(self.request.tid,
                                      self.session,
                                      self.session.cc,
                                      request['operation'],
                                      request['args'])
