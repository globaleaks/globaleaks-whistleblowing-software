# Handlers dealing with tip interface for receivers (rtip)
import copy
import json
import mimetypes
import os
import re
import time

from datetime import datetime

from nacl.encoding import Base64Encoder
from sqlalchemy import and_, or_
from sqlalchemy.orm import aliased
from twisted.internet.threads import deferToThread
from twisted.internet.defer import inlineCallbacks

from globaleaks import models
from globaleaks.handlers.auditlog import db_get_report_audit_log
from globaleaks.handlers.admin.context import admin_serialize_context
from globaleaks.handlers.admin.node import db_admin_serialize_node
from globaleaks.handlers.admin.notification import db_get_notification
from globaleaks.handlers.base import BaseHandler
from globaleaks.handlers.operation import OperationHandler
from globaleaks.handlers.public import serialize_questionnaire
from globaleaks.handlers.whistleblower.submission import data_hashes, db_archive_questionnaire_schema, \
    db_create_receivertip, db_validate_answers, decrypt_tip, extract_statistical_data, MAX_ANSWERS_DEPTH
from globaleaks.handlers.user import serialize_user, user_serialize_user
from globaleaks.models import UserProfile, serializers

from globaleaks.orm import db_get, db_del, db_log, transact
from globaleaks.rest import errors, requests
from globaleaks.settings import Settings
from globaleaks.state import State
from globaleaks.utils.antivirus import enqueue_antivirus_scan, enqueue_tip_files_for_rescan, get_av_result, prepare_file_download, serialize_files_metadata_csv
from globaleaks.utils.crypto import GCE, sha256, sha512
from globaleaks.utils.fs import directory_traversal_check
from globaleaks.utils.log import log
from globaleaks.utils.templating import Templating, mail_uses_smtp2
from globaleaks.utils.utility import datetime_now, datetime_null, datetime_never, get_expiration
from globaleaks.utils.json import JSONEncoder
from globaleaks.models.config import db_get_config_variable
from io import BytesIO
from globaleaks.utils.securetempfile import SecureTemporaryFile
from globaleaks.utils.zipstream import ZipStream

@transact
def get_report_audit_log(session, tid, user_id, itip_id):
    _, _, _ = db_access_rtip(session, tid, user_id, itip_id)

    return db_get_report_audit_log(session, tid, itip_id)


def db_notify_grant_access(session, user):
    """
    Transaction for the creation of notifications related to grant of access to report
    :param session: An ORM session
    :param user: A user to which send the notification
    """
    notif = State.tenants[user.tid].cache.notification
    if (notif and not notif.enable_receiver_notification_emails) or not user.notification:
        return

    data = {
        'type': 'tip_access'
    }

    data['user'] = serialize_user(session, user, user.language)
    data['node'] = db_admin_serialize_node(session, user.tid, user.language)

    data['notification'] = db_get_notification(session, user.tid, user.language)

    subject, body = Templating().get_mail_subject_and_body(data)

    session.add(models.Mail({
        'address': data['user']['mail_address'],
        'subject': subject,
        'body': body,
        'tid': user.tid,
        'secondary_smtp': mail_uses_smtp2(data['notification'], data['type'])
    }))


def db_grant_tip_access(session, tid, user_session, itip, rtip, receiver_id):
    """
    Transaction for granting a user access to a report

    :param session: An ORM session
    :param tid: A tenant ID of the user performing the operation
    :param user_session: A user session
    :param itip: An itip on which to perform operation
    :param rtip: An rtip on which to perform operation
    :param receiver_id: A user ID of the the user to which grant access to the report
    """
    user_id = user_session.user_id
    user_cc = user_session.cc

    existing = session.query(models.ReceiverTip).filter(models.ReceiverTip.receiver_id == receiver_id,
                                                        models.ReceiverTip.internaltip_id == itip.id).one_or_none()

    if existing:
        return None, None

    new_receiver = db_get(session,
                          models.User,
                          (models.User.tid == tid,
                           models.User.id == receiver_id,
                           models.User.role == 'receiver',
                           models.User.enabled.is_(True)))

    if itip.crypto_tip_pub_key and not new_receiver.crypto_pub_key:
        # Access to encrypted submissions could be granted only if the recipient is fully activated with encryption keys
        return None, None

    _tip_key = b''
    if itip.crypto_tip_pub_key:
        _tip_key = GCE.asymmetric_decrypt(user_cc, Base64Encoder.decode(rtip.crypto_tip_prv_key))
        _tip_key = GCE.asymmetric_encrypt(new_receiver.crypto_pub_key, _tip_key)

    new_rtip = db_create_receivertip(session, new_receiver, itip, _tip_key)
    new_rtip.new = False
    if itip.deprecated_crypto_files_pub_key:
        _files_key = GCE.asymmetric_decrypt(user_cc, Base64Encoder.decode(rtip.deprecated_crypto_files_prv_key))
        new_rtip.deprecated_crypto_files_prv_key = Base64Encoder.encode(
            GCE.asymmetric_encrypt(new_receiver.crypto_pub_key, _files_key))

    wbfiles = session.query(models.WhistleblowerFile) \
                     .filter(models.WhistleblowerFile.receivertip_id == rtip.id)

    for wbfile in wbfiles:
        wf = models.WhistleblowerFile()
        wf.internalfile_id = wbfile.internalfile_id
        wf.receivertip_id = new_rtip.id
        wf.new = False
        session.add(wf)

    return new_receiver, new_rtip


def db_revoke_tip_access(session, tid, user_id, itip, receiver_id):
    """
    Transaction for revoking a user access to a report

    :param session: An ORM session
    :param tid: A tenant ID of the user performing the operation
    :param user_id: A user ID of the user performing the operation
    :param itip: An itip on which to perform operation
    :param receiver_id: A user ID of the the user to which revoke access to the report
    """
    # The access is revocable only within the tenant of the user performing
    # the operation: on the report created by a forward neither tenant can
    # remove the recipients of the other
    rtip = session.query(models.ReceiverTip) \
        .filter(models.ReceiverTip.internaltip_id == itip.id,
                models.ReceiverTip.receiver_id == receiver_id,
                models.User.id == models.ReceiverTip.receiver_id,
                models.User.tid == tid).one_or_none()

    if rtip is None:
        return False

    session.delete(rtip)

    return True


@transact
def grant_tip_access(session, tid, user_session, itip_id, receiver_id):
    user_id = user_session.user_id

    log_data = {
        'recipient_id': receiver_id
    }

    user, rtip, itip = db_access_rtip(session, tid, user_id, itip_id)

    if user_id == receiver_id or not user_session.permissions.can_grant_access_to_reports:
        raise errors.ForbiddenOperation

    new_receiver, _ = db_grant_tip_access(session, tid, user_session, itip, rtip, receiver_id)
    if new_receiver:
        db_notify_grant_access(session, new_receiver)
        db_log(session, tid=tid, type='grant_access', user_id=user_id, object_id=itip.id, data=log_data)


@transact
def revoke_tip_access(session, tid, user_session, itip_id, receiver_id):
    user_id = user_session.user_id

    log_data = {
        'recipient_id': receiver_id
    }

    user, rtip, itip = db_access_rtip(session, tid, user_id, itip_id)

    if user_id == receiver_id or not user_session.permissions.can_grant_access_to_reports:
        raise errors.ForbiddenOperation

    if db_revoke_tip_access(session, tid, user, itip, receiver_id):
        db_log(session, tid=tid, type='revoke_access', user_id=user_id, object_id=itip.id, data=log_data)


@transact
def transfer_tip_access(session, tid, user_session, itip_id, receiver_id):
    user_id = user_session.user_id

    log_data = {
        'recipient_id': receiver_id
    }

    user, rtip, itip = db_access_rtip(session, tid, user_id, itip_id)
    if user_id == receiver_id or not user_session.permissions.can_transfer_access_to_reports:
        raise errors.ForbiddenOperation

    new_receiver, _ = db_grant_tip_access(session, tid, user_session, itip, rtip, receiver_id)
    if new_receiver:
        if not db_revoke_tip_access(session, tid, user, itip, user_id):
            raise errors.ForbiddenOperation

        db_notify_grant_access(session, new_receiver)
        db_log(session, tid=tid, type='transfer_access', user_id=user_id, object_id=itip.id, data=log_data)


def db_get_ttl(session, orm_object_model, orm_object_id):
    """
    Transaction for retrieving the data retention

    :param session: An ORM session
    :param orm_object_model: An ORM object type
    :param orm_object_id: The ORM object id
    """
    # we exploit the fact that we have the same "tip_timetolive" name in
    # the SubmissionSubStatus, SubmissionStatus and Context tables
    row = (
        session.query(orm_object_model.tip_timetolive)
        .filter(orm_object_model.id == orm_object_id)
        .one_or_none()
    )

    # row is either a tuple-like result (ttl,) or None
    return row[0] if row and row[0] is not None else 365


def db_recalculate_data_retention(session, itip, report_reopen_request):
    """
    Transaction for recaulating the data retention after a status change

    :param session: An ORM session
    :param itip: The internaltip ORM object
    """
    prev_expiration_date = itip.expiration_date
    if report_reopen_request:
        # use the context-defined data retention
        ttl = db_get_ttl(session, models.Context, itip.context_id)
        if ttl > 0:
            itip.expiration_date = get_expiration(ttl)
        else:
            itip.expiration_date = datetime_never()
    elif itip.status == "closed" and itip.substatus is not None:
        ttl = db_get_ttl(session, models.SubmissionSubStatus, itip.substatus)
        if ttl > 0:
            itip.expiration_date = get_expiration(ttl)

    return prev_expiration_date, itip.expiration_date


