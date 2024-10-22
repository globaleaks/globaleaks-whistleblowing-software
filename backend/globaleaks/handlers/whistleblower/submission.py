# -*- coding: utf-8 -*-
#
# Handlerse dealing with submission interface
import base64
import json
import re
import uuid

from nacl.encoding import Base64Encoder
from nacl.public import PrivateKey

from globaleaks import models
from globaleaks.handlers.admin.questionnaire import db_get_questionnaire
from globaleaks.handlers.base import BaseHandler
from globaleaks.orm import db_get, db_log, transact
from globaleaks.rest import errors, requests
from globaleaks.state import State
from globaleaks.utils.crypto import sha256, GCE
from globaleaks.utils.json import JSONEncoder
from globaleaks.utils.utility import get_expiration, datetime_null


def index_answers(answers, parent_index=''):
    for key in answers:
        if not re.match(requests.uuid_regexp, key) or \
                not isinstance(answers[key], list):
            continue

        index = 0
        for answer in answers[key]:
            str_index = str(index)
            if parent_index:
               str_index = parent_index + "-" + str_index

            answer['index'] = str_index
            index_answers(answer, str_index)
            index += 1


def decrypt_tip(user_key, tip_prv_key, tip):
    tip_key = GCE.asymmetric_decrypt(user_key, tip_prv_key)

    if 'label' in tip and tip['label']:
        tip['label'] = GCE.asymmetric_decrypt(tip_key, base64.b64decode(tip['label'].encode())).decode()

    for questionnaire in tip['questionnaires']:
        questionnaire['answers'] = json.loads(GCE.asymmetric_decrypt(tip_key, base64.b64decode(questionnaire['answers'].encode())).decode())

    for q in tip['questionnaires']:
        index_answers(q['answers'])

    for k in ['whistleblower_identity']:
        if k in tip['data'] and tip['data'][k]:
            tip['data'][k] = json.loads(GCE.asymmetric_decrypt(tip_key, base64.b64decode(tip['data'][k].encode())).decode())

            if k == 'whistleblower_identity' and isinstance(tip['data'][k], list):
                # Fix for issue: https://github.com/globaleaks/whistleblowing-software/issues/2612
                # The bug is due to the fact that the data was initially saved as an array of one entry
                tip['data'][k] = tip['data'][k][0]

    if 'iar' in tip:
        if tip['iar']['request_motivation']:
            try:
                tip['iar']['request_motivation'] = GCE.asymmetric_decrypt(tip_key, base64.b64decode(tip['iar']['request_motivation'])).decode()
            except:
                pass

        if tip['iar']['reply_motivation']:
            try:
                tip['iar']['reply_motivation'] = GCE.asymmetric_decrypt(tip_key, base64.b64decode(tip['iar']['reply_motivation'])).decode()
            except:
                pass

    for x in tip['comments']:
        if x['content']:
            x['content'] = GCE.asymmetric_decrypt(tip_key, base64.b64decode(x['content'].encode())).decode()

        if 'data' in x and 'motivation' in x['data'] and x['data']['motivation']:
            x['data']['motivation'] = GCE.asymmetric_decrypt(tip_key, base64.b64decode(x['data']['motivation'].encode())).decode()


    for x in tip['wbfiles'] + tip['rfiles']:
        for k in ['name', 'description', 'type', 'size']:
            if k in x and x[k]:
                x[k] = GCE.asymmetric_decrypt(tip_key, base64.b64decode(x[k].encode())).decode()
                if k == 'size':
                    x[k] = int(x[k])

    for f in tip.get('forwardings', []):
        f['questionnaire']['answers'] = json.loads(GCE.asymmetric_decrypt(tip_key, base64.b64decode(f['questionnaire']['answers'].encode())).decode())
        index_answers(f['questionnaire']['answers'])

    return tip


def db_set_internaltip_answers(session, itip_id, questionnaire_hash, answers, stat_answers, date=None):
    x = session.query(models.InternalTipAnswers) \
               .filter(models.InternalTipAnswers.internaltip_id == itip_id,
                       models.InternalTipAnswers.questionnaire_hash == questionnaire_hash).one_or_none()

    if x is not None:
        return

    ita = models.InternalTipAnswers()
    ita.internaltip_id = itip_id
    ita.questionnaire_hash = questionnaire_hash
    ita.answers = answers
    ita.stat_answers = stat_answers

    if date:
        ita.creation_date = date

    session.add(ita)

    return ita


