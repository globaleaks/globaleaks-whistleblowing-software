# -*- coding: utf-8 -*-
#
# Handlers dealing with tip interface for receivers (rtip)
import base64
import copy
import json
import os
import re
import time

from datetime import datetime, timedelta

from twisted.internet.threads import deferToThread
from twisted.internet.defer import inlineCallbacks, returnValue

from globaleaks import models
from globaleaks.handlers.admin.context import admin_serialize_context
from globaleaks.handlers.admin.node import db_admin_serialize_node
from globaleaks.handlers.admin.notification import db_get_notification
from globaleaks.handlers.base import BaseHandler
from globaleaks.handlers.operation import OperationHandler
from globaleaks.handlers.whistleblower.submission import db_create_receivertip, decrypt_tip
from globaleaks.handlers.whistleblower.wbtip import db_notify_report_update
from globaleaks.handlers.user import user_serialize_user
from globaleaks.models import serializers, EnumStateFile
from globaleaks.models.serializers import process_logs
from globaleaks.orm import db_get, db_del, db_log, transact
from globaleaks.rest import errors, requests
from globaleaks.state import State
from globaleaks.utils.crypto import GCE
from globaleaks.utils.file_analysis import FileAnalysis
from globaleaks.utils.fs import directory_traversal_check
from globaleaks.utils.log import log
from globaleaks.utils.templating import Templating
from globaleaks.utils.utility import datetime_now, datetime_null, datetime_never, get_expiration
from globaleaks.utils.json import JSONEncoder


def db_notify_grant_access(session, user):
    """
    Transaction for the creation of notifications related to grant of access to report
    :param session: An ORM session
    :param user: A user to which send the notification
    """
    data = {
        'type': 'tip_access'
    }

    data['user'] = user_serialize_user(session, user, user.language)
    data['node'] = db_admin_serialize_node(session, user.tid, user.language)

    if data['node']['mode'] == 'default':
        data['notification'] = db_get_notification(session, user.tid, user.language)
    else:
        data['notification'] = db_get_notification(session, 1, user.language)

    subject, body = Templating().get_mail_subject_and_body(data)

    session.add(models.Mail({
        'address': data['user']['mail_address'],
        'subject': subject,
        'body': body,
        'tid': user.tid
    }))


def db_grant_tip_access(session, tid, user_id, user_cc, itip, rtip, receiver_id):
    """
    Transaction for granting a user access to a report

    :param session: An ORM session
    :param tid: A tenant ID of the user performing the operation
    :param user_id: A user ID of the user performing the operation
    :param user_cc: A user crypto key
    :param itip: An itip on which to perform operation
    :param rtip: An rtip on which to perform operation
    :param receiver_id: A user ID of the the user to which grant access to the report
    """
    existing = session.query(models.ReceiverTip).filter(models.ReceiverTip.receiver_id == receiver_id,
                                                        models.ReceiverTip.internaltip_id == itip.id).one_or_none()

    if existing:
        return

    new_receiver = db_get(session,
                          models.User,
                          models.User.id == receiver_id)

    if itip.crypto_tip_pub_key and not new_receiver.crypto_pub_key:
        # Access to encrypted submissions could be granted only if the recipient has performed first login
        return

    _tip_key = b''
    if itip.crypto_tip_pub_key:
        _tip_key = GCE.asymmetric_decrypt(user_cc, base64.b64decode(rtip.crypto_tip_prv_key))
        _tip_key = GCE.asymmetric_encrypt(new_receiver.crypto_pub_key, _tip_key)

    new_rtip = db_create_receivertip(session, new_receiver, itip, _tip_key)
    new_rtip.new = False
    if itip.deprecated_crypto_files_pub_key:
        _files_key = GCE.asymmetric_decrypt(user_cc, base64.b64decode(rtip.deprecated_crypto_files_prv_key))
        new_rtip.deprecated_crypto_files_prv_key = base64.b64encode(
            GCE.asymmetric_encrypt(new_receiver.crypto_pub_key, _files_key))

    wbfiles = session.query(models.WhistleblowerFile) \
                     .filter(models.WhistleblowerFile.receivertip_id == rtip.id)

    for wbfile in wbfiles:
        rf = models.WhistleblowerFile()
        rf.internalfile_id = wbfile.internalfile_id
        rf.receivertip_id = new_rtip.id
        rf.new = False
        session.add(rf)

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
    rtip = session.query(models.ReceiverTip) \
        .filter(models.ReceiverTip.internaltip_id == itip.id,
                models.ReceiverTip.receiver_id == receiver_id).one_or_none()
    if rtip is None:
        return False

    session.delete(rtip)

    return True