def db_update_submission_status(session, tid, user_id, itip, status_id, substatus_id=None):
    """
    Transaction for registering a change of status of a submission

    :param session: An ORM session
    :param tid: A tenant ID of the user performing the operation
    :param user_id: A user ID of the user changing the state
    :param itip:  The ID of the submission
    :param status_id:  The new status ID
    :param substatus_id: A new substatus ID
    """
    if status_id == 'new':
        return

    db_get(session,
           models.SubmissionStatus,
           (models.SubmissionStatus.tid == tid,
            models.SubmissionStatus.id == status_id))

    if substatus_id:
        db_get(session,
               models.SubmissionSubStatus,
               (models.SubmissionSubStatus.tid == tid,
                models.SubmissionSubStatus.submissionstatus_id == status_id,
                models.SubmissionSubStatus.id == substatus_id))

    report_close_request = itip.status != "closed" and status_id == "closed"
    report_reopen_request = itip.status == "closed" and status_id == "opened"

    itip.status = status_id
    itip.substatus = substatus_id or None

    log_data = {
      'status': itip.status,
      'substatus': itip.substatus
    }

    db_log(session, tid=tid, type='update_report_status', user_id=user_id, object_id=itip.id, data=log_data)

    if report_close_request:
        itip.reminder_date = datetime_never()

    prev_expiration_date, currect_expiration_date = db_recalculate_data_retention(session, itip, report_reopen_request)

    if prev_expiration_date != itip.expiration_date:
       log_data = {
           'prev_expiration_date': int(datetime.timestamp(prev_expiration_date)),
           'curr_expiration_date': int(datetime.timestamp(itip.expiration_date))
       }

       db_log(session, tid=tid, type='update_report_expiration', user_id=user_id, object_id=itip.id, data=log_data)


def db_update_temporary_redaction(session, tid, user_id, redaction, redaction_data):
    """
    Update the redaction data of a tip

    :param session: An ORM session
    :param tid: A tenant ID of the user performing the operation
    :param user_id: A user ID of the user changing the state
    :param itip_id: The ID of the Tip instance to be updated
    :param id: The object_id
    :param redaction_data: The updated redaction data
    """
    new_temporary_redaction = get_new_temporary_redaction(redaction_data['temporary_redaction'], redaction.permanent_redaction)

    log_data = {
        'old_remporary_redaction': redaction.temporary_redaction,
        'new_temporary_redaction': new_temporary_redaction
    }

    db_log(session, tid=tid, type='update_redaction', user_id=user_id, object_id=redaction.id, data=log_data)

    if len(new_temporary_redaction) == 0 and (not redaction.permanent_redaction or len(redaction.permanent_redaction) == 0):
        session.delete(redaction)
    else:
        redaction.temporary_redaction = new_temporary_redaction
        redaction.update_date = datetime.now()


def redact_content(content, ranges, character='0x2588'):
    # The redaction ranges are produced by the client from
    # textarea.selectionStart/selectionEnd, which are UTF-16 code-unit offsets.
    # Operate on UTF-16 code units here too, otherwise any astral character
    # (U+10000+, e.g. emoji) before a range would shift the applied mask and
    # leak the leading character(s) of the redacted value (the redaction is
    # destructive, so the mis-masked string becomes the only stored copy).
    mask = chr(int(character[2:], 16)).encode('utf-16-le')
    data = content.encode('utf-16-le')
    result = [data[i:i + 2] for i in range(0, len(data), 2)]
    length = len(result)

    normalized = []
    for r in ranges if isinstance(ranges, list) else []:
        # Ignore range elements that are not mappings: the stored value comes
        # from a JSON column with no descriptor, so a malformed redaction could
        # otherwise carry a non-dict element (e.g. an int, string or list) and
        # crash this consumption path for every non-privileged co-recipient.
        if not isinstance(r, dict):
            continue

        start, end = r.get('start', 0), r.get('end', 0)

        # Ignore ranges that are not expressed as plain integers (e.g. floats,
        # None or the '-inf'/'inf' sentinels used for file redactions) and clamp
        # the bounds to the actual content length so that a stored range can
        # never drive an allocation larger than the content itself.
        if isinstance(start, bool) or isinstance(end, bool) or \
                not isinstance(start, int) or not isinstance(end, int):
            continue

        start = max(0, min(start, length))
        end = max(0, min(end + 1, length))

        if start < end:
            normalized.append((start, end))

    for start, end in sorted(normalized):
        result[start:end] = [mask] * (end - start)

    return b''.join(result).decode('utf-16-le', 'replace')


def db_redact_data(session, tid, user_id, redaction, temporary_redaction, permanent_redaction):
    """
    Transaction for updating redaction data

    :param session: An ORM session
    :param tid: A tenant ID
    :param user_id: The user ID of the user performing the operation
    :param redaction: Object used to update mask in database
    :param temporary_redaction: new permanent ranges that to be marked
    :param permanent_redaction: existing temporary ranges that are marked
    :param redaction_data: redaction request
    """
    log_data = {
        'old_temporary_redaction': redaction.temporary_redaction,
        'new_temporary_redaction': temporary_redaction,
        'old_permanent_redaction': redaction.permanent_redaction,
        'new_permanent_redaction': permanent_redaction,
    }

    db_log(session, tid=tid, type='update_redaction', user_id=user_id, object_id=redaction.id, data=log_data)

    redaction.temporary_redaction = temporary_redaction
    redaction.permanent_redaction = permanent_redaction
    redaction.update_date = datetime.now()


def validate_ranges(current_mask, new_mask):
    for new_range in new_mask:
        new_start, new_end = new_range['start'], new_range['end']
        is_within = False

        for current_range in current_mask:
            current_start, current_end = current_range['start'], current_range['end']
            if current_start <= new_start <= new_end <= current_end:
                is_within = True
                break

        if not is_within:
            return False

    return True


def merge_and_sort_ranges(list1, list2):
    list2_merged = []
    current_range = None

    if not list1 and not list2:
        return []

    for range_item in list2:
        if current_range is None:
            current_range = range_item
        elif range_item['start'] <= current_range['end'] + 1:
            current_range['end'] = max(current_range['end'], range_item['end'])
        else:
            list2_merged.append(current_range)
            current_range = range_item

    if current_range:
        list2_merged.append(current_range)

    combined_ranges = list1 + list2_merged
    combined_ranges.sort(key=lambda x: x['start'])

    merged_ranges = []
    current_range = combined_ranges[0]

    for range_item in combined_ranges[1:]:
        if range_item['start'] <= current_range['end'] + 1:
            current_range['end'] = max(current_range['end'], range_item['end'])
        else:
            merged_ranges.append(current_range)
            current_range = range_item

    merged_ranges.append(current_range)

    return merged_ranges


def get_new_temporary_redaction(current_mask, new_mask):
    result = []

    # Add the current mask ranges to the result list
    for range_ in current_mask:
        result.append(range_)

    # Iterate through the new mask ranges and remove overlapping ranges
    for new_range in new_mask:
        new_start, new_end = new_range['start'], new_range['end']
        updated_result = []

        # Check for overlaps with each range in the current mask
        for current_range in result:
            current_start, current_end = current_range['start'], current_range['end']

            # Case 1: No overlap, keep the current range
            if new_end < current_start or new_start > current_end:
                updated_result.append(current_range)

            # Case 2: Overlap, split the current range into two if needed
            else:
                if new_start > current_start:
                    updated_result.append({'start': current_start, 'end': new_start - 1})
                if new_end < current_end:
                    updated_result.append({'start': new_end + 1, 'end': current_end})

        result = updated_result

    return merge_and_sort_ranges(result, [])


def db_redact_comment(session, tid, user_id, itip_id, redaction, redaction_data, tip_data):
    currentMaskedData = next((masked_content for masked_content in tip_data['redactions'] if
                              masked_content['id'] == redaction_data['id']), None)

    if not currentMaskedData or not validate_ranges(currentMaskedData['temporary_redaction'], redaction_data['permanent_redaction']):
        return

    currentMaskedContent = next((masked_content for masked_content in tip_data.get('comments', []) if
                                 masked_content['id'] == redaction_data['reference_id']), None)

    if not currentMaskedContent:
        return

    new_temporary_redaction = get_new_temporary_redaction(currentMaskedData['temporary_redaction'],
                                                          redaction_data['permanent_redaction'])

    new_permanent_redaction = merge_and_sort_ranges(currentMaskedData['permanent_redaction'],
                                                    redaction_data['permanent_redaction'])

    db_redact_data(session, tid, user_id, redaction, new_temporary_redaction, new_permanent_redaction)

    content = redact_content(currentMaskedContent.get('content'), new_permanent_redaction)

    comment = session.query(models.Comment).get(redaction_data['reference_id'])
    comment.content = Base64Encoder.encode(GCE.asymmetric_encrypt(itip_id.crypto_tip_pub_key, content)).decode()


def db_redact_answers(answers, redaction, depth=0):
    if depth >= MAX_ANSWERS_DEPTH:
        return

    for key in answers:
        if not re.match(requests.uuid_regexp, key) or \
                not isinstance(answers[key], list):
            continue

        for inner_idx, answer in enumerate(answers[key]):
            if 'value' in answer:
                if key == redaction.reference_id and answer['index'] == redaction.entry:
                    answer['value'] = redact_content(answer['value'], redaction.permanent_redaction)
                    return
            else:
                db_redact_answers(answer, redaction, depth + 1)


