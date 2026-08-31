# Handlerse dealing with submission interface
import contextlib
import copy
import json
import re

from datetime import datetime

from nacl.encoding import Base64Encoder
from nacl.exceptions import CryptoError
from nacl.public import PrivateKey
from sqlalchemy.orm import aliased


from globaleaks import models
from globaleaks.handlers.admin.questionnaire import db_get_questionnaire
from globaleaks.handlers.auth import db_set_receipt_hash
from globaleaks.handlers.base import BaseHandler
from globaleaks.orm import db_get, db_log, transact
from globaleaks.rest import errors, requests
from globaleaks.state import State
from globaleaks.utils.crypto import sha256, sha512, GCE
from globaleaks.utils.json import JSONEncoder
from globaleaks.utils.utility import get_expiration, datetime_null, parse_ISO8601


# Maximum nesting depth traversed when indexing/masking questionnaire answers.
# Bounds every answer-tree recursion (index_answers, redact_answers,
# db_redact_answers, db_redact_whistleblower_identities) so a report with
# maliciously deep nesting cannot exhaust the interpreter recursion limit and
# turn every consumption-time read into a 500 for all viewers.
MAX_ANSWERS_DEPTH = 64


def index_answers(answers, parent_index='', depth=0):
    if depth >= MAX_ANSWERS_DEPTH:
        return

    for key in answers:
        if not re.match(requests.uuid_regexp, key) or \
                not isinstance(answers[key], list):
            continue

        for index, answer in enumerate(answers[key]):
            str_index = str(index)
            if parent_index:
               str_index = parent_index + "-" + str_index

            answer['index'] = str_index
            index_answers(answer, str_index, depth + 1)


def decrypt_hashes(tip_key, holder, prefix=''):
    for k in [prefix + 'hash_sha256', prefix + 'hash_sha512']:
        if holder.get(k):
            with contextlib.suppress(CryptoError, ValueError):
                holder[k] = GCE.asymmetric_decrypt(tip_key, Base64Encoder.decode(holder[k].encode())).decode()


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
        decrypt_hashes(tip_key, questionnaire)

    for q in tip['questionnaires']:
        index_answers(q['answers'])

    for k in ['whistleblower_identity']:
        if k in tip['data'] and tip['data'][k]:
            tip['data'][k] = json.loads(GCE.asymmetric_decrypt(tip_key, Base64Encoder.decode(tip['data'][k].encode())).decode())

            if k == 'whistleblower_identity' and isinstance(tip['data'][k], list):
                # Fix for issue: https://github.com/globaleaks/globaleaks-whistleblowing-software/issues/2612
                # The bug is due to the fact that the data was initially saved as an array of one entry
                tip['data'][k] = tip['data'][k][0]

            decrypt_hashes(tip_key, tip['data'], k + '_')

    if tip['data'].get('receipt'):
        with contextlib.suppress(CryptoError, ValueError):
            tip['data']['receipt'] = GCE.asymmetric_decrypt(
                tip_key, Base64Encoder.decode(tip['data']['receipt'].encode())).decode()
            decrypt_hashes(tip_key, tip['data'], 'receipt_')

    if 'iar' in tip:
        if tip['iar']['request_motivation']:
            with contextlib.suppress(CryptoError, ValueError):
                tip['iar']['request_motivation'] = GCE.asymmetric_decrypt(tip_key, Base64Encoder.decode(tip['iar']['request_motivation'])).decode()

        if tip['iar']['reply_motivation']:
            with contextlib.suppress(CryptoError, ValueError):
                tip['iar']['reply_motivation'] = GCE.asymmetric_decrypt(tip_key, Base64Encoder.decode(tip['iar']['reply_motivation'])).decode()

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


def data_hashes(value, crypto_tip_pub_key=''):
    """
    The fingerprints of a datum of a report, computed on the value as it was
    """
    if value is None:
        return '', ''

    val_str = value if isinstance(value, str) else json.dumps(value, sort_keys=True)

    hash_sha256 = sha256(val_str)
    hash_sha512 = sha512(val_str)

    if not crypto_tip_pub_key:
        return hash_sha256.decode(), hash_sha512.decode()

    return Base64Encoder.encode(GCE.asymmetric_encrypt(crypto_tip_pub_key, hash_sha256)).decode(), \
           Base64Encoder.encode(GCE.asymmetric_encrypt(crypto_tip_pub_key, hash_sha512)).decode()