@transact
def grant_tip_access(session, tid, user_id, user_cc, itip_id, receiver_id):
    user, rtip, itip = db_access_rtip(session, tid, user_id, itip_id)
    if user_id == receiver_id or not user.can_grant_access_to_reports:
        raise errors.ForbiddenOperation

    new_receiver, _ = db_grant_tip_access(session, tid, user, user_cc, itip, rtip, receiver_id)
    if new_receiver:
        db_notify_grant_access(session, new_receiver)
        db_log(session, tid=tid, type='grant_access', user_id=user_id, object_id=itip.id)


@transact
def revoke_tip_access(session, tid, user_id, itip_id, receiver_id):
    user, rtip, itip = db_access_rtip(session, tid, user_id, itip_id)
    if user_id == receiver_id or not user.can_grant_access_to_reports:
        raise errors.ForbiddenOperation

    if db_revoke_tip_access(session, tid, user, itip, receiver_id):
        db_log(session, tid=tid, type='revoke_access', user_id=user_id, object_id=itip.id)


@transact
def transfer_tip_access(session, tid, user_id, user_cc, itip_id, receiver_id):
    log_data = {
        'recipient_id': receiver_id
    }

    user, rtip, itip = db_access_rtip(session, tid, user_id, itip_id)
    if user_id == receiver_id or not user.can_transfer_access_to_reports:
        raise errors.ForbiddenOperation

    new_receiver, _ = db_grant_tip_access(session, tid, user, user_cc, itip, rtip, receiver_id)
    if new_receiver:
        db_revoke_tip_access(session, tid, user, itip, user_id)
        db_notify_grant_access(session, new_receiver)
        db_log(session, tid=tid, type='transfer_access', user_id=user_id, object_id=itip.id, data=log_data)


def get_ttl(session, orm_object_model, orm_object_id):
    """
    Transaction for retrieving the data retention

    :param session: An ORM session
    :param orm_object_model: An ORM object type
    :param orm_object_id: The ORM object id
    """
    # we exploit the fact that we have the same "tip_timetolive" name in
    # the SubmissionSubStatus, SubmissionStatus and Context tables
    return session.query(orm_object_model.tip_timetolive) \
                  .filter(orm_object_model.id == orm_object_id).one()[0]


def recalculate_data_retention(session, itip, report_reopen_request):
    """
    Transaction for recaulating the data retention after a status change

    :param session: An ORM session
    :param itip: The internaltip ORM object
    :param report_reopen_request: boolean value, true if the report is being reopend
    """
    prev_expiration_date = itip.expiration_date
    if report_reopen_request:
        # use the context-defined data retention
        ttl = get_ttl(session, models.Context, itip.context_id)
        if ttl > 0:
            itip.expiration_date = get_expiration(ttl)
        else:
            itip.expiration_date = datetime_never()
    elif itip.status == "closed" and itip.substatus is not None:
        ttl = get_ttl(session, models.SubmissionSubStatus, itip.substatus)
        if ttl > 0:
            itip.expiration_date = get_expiration(ttl)

    return prev_expiration_date, itip.expiration_date