def db_redact_whistleblower_identities(whistleblower_identities, redaction, ranges=None, character='0x2588', depth=0):
    # The identity is stored/extracted as a fieldgroup answer keyed by field id
    # and, unlike questionnaire answers, is not indexed at read time; it is
    # therefore matched by reference id only (never by entry/index). The write
    # path masks it destructively with the permanent redaction; the consumption
    # path passes the temporary redaction and the lighter mask character.
    if depth >= MAX_ANSWERS_DEPTH:
        return

    if ranges is None:
        ranges = redaction.permanent_redaction

    for key in whistleblower_identities:
        # The identity entry carries, besides the answers of the identity
        # fields, scalar keys of its own (e.g. 'required_status', 'index'):
        # only the lists of answer entries are traversed, or a string value
        # would be iterated character by character and indexed as a mapping.
        if not isinstance(whistleblower_identities[key], list):
            continue
        for inner_idx, whistleblower_identity in enumerate(whistleblower_identities[key]):
            if not isinstance(whistleblower_identity, dict):
                continue
            if 'value' in whistleblower_identity:
                if key == redaction.reference_id:
                    whistleblower_identity['value'] = redact_content(whistleblower_identity['value'], ranges, character)
                    return
            else:
                db_redact_whistleblower_identities(whistleblower_identity, redaction, ranges, character, depth + 1)


def db_redact_answers_recursively(session, tid, user_id, itip_id, redaction, redaction_data, tip_data):
    currentMaskedData = next((masked_content for masked_content in tip_data['redactions'] if
                              masked_content['id'] == redaction_data['id']), None)

    if not currentMaskedData or not validate_ranges(currentMaskedData['temporary_redaction'], redaction_data['permanent_redaction']):
        return

    index = next((i for i, q in enumerate(tip_data['questionnaires'])
                  if redaction.reference_id in json.dumps(q['answers'])), None)
    if index is None:
        return

    new_temporary_redaction = get_new_temporary_redaction(currentMaskedData['temporary_redaction'],
                                                          copy.deepcopy(redaction_data['permanent_redaction']))

    new_permanent_redaction = merge_and_sort_ranges(currentMaskedData['permanent_redaction'],
                                                    redaction_data['permanent_redaction'])

    db_redact_data(session, tid, user_id, redaction, new_temporary_redaction, new_permanent_redaction)

    answers = tip_data['questionnaires'][index]['answers']

    db_redact_answers(answers, redaction)

    _content = answers

    if itip_id.crypto_tip_pub_key:
        _content = Base64Encoder.encode(
            GCE.asymmetric_encrypt(itip_id.crypto_tip_pub_key, json.dumps(_content, cls=JSONEncoder).encode())).decode()

    itip_answers = session.query(models.InternalTipAnswers) \
                          .filter_by(internaltip_id=currentMaskedData['internaltip_id']) \
                          .order_by(models.InternalTipAnswers.creation_date.asc()) \
                          .offset(index).limit(1).one_or_none()

    if itip_answers:
        itip_answers.answers = _content


def db_redact_whistleblower_identity(session, tid, user_id, itip_id, redaction, redaction_data, tip_data):
    currentMaskedData = next((masked_content for masked_content in tip_data['redactions'] if
                              masked_content['id'] == redaction_data['id']), None)

    if not currentMaskedData or not validate_ranges(currentMaskedData['temporary_redaction'], redaction_data['permanent_redaction']):
        return

    new_temporary_redaction = get_new_temporary_redaction(currentMaskedData['temporary_redaction'],
                                                          copy.deepcopy(redaction_data['permanent_redaction']))

    new_permanent_redaction = merge_and_sort_ranges(currentMaskedData['permanent_redaction'],
                                                    redaction_data['permanent_redaction'])

    db_redact_data(session, tid, user_id, redaction, new_temporary_redaction, new_permanent_redaction)

    whistleblower_identity = tip_data['data']['whistleblower_identity']
    db_redact_whistleblower_identities(whistleblower_identity, redaction)

    _content = whistleblower_identity
    if itip_id.crypto_tip_pub_key:
        _content = Base64Encoder.encode(
            GCE.asymmetric_encrypt(itip_id.crypto_tip_pub_key, json.dumps(_content, cls=JSONEncoder).encode())).decode()

    itip_whistleblower_identity = session.query(models.InternalTipData) \
                        .filter_by(internaltip_id=currentMaskedData['internaltip_id'],
                                   key='whistleblower_identity').first()
    if itip_whistleblower_identity:
        itip_whistleblower_identity.value = _content


def db_set_closure_answers(session, itip, questionnaire_hash, answers, stat_answers, plaintext=None):
    """
    Register on a report the answers of its closure questionnaire

    :param session: An ORM session
    :param itip: The internaltip the answers are registered on
    :param questionnaire_hash: The hash of the archived questionnaire schema
    :param answers: The answers, encrypted with the key of the report when it has one
    :param stat_answers: The statistical data extracted from the answers
    """
    if not session.query(models.InternalTipAnswers) \
                  .filter(models.InternalTipAnswers.internaltip_id == itip.id,
                          models.InternalTipAnswers.questionnaire_hash == questionnaire_hash).count():
        ita = models.InternalTipAnswers()
        ita.internaltip_id = itip.id
        ita.questionnaire_hash = questionnaire_hash
        ita.answers = answers
        ita.stat_answers = stat_answers
        ita.hash_sha256, ita.hash_sha512 = data_hashes(answers if plaintext is None else plaintext, itip.crypto_tip_pub_key)
        session.add(ita)

    itd = models.InternalTipData()
    itd.internaltip_id = itip.id
    itd.key = 'closure_questionnaire'
    itd.value = questionnaire_hash
    itd.hash_sha256, itd.hash_sha512 = data_hashes(questionnaire_hash)
    session.add(itd)


def db_store_closure_questionnaire_answers(session, tid, user_id, itip, answers):
    """
    Require and store the answers of the closure questionnaire of the channel

    The answers are stored as any questionnaire and shared with every
    recipient of the report; when the report has been forwarded a copy is
    registered on the report of each forward, wrapped with its own key, so
    that the recipients of the receiving tenants read them as well.

    :param session: An ORM session
    :param tid: The tenant ID
    :param user_id: The user ID of the user closing the report
    :param itip: The internaltip being closed
    :param answers: The answers of the closure questionnaire
    """
    context = session.query(models.Context).get(itip.context_id)
    if context is None or not context.closure_questionnaire_id:
        return

    if session.query(models.InternalTipData) \
              .filter(models.InternalTipData.internaltip_id == itip.id,
                      models.InternalTipData.key == 'closure_questionnaire').count():
        return

    if not answers:
        raise errors.InputValidationError

    steps, _ = db_validate_answers(session, tid, context.closure_questionnaire_id, answers, True)
    questionnaire_hash = db_archive_questionnaire_schema(session, steps)

    stat_data = extract_statistical_data(session, tid, answers)

    _answers = answers
    if itip.crypto_tip_pub_key:
        if stat_data:
            crypto_stat_pub_key = db_get(session, models.Config.value, (models.Config.tid == tid, models.Config.var_name == 'crypto_stat_pub_key'))[0]
            stat_data = Base64Encoder.encode(GCE.asymmetric_encrypt(crypto_stat_pub_key, json.dumps(stat_data, cls=JSONEncoder).encode())).decode()

        _answers = Base64Encoder.encode(GCE.asymmetric_encrypt(itip.crypto_tip_pub_key, json.dumps(answers).encode())).decode()

    db_set_closure_answers(session, itip, questionnaire_hash, _answers, stat_data, answers)

    db_log(session, tid=tid, type='add_answers', user_id=user_id, object_id=itip.id, data={'questionnaire_hash': questionnaire_hash})

    for forwarded_itip in session.query(models.InternalTip) \
                                 .filter(models.InternalTipForwarding.internaltip_id == itip.id,
                                         models.InternalTip.id == models.InternalTipForwarding.forwarding_internaltip_id):
        _answers = answers
        if forwarded_itip.crypto_tip_pub_key:
            _answers = Base64Encoder.encode(GCE.asymmetric_encrypt(forwarded_itip.crypto_tip_pub_key, json.dumps(answers).encode())).decode()

        db_set_closure_answers(session, forwarded_itip, questionnaire_hash, _answers, {}, answers)


@transact
def update_tip_submission_status(session, tid, user_id, rtip_id, status_id, substatus_id, answers=None):
    """
    Transaction for registering a change of status of a submission

    :param session: An ORM session
    :param tid: The tenant ID
    :param user_id: A user ID of the user changing the state
    :param rtip_id: The ID of the rtip accessed by the user
    :param status_id:  The new status ID
    :param substatus_id: A new substatus ID
    :param answers: The answers of the closure questionnaire of the channel,
                    required when one is configured and the report is closed
    """
    _, rtip, itip = db_access_rtip(session, tid, user_id, rtip_id)
    db_enforce_report_ownership(tid, itip)

    if status_id == 'closed':
        db_store_closure_questionnaire_answers(session, tid, user_id, itip, answers)

    if itip.status != status_id or itip.substatus != substatus_id:
        itip.update_date = rtip.last_access = datetime_now()

    # send mail notification to all users with access to the report excluding <user_id>
    for user in session.query(models.User) \
                       .filter(models.User.id == models.ReceiverTip.receiver_id,
                               models.ReceiverTip.internaltip_id == itip.id,
                               models.ReceiverTip.receiver_id != user_id,
                               models.ReceiverTip.last_notification < models.ReceiverTip.last_access):
        # Imported here as the module of the whistleblower imports this one
        from globaleaks.handlers.whistleblower.wbtip import db_notify_report_update
        db_notify_report_update(session, user, rtip, itip)

    db_update_submission_status(session, tid, user_id, itip, status_id, substatus_id)


def db_access_rtip(session, tid, user_id, itip_id):
    """
    Transaction retrieving an rtip and performing basic access checks

    :param session: An ORM session
    :param tid: A tenant ID of the user
    :param user_id: A user ID
    :param itip_id: the requested rtip ID
    :return: A model requested
    """
    user, rtip, itip = db_get(session,
                              (models.User, models.ReceiverTip, models.InternalTip),
                              (models.User.id == user_id,
                               models.User.tid == tid,
                               models.InternalTip.id == itip_id,
                               models.ReceiverTip.receiver_id == models.User.id,
                               models.ReceiverTip.internaltip_id == models.InternalTip.id))

    if itip.type == 'forward-request' and tid != 1 and db_get_forward_request_source_tid(session, itip) != tid:
        raise errors.ForbiddenOperation

    return user, rtip, itip


