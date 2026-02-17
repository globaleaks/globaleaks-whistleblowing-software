# Handlerse dealing with submission interface
import json
import re

from nacl.encoding import Base64Encoder
from nacl.public import PrivateKey
from sqlalchemy.orm import aliased


from globaleaks import models
from globaleaks.handlers.admin.questionnaire import db_get_questionnaire
from globaleaks.handlers.base import BaseHandler
from globaleaks.orm import db_get, db_log, transact
from globaleaks.rest import errors, requests
from globaleaks.state import State
from globaleaks.utils.crypto import sha256, sha512, GCE
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


# Field types whose answers are aggregable as option distributions
STATISTICAL_CHOICE_TYPES = ('selectbox', 'multichoice', 'checkbox')


def _entry_is_option_selected(flag):
    return flag is True or (isinstance(flag, str) and flag.strip().lower() == 'true')


def _extract_entry_answer_value(field_type, entry):
    if field_type == 'checkbox':
        # A checkbox answer has no single 'value': each option is stored as a
        # separate flag keyed by its option id (bool True or the string 'True').
        return [option_id for option_id, flag in entry.items()
                if re.match(requests.uuid_regexp, option_id) and _entry_is_option_selected(flag)]

    return entry.get('value')


def extract_statistical_data(session, tid:int, answers:dict):
    def collect_answer_entries(answer_map):
        collected = {}
        if not isinstance(answer_map, dict):
            return collected

        for field_id, entries in answer_map.items():
            if not re.match(requests.uuid_regexp, field_id) or not isinstance(entries, list) or not entries:
                continue

            first_entry = entries[0]
            if isinstance(first_entry, dict):
                collected[field_id] = first_entry

                nested = collect_answer_entries(first_entry)
                if nested:
                    collected.update(nested)

        return collected

    answer_entries = collect_answer_entries(answers)
    answer_field_ids = list(answer_entries.keys())
    if not answer_field_ids:
        return {}

    template_field = aliased(models.Field)
    statistical_fields = session.query(models.Field.id, models.Field.type, models.Field.template_id, models.Field.instance, models.Field.statistical, template_field.statistical).outerjoin(template_field, template_field.id == models.Field.template_id).filter(models.Field.tid.in_({1, tid}), models.Field.id.in_(answer_field_ids)).all()

    statistical_fields_by_id = {field_id: {'type': field_type, 'template_id': template_id, 'instance': instance, 'field_statistical': field_statistical, 'template_statistical': template_statistical} for field_id, field_type, template_id, instance, field_statistical, template_statistical in statistical_fields}
    answers_dict = dict()
    for k, entry in answer_entries.items():
        if k not in statistical_fields_by_id:
            continue

        field_data = statistical_fields_by_id[k]
        is_template_choice = (field_data['type'] in STATISTICAL_CHOICE_TYPES and field_data['instance'] == 'reference' and field_data['template_id'])
        include_in_statistical_data = bool(field_data['field_statistical']) or (is_template_choice and bool(field_data['template_statistical']))
        if not include_in_statistical_data:
            continue

        answer_value = _extract_entry_answer_value(field_data['type'], entry)
        if answer_value in (None, '', []):
            continue

        answers_dict[k] = answer_value

        if is_template_choice and field_data['template_statistical']:
            template_key = 'template:%s' % field_data['template_id']
            if template_key not in answers_dict:
                answers_dict[template_key] = answer_value

    return answers_dict


def decrypt_tip(user_key, tip_prv_key, tip):
    tip_key = GCE.asymmetric_decrypt(user_key, tip_prv_key)

    if 'label' in tip and tip['label']:
        tip['label'] = GCE.asymmetric_decrypt(tip_key, Base64Encoder.decode(tip['label'].encode())).decode()

    for questionnaire in tip['questionnaires']:
        questionnaire['answers'] = json.loads(GCE.asymmetric_decrypt(tip_key, Base64Encoder.decode(questionnaire['answers'].encode())).decode())

    for q in tip['questionnaires']:
        index_answers(q['answers'])

    for k in ['whistleblower_identity']:
        if k in tip['data'] and tip['data'][k]:
            tip['data'][k] = json.loads(GCE.asymmetric_decrypt(tip_key, Base64Encoder.decode(tip['data'][k].encode())).decode())

            if k == 'whistleblower_identity' and isinstance(tip['data'][k], list):
                # Fix for issue: https://github.com/globaleaks/globaleaks-whistleblowing-software/issues/2612
                # The bug is due to the fact that the data was initially saved as an array of one entry
                tip['data'][k] = tip['data'][k][0]

    if 'iar' in tip:
        if tip['iar']['request_motivation']:
            try:
                tip['iar']['request_motivation'] = GCE.asymmetric_decrypt(tip_key, Base64Encoder.decode(tip['iar']['request_motivation'])).decode()
            except:
                pass

        if tip['iar']['reply_motivation']:
            try:
                tip['iar']['reply_motivation'] = GCE.asymmetric_decrypt(tip_key, Base64Encoder.decode(tip['iar']['reply_motivation'])).decode()
            except:
                pass

    for x in tip['comments']:
        for k in ['content', 'hash_sha256', 'hash_sha512']:
            if k in x and x[k]:
                x[k] = GCE.asymmetric_decrypt(tip_key, Base64Encoder.decode(x[k].encode())).decode()

    for x in tip['wbfiles'] + tip['rfiles']:
        for k in ['name', 'description', 'type', 'size', 'hash_sha256', 'hash_sha512']:
            if k in x and x[k]:
                x[k] = GCE.asymmetric_decrypt(tip_key, Base64Encoder.decode(x[k].encode())).decode()
                if k == 'size':
                    x[k] = int(x[k])

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