def db_update_submission_status(session, tid, user_id, itip, status_id, substatus_id, motivation=None):
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

    if itip.crypto_tip_pub_key and motivation is not None:
        motivation = base64.b64encode(GCE.asymmetric_encrypt(itip.crypto_tip_pub_key, motivation)).decode()

    can_reopen_reports = session.query(models.User.can_reopen_reports).filter(models.User.id == user_id).one()[0]
    report_reopen_request = itip.status == "closed" and status_id == "opened"

    if report_reopen_request and not can_reopen_reports:
        raise errors.ForbiddenOperation  # mandatory permission setting missing

    if report_reopen_request and motivation is None:
        raise errors.ForbiddenOperation  # motivation must be given when restoring closed tips

    itip.status = status_id
    itip.substatus = substatus_id or None

    prev_expiration_date, curr_expiration_date = recalculate_data_retention(session, itip, report_reopen_request)

    log_data = {
      'status': itip.status,
      'substatus': itip.substatus,
      'motivation': motivation,
    }

    db_log(session, tid=tid, type='update_report_status', user_id=user_id, object_id=itip.id, data=log_data)

    if prev_expiration_date != curr_expiration_date:
        log_data = {
            'prev_expiration_date': int(datetime.timestamp(prev_expiration_date)),
            'curr_expiration_date': int(datetime.timestamp(curr_expiration_date))
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
    new_temporary_redaction = get_new_temporary_redaction(redaction_data['temporary_redaction'],
                                                          redaction.permanent_redaction)

    log_data = {
        'old_remporary_redaction': redaction.temporary_redaction,
        'new_temporary_redaction': new_temporary_redaction
    }

    db_log(session, tid=tid, type='update_redaction', user_id=user_id, object_id=redaction.id, data=log_data)

    if len(new_temporary_redaction) == 0 and (
            not redaction.permanent_redaction or len(redaction.permanent_redaction) == 0):
        session.delete(redaction)
    else:
        redaction.temporary_redaction = new_temporary_redaction
        redaction.update_date = datetime.now()


def redact_content(content, ranges, character='0x2588'):
    result = list(content)

    ranges = sorted(ranges, key=lambda x: x['start'])

    for r in ranges:
        start, end = r.get('start', 0), r.get('end', 0) + 1

        if start < end:
            result[start:end] = chr(int(character[2:], 16)) * (end - start)

    return ''.join(result)


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

    if not currentMaskedData or not validate_ranges(currentMaskedData['temporary_redaction'],
                                                    redaction_data['permanent_redaction']):
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
    comment.content = base64.b64encode(GCE.asymmetric_encrypt(itip_id.crypto_tip_pub_key, content)).decode()


def db_redact_answers(answers, redaction):
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
                db_redact_answers(answer, redaction)


def db_redact_whistleblower_identities(whistleblower_identities, redaction):
    for key in whistleblower_identities:
        if isinstance(whistleblower_identities[key], bool):
            continue
        for inner_idx, whistleblower_identity in enumerate(whistleblower_identities[key]):
            if 'value' in whistleblower_identity:
                if key == redaction.reference_id:
                    whistleblower_identity['value'] = redact_content(whistleblower_identity['value'],
                                                                     redaction.permanent_redaction)
                    return
            else:
                db_redact_whistleblower_identities(whistleblower_identity, redaction)


def db_redact_answers_recursively(session, tid, user_id, itip_id, redaction, redaction_data, tip_data):
    currentMaskedData = next((masked_content for masked_content in tip_data['redactions'] if
                              masked_content['id'] == redaction_data['id']), None)

    if not validate_ranges(currentMaskedData['temporary_redaction'], redaction_data['permanent_redaction']):
        return

    new_temporary_redaction = get_new_temporary_redaction(currentMaskedData['temporary_redaction'],
                                                          copy.deepcopy(redaction_data['permanent_redaction']))

    new_permanent_redaction = merge_and_sort_ranges(currentMaskedData['permanent_redaction'],
                                                    redaction_data['permanent_redaction'])

    db_redact_data(session, tid, user_id, redaction, new_temporary_redaction, new_permanent_redaction)

    answers = tip_data['questionnaires'][0]['answers']

    db_redact_answers(answers, redaction)

    _content = answers

    if itip_id.crypto_tip_pub_key:
        _content = base64.b64encode(
            GCE.asymmetric_encrypt(itip_id.crypto_tip_pub_key, json.dumps(_content, cls=JSONEncoder).encode())).decode()

    itip_answers = session.query(models.InternalTipAnswers) \
                          .filter_by(internaltip_id=currentMaskedData['internaltip_id']).first()

    if itip_answers:
        itip_answers.answers = _content


def db_redact_whistleblower_identity(session, tid, user_id, itip_id, redaction, redaction_data, tip_data):
    currentMaskedData = next((masked_content for masked_content in tip_data['redactions'] if
                              masked_content['id'] == redaction_data['id']), None)

    if not validate_ranges(currentMaskedData['temporary_redaction'], redaction_data['permanent_redaction']):
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
        _content = base64.b64encode(
            GCE.asymmetric_encrypt(itip_id.crypto_tip_pub_key, json.dumps(_content, cls=JSONEncoder).encode())).decode()

    itip_whistleblower_identity = session.query(models.InternalTipData) \
                        .filter_by(internaltip_id=currentMaskedData['internaltip_id']).first()
    if itip_whistleblower_identity:
        itip_whistleblower_identity.value = _content


@transact
def update_tip_submission_status(session, tid, user_id, rtip_id, status_id, substatus_id, motivation):
    """
    Transaction for registering a change of status of a submission

    :param session: An ORM session
    :param tid: The tenant ID
    :param user_id: A user ID of the user changing the state
    :param rtip_id: The ID of the rtip accessed by the user
    :param status_id:  The new status ID
    :param substatus_id: A new substatus ID
    """
    _, rtip, itip = db_access_rtip(session, tid, user_id, rtip_id)

    if itip.status != status_id or itip.substatus != substatus_id:
        itip.update_date = rtip.last_access = datetime_now()

    # send mail notification to all users with access to the report excluding <user_id>
    for user in session.query(models.User) \
                       .filter(models.User.id == models.ReceiverTip.receiver_id,
                               models.ReceiverTip.internaltip_id == itip.id,
                               models.ReceiverTip.receiver_id != user_id):
        db_notify_report_update(session, user, rtip, itip)

    db_update_submission_status(session, tid, user_id, itip, status_id, substatus_id, motivation)


def db_access_rtip(session, tid, user_id, itip_id):
    """
    Transaction retrieving an rtip and performing basic access checks

    :param session: An ORM session
    :param tid: A tenant ID of the user
    :param user_id: A user ID
    :param itip_id: the requested rtip ID
    :return: A model requested
    """
    return db_get(session,
                  (models.User, models.ReceiverTip, models.InternalTip),
                  (models.User.id == user_id,
                   models.InternalTip.id == itip_id,
                   models.ReceiverTip.receiver_id == models.User.id,
                   models.ReceiverTip.internaltip_id == models.InternalTip.id,
                   models.InternalTip.tid == tid))


def db_access_rfile(session, tid, user_id, rfile_id):
    """
    Transaction retrieving an rfile and performing basic access checks

    :param session: An ORM session
    :param tid: A tenant ID of the user
    :param user_id: A user ID
    :param rfile_id: the requested rfile ID
    :return: A model requested
    """
    itips_ids = [x[0] for x in session.query(models.InternalTip.id)
                                      .filter(models.InternalTip.id == models.ReceiverTip.internaltip_id,
                                              models.ReceiverTip.receiver_id == user_id,
                                              models.InternalTip.tid == tid)]

    return db_get(session,
                  models.ReceiverFile,
                  (models.ReceiverFile.id == rfile_id,
                   models.ReceiverFile.internaltip_id.in_(itips_ids),
                   models.InternalTip.tid == tid))


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
                                models.InternalTip.status != 'closed',
                                models.InternalTip.tid == tid).one()

    rtip.last_access = datetime_now()
    if uploaded_file['visibility'] == 0:
        itip.update_date = rtip.last_access

    if itip.crypto_tip_pub_key:
        for k in ['name', 'description', 'type', 'size']:
            if k == 'size':
                uploaded_file[k] = str(uploaded_file[k])
            uploaded_file[k] = base64.b64encode(GCE.asymmetric_encrypt(itip.crypto_tip_pub_key, uploaded_file[k]))

    new_file = models.ReceiverFile()
    new_file.id = uploaded_file['filename']
    new_file.author_id = user_id
    new_file.name = uploaded_file['name']
    new_file.description = uploaded_file['description']
    new_file.content_type = uploaded_file['type']
    new_file.size = uploaded_file['size']
    new_file.internaltip_id = itip.id
    new_file.visibility = uploaded_file['visibility']

    session.add(new_file)

    return serializers.serialize_rfile(session, new_file)


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

    if itip.reminder_date < rtip.last_access:
        itip.reminder_date = datetime_never()

    if itip.status == 'new':
        itip.update_date = rtip.last_access
        db_update_submission_status(session, tid, user_id, itip, 'opened', None)

    db_log(session, tid=tid, type='access_report', user_id=user_id, object_id=itip.id)

    return serializers.serialize_rtip(session, itip, rtip, language), base64.b64decode(rtip.crypto_tip_prv_key)


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