def db_access_rfile(session, tid, user_id, rfile_id):
    """
    Transaction retrieving an rfile and performing basic access checks

    :param session: An ORM session
    :param tid: A tenant ID of the user
    :param user_id: A user ID
    :param rfile_id: the requested rfile ID
    :return: A model requested
    """
    # The receivertip is the access capability: it reaches across tenants the
    # report of a forward, that the recipients of the two tenants share. A
    # public file is accessible to all of them, an internal file only to the
    # recipients of the tenant of its author, a personal file to the author.
    author = aliased(models.User)

    return (
        session.query(models.ReceiverFile)
        .join(
            models.ReceiverTip,
            models.ReceiverTip.internaltip_id == models.ReceiverFile.internaltip_id
        )
        .join(
            models.User,
            models.User.id == models.ReceiverTip.receiver_id
        )
        .filter(
            models.ReceiverFile.id == rfile_id,
            models.ReceiverTip.receiver_id == user_id,
            models.User.tid == tid,
            or_(
                models.ReceiverFile.visibility == 0,
                models.ReceiverFile.visibility == 3,
                models.ReceiverFile.author_id == user_id,
                and_(
                    models.ReceiverFile.visibility == 1,
                    models.ReceiverFile.author_id.in_(
                        session.query(author.id).filter(author.tid == tid)
                    )
                )
            )
        )
        .one_or_none()
    )


@transact
def register_rfile_on_db(session, tid, user_id, itip_id, uploaded_file):
    """
    Register a file on the database

    :param session: An ORM session
    :param tid: A tenant id
    :param itip_id: A id of the rtip on which attaching the file
    :param uploaded_file: A file to be attached
    :return: A descriptor of the file
    """
    rtip, itip = session.query(models.ReceiverTip, models.InternalTip) \
                        .filter(models.InternalTip.id == itip_id,
                                models.ReceiverTip.receiver_id == user_id,
                                models.ReceiverTip.internaltip_id == models.InternalTip.id,
                                models.User.id == user_id,
                                models.User.tid == tid).one()

    visibility = uploaded_file['visibility']
    if isinstance(visibility, bytes):
        visibility = visibility.decode()
    uploaded_file['visibility'] = visibility

    # On the report created by a forward the files are exchanged between the
    # two tenants under the forward visibility; the public visibility is
    # refused there until the whistleblower can be delivered the files, and
    # the tenant that received the forward answers with messages alone so
    # every upload of its own is refused
    if visibility not in ('public', 'internal', 'personal', 'forward') or \
            (visibility == 'forward' and itip.type != 'forward') or \
            (visibility == 'public' and itip.type == 'forward') or \
            (itip.type == 'forward' and itip.tid == tid):
        raise errors.InputValidationError

    rtip.last_access = datetime_now()
    if visibility in ('public', 'forward'):
        itip.update_date = rtip.last_access

    if itip.crypto_tip_pub_key:
        for k in ['name', 'description', 'type', 'size', 'hash_sha256', 'hash_sha512']:
            if k == 'size':
                uploaded_file[k] = str(uploaded_file[k])
            uploaded_file[k] = Base64Encoder.encode(GCE.asymmetric_encrypt(itip.crypto_tip_pub_key, uploaded_file[k]))

    new_file = models.ReceiverFile()
    new_file.id = uploaded_file['filename']
    new_file.author_id = user_id
    new_file.name = uploaded_file['name']
    new_file.description = uploaded_file['description']
    new_file.content_type = uploaded_file['type']
    new_file.size = uploaded_file['size']
    new_file.internaltip_id = itip.id
    new_file.visibility = uploaded_file['visibility']
    new_file.hash_sha256 = uploaded_file['hash_sha256']
    new_file.hash_sha512 = uploaded_file['hash_sha512']

    session.add(new_file)

    db_log(session, tid=tid, type='upload_file', user_id=user_id, object_id=new_file.id, data={'internaltip_id': itip.id})

    return serializers.serialize_rfile(session, new_file), itip.crypto_tip_pub_key


def db_get_rtip(session, tid, user_id, itip_id, language):
    """
    Transaction retrieving an rtip

    :param session: An ORM session
    :param tid: A tenant ID
    :param user_id: A user ID of the user opening the submission
    :param itip_id: An itip ID to accessed
    :param language: A language to be used for the serialization
    :return:  The serialized descriptor of the rtip
    """
    _, rtip, itip = db_access_rtip(session, tid, user_id, itip_id)

    rtip.last_access = datetime_now()
    if rtip.access_date == datetime_null():
        rtip.access_date = rtip.last_access

    # The reminder belongs to the recipients of the tenant the report belongs
    # to: the access of a recipient reading it from the other side of a forward
    # does not resolve it
    if itip.is_owned_by(tid) and \
            itip.reminder_date < rtip.last_access:
        itip.reminder_date = datetime_never()

    # The report created by a forward is marked as opened by the recipients of
    # the tenant that received it alone: to the tenant that performed the
    # forward the status stands as the indicator of that opening
    if itip.status == 'new' and itip.is_owned_by(tid):
        itip.update_date = rtip.last_access
        db_update_submission_status(session, tid, user_id, itip, 'opened')

    db_log(session, tid=tid, type='access_report', user_id=user_id, object_id=itip.id)

    report = serializers.serialize_rtip(session, itip, rtip, language)
    if itip.crypto_tip_pub_key and not rtip.crypto_tip_prv_key:
        forward_request = report.get('data', {}).get('forward_request')
        report['data'] = {}
        if forward_request:
            report['data']['forward_request'] = forward_request
        report['label'] = ''
        for questionnaire in report['questionnaires']:
            questionnaire['answers'] = {}

    from globaleaks.handlers.recipient import forward

    report['context_id'] = forward.db_get_presented_context_id(session, tid, itip)

    # 'allow_forward' carries the authorization of a request of forward, while
    # the possibility of forwarding the report is a separate computed property
    report['can_forward'] = forward.db_can_forward_report(session, tid, itip)

    # The receipt handed over to the whistleblower stays valid until they use it
    # and replace it with one of their own
    if itip.type == 'forward-request':
        report['forward_receipt_valid'] = db_forward_receipt_is_valid(session, itip)

    # The closure questionnaire of the channel is compiled from the report
    # itself: its schema travels with the reports of the recipients entitled
    # to close them, for as long as the closure has not been answered, and is
    # never published by the public API
    report['closure_questionnaire_schema'] = None
    if not session.query(models.InternalTipData) \
                  .filter(models.InternalTipData.internaltip_id == itip.id,
                          models.InternalTipData.key == 'closure_questionnaire').count():
        context = session.query(models.Context).get(itip.context_id)
        if context is not None and context.closure_questionnaire_id:
            questionnaire = session.query(models.Questionnaire) \
                                   .filter(models.Questionnaire.tid.in_({1, tid, State.tenants[tid].cache.ptid}),
                                           models.Questionnaire.id == context.closure_questionnaire_id) \
                                   .one_or_none()
            if questionnaire is not None:
                report['closure_questionnaire_schema'] = serialize_questionnaire(session, tid, questionnaire, language, serialize_templates=True, include_scoring=False)

    return report, Base64Encoder.decode(rtip.crypto_tip_prv_key)


@transact
def get_rtip(session, tid, user_id, itip_id, language):
    """
    Transaction retrieving an rtip

    :param session: An ORM session
    :param tid: A tenant ID
    :param user_id: A user ID of the user opening the submission
    :param itip_id: An itip ID to accessed
    :param language: A language to be used for the serialization
    :return:  The serialized descriptor of the rtip
    """
    return db_get_rtip(session, tid, user_id, itip_id, language)


def redact_answers(answers, redactions, depth=0):
    if depth >= MAX_ANSWERS_DEPTH:
        return

    for key in answers:
        if not re.match(requests.uuid_regexp, key) or \
                not isinstance(answers[key], list):
            continue

        for inner_idx, answer in enumerate(answers[key]):
            if 'value' in answer:
                for redaction in redactions:
                    if key == redaction.reference_id and answer['index'] == redaction.entry:
                        answer['value'] = redact_content(answer['value'], redaction.temporary_redaction, '0x2591')
            else:
                redact_answers(answer, redactions, depth + 1)


def mask_report_files(report, masked_ids, hide_name=True):
    """
    Flag as masked the files referenced by an active masking so that the client
    renders a placeholder and download/export of their content is blocked. The
    file name is hidden from viewers not entitled to mask/redact (and the
    whistleblower); recipients holding the permission keep seeing it, otherwise
    they could not tell what has been masked nor decide to unmask it.

    :param report: A serialized (and decrypted) report
    :param masked_ids: The set of file reference ids that are masked
    :param hide_name: Whether the file name must be masked as well
    """
    for f in report.get('wbfiles', []):
        if f.get('ifile_id', f.get('id')) in masked_ids:
            if hide_name:
                f['name'] = chr(0x2591) * len(f['name'])
            f['masked'] = True

    for f in report.get('rfiles', []):
        if f.get('id') in masked_ids:
            if hide_name:
                f['name'] = chr(0x2591) * len(f['name'])
            f['masked'] = True


def db_user_can_bypass_masking(session, user_id):
    # Viewers holding the masking/redaction permission read unmasked content to
    # moderate it; a missing user record (the whistleblower) is never privileged.
    user = session.query(models.User).get(user_id)
    if user is None:
        return False

    return user.has_permission('can_mask_information') or \
        user.has_permission('can_redact_information')


