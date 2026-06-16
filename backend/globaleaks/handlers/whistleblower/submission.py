# Handlerse dealing with submission interface
import copy
import json
import re

from datetime import datetime

from nacl.encoding import Base64Encoder
from nacl.public import PrivateKey


from globaleaks import models
from globaleaks.handlers.admin.questionnaire import db_get_questionnaire
from globaleaks.handlers.auth import db_set_receipt_hash
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
            except Exception:
                pass

        if tip['iar']['reply_motivation']:
            try:
                tip['iar']['reply_motivation'] = GCE.asymmetric_decrypt(tip_key, Base64Encoder.decode(tip['iar']['reply_motivation'])).decode()
            except Exception:
                pass

    for x in tip['comments']:
        if x['content']:
            x['content'] = GCE.asymmetric_decrypt(tip_key, Base64Encoder.decode(x['content'].encode())).decode()

    for x in tip['wbfiles'] + tip['rfiles']:
        for k in ['name', 'description', 'type', 'size']:
            if k in x and x[k]:
                x[k] = GCE.asymmetric_decrypt(tip_key, Base64Encoder.decode(x[k].encode())).decode()
                if k == 'size':
                    x[k] = int(x[k])

    return tip


def db_set_internaltip_answers(session, itip_id, questionnaire_hash, answers, date=None):
    x = session.query(models.InternalTipAnswers) \
               .filter(models.InternalTipAnswers.internaltip_id == itip_id,
                       models.InternalTipAnswers.questionnaire_hash == questionnaire_hash).one_or_none()

    if x is not None:
        return

    ita = models.InternalTipAnswers()
    ita.internaltip_id = itip_id
    ita.questionnaire_hash = questionnaire_hash
    ita.answers = answers

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


def iterate_answers(steps, answers):
    """
    Iterate the submitted answers against the authoritative questionnaire
    schema yielding (field, entry) pairs and recursing into fieldgroups.
    """
    def iterate_field(field, entries):
        if not isinstance(entries, list):
            return

        for entry in entries:
            if not isinstance(entry, dict):
                continue

            yield field, entry

            if field['type'] == 'fieldgroup':
                for child in field.get('children', []):
                    yield from iterate_field(child, entry.get(child['id'], []))

    for step in steps:
        for field in step['children']:
            yield from iterate_field(field, answers.get(field['id'], []))


def evaluate_selected_options(field, entry):
    """
    Yield the options of a field that result selected by an answer entry
    """
    if field['type'] not in ('checkbox', 'selectbox', 'multichoice'):
        return

    for option in field.get('options', []):
        if field['type'] == 'checkbox':
            selected = bool(entry.get(option['id']))
        else:
            selected = entry.get('value') == option['id']

        if selected:
            yield option


def db_evaluate_answers_score(context, steps, answers):
    """
    Compute the submission score from the submitted answers and the
    authoritative questionnaire schema.

    The score must be derived server-side and never be trusted from the
    client request: option score weights are not exposed on the public API
    and the computation is performed exclusively here.
    """
    points = {'sum': 0, 'mul': 1}

    for field, entry in iterate_answers(steps, answers):
        for option in evaluate_selected_options(field, entry):
            if option['score_type'] == 'addition':
                points['sum'] += option['score_points']
            elif option['score_type'] == 'multiplier':
                points['mul'] *= option['score_points']

    score = points['sum'] * points['mul']

    if score < context.score_threshold_medium:
        return 0
    elif score < context.score_threshold_high:
        return 1

    return 2


def db_evaluate_block_submission(steps, answers):
    """
    Return whether the submitted answers select an option that the
    questionnaire marks as blocking. Such options are screening choices that
    must abort the submission; the official client refuses to finalize, but the
    invariant must be enforced server-side as well so that a modified client
    cannot complete a submission the administrator configured to be blocked.
    """
    for field, entry in iterate_answers(steps, answers):
        for option in evaluate_selected_options(field, entry):
            if option.get('block_submission'):
                return True

    return False


_UNDEFINED = object()