def db_set_internaltip_data(session, itip_id, key, value, date=None):
    x = session.query(models.InternalTipData) \
               .filter(models.InternalTipData.internaltip_id == itip_id,
                       models.InternalTipData.key == key).one_or_none()

    if x is not None:
        return

    itd = models.InternalTipData()
    itd.internaltip_id = itip_id
    itd.key = key
    itd.value = value

    if date:
        itd.creation_date = date

    session.add(itd)

    return itd


def db_assign_submission_progressive(session, tid):
    counter = session.query(models.Config).filter(models.Config.tid == tid, models.Config.var_name == 'counter_submissions').one()
    counter.value += 1
    return counter.value


def db_archive_questionnaire_schema(session, questionnaire):
    hash = sha256(json.dumps(questionnaire, sort_keys=True)).decode("utf-8")
    if session.query(models.ArchivedSchema).filter(models.ArchivedSchema.hash == hash).count():
        return hash

    aqs = models.ArchivedSchema()
    aqs.hash = hash
    aqs.schema = questionnaire
    session.add(aqs)

    return hash


def db_create_receivertip(session, receiver, internaltip, tip_key):
    """
    Create a receiver tip for the specified receiver
    """
    receivertip = models.ReceiverTip()
    receivertip.internaltip_id = internaltip.id
    receivertip.receiver_id = receiver.id
    receivertip.crypto_tip_prv_key = Base64Encoder.encode(tip_key)
    session.add(receivertip)
    return receivertip

def is_valid_uuid(value):
    try:
        return str(uuid.UUID(value, version=4)) == value
    except ValueError:
        return False

def find_statistical_info(session, tid:str, answers:dict, default_language:str):
    answers_dict = dict()
    for k, v in answers.items():
        field = db_get(session, models.Field, (models.Field.id == k, models.Field.tid == tid))
        if not field or not field.statistical:
            continue

        value_id = v[0].get('value')

        if not is_valid_uuid(value_id):
            answers_dict[k] = value_id
            continue

        field_value = db_get(session, models.FieldOption, (models.FieldOption.id == value_id))
        answers_dict[k] = field_value.label.get(default_language[0]) if field_value else None
    return answers_dict