@transact
def redact_report(session, user_session, report, enforce=False):
    redactions = session.query(models.Redaction).filter(models.Redaction.internaltip_id == report['id']).all()

    if not len(redactions):
        return report

    # Text content (answers, identity and comments) is masked only for viewers
    # without the masking/redaction permission (recipients without it and the
    # whistleblower); the content of a masked file is instead never downloadable
    # by anyone, so masked files are flagged and their name is hidden for everyone.
    # A forward enforces the redactions regardless of the viewer's permission.
    privileged = not enforce and db_user_can_bypass_masking(session, user_session.user_id)

    if not privileged:
        redactions_by_reference_id = {}
        for redaction in redactions:
            redactions_by_reference_id.setdefault(redaction.reference_id, []).append(redaction)

        for q in report['questionnaires']:
            redact_answers(q['answers'], redactions)

        # The whistleblower identity is extracted from the questionnaire answers
        # and not indexed, so it is masked by its own reference-id-only traversal.
        identity = report.get('data', {}).get('whistleblower_identity')
        if isinstance(identity, dict):
            for redaction in redactions:
                db_redact_whistleblower_identities(identity, redaction, redaction.temporary_redaction, '0x2591')

        for comment in report['comments']:
            # Apply every redaction targeting the comment, not just the first:
            # redact_content is length-preserving, so the masks compose.
            for redaction in redactions_by_reference_id.get(comment['id'], []):
                comment['content'] = redact_content(comment['content'], redaction.temporary_redaction, '0x2591')

    mask_report_files(report, {r.reference_id for r in redactions if r.entry == '0'}, hide_name=not privileged)

    return report


def db_delete_itip(session, itip_id):
    """
    Transaction for deleting a submission

    :param session: An ORM session
    :param itip_id: A submission ID
    """
    db_del(session, models.InternalTip, models.InternalTip.id == itip_id)


def db_forward_receipt_is_valid(session, itip):
    """
    Check whether the receipt handed over on a request of forward is still valid

    The receipt is issued when the forward is performed and stays valid until
    the whistleblower accesses the report and replaces it with one of its own.

    :param session: An ORM session
    :param itip: The internaltip of the request of forward
    :return: True when the receipt still grants the access to the forwarded report
    """
    forwarded = session.query(models.InternalTip) \
                       .join(models.InternalTipForwarding,
                             models.InternalTipForwarding.forwarding_internaltip_id == models.InternalTip.id) \
                       .filter(models.InternalTipForwarding.internaltip_id == itip.id) \
                       .one_or_none()

    return forwarded is not None and forwarded.receipt_change_needed


def db_get_forward_request_source_tid(session, itip):
    data = session.query(models.InternalTipData) \
                  .filter(models.InternalTipData.internaltip_id == itip.id,
                          models.InternalTipData.key == 'forward_request') \
                  .one_or_none()
    if data is None:
        return None

    try:
        return int(data.value.get('source_tid'))
    except (AttributeError, TypeError, ValueError):
        return None


def db_enforce_report_ownership(tid, itip):
    """
    Confine the operations on a report to the recipients of the tenant it
    belongs to, that operate it as they operate any report of their
    whistleblowers; the recipients reading it from the other side of a forward
    take part in its exchanges and never operate it
    """
    if not itip.is_owned_by(tid):
        raise errors.ForbiddenOperation


def db_postpone_expiration(session, itip, expiration_date):
    """
    Transaction for postponing the expiration of a submission

    :param session: An ORM session
    :param itip: A submission model to be postponed
    :param expiration_date: The date timestamp to be set in milliseconds
    """
    policy = db_get_ttl(session, models.Context, itip.context_id)

    expiration_date = expiration_date / 1000
    expiration_date = datetime.fromtimestamp(expiration_date)

    # Enable to anticipate but not before 90 days since current day
    min_date = time.time() + 90 * 86400
    min_date = min_date - min_date % 86400
    min_date = datetime.fromtimestamp(min_date)
    if itip.expiration_date <= min_date:
        min_date = itip.expiration_date

    # Enable to postpone but not after max(365, 2 time the policy)
    if policy <= 0:
        max_date = datetime_never()
    else:
        max_date = time.time() + (max(365, 2 * policy) + 1) * 86400
        max_date = max_date - max_date % 86400
        max_date = datetime.fromtimestamp(max_date)

    if expiration_date <= min_date:
        expiration_date = min_date
    elif expiration_date >= max_date:
        expiration_date = max_date

    prev_expiration_date = itip.expiration_date
    itip.expiration_date = expiration_date

    itip.update_date = datetime_now()

    return prev_expiration_date, expiration_date


def db_set_reminder(session, itip, reminder_date):
    """
    Transaction for setting a reminder for a report

    :param session: An ORM session
    :param itip: A submission model to be postponed
    :param reminder_date: The date timestamp to be set in milliseconds
    """
    reminder_date = reminder_date / 1000
    reminder_date = min(reminder_date, 32503680000)
    reminder_date = datetime.fromtimestamp(reminder_date)

    itip.reminder_date = reminder_date


@transact
def delete_rtip(session, tid, user_session, itip_id):
    """
    Transaction for deleting a submission

    :param session: An ORM session
    :param tid: A tenant ID of the user performing the operation
    :param user_id: A user ID of the user performing the operation
    :param itip_id: An itip ID of the submission object of the operation
    """
    user, rtip, itip = db_access_rtip(session, tid, user_session.user_id, itip_id)

    if not user_session.permissions.can_delete_submission:
        raise errors.ForbiddenOperation

    db_enforce_report_ownership(tid, itip)

    db_delete_itip(session, itip.id)

    db_log(session, tid=tid, type='delete_report', user_id=user_session.user_id, object_id=itip.id)


def delete_wbfile(session, tid, user_id, file_id):
    """
    Transaction for deleting a wbfile
    :param session: An ORM session
    :param tid: A tenant ID
    :param user_id: The user ID of the user performing the operation
    :param file_id: The file ID of the wbfile to be deleted
    """
    ifile = (
        session.query(models.InternalFile)
               .filter(models.InternalFile.id == file_id,
                       models.WhistleblowerFile.internalfile_id == models.InternalFile.id,
                       models.ReceiverTip.id == models.WhistleblowerFile.receivertip_id,
                       models.ReceiverTip.receiver_id == user_id,
                       models.InternalTip.id == models.ReceiverTip.internaltip_id,
                       models.InternalTip.tid == tid)
               .first()
    )

    if ifile:
        session.delete(ifile)


@transact
def postpone_expiration(session, tid, user_session, itip_id, expiration_date):
    """
    Transaction for postponing the expiration of a submission

    :param session: An ORM session
    :param tid: A tenant ID of the user performing the operation
    :param user_session: A user session
    :param itip_id: An itip ID of the submission object of the operation
    :param expiration_date: A new expiration date
    """
    user_id = user_session.user_id

    user, rtip, itip = db_access_rtip(session, tid, user_id, itip_id)

    if not user_session.permissions.can_postpone_expiration:
        raise errors.ForbiddenOperation

    db_enforce_report_ownership(tid, itip)

    prev_expiration_date, curr_expiration_date = db_postpone_expiration(session, itip, expiration_date)

    log_data = {
      'prev_expiration_date': int(datetime.timestamp(prev_expiration_date)),
      'curr_expiration_date': int(datetime.timestamp(curr_expiration_date))
    }

    db_log(session, tid=tid, type='update_report_expiration', user_id=user_id, object_id=itip.id, data=log_data)


@transact
def set_reminder(session, tid, user_id, itip_id, reminder_date):
    """
    Transaction for postponing the expiration of a submission

    :param session: An ORM session
    :param tid: A tenant ID of the user performing the operation
    :param user_id: A user ID of the user performing the operation
    :param itip_id: An itip ID of the submission object of the operation
    :param reminder_date: A new reminder expiration date
    """
    user, rtip, itip = db_access_rtip(session, tid, user_id, itip_id)
    db_enforce_report_ownership(tid, itip)

    db_set_reminder(session, itip, reminder_date)


@transact
def set_internaltip_variable(session, tid, user_id, itip_id, key, value):
    """
    Transaction for setting properties of a submission

    :param session: An ORM session
    :param tid: A tenant ID of the user performing the operation
    :param user_id: A user ID of the user performing the operation
    :param itip_id: An itip ID of the submission object of the operation
    :param key: A key of the property to be set
    :param value: A value to be assigned to the property
    """
    user, _, itip = db_access_rtip(session, tid, user_id, itip_id)

    if key == 'allow_forward':
        # The request of forward is authorized by the recipients of the tenant
        # that received it, that are the recipients of the channel on which it
        # has been filed; the tenant that issued it has access to follow its
        # outcome and never to decide it
        if itip.type != 'forward-request' or tid != itip.tid:
            raise errors.ForbiddenOperation

        forward_request = session.query(models.InternalTipData) \
                                 .filter(models.InternalTipData.internaltip_id == itip.id,
                                         models.InternalTipData.key == 'forward_request') \
                                 .one_or_none()
        if forward_request is None:
            raise errors.InputValidationError("Missing forward request metadata")

        try:
            source_tid = int(forward_request.value.get('source_tid'))
        except (TypeError, ValueError):
            raise errors.InputValidationError("Invalid forward request source")

        # The authorization is granted on the single request and enables a
        # single forward; the request keeps its nature and is never turned
        # into a report of the tenant that received it
        itip.allow_forward = bool(value)
        itip.update_date = datetime_now()

        # The decision drives the lifecycle of the request: denying it closes it
        # and frees the tenant that issued it to file a new one, authorizing it
        # brings it back among the open ones
        db_update_submission_status(session, tid, user_id, itip,
                                    'opened' if itip.allow_forward else 'closed')

        log_type = 'report_forward_request_authorized' if itip.allow_forward else \
            'report_forward_request_denied'

        db_log(session, tid=tid, type=log_type,
               user_id=user_id, object_id=itip.id, data={'source_tid': source_tid})
        db_log(session, tid=source_tid, type=log_type,
               user_id=None, object_id=itip.id, data={'authorizing_tid': tid})
        return

    if key in ('label', 'important'):
        db_enforce_report_ownership(tid, itip)

    if itip.crypto_tip_pub_key and value and key in ['label']:
        value = Base64Encoder.encode(GCE.asymmetric_encrypt(itip.crypto_tip_pub_key, value))

    setattr(itip, key, value)