def find_answers_field(answers, field_id):
    """
    Server-side port of the client FieldUtilitiesService.findField: return the
    first answer entry of the field identified by field_id, searching the whole
    answers tree, or _UNDEFINED when the field carries no answer.
    """
    for key, value in answers.items():
        if not isinstance(value, list) or not value:
            if key == field_id:
                return _UNDEFINED
            continue

        if key == field_id:
            return value[0]

        if isinstance(value[0], dict):
            r = find_answers_field(value[0], field_id)
            if r is not _UNDEFINED:
                return r

    return _UNDEFINED


def is_field_triggered(parent_enabled, field, answers, identity_provided, part_of_identity):
    """
    Server-side port of the client FieldUtilitiesService.isFieldTriggered:
    determine whether a field is enabled given the submitted answers and the
    option triggers configured on the questionnaire schema.
    """
    if parent_enabled is not None and not parent_enabled:
        return False

    if part_of_identity and not identity_provided:
        return False

    triggers = field.get('triggered_by_options') or []
    if not triggers:
        return True

    count = 0
    for trigger in triggers:
        answers_field = find_answers_field(answers, trigger['field'])
        if answers_field is _UNDEFINED or not isinstance(answers_field, dict):
            continue

        option = trigger['option']
        if answers_field.get('value') == option or answers_field.get(option):
            if trigger.get('sufficient'):
                return True
            count += 1

    return count == len(triggers)


def evaluate_receivers_override(steps, answers, identity_provided):
    """
    Server-side port of the recipients override computed by the client in
    FieldUtilitiesService.updateAnswers: traverse the enabled fields in schema
    order and return the trigger_receiver list of the last selected option that
    declares one, or None when no override is triggered.

    A triggered override replaces the recipients selection entirely, taking
    precedence over the context configuration including mandatory recipients;
    replicating the client algorithm exactly ensures that the selection the
    client would have submitted is the only one the backend accepts. Mirroring
    the client, the answers of fields that are not enabled are cleared as the
    traversal proceeds so that they cannot trigger downstream fields.
    """
    # Work on a copy: the traversal clears disabled fields like the client and
    # the original answers are still needed for scoring and storage.
    answers = copy.deepcopy(answers)

    override = {'value': None}

    def walk(parent_enabled, fields, local_answers, part_of_identity):
        for field in fields:
            enabled = is_field_triggered(parent_enabled, field, answers, identity_provided, part_of_identity)

            if not enabled and field['id'] in local_answers:
                local_answers[field['id']] = [{}]

            entries = local_answers.get(field['id'])
            if not isinstance(entries, list) or not entries:
                entries = [{}]

            child_part = part_of_identity or field.get('template_id') == 'whistleblower_identity'

            for entry in entries:
                if isinstance(entry, dict):
                    walk(enabled, field.get('children', []), entry, child_part)

            if not enabled:
                continue

            for entry in entries:
                if not isinstance(entry, dict):
                    continue

                for option in evaluate_selected_options(field, entry):
                    if option.get('trigger_receiver'):
                        override['value'] = option['trigger_receiver']

    for step in steps:
        step_enabled = is_field_triggered(None, step, answers, identity_provided, False)
        walk(step_enabled, step['children'], answers, step.get('template_id') == 'whistleblower_identity')

    return override['value']