def redact_answers(answers, redactions):
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
                redact_answers(answer, redactions)


@transact
def redact_report(session, user_id, report, enforce=False):
    user = session.query(models.User).get(user_id)

    redactions = session.query(models.Redaction).filter(models.Redaction.internaltip_id == report['id']).all()

    if not enforce and \
            (user.can_mask_information or \
             user.can_redact_information or \
             not len(redactions)):
        return report

    redactions_by_reference_id = {}
    for redaction in redactions:
        if redaction.reference_id not in redactions_by_reference_id:
            redactions_by_reference_id[redaction.reference_id] = []
        redactions_by_reference_id[redaction.reference_id].append(redaction)

    for q in report['questionnaires']:
        redact_answers(q['answers'], redactions)

    for comment in report['comments']:
        if comment['id'] in redactions_by_reference_id:
            comment['content'] = redact_content(comment['content'],
                                                redactions_by_reference_id[comment['id']][0].temporary_redaction,
                                                '0x2591')

    report['wbfiles'] = [x for x in report['wbfiles'] if x['ifile_id'] not in redactions_by_reference_id]

    return report


def db_delete_itip(session, itip_id):
    """
    Transaction for deleting a submission

    :param session: An ORM session
    :param itip_id: A submission ID
    """
    db_del(session, models.InternalTip, models.InternalTip.id == itip_id)