def db_set_internaltip_answers(session, itip_id, questionnaire_id, questionnaire_hash, answers, stat_answers, date=None, plaintext=None, crypto_tip_pub_key=''):
    x = session.query(models.InternalTipAnswers) \
               .filter(models.InternalTipAnswers.internaltip_id == itip_id,
                       models.InternalTipAnswers.questionnaire_hash == questionnaire_hash).one_or_none()

    if x is not None:
        return

    ita = models.InternalTipAnswers()
    ita.internaltip_id = itip_id
    ita.questionnaire_id = questionnaire_id
    ita.questionnaire_hash = questionnaire_hash
    ita.answers = answers
    ita.stat_answers = stat_answers
    ita.hash_sha256, ita.hash_sha512 = data_hashes(answers if plaintext is None else plaintext, crypto_tip_pub_key)

    if date:
        ita.creation_date = date

    session.add(ita)

    return ita


def db_set_internaltip_data(session, itip_id, key, value, date=None, plaintext=None, crypto_tip_pub_key=''):
    x = session.query(models.InternalTipData) \
               .filter(models.InternalTipData.internaltip_id == itip_id,
                       models.InternalTipData.key == key).one_or_none()

    if x is not None:
        return

    itd = models.InternalTipData()
    itd.internaltip_id = itip_id
    itd.key = key
    itd.value = value
    itd.hash_sha256, itd.hash_sha512 = data_hashes(value if plaintext is None else plaintext, crypto_tip_pub_key)

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

    The answers are expected to be already reconciled with the trigger logic
    (see db_clear_disabled_answers) so that only the fields the conditional
    questionnaire logic enables are counted, exactly as the client does before
    submitting: counting a trigger-hidden field would let a modified client
    forge the triage score.
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

    The answers are expected to be already reconciled with the trigger logic
    (see db_clear_disabled_answers) so that a blocking option belonging to a
    field the questionnaire keeps hidden does not abort the submission, exactly
    as the client only screens the fields it actually enables.
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


def db_clear_disabled_answers(steps, answers, identity_provided):
    """
    Return a deep copy of the submitted answers with the answers of the fields
    disabled by the questionnaire trigger logic cleared, mirroring the client
    FieldUtilitiesService.updateAnswers.

    Every server-side consumer that derives a decision from the answers (the
    recipients override and the triage score) must consider only the fields the
    conditional questionnaire logic actually enables, exactly as the official
    client does before submitting. Operating on the raw answers would let a
    modified client have a trigger-hidden field counted (e.g. selecting the
    high-score option of a field the questionnaire keeps hidden to forge the
    triage score). Clearing the disabled fields as the traversal proceeds also
    ensures, like the client, that a disabled field cannot trigger downstream
    fields.
    """
    answers = copy.deepcopy(answers)

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

    for step in steps:
        step_enabled = is_field_triggered(None, step, answers, identity_provided, False)
        walk(step_enabled, step['children'], answers, step.get('template_id') == 'whistleblower_identity')

    return answers


def evaluate_receivers_override(steps, answers):
    """
    Server-side port of the recipients override computed by the client in
    FieldUtilitiesService.updateAnswers: traverse the enabled fields in schema
    order and return the recipients triggered by the last answer that triggers
    any, or None when no override is triggered.

    A checkbox accepts more than one answer at a time: the recipients it
    triggers are the ones of every box ticked, taken together. The fields
    answered with a single option contribute that option alone, so the same sum
    leaves them unchanged, and the last field answering with a trigger keeps
    replacing the previous one.

    A triggered override replaces the recipients selection entirely, taking
    precedence over the context configuration including mandatory recipients;
    replicating the client algorithm exactly ensures that the selection the
    client would have submitted is the only one the backend accepts.

    The answers are expected to be already reconciled with the trigger logic
    (see db_clear_disabled_answers), so a disabled field carries no selected
    option and cannot contribute an override; iterating in schema order then
    yields the same "last answer wins" precedence as the client (only
    fieldgroups have children, and they never carry scorable/override options).
    """
    override = None

    for field, entry in iterate_answers(steps, answers):
        triggered = []

        for option in evaluate_selected_options(field, entry):
            for receiver in option.get('trigger_receiver') or []:
                if receiver not in triggered:
                    triggered.append(receiver)

        if triggered:
            override = triggered

    return override