def db_create_submission(session, tid, request, user_session, client_using_tor, client_using_mobile):
    encryption = db_get(session, models.Config, (models.Config.tid == tid, models.Config.var_name == 'encryption'))
    analyst_encrypt = db_get(session, models.Config.value, (models.Config.tid == tid, models.Config.var_name == 'global_stat_pub_key'))
    default_language = db_get(session, models.Config.value, (models.Config.tid == tid, models.Config.var_name == 'default_language'))
    crypto_is_available = encryption.value

    context, questionnaire = db_get(session,
                                    (models.Context, models.Questionnaire),
                                    (models.Context.id == request['context_id'],
                                     models.Questionnaire.id == models.Context.questionnaire_id))

    answers = request['answers']
    steps = db_get_questionnaire(session, tid, questionnaire.id, None, True)['steps']
    questionnaire_hash = db_archive_questionnaire_schema(session, steps)

    receivers = []
    for r in session.query(models.User).filter(models.User.id.in_(request['receivers'])):
        if crypto_is_available:
            if r.crypto_pub_key:
                # This is the regular condition of systems setup on Globaleaks 4
                # Since this version, encryption is enabled by default and
                # users need to perform their first access before they
                # could receive reports.
                receivers.append(r)
            elif encryption.update_date != datetime_null():
                # This is the exceptional condition of systems setup when
                # encryption was implemented via PGP.
                # For continuity reason of those production systems
                # encryption could not be enforced.
                receivers.append(r)
                crypto_is_available = False
        else:
            receivers.append(r)

    if not receivers:
        raise errors.InputValidationError("Unable to deliver the submission to at least one recipient")

    if 0 < context.maximum_selectable_receivers < len(request['receivers']):
        raise errors.InputValidationError("The number of recipients selected exceed the configured limit")

    itip = models.InternalTip()
    itip.tid = tid
    itip.status = 'new'

    # Ensure that update_date and creation_date have the same value at creation time.
    itip.update_date = itip.creation_date

    itip.progressive = db_assign_submission_progressive(session, tid)

    if context.tip_timetolive > 0:
        itip.expiration_date = get_expiration(context.tip_timetolive)

    if context.tip_reminder > 0:
        itip.reminder_date = get_expiration(context.tip_reminder)

    # Evaluate the score level
    itip.score = request['score']

    itip.tor = client_using_tor
    itip.mobile = client_using_mobile

    itip.context_id = context.id

    whistleblower_identity = session.query(models.Field) \
                                    .filter(models.Field.template_id == 'whistleblower_identity',
                                            models.Field.step_id == models.Step.id,
                                            models.Step.questionnaire_id == context.questionnaire_id).one_or_none()

    if whistleblower_identity is not None:
        itip.enable_whistleblower_identity = True

    receipt = GCE.generate_receipt()
    itip.receipt_hash = GCE.hash_password(receipt, State.tenants[tid].cache.receipt_salt)

    session.add(itip)
    session.flush()

    user_session.user_id = itip.id

    # Evaluate if the whistleblower tip should be encrypted
    if crypto_is_available:
        crypto_tip_prv_key, itip.crypto_tip_pub_key = GCE.generate_keypair()
        wb_key = GCE.derive_key(receipt.encode(), State.tenants[tid].cache.receipt_salt)
        itip.crypto_pub_key = PrivateKey(user_session.cc, Base64Encoder).public_key.encode(Base64Encoder)
        itip.crypto_prv_key = Base64Encoder.encode(GCE.symmetric_encrypt(wb_key, user_session.cc))
        itip.crypto_tip_prv_key = Base64Encoder.encode(GCE.asymmetric_encrypt(itip.crypto_pub_key, crypto_tip_prv_key))

    # Apply special handling to the whistleblower identity question
    if itip.enable_whistleblower_identity and request['identity_provided'] and answers[whistleblower_identity.id]:
        if crypto_is_available:
            wbi = base64.b64encode(GCE.asymmetric_encrypt(itip.crypto_tip_pub_key, json.dumps(answers[whistleblower_identity.id][0]).encode())).decode()
        else:
            wbi = answers[whistleblower_identity.id][0]

        answers[whistleblower_identity.id] = ''

        db_set_internaltip_data(session, itip.id, 'whistleblower_identity', wbi, itip.creation_date)

    stat_answers = '{}'
    if crypto_is_available:
        aux_answers = find_statistical_info(session, tid, answers, default_language)
        if aux_answers != {}:
            stat_answers = base64.b64encode(
                GCE.asymmetric_encrypt(
                    analyst_encrypt[0],
                    json.dumps(aux_answers, cls=JSONEncoder).encode()
                )
            ).decode()

        answers = base64.b64encode(GCE.asymmetric_encrypt(itip.crypto_tip_pub_key, json.dumps(answers, cls=JSONEncoder).encode())).decode()

    db_set_internaltip_answers(session, itip.id, questionnaire_hash, answers, stat_answers, itip.creation_date)

    for uploaded_file in user_session.files:
        if crypto_is_available:
            for k in ['name', 'type', 'size']:
                uploaded_file[k] = base64.b64encode(GCE.asymmetric_encrypt(itip.crypto_tip_pub_key, str(uploaded_file[k])))

        new_file = models.InternalFile()
        new_file.tid = tid
        new_file.id = uploaded_file['filename']
        new_file.name = uploaded_file['name']
        new_file.content_type = uploaded_file['type']
        new_file.size = uploaded_file['size']
        new_file.internaltip_id = itip.id
        new_file.reference_id = uploaded_file['reference_id']
        new_file.creation_date = itip.creation_date
        session.add(new_file)

    for user in receivers:
        if crypto_is_available:
            _tip_key = GCE.asymmetric_encrypt(user.crypto_pub_key, crypto_tip_prv_key)
        else:
            _tip_key = b''

        db_create_receivertip(session, user, itip, _tip_key)

    operator_id = user_session.properties.get('operator_session', '')
    if operator_id:
        # this is actually an operator which is operating on behalf of a whistleblower
        itip.receipt_change_needed = True
        itip.operator_id = operator_id

    db_log(session, tid=tid, type='whistleblower_new_report', user_id=operator_id, object_id=itip.id)

    return {'receipt': receipt}


@transact
def create_submission(session, tid, request, user_session, client_using_tor, client_using_mobile):
    return db_create_submission(session, tid, request, user_session, client_using_tor, client_using_mobile)


class SubmissionInstance(BaseHandler):
    """
    The interface to perform a submission
    """
    check_roles = 'whistleblower'

    def post(self):
        """
        Perform a submission
        """
        request = self.validate_request(self.request.content.read(), requests.SubmissionDesc)

        return create_submission(self.request.tid,
                                 request,
                                 self.session,
                                 self.request.client_using_tor,
                                 self.request.client_using_mobile)