def db_validate_submission_receivers(session, context, steps, answers, identity_provided, requested_receivers):
    """
    Enforce server-side the recipients selection policy configured on the
    context, an invariant otherwise enforced only by the official client:

    - a questionnaire option may trigger a recipients override that replaces
      any other selection policy: the selection must then be exactly and only
      the recipients triggered by the answers;
    - otherwise the selected recipients must be configured on the context;
    - recipients flagged as forcefully selected must always be included;
    - when recipients selection is disabled, the selection must match the set
      the client selects by default: all the recipients configured on the
      context when select_all_receivers is set, otherwise only the recipients
      flagged as forcefully selected.
    """
    override = evaluate_receivers_override(steps, answers, identity_provided)
    if override is not None:
        if requested_receivers != set(override):
            raise errors.InputValidationError("The selected recipients do not match the recipients triggered by the answers")
        return

    context_receivers = set()
    mandatory_receivers = set()

    for receiver_id, forcefully_selected in session.query(models.ReceiverContext.receiver_id, models.User.forcefully_selected) \
                                                   .filter(models.ReceiverContext.context_id == context.id,
                                                           models.User.id == models.ReceiverContext.receiver_id,
                                                           models.User.role == 'receiver'):
        context_receivers.add(receiver_id)
        if forcefully_selected:
            mandatory_receivers.add(receiver_id)

    if not context.allow_recipients_selection:
        # Mirror the client: with selection disabled the recipients are the ones
        # selected by default, i.e. all the context recipients when
        # select_all_receivers is set and only the mandatory ones otherwise.
        expected_receivers = context_receivers if context.select_all_receivers else mandatory_receivers
        if requested_receivers != expected_receivers:
            raise errors.InputValidationError("The selected recipients do not match the recipients configured on the context")
        return

    if not requested_receivers.issubset(context_receivers):
        raise errors.InputValidationError("The selected recipients are not configured on the context")

    if not mandatory_receivers.issubset(requested_receivers):
        raise errors.InputValidationError("The selected recipients do not include the mandatory recipients")

    if 0 < context.maximum_selectable_receivers < len(requested_receivers):
        raise errors.InputValidationError("The number of recipients selected exceed the configured limit")


# Fixed input_validation patterns the client applies to inputbox answers
# (see client Constants / FieldUtilitiesService.getValidator). They mirror the
# client regexps so that an answer the official client accepts is accepted here
# too. The administrator-defined 'custom' regexp is intentionally not enforced
# server-side: it is arbitrary, attacker-supplied input would be matched against
# it, and a poorly written pattern would expose the server to catastrophic
# backtracking (ReDoS); its enforcement stays a client-side convenience.
input_validation_patterns = {
    'email': r'^[\w+-.]{1,100}@[\w+-.]{1,100}\.[A-Za-z]{2,}$',
    'number': r'^\d+$',
    'phonenumber': r'^[+]?\d+$',
}