def db_create_submission(session, tid, request, user_session, client_using_tor, client_using_mobile):
    encryption = db_get(session, models.Config, (models.Config.tid == tid, models.Config.var_name == 'encryption'))

    crypto_is_available = State.tenants[tid].cache.encryption

    context, questionnaire = db_get(session,
                                    (models.Context, models.Questionnaire),
                                    (models.Context.id == request['context_id'],
                                     models.Questionnaire.id == models.Context.questionnaire_id))

    answers = request['answers']

    for _, field_items in answers.items():
        for item in field_items:
            if 'value' in item and item['value']:
                val_str = str(item['value'])
                item['hash_sha256'] = sha256(val_str).decode()
                item['hash_sha512'] = sha512(val_str).decode()

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

    receipt = request['receipt']

    if len(receipt) == 44:
        key = Base64Encoder.decode(receipt.encode())
        itip.receipt_hash = sha256(key).decode()
    else:
        key, itip.receipt_hash = GCE.calculate_key_and_hash(receipt, State.tenants[tid].cache.receipt_salt)

    session.add(itip)
    session.flush()

    user_session.user_id = itip.id

    # Evaluate if the whistleblower tip should be encrypted
    if crypto_is_available:
        crypto_tip_prv_key, itip.crypto_tip_pub_key = GCE.generate_keypair()
        itip.crypto_pub_key = PrivateKey(user_session.cc, Base64Encoder).public_key.encode(Base64Encoder)
        itip.crypto_prv_key = Base64Encoder.encode(GCE.symmetric_encrypt(key, user_session.cc))
        itip.crypto_tip_prv_key = Base64Encoder.encode(GCE.asymmetric_encrypt(itip.crypto_pub_key, crypto_tip_prv_key))

    # Apply special handling to the whistleblower identity question
    if itip.enable_whistleblower_identity and request['identity_provided'] and answers[whistleblower_identity.id]:

        identity_data = answers[whistleblower_identity.id][0]
        for key, field_items in identity_data.items():
            if isinstance(field_items, list):
                for item in field_items:
                    if 'value' in item and item['value']:
                        val_str = str(item['value'])
                        item['hash_sha256'] = sha256(val_str).decode()
                        item['hash_sha512'] = sha512(val_str).decode()

        if crypto_is_available:
            wbi = Base64Encoder.encode(GCE.asymmetric_encrypt(itip.crypto_tip_pub_key, json.dumps(answers[whistleblower_identity.id][0]).encode())).decode()
        else:
            wbi = answers[whistleblower_identity.id][0]

        answers[whistleblower_identity.id] = ''

        db_set_internaltip_data(session, itip.id, 'whistleblower_identity', wbi, itip.creation_date)

    stat_data = extract_statistical_data(session, tid, answers)
    if crypto_is_available:
        if stat_data:
            crypto_stat_pub_key = db_get(session, models.Config.value, (models.Config.tid == tid, models.Config.var_name == 'crypto_stat_pub_key'))[0]
            stat_data = Base64Encoder.encode(GCE.asymmetric_encrypt(crypto_stat_pub_key, json.dumps(stat_data, cls=JSONEncoder).encode())).decode()

        answers = Base64Encoder.encode(GCE.asymmetric_encrypt(itip.crypto_tip_pub_key, json.dumps(answers, cls=JSONEncoder).encode())).decode()

    db_set_internaltip_answers(session, itip.id, questionnaire_hash, answers, stat_data, itip.creation_date)

    for uploaded_file in user_session.files:
        if crypto_is_available:
            for k in ['name', 'type', 'size', 'hash_sha256', 'hash_sha512']:
                uploaded_file[k] = Base64Encoder.encode(GCE.asymmetric_encrypt(itip.crypto_tip_pub_key, str(uploaded_file[k])))

        new_file = models.InternalFile()
        new_file.tid = tid
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