def db_postpone_expiration(session, itip, expiration_date):
    """
    Transaction for postponing the expiration of a submission

    :param session: An ORM session
    :param itip: A submission model to be postponed
    :param expiration_date: The date timestamp to be set in milliseconds
    """
    prev_expiration_date = itip.expiration_date

    max_date = 32503676400
    expiration_date = expiration_date / 1000
    expiration_date = expiration_date if expiration_date < max_date else max_date
    expiration_date = datetime.fromtimestamp(expiration_date)

    min_date = time.time() + 91 * 86400
    min_date = min_date - min_date % 86400
    min_date = datetime.fromtimestamp(min_date)
    if itip.expiration_date <= min_date:
        min_date = itip.expiration_date

    if expiration_date >= min_date:
        itip.expiration_date = expiration_date

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
def delete_rtip(session, tid, user_id, itip_id):
    """
    Transaction for deleting a submission

    :param session: An ORM session
    :param tid: A tenant ID of the user performing the operation
    :param user_id: A user ID of the user performing the operation
    :param itip_id: An itip ID of the submission object of the operation
    """
    user, rtip, itip = db_access_rtip(session, tid, user_id, itip_id)

    if not user.can_delete_submission:
        raise errors.ForbiddenOperation

    db_delete_itip(session, itip.id)

    db_log(session, tid=tid, type='delete_report', user_id=user_id, object_id=itip.id)


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
def postpone_expiration(session, tid, user_id, itip_id, expiration_date):
    """
    Transaction for postponing the expiration of a submission

    :param session: An ORM session
    :param tid: A tenant ID of the user performing the operation
    :param user_id: A user ID of the user performing the operation
    :param itip_id: An itip ID of the submission object of the operation
    :param expiration_date: A new expiration date
    """
    user, rtip, itip = db_access_rtip(session, tid, user_id, itip_id)

    if not user.can_postpone_expiration:
        raise errors.ForbiddenOperation

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
    _, _, itip = db_access_rtip(session, tid, user_id, itip_id)

    if itip.crypto_tip_pub_key and value and key in ['label']:
        value = base64.b64encode(GCE.asymmetric_encrypt(itip.crypto_tip_pub_key, value))

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
    _, rtip, _ = db_access_rtip(session, tid, user_id, itip_id)
    setattr(rtip, key, value)


def db_create_identityaccessrequest_notifications(session, itip, rtip, iar):
    """
    Transaction for the creation of notifications related to identity access requests
    :param session: An ORM session
    :param itip: A itip ID of the tip involved in the request
    :param rtip: A rtip ID of the rtip involved in the request
    :param iar: A identity access request model
    """
    for user in session.query(models.User).filter(models.User.role == 'custodian',
                                                  models.User.tid == itip.tid,
                                                  models.User.notification.is_(True)):
        context = session.query(models.Context).filter(models.Context.id == itip.context_id).one()

        data = {
            'type': 'identity_access_request'
        }

        data['user'] = user_serialize_user(session, user, user.language)
        data['tip'] = serializers.serialize_rtip(session, itip, rtip, user.language)
        data['context'] = admin_serialize_context(session, context, user.language)
        data['iar'] = serializers.serialize_identityaccessrequest(session, iar)
        data['node'] = db_admin_serialize_node(session, itip.tid, user.language)

        if data['node']['mode'] == 'default':
            data['notification'] = db_get_notification(session, itip.tid, user.language)
        else:
            data['notification'] = db_get_notification(session, 1, user.language)

        subject, body = Templating().get_mail_subject_and_body(data)

        session.add(models.Mail({
            'address': data['user']['mail_address'],
            'subject': subject,
            'body': body,
            'tid': itip.tid
        }))