def db_validate_field_entry(field, entry):
    """
    Enforce the per-field constraints the official client applies to a single
    answer entry so that a modified client cannot persist an answer the
    questionnaire does not allow:

    - text fields (inputbox, textarea) must respect the minimum and maximum
      length configured on the field, and an inputbox additionally honours the
      configured input_validation format (email, number, phonenumber);
    - choice fields (selectbox, multichoice, checkbox) may only select options
      that the questionnaire actually defines on the field;
    - date and daterange answers must be well formed so that the recipient-side
      code reading them (templating/export) cannot be fed a malformed value;
    - a tos acceptance is a boolean flag.

    Mirroring the client's validators, the constraints are enforced only when an
    answer is actually provided: an empty value is left to the (conditional)
    required-field policy, which is out of scope here. Field types that carry no
    questionnaire-constrained leaf value (fileupload, voice, whose content flows
    through the attachments pipeline) are left untouched, consistently with the
    rest of the submission pipeline.
    """
    field_type = field['type']

    if field_type in ('inputbox', 'textarea'):
        value = entry.get('value', '')
        if value:
            if not isinstance(value, str):
                raise errors.InputValidationError("Invalid answer value")

            attrs = field.get('attrs', {})

            try:
                min_len = int(attrs.get('min_len', {}).get('value'))
            except (TypeError, ValueError):
                min_len = 0

            try:
                max_len = int(attrs.get('max_len', {}).get('value'))
            except (TypeError, ValueError):
                max_len = 4096

            if len(value) < min_len:
                raise errors.InputValidationError("Answer is shorter than the minimum allowed length")

            if 0 <= max_len < len(value):
                raise errors.InputValidationError("Answer exceeds the maximum allowed length")

            if field_type == 'inputbox':
                input_validation = attrs.get('input_validation', {}).get('value')
                pattern = input_validation_patterns.get(input_validation)
                if pattern is not None and not re.match(pattern, value):
                    raise errors.InputValidationError("Answer does not match the required format")

    elif field_type in ('selectbox', 'multichoice'):
        value = entry.get('value', '')
        if value:
            option_ids = {option['id'] for option in field.get('options', [])}
            if not isinstance(value, str) or value not in option_ids:
                raise errors.InputValidationError("Selected option does not exist")

    elif field_type == 'checkbox':
        # Checkbox selections are stored as option_id -> flag pairs; any key
        # shaped like an option id must reference an option defined on the field.
        option_ids = {option['id'] for option in field.get('options', [])}
        for key in entry:
            if re.match(requests.uuid_regexp, key) and key not in option_ids:
                raise errors.InputValidationError("Selected option does not exist")

    elif field_type == 'date':
        # A date answer is the ISO 8601 datetime string produced by the client;
        # require it to be parseable exactly as the recipient-side reader does
        # (see ISO8601_to_day_str) so a malformed value cannot break the export.
        value = entry.get('value', '')
        if value:
            if not isinstance(value, str):
                raise errors.InputValidationError("Invalid date value")

            try:
                datetime(year=int(value[0:4]),
                         month=int(value[5:7]),
                         day=int(value[8:10]),
                         hour=int(value[11:13]),
                         minute=int(value[14:16]),
                         second=int(value[17:19]))
            except (TypeError, ValueError):
                raise errors.InputValidationError("Invalid date value")

    elif field_type == 'daterange':
        # A daterange answer is a 'start:end' pair of millisecond timestamps;
        # require both to be parseable (as the recipient-side reader does) and
        # ordered, rejecting any value that would later raise on export.
        value = entry.get('value', '')
        if value:
            if not isinstance(value, str):
                raise errors.InputValidationError("Invalid date range value")

            parts = value.split(':')
            if len(parts) != 2:
                raise errors.InputValidationError("Invalid date range value")

            try:
                start = int(parts[0])
                end = int(parts[1])
                datetime.fromtimestamp(start / 1000)
                datetime.fromtimestamp(end / 1000)
            except (TypeError, ValueError, OverflowError, OSError):
                raise errors.InputValidationError("Invalid date range value")

            if start > end:
                raise errors.InputValidationError("Invalid date range value")

    elif field_type == 'tos':
        # A terms-of-service acceptance is stored as a boolean flag.
        value = entry.get('value', '')
        if value != '' and not isinstance(value, bool):
            raise errors.InputValidationError("Invalid answer value")


def db_validate_submission_answers(steps, answers):
    """
    Enforce that the submitted answers conform to the authoritative
    questionnaire schema, an invariant otherwise enforced only by the official
    client. The traversal is driven by the schema so that the submitted answers
    map one-to-one onto the questionnaire the administrator configured.

    The structural validation polices the exact surface that the recursive
    helpers operating on the stored answers descend into (see index_answers): a
    key shaped like a field id (a UUID) whose value is a list of answer entries.
    In a schema-conformant submission this pattern occurs only for the children
    of a fieldgroup, so the traversal rejects any field the questionnaire does
    not define at that position (a question that does not exist). This also
    bounds the answers nesting to the depth configured by the administrator and
    prevents a modified client from persisting arbitrarily deep answers that
    would later exhaust the recursion limit when recipients open or export the
    report.

    Each entry is additionally validated against the constraints of its field
    (see db_validate_field_entry) so that oversized or malformed text answers,
    selections of options the questionnaire does not define, and ill-formed
    date/daterange/tos values are rejected as well.
    """
    def validate_entries(field, entries):
        if not isinstance(entries, list):
            raise errors.InputValidationError("Invalid answers structure")

        children = {}
        if field['type'] == 'fieldgroup':
            children = {child['id']: child for child in field.get('children', [])}

        for entry in entries:
            if not isinstance(entry, dict):
                raise errors.InputValidationError("Invalid answers structure")

            db_validate_field_entry(field, entry)

            for key, value in entry.items():
                # Only keys shaped like a field id and carrying a list of
                # entries are recursed into by the helpers reading the answers;
                # anything else is leaf answer data validated above.
                if not isinstance(value, list) or not re.match(requests.uuid_regexp, key):
                    continue

                child = children.get(key)
                if child is None:
                    raise errors.InputValidationError("Unexpected nested field in answers")

                validate_entries(child, value)

    schema_fields = {field['id']: field for step in steps for field in step['children']}

    for key, value in answers.items():
        if not isinstance(value, list) or not re.match(requests.uuid_regexp, key):
            continue

        field = schema_fields.get(key)
        if field is None:
            raise errors.InputValidationError("Unexpected field in answers")

        validate_entries(field, value)