@transact
def set_receivertip_variable(session, tid, user_id, itip_id, key, value):
    """
    Transaction for setting properties of a submission

    :param session: An ORM session
    :param tid: A tenant ID of the user performing the operation
    :param user_id: A user ID of the user performing the operation
    :param itip_id: An itip ID of the submission object of the operation
    :param key: A key of the property to be set
    :param value: A value to be assigned to the property
    """
    _, rtip, _= db_access_rtip(session, tid, user_id, itip_id)
    setattr(rtip, key, value)


def db_create_identityaccessrequest_notifications(session, itip, rtip, iar):
    """
    Transaction for the creation of notifications related to identity access requests
    :param session: An ORM session
    :param itip: A itip ID of the tip involved in the request
    :param rtip: A rtip ID of the rtip involved in the request
    :param iar: A identity access request model
    """
    notif = State.tenants[itip.tid].cache.notification
    if notif and not notif.enable_custodian_notification_emails:
        return

    for user in session.query(models.User).filter(models.User.role == 'custodian',
                                                  models.User.tid == itip.tid,
                                                  models.User.notification.is_(True)):
        context = session.query(models.Context).filter(models.Context.id == itip.context_id).one()

        data = {
            'type': 'identity_access_request'
        }

        data['user'] = serialize_user(session, user, user.language)
        data['tip'] = serializers.serialize_rtip(session, itip, rtip, user.language)
        data['context'] = admin_serialize_context(session, context, user.language)
        data['iar'] = serializers.serialize_identityaccessrequest(session, iar)
        data['node'] = db_admin_serialize_node(session, itip.tid, user.language)

        data['notification'] = db_get_notification(session, itip.tid, user.language)

        subject, body = Templating().get_mail_subject_and_body(data)

        session.add(models.Mail({
            'address': data['user']['mail_address'],
            'subject': subject,
            'body': body,
            'tid': itip.tid,
            'secondary_smtp': mail_uses_smtp2(data['notification'], data['type'])
        }))


@transact
def create_identityaccessrequest(session, tid, user_session, itip_id, request):
    """
    Transaction for the creation of notifications related to identity access requests
    :param session: An ORM session
    :param tid: A tenant ID of the user issuing the request
    :param user_id: A user ID of the user issuing the request
    :param itip_id: A itip_id ID of the rtip involved in the request
    :param request: The request data
    """
    user_id = user_session.user_id
    user_cc = user_session.cc

    user, rtip, itip = db_access_rtip(session, tid, user_id, itip_id)

    # An authorization to access the whistleblower identity is granted at the
    # report level and is definitive: once any request has been authorized the
    # identity is disclosed to every recipient of the report, so a further
    # request must not be accepted. Allowing one would let a later pending
    # request re-hide an identity that was already, irrevocably, released.
    if session.query(models.IdentityAccessRequest) \
              .filter(models.IdentityAccessRequest.internaltip_id == itip.id,
                      models.IdentityAccessRequest.reply == 'authorized').count():
        raise errors.ForbiddenOperation

    crypto_tip_prv_key = GCE.asymmetric_decrypt(user_cc, Base64Encoder.decode(rtip.crypto_tip_prv_key))

    iar = models.IdentityAccessRequest()
    iar.internaltip_id = itip.id
    iar.request_user_id = user.id
    iar.request_motivation = Base64Encoder.encode(
        GCE.asymmetric_encrypt(itip.crypto_tip_pub_key, request['request_motivation']))
    session.add(iar)
    session.flush()

    db_log(session, tid=tid, type='request_identity_access', user_id=user_id, object_id=itip.id)

    custodians = 0
    for custodian in session.query(models.User).filter(models.User.tid == tid, models.User.role == 'custodian', models.User.enabled == True):
        iarc = models.IdentityAccessRequestCustodian()
        iarc.identityaccessrequest_id = iar.id
        iarc.custodian_id = custodian.id
        iarc.crypto_tip_prv_key = Base64Encoder.encode(GCE.asymmetric_encrypt(custodian.crypto_pub_key, crypto_tip_prv_key))
        session.add(iarc)
        custodians += 1

    if not custodians:
        iar.reply_date = datetime_now()
        iar.reply_user_id = user_id
        iar.reply = 'authorized'
        db_log(session, tid=tid, type='authorize_identity_access', user_id=user_id, object_id=itip.id)

    db_create_identityaccessrequest_notifications(session, itip, rtip, iar)

    return serializers.serialize_identityaccessrequest(session, iar)


@transact
def create_comment(session, tid, user_id, itip_id, content, visibility='public'):
    """
    Transaction for registering a new comment
    :param session: An ORM session
    :param tid: A tenant ID
    :param user_id: The user id of the user creating the comment
    :param itip_id: The rtip associated to the comment to be created
    :param content: The content of the comment
    :param visibility: The visibility type of the comment
    :return: A serialized descriptor of the comment
    """
    user, rtip, itip = db_access_rtip(session, tid, user_id, itip_id)

    # The forward visibility holds the space shared by the two tenants of a
    # forward; the public visibility keeps holding the space where the
    # whistleblower is, that on the report created by a forward stays between
    # the whistleblower and the tenant that received it. The recipients of
    # that tenant write in those two spaces alone, mirroring the interface
    # that offers them no other
    if visibility not in ('public', 'internal', 'personal', 'forward') or \
            (visibility == 'forward' and itip.type != 'forward') or \
            (visibility == 'public' and itip.type == 'forward' and user.tid != itip.tid) or \
            (visibility in ('internal', 'personal') and itip.type == 'forward' and user.tid == itip.tid):
        raise errors.InputValidationError

    rtip.last_access = datetime_now()
    if visibility in ('public', 'forward'):
        itip.update_date = rtip.last_access

    # The messages of the whistleblower are tracked on the forwarding so that
    # the whistleblower interface can present the exchanges left to be read
    if visibility == 'public' and itip.type == 'forward':
        forwarding = session.query(models.InternalTipForwarding) \
                            .filter(models.InternalTipForwarding.forwarding_internaltip_id == itip.id) \
                            .one_or_none()
        if forwarding is not None:
            forwarding.update_date = rtip.last_access

    hash_sha256 = sha256(content)
    hash_sha512 = sha512(content)
    _content = content
    _hash_sha256 = hash_sha256.decode()
    _hash_sha512 = hash_sha512.decode()
    if itip.crypto_tip_pub_key:
        _content = Base64Encoder.encode(GCE.asymmetric_encrypt(itip.crypto_tip_pub_key, content)).decode()
        _hash_sha256 = Base64Encoder.encode(GCE.asymmetric_encrypt(itip.crypto_tip_pub_key, hash_sha256)).decode()
        _hash_sha512 = Base64Encoder.encode(GCE.asymmetric_encrypt(itip.crypto_tip_pub_key, hash_sha512)).decode()

    comment = models.Comment()
    comment.internaltip_id = itip.id
    comment.type = 'receiver'
    comment.author_id = rtip.receiver_id
    comment.content = _content
    comment.visibility = visibility
    comment.hash_sha256 = _hash_sha256
    comment.hash_sha512 = _hash_sha512
    session.add(comment)
    session.flush()

    db_log(session, tid=tid, type='add_comment', user_id=user_id, object_id=comment.id, data={'internaltip_id': itip.id})

    ret = serializers.serialize_comment(session, comment)
    ret['content'] = content
    ret['hash_sha256'] = hash_sha256
    ret['hash_sha512'] = hash_sha512
    return ret


def validate_redaction_ranges(ranges):
    # temporary_redaction/permanent_redaction reach the range math
    # (validate_ranges/merge_and_sort_ranges/get_new_temporary_redaction) and the
    # stored JSON columns straight from the client. Accept only a list of
    # {'start', 'end'} where each bound is an integer or the '-inf'/'inf' file
    # sentinel, so malformed input can never crash those helpers.
    if not isinstance(ranges, list):
        raise errors.InputValidationError

    for r in ranges:
        if not isinstance(r, dict):
            raise errors.InputValidationError

        for bound in ('start', 'end'):
            v = r.get(bound)
            if isinstance(v, bool) or not (isinstance(v, int) or v in ('-inf', 'inf')):
                raise errors.InputValidationError


def validate_redaction_request(data):
    # An empty field ('' or []) carries no range and is left to the callee.
    for key in ('temporary_redaction', 'permanent_redaction'):
        ranges = data.get(key)
        if ranges:
            validate_redaction_ranges(ranges)