@transact
def create_identityaccessrequest(session, tid, user_id, user_cc, itip_id, request):
    """
    Transaction for the creation of notifications related to identity access requests
    :param session: An ORM session
    :param tid: A tenant ID of the user issuing the request
    :param user_id: A user ID of the user issuing the request
    :param itip_id: A itip_id ID of the rtip involved in the request
    :param request: The request data
    """
    user, rtip, itip = db_access_rtip(session, tid, user_id, itip_id)

    crypto_tip_prv_key = GCE.asymmetric_decrypt(user_cc, base64.b64decode(rtip.crypto_tip_prv_key))

    iar = models.IdentityAccessRequest()
    iar.internaltip_id = itip.id
    iar.request_user_id = user.id
    iar.request_motivation = base64.b64encode(
        GCE.asymmetric_encrypt(itip.crypto_tip_pub_key, request['request_motivation']))
    session.add(iar)
    session.flush()

    custodians = 0
    for custodian in session.query(models.User).filter(models.User.tid == tid, models.User.role == 'custodian',
                                                       models.User.enabled == True):
        iarc = models.IdentityAccessRequestCustodian()
        iarc.identityaccessrequest_id = iar.id
        iarc.custodian_id = custodian.id
        iarc.crypto_tip_prv_key = base64.b64encode(GCE.asymmetric_encrypt(custodian.crypto_pub_key, crypto_tip_prv_key))
        session.add(iarc)
        custodians += 1

    if not custodians:
        iar.reply_date = datetime_now()
        iar.reply_user_id = user_id
        iar.reply = 'authorized'

    db_create_identityaccessrequest_notifications(session, itip, rtip, iar)

    return serializers.serialize_identityaccessrequest(session, iar)


@transact
def create_comment(session, tid, user_id, itip_id, content, visibility=0):
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
    _, rtip, itip = db_access_rtip(session, tid, user_id, itip_id)

    rtip.last_access = datetime_now()
    if visibility == 0:
        itip.update_date = rtip.last_access

    _content = content
    if itip.crypto_tip_pub_key:
        _content = base64.b64encode(GCE.asymmetric_encrypt(itip.crypto_tip_pub_key, content)).decode()

    comment = models.Comment()
    comment.internaltip_id = itip.id
    comment.type = 'receiver'
    comment.author_id = rtip.receiver_id
    comment.content = _content
    comment.visibility = visibility
    session.add(comment)
    session.flush()

    ret = serializers.serialize_comment(session, comment)
    ret['content'] = content
    return ret


@transact
def create_redaction(session, tid, user_id, data):
    user, rtip, itip = db_access_rtip(session, tid, user_id, data['internaltip_id'])

    itip.update_date = rtip.last_access = datetime_now()

    if not user.can_mask_information:
        return

    mask_content = {}
    if itip.crypto_tip_pub_key:
        if isinstance(data, dict):
            mask_content = data
        else:
            content_str = data.get('content', str(data))
            content_bytes = content_str.encode()
            mask_content = base64.b64encode(GCE.asymmetric_encrypt(itip.crypto_tip_pub_key, content_bytes)).decode()

    redaction = models.Redaction()
    redaction.id = data.get('id')
    redaction.reference_id = data.get('reference_id')
    redaction.entry = data.get('entry', '0')
    redaction.internaltip_id = itip.id
    redaction.temporary_redaction = data.get('temporary_redaction')
    redaction.permanent_redaction = []
    session.add(redaction)
    session.flush()

    return serializers.serialize_redaction(session, redaction)


@transact
def update_redaction(session, tid, user_id, redaction_id, redaction_data, tip_data):
    """
    Transaction for updating tip redaction

    :param session: An ORM session
    :param tid: The tenant ID
    :param user_id: A user ID of the user performing the operation
    :param redaction_id: The ID of the mask to be updated
    """
    user, rtip, itip = db_access_rtip(session, tid, user_id, redaction_data['internaltip_id'])

    redaction = session.query(models.Redaction).get(redaction_id)

    operation = redaction_data['operation']
    content_type = redaction_data['content_type']

    if not redaction or redaction.internaltip_id != itip.id:
        return

    if operation.endswith('mask') and user.can_mask_information:
        db_update_temporary_redaction(session, tid, user_id, redaction, redaction_data)

        if operation == 'full-unmask':
            if redaction.permanent_redaction:
                redaction.temporary_redaction = []
            else:
                session.delete(redaction)

    elif operation == 'redact' and user.can_redact_information:
        if content_type == "answer":
            db_redact_answers_recursively(session, tid, user_id, itip, redaction, redaction_data, tip_data)
        elif content_type == "comment":
            db_redact_comment(session, tid, user_id, itip, redaction, redaction_data, tip_data)
        elif content_type == 'file':
            if len(redaction.temporary_redaction) == 1 and \
                    redaction.temporary_redaction[0].get('start', False) == '-inf' and \
                    redaction.temporary_redaction[0].get('start', False) == '-inf':
                delete_wbfile(session, tid, user_id, redaction.reference_id)
                session.delete(redaction)
        elif content_type == 'whistleblower_identity':
            db_redact_whistleblower_identity(session, tid, user_id, itip, redaction, redaction_data, tip_data)