def db_validate_answers(session, tid, questionnaire_id, answers):
    """
    Load the authoritative questionnaire schema, with templates serialized so
    that fieldgroup children are present, and enforce that the submitted
    answers conform to it (see db_validate_submission_answers) and do not
    select an option the questionnaire marks as blocking (see
    db_evaluate_block_submission). The schema steps are returned for further
    server-side processing.

    This is the single entry point shared by the submission and the
    whistleblower tip endpoints that persist answers, so that the bound on the
    answers nesting depth and the screening choices that must abort persistence
    are enforced identically everywhere and cannot be forgotten on a code path a
    modified client could reach.
    """
    steps = db_get_questionnaire(session, tid, questionnaire_id, None, True)['steps']
    db_validate_submission_answers(steps, answers)

    if db_evaluate_block_submission(steps, answers):
        raise errors.InputValidationError("Blocked")

    return steps


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
    # Re-evaluate the intake gates at finalization time so that an already
    # issued submission session cannot complete a report after submissions
    # have been administratively disabled or stopped by the low-disk lockout.
    if not State.accept_submissions or State.tenants[tid].cache['disable_submissions']:
        raise errors.SubmissionDisabled

    encryption = db_get(session, models.Config, (models.Config.tid == tid, models.Config.var_name == 'encryption'))

    crypto_is_available = State.tenants[tid].cache.encryption

    context, questionnaire = db_get(session,
                                    (models.Context, models.Questionnaire),
                                    (models.Context.tid == tid,
                                     models.Context.id == request['context_id'],
                                     models.Questionnaire.id == models.Context.questionnaire_id))

    answers = request['answers']
    steps = db_validate_answers(session, tid, questionnaire.id, answers)
    questionnaire_hash = db_archive_questionnaire_schema(session, steps)

    db_validate_submission_receivers(session, context, steps, answers, request['identity_provided'], set(request['receivers']))

    receivers = []
    for r in session.query(models.User).filter(models.User.tid == tid, models.User.id.in_(request['receivers']), models.User.role == 'receiver'):
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

    # Evaluate the score level from the submitted answers using the
    # authoritative questionnaire schema. The score is computed server-side
    # and the client-supplied value, if any, is ignored.
    if State.tenants[tid].cache.enable_scoring_system:
        itip.score = db_evaluate_answers_score(context, steps, answers)

    itip.tor = client_using_tor
    itip.mobile = client_using_mobile

    itip.context_id = context.id

    whistleblower_identity = session.query(models.Field) \
                                    .filter(models.Field.template_id == 'whistleblower_identity',
                                            models.Field.step_id == models.Step.id,
                                            models.Step.questionnaire_id == context.questionnaire_id).one_or_none()

    if whistleblower_identity is not None:
        itip.enable_whistleblower_identity = True

    key = db_set_receipt_hash(session, tid, itip, request['receipt'])

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
        if crypto_is_available:
            wbi = Base64Encoder.encode(GCE.asymmetric_encrypt(itip.crypto_tip_pub_key, json.dumps(answers[whistleblower_identity.id][0]).encode())).decode()
        else:
            wbi = answers[whistleblower_identity.id][0]

        answers[whistleblower_identity.id] = ''

        db_set_internaltip_data(session, itip.id, 'whistleblower_identity', wbi, itip.creation_date)

    if crypto_is_available:
        answers = Base64Encoder.encode(GCE.asymmetric_encrypt(itip.crypto_tip_pub_key, json.dumps(answers, cls=JSONEncoder).encode())).decode()

    db_set_internaltip_answers(session, itip.id, questionnaire_hash, answers, itip.creation_date)

    for uploaded_file in user_session.files:
        if crypto_is_available:
            for k in ['name', 'type', 'size']:
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