@transact
def create_redaction(session, tid, user_session, data):
    user_id = user_session.user_id

    user, rtip, itip = db_access_rtip(session, tid, user_id, data['internaltip_id'])
    db_enforce_report_ownership(tid, itip)

    if not user_session.has_permission('can_mask_information'):
        raise errors.ForbiddenOperation

    itip.update_date = rtip.last_access = datetime_now()

    reference_id = data.get('reference_id')

    # A redaction must reference content belonging to its own report. File and
    # comment references are globally-unique row ids, so reject any reference_id
    # that resolves to another report's object. Answer and identity references
    # are questionnaire field keys (shared across reports that use the same
    # questionnaire, e.g. the default one), so there is no per-report row to
    # validate here; they are instead confined by the report-scoped redaction
    # loading at consumption time (see redact_report).
    #
    # In addition, a personal (visibility == 2) recipient file or comment
    # belongs to a single recipient (author_id) and an internal (visibility == 1)
    # one to the recipients of the author's tenant; reject any reference to an
    # object the referencing user is not shown, mirroring the access guard
    # enforced in db_access_rfile and in serialize_rtip's visibility filter.
    author = aliased(models.User)
    same_tenant_authors = session.query(author.id).filter(author.tid == tid)

    if reference_id and \
            (session.query(models.InternalFile)
                    .filter(models.InternalFile.id == reference_id,
                            models.InternalFile.internaltip_id != itip.id).first() or
             session.query(models.ReceiverFile)
                    .filter(models.ReceiverFile.id == reference_id,
                            or_(models.ReceiverFile.internaltip_id != itip.id,
                                and_(models.ReceiverFile.visibility == 2,
                                     models.ReceiverFile.author_id != user_id),
                                and_(models.ReceiverFile.visibility == 1,
                                     models.ReceiverFile.author_id != user_id,
                                     ~models.ReceiverFile.author_id.in_(same_tenant_authors)))).first() or
             session.query(models.Comment)
                    .filter(models.Comment.id == reference_id,
                            or_(models.Comment.internaltip_id != itip.id,
                                and_(models.Comment.visibility == 2,
                                     models.Comment.author_id != user_id),
                                and_(models.Comment.visibility == 1,
                                     models.Comment.author_id != user_id,
                                     ~models.Comment.author_id.in_(same_tenant_authors)))).first()):
        raise errors.InputValidationError

    redaction = models.Redaction()
    redaction.id = data.get('id')
    redaction.reference_id = data.get('reference_id')
    redaction.entry = data.get('entry', '0')
    redaction.internaltip_id = itip.id
    redaction.temporary_redaction = data.get('temporary_redaction')
    redaction.permanent_redaction = []
    session.add(redaction)
    session.flush()

    log_data = {
        'old_temporary_redaction': [],
        'new_temporary_redaction': redaction.temporary_redaction,
        'old_permanent_redaction': [],
        'new_permanent_redaction': redaction.permanent_redaction,
    }

    db_log(session, tid=tid, type='update_redaction', user_id=user_id, object_id=redaction.id, data=log_data)

    return serializers.serialize_redaction(session, redaction)


@transact
def update_redaction(session, tid, user_session, redaction_id, redaction_data, tip_data):
    """
    Transaction for updating tip redaction

    :param session: An ORM session
    :param tid: The tenant ID
    :param user_session: A user session
    :param redaction_id: The ID of the mask to be updated
    """
    user_id = user_session.user_id

    user, rtip, itip = db_access_rtip(session, tid, user_id, redaction_data['internaltip_id'])
    db_enforce_report_ownership(tid, itip)

    redaction = session.query(models.Redaction).get(redaction_id)

    operation = redaction_data['operation']
    content_type = redaction_data['content_type']

    if not redaction or redaction.internaltip_id != itip.id:
        return

    if operation.endswith('mask') and user_session.permissions.can_mask_information:
        db_update_temporary_redaction(session, tid, user_id, redaction, redaction_data)

        if operation == 'full-unmask':
            if redaction.permanent_redaction:
                redaction.temporary_redaction = []
            else:
                session.delete(redaction)

    elif operation == 'redact' and user_session.permissions.can_redact_information:
        if content_type == "answer":
            db_redact_answers_recursively(session, tid, user_id, itip, redaction, redaction_data, tip_data)
        elif content_type == "comment":
            db_redact_comment(session, tid, user_id, itip, redaction, redaction_data, tip_data)
        elif content_type == 'file':
            if len(redaction.temporary_redaction) == 1 and \
                    redaction.temporary_redaction[0].get('start', False) == '-inf' and \
                    redaction.temporary_redaction[0].get('end', False) == 'inf':
                log_data = {
                    'old_temporary_redaction': redaction.temporary_redaction,
                    'new_temporary_redaction': [],
                    'old_permanent_redaction': redaction.permanent_redaction,
                    'new_permanent_redaction': [],
                }

                db_log(session, tid=tid, type='update_redaction', user_id=user_id, object_id=redaction.id, data=log_data)

                if session.query(models.ReceiverFile) \
                          .filter(models.ReceiverFile.id == redaction.reference_id).count():
                    delete_rfile(session, tid, user_id, redaction.reference_id)
                else:
                    delete_wbfile(session, tid, user_id, redaction.reference_id)

                session.delete(redaction)
        elif content_type == 'whistleblower_identity':
            db_redact_whistleblower_identity(session, tid, user_id, itip, redaction, redaction_data, tip_data)


def delete_rfile(session, tid, user_id, file_id):
    """
    Transaction for deleting a rfile
    :param session: An ORM session
    :param tid: A tenant ID
    :param user_id: The user ID of the user performing the operation
    :param file_id: The file ID of the rfile to be deleted
    """
    rfile = db_access_rfile(session, tid, user_id, file_id)
    if rfile is None:
        raise errors.ResourceNotFound

    session.delete(rfile)


class RTipRedactionCollection(BaseHandler):
    """
    Interface used to handle rtip mask
    """
    check_roles = 'receiver'

    def operation_descriptors(self):
        return {
            'update_redaction': RTipRedactionCollection.update_redaction
        }

    def post(self):
        payload = self.request.content.read().decode('utf-8')
        data = json.loads(payload)
        validate_redaction_request(data)

        return create_redaction(self.request.tid, self.session, data)

    @inlineCallbacks
    def put(self, redaction_id):
        payload = self.request.content.read().decode('utf-8')
        data = json.loads(payload)
        validate_redaction_request(data)

        tip, crypto_tip_prv_key = yield get_rtip(self.request.tid, self.session.user_id, data['internaltip_id'], self.request.language)

        if crypto_tip_prv_key:
            tip = yield deferToThread(decrypt_tip, self.session.cc, crypto_tip_prv_key, tip)

        redaction = yield update_redaction(self.request.tid, self.session, redaction_id, data, tip)

        return redaction


class RTipInstance(OperationHandler):
    """
    This interface exposes the Receiver's Tip
    """
    check_roles = 'receiver'

    @inlineCallbacks
    def get(self, tip_id):
        tip, crypto_tip_prv_key = yield get_rtip(self.request.tid, self.session.user_id, tip_id, self.request.language)

        if State.tenants[self.request.tid].cache.antivirus_enabled and crypto_tip_prv_key:
            enqueue_tip_files_for_rescan(tip, GCE.asymmetric_decrypt(self.session.cc, crypto_tip_prv_key))

        tip = yield serializers.process_logs(tip, tip['id'])

        if crypto_tip_prv_key:
            tip = yield deferToThread(decrypt_tip, self.session.cc, crypto_tip_prv_key, tip)

        tip = yield redact_report(self.session, tip)

        return tip

    def operation_descriptors(self):
        return {
            'grant': RTipInstance.grant_tip_access,
            'revoke': RTipInstance.revoke_tip_access,
            'postpone': RTipInstance.postpone_expiration,
            'set_reminder': RTipInstance.set_reminder,
            'set': RTipInstance.set_tip_val,
            'update_status': RTipInstance.update_submission_status,
            'transfer': RTipInstance.transfer_tip
        }

    def set_tip_val(self, req_args, itip_id, *args, **kwargs):
        value = req_args['value']
        key = req_args['key']

        if key == 'enable_notifications':
            return set_receivertip_variable(self.request.tid, self.session.user_id, itip_id, key, value)

        elif key in ['important', 'label', 'allow_forward']:
            if key == 'label' and not self.session.has_permission('can_change_label'):
                raise errors.ForbiddenOperation

            return set_internaltip_variable(self.request.tid, self.session.user_id, itip_id, key, value)

        raise errors.ForbiddenOperation


    def grant_tip_access(self, req_args, itip_id, *args, **kwargs):
        return grant_tip_access(self.request.tid, self.session, itip_id, req_args['receiver'])

    def revoke_tip_access(self, req_args, itip_id, *args, **kwargs):
        return revoke_tip_access(self.request.tid, self.session, itip_id, req_args['receiver'])

    def transfer_tip(self, req_args, itip_id, *args, **kwargs):
        return transfer_tip_access(self.request.tid, self.session, itip_id, req_args['receiver'])

    def postpone_expiration(self, req_args, itip_id, *args, **kwargs):
        return postpone_expiration(self.request.tid, self.session, itip_id, req_args['value'])

    def set_reminder(self, req_args, itip_id, *args, **kwargs):
        return set_reminder(self.request.tid, self.session.user_id, itip_id, req_args['value'])

    def update_submission_status(self, req_args, rtip_id, *args, **kwargs):
        if not self.session.has_permission('can_change_status'):
            raise errors.ForbiddenOperation

        return update_tip_submission_status(self.request.tid, self.session.user_id, rtip_id,
                                            req_args['status'], req_args['substatus'],
                                            req_args.get('answers'))

    def delete(self, itip_id):
        """
        Remove the Internaltip and all the associated data
        """
        return delete_rtip(self.request.tid, self.session, itip_id)


class RTipCommentCollection(BaseHandler):
    """
    Interface use to write rtip comments
    """
    check_roles = 'receiver'

    def post(self, itip_id):
        request = self.validate_request(self.request.content.read(), requests.CommentDesc)
        return create_comment(self.request.tid, self.session.user_id, itip_id, request['content'], request['visibility'])