@transact
def delete_rfile(session, tid, user_id, file_id):
    """
    Transation for deleting a rfile
    :param session: An ORM session
    :param tid: A tenant ID
    :param user_id: The user ID of the user performing the operation
    :param file_id: The file ID of the rfile to be deleted
    """
    rfile = db_access_rfile(session, tid, user_id, file_id)
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

        return create_redaction(self.request.tid, self.session.user_id, data)

    @inlineCallbacks
    def put(self, redaction_id):
        payload = self.request.content.read().decode('utf-8')
        data = json.loads(payload)

        tip, crypto_tip_prv_key = yield get_rtip(self.request.tid, self.session.user_id, data['internaltip_id'],
                                                 self.request.language)

        if State.tenants[self.request.tid].cache.encryption and crypto_tip_prv_key:
            tip = yield deferToThread(decrypt_tip, self.session.cc, crypto_tip_prv_key, tip)

        redaction = yield update_redaction(self.request.tid, self.session.user_id, redaction_id, data, tip)

        returnValue(redaction)


class RTipInstance(OperationHandler):
    """
    This interface exposes the Receiver's Tip
    """
    check_roles = 'receiver'

    @inlineCallbacks
    def get(self, tip_id):
        tip, crypto_tip_prv_key = yield get_rtip(self.request.tid, self.session.user_id, tip_id, self.request.language)

        tip = yield serializers.process_logs(tip, tip['id'])

        if State.tenants[self.request.tid].cache.encryption and crypto_tip_prv_key:
            tip = yield deferToThread(decrypt_tip, self.session.cc, crypto_tip_prv_key, tip)

        tip = yield redact_report(self.session.user_id, tip)

        returnValue(tip)

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

        return set_internaltip_variable(self.request.tid, self.session.user_id, itip_id, key, value)

    def grant_tip_access(self, req_args, itip_id, *args, **kwargs):
        return grant_tip_access(self.request.tid, self.session.user_id, self.session.cc, itip_id, req_args['receiver'])

    def revoke_tip_access(self, req_args, itip_id, *args, **kwargs):
        return revoke_tip_access(self.request.tid, self.session.user_id, itip_id, req_args['receiver'])

    def transfer_tip(self, req_args, itip_id, *args, **kwargs):
        return transfer_tip_access(self.request.tid, self.session.user_id, self.session.cc, itip_id,
                                   req_args['receiver'])

    def postpone_expiration(self, req_args, itip_id, *args, **kwargs):
        return postpone_expiration(self.request.tid, self.session.user_id, itip_id, req_args['value'])

    def set_reminder(self, req_args, itip_id, *args, **kwargs):
        return set_reminder(self.request.tid, self.session.user_id, itip_id, req_args['value'])

    def update_submission_status(self, req_args, rtip_id, *args, **kwargs):
        return update_tip_submission_status(self.request.tid, self.session.user_id, rtip_id,
                                            req_args['status'], req_args['substatus'], req_args['motivation'])

    def delete(self, itip_id):
        """
        Remove the Internaltip and all the associated data
        """
        return delete_rtip(self.request.tid, self.session.user_id, itip_id)