def db_validate_submission_receivers(session, context, steps, answers, requested_receivers):
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
    override = evaluate_receivers_override(steps, answers)
    if override is not None:
        if requested_receivers != set(override):
            raise errors.InputValidationError("The selected recipients do not match the recipients triggered by the answers")
        return

    context_receivers = set()
    mandatory_receivers = set()

    for receiver_id, forcefully_selected in session.query(models.ReceiverContext.receiver_id, models.User.forcefully_selected) \
                                                   .filter(models.ReceiverContext.context_id == context.id,
                                                           models.User.id == models.ReceiverContext.receiver_id,
                                                           models.User.role == 'receiver',
                                                           models.User.enabled.is_(True)):
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
                parse_ISO8601(value)
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
    Reduce the submitted answers, in place, to the canonical data the
    authoritative questionnaire schema defines, an invariant otherwise enforced
    only by the official client. The traversal is driven by the schema so that
    what is persisted maps one-to-one onto the questionnaire the administrator
    configured.

    Every key that does not carry recognised answer data for its field is
    dropped rather than persisted: the client's transient required_status flag,
    a field the questionnaire does not define at that position (a question that
    does not exist), and any key a modified client appends. This is what keeps a
    modified client from smuggling unbounded content under an arbitrary key past
    the per-field length and format checks, and bounds the answers nesting to
    the depth the administrator configured so that arbitrarily deep answers
    cannot later exhaust the recursion limit when recipients open or export the
    report.

    The answer value each field does carry is still validated against the
    field's constraints (see db_validate_field_entry), so that oversized or
    malformed text answers, selections of options the questionnaire does not
    define, and ill-formed date/daterange/tos values are rejected rather than
    stored.
    """
    # Field types whose answer entry carries a single leaf 'value' (text, a
    # selected option id, a date/daterange string or a tos boolean), constrained
    # per type by db_validate_field_entry. The remaining types carry their
    # answer differently: checkbox as option_id -> flag pairs, fieldgroup as
    # child_field_id -> entries, and fileupload/voice carry no leaf value at all
    # (their content flows through the attachments pipeline).
    value_field_types = ('inputbox', 'textarea', 'selectbox', 'multichoice',
                         'date', 'daterange', 'tos')

    def prune_entries(field, entries):
        field_type = field['type']

        children = {}
        if field_type == 'fieldgroup':
            children = {child['id']: child for child in field.get('children', [])}

        option_ids = set()
        if field_type == 'checkbox':
            option_ids = {option['id'] for option in field.get('options', [])}

        for entry in entries:
            if not isinstance(entry, dict):
                raise errors.InputValidationError("Invalid answers structure")

            db_validate_field_entry(field, entry)

            # Keep only the keys that carry recognised answer data for this
            # field and drop everything else: the recursion descends into the
            # children of a fieldgroup (the shape index_answers reads), a
            # checkbox keeps its option flags, a value-bearing field keeps its
            # leaf value, and any other key is discarded so it is neither
            # persisted nor able to escape the checks db_validate_field_entry
            # applied above.
            for key in list(entry.keys()):
                value = entry[key]

                if field_type in value_field_types:
                    if key == 'value':
                        continue
                elif field_type == 'fieldgroup':
                    child = children.get(key)
                    if child is not None and isinstance(value, list):
                        prune_entries(child, value)
                        continue
                elif field_type == 'checkbox':
                    if key in option_ids and isinstance(value, bool):
                        continue

                del entry[key]

    schema_fields = {field['id']: field for step in steps for field in step['children']}

    for key in list(answers.keys()):
        value = answers[key]

        field = schema_fields.get(key) if re.match(requests.uuid_regexp, key) else None
        if field is None or not isinstance(value, list):
            del answers[key]
            continue

        prune_entries(field, value)


def db_validate_answers(session, tid, questionnaire_id, answers, identity_provided):
    """
    Load the authoritative questionnaire schema, with templates serialized so
    that fieldgroup children are present, and enforce that the submitted
    answers conform to it (see db_validate_submission_answers) and do not
    select an option the questionnaire marks as blocking (see
    db_evaluate_block_submission). The schema steps and the answers reconciled
    with the trigger logic are returned for further server-side processing.

    This is the single entry point shared by the submission and the
    whistleblower tip endpoints that persist answers, so that the bound on the
    answers nesting depth and the screening choices that must abort persistence
    are enforced identically everywhere and cannot be forgotten on a code path a
    modified client could reach.

    The blocking-option check, like the recipients override and the triage
    score, is evaluated on the answers reconciled with the trigger logic (see
    db_clear_disabled_answers): a blocking option belonging to a field the
    questionnaire keeps hidden must not abort the submission, exactly as the
    official client only screens the fields it actually enables. The
    reconciliation is performed once here and the result returned so that the
    callers do not repeat it.
    """
    steps = db_get_questionnaire(session, tid, questionnaire_id, None, True)['steps']
    db_validate_submission_answers(steps, answers)

    enabled_answers = db_clear_disabled_answers(steps, answers, identity_provided)

    if db_evaluate_block_submission(steps, enabled_answers):
        raise errors.InputValidationError("Blocked")

    return steps, enabled_answers


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

    # The answers are validated and reconciled with the questionnaire trigger
    # logic once (see db_validate_answers), mirroring the client: the blocking
    # screening, the recipients override and the triage score are all derived
    # from the fields the conditional logic actually enables, so a modified
    # client cannot have a trigger-hidden field counted. The original answers are
    # kept for storage (the whistleblower identity handling reads them).
    steps, enabled_answers = db_validate_answers(session, tid, questionnaire.id, answers, request['identity_provided'])
    questionnaire_hash = db_archive_questionnaire_schema(session, steps)

    db_validate_submission_receivers(session, context, steps, enabled_answers, set(request['receivers']))

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
        itip.score = db_evaluate_answers_score(context, steps, enabled_answers)

    itip.tor = client_using_tor
    itip.mobile = client_using_mobile

    itip.context_id = context.id

    # The automatic additional questionnaire of the channel is asked by the report itself
    itip.additional_questionnaire_id = context.additional_questionnaire_id

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
    identity_provided = False
    if itip.enable_whistleblower_identity and request['identity_provided'] and answers[whistleblower_identity.id]:
        identity_provided = True

        identity_data = answers[whistleblower_identity.id][0]

        if crypto_is_available:
            wbi = Base64Encoder.encode(GCE.asymmetric_encrypt(itip.crypto_tip_pub_key, json.dumps(answers[whistleblower_identity.id][0]).encode())).decode()
        else:
            wbi = answers[whistleblower_identity.id][0]

        answers[whistleblower_identity.id] = ''

        db_set_internaltip_data(session, itip.id, 'whistleblower_identity', wbi, itip.creation_date, identity_data, itip.crypto_tip_pub_key)

    stat_data = extract_statistical_data(session, tid, answers)
    plaintext_answers = answers
    if crypto_is_available:
        if stat_data:
            crypto_stat_pub_key = db_get(session, models.Config.value, (models.Config.tid == tid, models.Config.var_name == 'crypto_stat_pub_key'))[0]
            stat_data = Base64Encoder.encode(GCE.asymmetric_encrypt(crypto_stat_pub_key, json.dumps(stat_data, cls=JSONEncoder).encode())).decode()

        answers = Base64Encoder.encode(GCE.asymmetric_encrypt(itip.crypto_tip_pub_key, json.dumps(answers, cls=JSONEncoder).encode())).decode()

    db_set_internaltip_answers(session, itip.id, context.questionnaire_id, questionnaire_hash, answers, stat_data, itip.creation_date, plaintext_answers, itip.crypto_tip_pub_key)

    operator_id = user_session.properties.get('operator_session', '')
    if operator_id:
        # this is actually an operator which is operating on behalf of a whistleblower
        itip.receipt_change_needed = True
        itip.operator_id = operator_id

    # The report is recorded before the files attached to it, so that its log
    # opens with the report and continues with what it is made of
    db_log(session, tid=tid, type='whistleblower_new_report', user_id=operator_id, object_id=itip.id)

    db_log(session, tid=tid, type='whistleblower_add_answers', user_id=operator_id, object_id=itip.id, data={'questionnaire_hash': questionnaire_hash})

    if identity_provided:
        db_log(session, tid=tid, type='whistleblower_provide_identity', user_id=operator_id, object_id=itip.id)

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

        # A file attached to the report is tracked as one attached later on:
        # the log of the report names every file it is made of
        db_log(session, tid=tid, type='whistleblower_upload_file', user_id=itip.id, object_id=new_file.id, data={'internaltip_id': itip.id})

    for user in receivers:
        if crypto_is_available:
            _tip_key = GCE.asymmetric_encrypt(user.crypto_pub_key, crypto_tip_prv_key)
        else:
            _tip_key = b''

        db_create_receivertip(session, user, itip, _tip_key)



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