class WhistleblowerFileDownload(BaseHandler):
    """
    This handler exposes wbfiles for download.
    """
    check_roles = 'receiver'
    handler_exec_time_threshold = 3600

    @transact
    def download_wbfile(self, session, tid, user_id, file_id):
        user, ifile, wbfile, rtip = db_get(session,
                                           (models.User,
                                            models.InternalFile,
                                            models.WhistleblowerFile,
                                            models.ReceiverTip),
                                           (models.User.id == user_id,
                                            models.User.tid == tid,
                                            models.ReceiverTip.receiver_id == models.User.id,
                                            models.ReceiverTip.id == models.WhistleblowerFile.receivertip_id,
                                            models.InternalFile.id == models.WhistleblowerFile.internalfile_id,
                                            models.WhistleblowerFile.id == file_id))

        antivirus_enabled = db_get_config_variable(session, tid, 'antivirus_enabled')
        recheck_needed = prepare_file_download(ifile, antivirus_enabled)

        # The masker keeps access to the content; only recipients without the
        # masking/redaction permission are denied (the whistleblower is denied
        # in its own handler, having no such permission).
        from globaleaks.handlers.whistleblower.wbtip import db_file_is_masked
        if db_file_is_masked(session, ifile.internaltip_id, ifile.id) and \
                not user.has_permission('can_mask_information') and \
                not user.has_permission('can_redact_information'):

            raise errors.ForbiddenOperation

        if wbfile.access_date == datetime_null():
            wbfile.access_date = datetime_now()

        db_log(session, tid=tid, type='access_file', user_id=user_id, object_id=wbfile.id, data={'internaltip_id': ifile.internaltip_id})

        return (ifile.name, ifile.id, wbfile.id, rtip.crypto_tip_prv_key,
                rtip.deprecated_crypto_files_prv_key, user.pgp_key_public,
                ifile.state, antivirus_enabled, recheck_needed, ifile.size)

    @inlineCallbacks
    def get(self, wbfile_id):
        (name, ifile_id, wbfile_id, tip_prv_key, tip_prv_key2, pgp_key,
         state, antivirus_enabled, recheck_needed, size) = yield self.download_wbfile(
            self.request.tid, self.session.user_id, wbfile_id)

        if recheck_needed and tip_prv_key:
            _tip_prv_key = GCE.asymmetric_decrypt(self.session.cc, Base64Encoder.decode(tip_prv_key))
            enqueue_antivirus_scan(ifile_id, _tip_prv_key)

        filelocation = os.path.join(self.state.settings.attachments_path, wbfile_id)
        if not os.path.exists(filelocation):
            filelocation = os.path.join(self.state.settings.attachments_path, ifile_id)

        directory_traversal_check(self.state.settings.attachments_path, filelocation)
        self.check_file_presence(filelocation)

        files = []

        if tip_prv_key:
            tip_prv_key = GCE.asymmetric_decrypt(self.session.cc, Base64Encoder.decode(tip_prv_key))
            name = GCE.asymmetric_decrypt(tip_prv_key, Base64Encoder.decode(name.encode())).decode()

            try:
                # First attempt
                sfo = GCE.streaming_encryption_open('DECRYPT', tip_prv_key, filelocation)
                files.append({'fo': sfo, 'name': name})
            except Exception:
                # Second attempt

                if not tip_prv_key2:
                    raise

                files_prv_key2 = GCE.asymmetric_decrypt(self.session.cc, Base64Encoder.decode(tip_prv_key2))
                sfo = GCE.streaming_encryption_open('DECRYPT', files_prv_key2, filelocation)
                files.append({'fo': sfo, 'name': name})
        else:
            files.append({'path': filelocation, 'name': name})

        mimetype, _ = mimetypes.guess_type(name)
        mimetype = mimetype or 'application/octet-stream'
        if tip_prv_key and size:
            size = int(GCE.asymmetric_decrypt(tip_prv_key, Base64Encoder.decode(str(size).encode())).decode())

        metadata = serialize_files_metadata_csv([{'name': name, 'type': mimetype,
                                                  'size': size, 'av_result': get_av_result(state)}])
        files.append({'fo': BytesIO(metadata), 'name': 'metadata.csv'})

        zipstream = ZipStream(files)
        stf = SecureTemporaryFile(self.state.settings.tmp_path)

        with stf.open('w') as f:
            for x in zipstream:
                f.write(x)

        zip_name = os.path.splitext(name)[0] + '.zip'
        with stf.open('r') as f:
            if pgp_key:
                # PGP wrapping encrypts the whole archive; serialize it per user
                # so a recipient cannot run several of these CPU-heavy downloads
                # at once.
                yield self.serialize_download(self.write_file_as_download, zip_name, f, pgp_key)
            else:
                yield self.write_file_as_download(zip_name, f, pgp_key)



class ReceiverFileUpload(BaseHandler):
    """
    Receiver interface to upload a file intended for the whistleblower
    """
    check_roles = 'receiver'
    upload_handler = True

    @inlineCallbacks
    def post(self, itip_id):
        # The file is only registered here: the delivery job writes it to the
        # attachments, because that is where its content is scanned, and a copy
        # written before the scan would be reachable while still unverified.
        result, _ = yield register_rfile_on_db(self.request.tid, self.session.user_id, itip_id, self.uploaded_file)
        return result


class ReceiverFileDownload(BaseHandler):
    """
    This handler lets the recipient download and delete rfiles, which are files
    intended for delivery to the whistleblower.
    """
    check_roles = 'receiver'
    handler_exec_time_threshold = 3600

    @transact
    def download_rfile(self, session, tid, user_id, file_id):
        author = aliased(models.User)

        try:
            user, rfile, rtip = db_get(session,
                                       (models.User,
                                        models.ReceiverFile,
                                        models.ReceiverTip),
                                       (models.User.id == user_id,
                                        models.User.id == models.ReceiverTip.receiver_id,
                                        models.User.tid == tid,
                                        models.ReceiverFile.id == file_id,
                                        models.ReceiverFile.internaltip_id == models.ReceiverTip.internaltip_id,
                                        or_(models.ReceiverFile.visibility == 0,
                                            models.ReceiverFile.visibility == 3,
                                            models.ReceiverFile.author_id == user_id,
                                            and_(models.ReceiverFile.visibility == 1,
                                                 models.ReceiverFile.author_id.in_(
                                                     session.query(author.id).filter(author.tid == tid))))))

            antivirus_enabled = db_get_config_variable(session, tid, 'antivirus_enabled')
            recheck_needed = prepare_file_download(rfile, antivirus_enabled)
        except Exception:
            raise errors.ResourceNotFound

        # The masker keeps access to the content; only recipients without the
        # masking/redaction permission are denied (the whistleblower is denied
        # in its own handler, having no such permission).
        from globaleaks.handlers.whistleblower.wbtip import db_file_is_masked
        if db_file_is_masked(session, rfile.internaltip_id, rfile.id) and \
                not user.has_permission('can_mask_information') and \
                not user.has_permission('can_redact_information'):
            raise errors.ForbiddenOperation

        db_log(session, tid=tid, type='access_file', user_id=user_id, object_id=rfile.id, data={'internaltip_id': rfile.internaltip_id})

        return (rfile.name, rfile.id, rtip.crypto_tip_prv_key, user.pgp_key_public,
                rfile.state, recheck_needed, rfile.size)


    @inlineCallbacks
    def get(self, rfile_id):
        (name, filename, tip_prv_key, pgp_key,
         state, recheck_needed, size) = yield self.download_rfile(
            self.request.tid, self.session.user_id, rfile_id)

        if recheck_needed and tip_prv_key:
            _tip_prv_key = GCE.asymmetric_decrypt(self.session.cc, Base64Encoder.decode(tip_prv_key))
            enqueue_antivirus_scan(filename, _tip_prv_key)

        filelocation = os.path.join(self.state.settings.attachments_path, filename)
        if not os.path.exists(filelocation):
            filelocation = os.path.join(self.state.settings.attachments_path, filename)

        directory_traversal_check(self.state.settings.attachments_path, filelocation)
        self.check_file_presence(filelocation)

        files = []

        if tip_prv_key:
            tip_prv_key = GCE.asymmetric_decrypt(self.session.cc, Base64Encoder.decode(tip_prv_key))
            name = GCE.asymmetric_decrypt(tip_prv_key, Base64Encoder.decode(name.encode())).decode()
            sfo = GCE.streaming_encryption_open('DECRYPT', tip_prv_key, filelocation)
            files.append({'fo': sfo, 'name': name})
        else:
            files.append({'path': filelocation, 'name': name})

        mimetype, _ = mimetypes.guess_type(name)
        mimetype = mimetype or 'application/octet-stream'
        if tip_prv_key and size:
            size = int(GCE.asymmetric_decrypt(tip_prv_key, Base64Encoder.decode(str(size).encode())).decode())

        metadata = serialize_files_metadata_csv([{'name': name, 'type': mimetype,
                                                  'size': size, 'av_result': get_av_result(state)}])
        files.append({'fo': BytesIO(metadata), 'name': 'metadata.csv'})

        zipstream = ZipStream(files)
        stf = SecureTemporaryFile(self.state.settings.tmp_path)

        with stf.open('w') as f:
            for x in zipstream:
                f.write(x)

        with stf.open('r') as f:
            if pgp_key:
                # PGP wrapping encrypts the whole archive; serialize it per user
                # so a recipient cannot run several of these CPU-heavy downloads
                # at once.
                yield self.serialize_download(self.write_file_as_download, name + '.zip', f, pgp_key)
            else:
                yield self.write_file_as_download(name + '.zip', f, pgp_key)


    def delete(self, file_id):
        """
        This interface allow the recipient to set the description of a ReceiverFile
        """
        return delete_rfile(self.request.tid, self.session.user_id, file_id)


class IdentityAccessRequestsCollection(BaseHandler):
    """
    Handler responsible of the creation of identity access requests
    """
    check_roles = 'receiver'

    def post(self, itip_id):
        request = self.validate_request(self.request.content.read(), requests.ReceiverIdentityAccessRequestDesc)

        return create_identityaccessrequest(self.request.tid,
                                            self.session,
                                            itip_id,
                                            request)


class ReportAuditLog(BaseHandler):
    """
    Handler that provides access to the audit log of a report
    """
    check_roles = 'receiver'

    def get(self, itip_id):
        return get_report_audit_log(self.session.tid, self.session.user_id, itip_id)