class RTipCommentCollection(BaseHandler):
    """
    Interface use to write rtip comments
    """
    check_roles = 'receiver'

    def post(self, itip_id):
        request = self.validate_request(self.request.content.read(), requests.CommentDesc)
        return create_comment(self.request.tid, self.session.user_id, itip_id, request['content'],
                              request['visibility'])


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
                                            models.ReceiverTip.receiver_id == models.User.id,
                                            models.ReceiverTip.id == models.WhistleblowerFile.receivertip_id,
                                            models.InternalFile.id == models.WhistleblowerFile.internalfile_id,
                                            models.WhistleblowerFile.id == file_id))

        redaction = session.query(models.Redaction) \
                           .filter(models.Redaction.reference_id == ifile.id, models.Redaction.entry == '0').one_or_none()

        if redaction is not None and \
                not user.can_mask_information and \
                not user.can_redact_information:
            raise errors.ForbiddenOperation

        if wbfile.access_date == datetime_null():
            wbfile.access_date = datetime_now()

        log.debug("Download of file %s by receiver %s" %
                  (wbfile.internalfile_id, rtip.receiver_id))

        return ifile.name, ifile.id, wbfile.id, rtip.crypto_tip_prv_key, rtip.deprecated_crypto_files_prv_key, user.pgp_key_public, ifile.state

    @inlineCallbacks
    def get(self, wbfile_id):
        name, ifile_id, wbfile_id, tip_prv_key, tip_prv_key2, pgp_key, state = yield self.download_wbfile(self.request.tid,
                                                                                                   self.session.user_id,
                                                                                                   wbfile_id)

        filelocation = os.path.join(self.state.settings.attachments_path, wbfile_id)
        if not os.path.exists(filelocation):
            filelocation = os.path.join(self.state.settings.attachments_path, ifile_id)

        directory_traversal_check(self.state.settings.attachments_path, filelocation)
        self.check_file_presence(filelocation)

        if tip_prv_key:
            tip_prv_key = GCE.asymmetric_decrypt(self.session.cc, base64.b64decode(tip_prv_key))
            name = GCE.asymmetric_decrypt(tip_prv_key, base64.b64decode(name.encode())).decode()

            try:
                # First attempt
                filelocation = GCE.streaming_encryption_open('DECRYPT', tip_prv_key, filelocation)
            except:
                # Second attempt
                if not tip_prv_key2:
                    raise

                files_prv_key2 = GCE.asymmetric_decrypt(self.session.cc, base64.b64decode(tip_prv_key2))
                filelocation = GCE.streaming_encryption_open('DECRYPT', files_prv_key2, filelocation)

        af = FileAnalysis()
        status = af.read_file_for_scanning(filelocation, name, state)

        yield self.write_file_as_download(name, filelocation, pgp_key)


class ReceiverFileUpload(BaseHandler):
    """
    Receiver interface to upload a file intended for the whistleblower
    """
    check_roles = 'receiver'
    upload_handler = True

    def post(self, itip_id):
        return register_rfile_on_db(self.request.tid, self.session.user_id, itip_id, self.uploaded_file)


class ReceiverFileDownload(BaseHandler):
    """
    This handler lets the recipient download and delete rfiles, which are files
    intended for delivery to the whistleblower.
    """
    check_roles = 'receiver'
    handler_exec_time_threshold = 3600

    @transact
    def download_rfile(self, session, tid, user_id, file_id):
        try:
            rfile, rtip, pgp_key = db_get(session,
                                          (models.ReceiverFile,
                                           models.ReceiverTip,
                                           models.User.pgp_key_public),
                                          (models.User.id == user_id,
                                           models.User.id == models.ReceiverTip.receiver_id,
                                           models.ReceiverFile.id == file_id,
                                           models.ReceiverFile.internaltip_id == models.ReceiverTip.internaltip_id))
        except:
            raise errors.ResourceNotFound
        else:
            return rfile.name, rfile.id, base64.b64decode(rtip.crypto_tip_prv_key), pgp_key, rfile.state

    @inlineCallbacks
    def get(self, rfile_id):
        name, filename, tip_prv_key, pgp_key, state = yield self.download_rfile(self.request.tid, self.session.user_id,
                                                                         rfile_id)

        filelocation = os.path.join(self.state.settings.attachments_path, filename)
        if not os.path.exists(filelocation):
            filelocation = os.path.join(self.state.settings.attachments_path, filename)

        filelocation = os.path.join(self.state.settings.attachments_path, filename)
        directory_traversal_check(self.state.settings.attachments_path, filelocation)
        self.check_file_presence(filelocation)

        if tip_prv_key:
            tip_prv_key = GCE.asymmetric_decrypt(self.session.cc, tip_prv_key)
            name = GCE.asymmetric_decrypt(tip_prv_key, base64.b64decode(name.encode())).decode()
            filelocation = GCE.streaming_encryption_open('DECRYPT', tip_prv_key, filelocation)

        af = FileAnalysis()
        status = af.read_file_for_scanning(filelocation, filename, state)
        yield self.write_file_as_download(name, filelocation, pgp_key)

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
                                            self.session.user_id,
                                            self.session.cc,
                                            itip_id,
                                            request)
