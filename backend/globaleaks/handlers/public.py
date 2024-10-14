# -*- coding: utf-8 -*-
#
# Handlers dealing with public API exporting main platform configuration/resources
import copy

from sqlalchemy import or_

from globaleaks import models, LANGUAGES_SUPPORTED, LANGUAGES_SUPPORTED_CODES
from globaleaks.handlers.base import BaseHandler
from globaleaks.models import get_localized_values
from globaleaks.models.config import ConfigFactory, ConfigL10NFactory
from globaleaks.orm import db_get, db_query, transact
from globaleaks.state import State

default_questionnaires = ['default']
default_questions = ['whistleblower_identity']

special_files = ['css', 'favicon', 'logo', 'script']

trigger_map = {
    'field': models.FieldOptionTriggerField,
    'step': models.FieldOptionTriggerStep
}


def db_get_languages(session, tid):
    return [x[0] for x in db_query(session, models.EnabledLanguage.name, models.EnabledLanguage.tid == tid)]


def serialize_submission_substatus(substatus, language):
    """
    Transaction to serialize a submission substatus

    :param substatus: The status to be serialized
    :param language: The language to be used in the serialization
    :return: The serialized descriptor of the specified status
    """
    if substatus.tip_timetolive <= -1:
        tip_timetolive_option = -1
    else:
        tip_timetolive_option = 0

    submission_substatus = {
        'id': substatus.id,
        'submissionstatus_id': substatus.submissionstatus_id,
        'order': substatus.order,
        'tip_timetolive': substatus.tip_timetolive,
        'tip_timetolive_option': tip_timetolive_option
    }

    return get_localized_values(submission_substatus, substatus, substatus.localized_keys, language)


def serialize_submission_status(session, status, language):
    """
    Transaction to serialize a submission status

    :param session: An ORM session
    :param status: The status to be serialized
    :param language: The language to be used in the serialization
    :return: The serialized descriptor of the specified status
    """
    submission_status = {
        'id': status.id,
        'order': status.order,
        'substatuses': []
    }

    # See if we have any substatuses we need to serialize
    substatuses = session.query(models.SubmissionSubStatus) \
                         .filter(models.SubmissionSubStatus.tid == status.tid,
                                 models.SubmissionSubStatus.submissionstatus_id == status.id) \
                         .order_by(models.SubmissionSubStatus.order)

    for substatus in substatuses:
        submission_status['substatuses'].append(serialize_submission_substatus(substatus, language))

    return get_localized_values(submission_status, status, status.localized_keys, language)


def db_get_submission_statuses(session, tid, language):
    """
    Transaction for fetching the submission statuses associated to a tenant

    :param session: An ORM session
    :param tid: A tenant ID
    :param language: The language to be used in the serialization
    :return: The list of descriptors for the submission statuses defined on the specified tenant
    """
    system_statuses = {}
    submission_statuses = []
    user_submission_statuses = []

    statuses = session.query(models.SubmissionStatus) \
                      .filter(models.SubmissionStatus.tid == tid) \
                      .order_by(models.SubmissionStatus.order)

    for status in statuses:
        status_dict = serialize_submission_status(session, status, language)
        if status.id in ['new', 'opened', 'closed']:
            system_statuses[status.id] = status_dict
        else:
            user_submission_statuses.append(status_dict)

    # Build the final array in the correct order
    submission_statuses.append(system_statuses['new'])
    submission_statuses.append(system_statuses['opened'])
    submission_statuses += user_submission_statuses
    submission_statuses.append(system_statuses['closed'])

    return submission_statuses


def db_get_submission_status(session, tid, status_id, language):
    """
    Transaction for fetching the submission status given its ID

    :param session: An ORM session
    :param tid: A tenant ID
    :param status_id: The ID of the submission status to be retriven
    :param language: The language to be used in the serialization
    :return: The serialized descriptor of the indicated submission status
    """
    status = db_get(session,
                    models.SubmissionStatus,
                    (models.SubmissionStatus.tid == tid,
                     models.SubmissionStatus.id == status_id))

    return serialize_submission_status(session, status, language)


def db_get_triggers_by_type(session, type, object_id):
    """
    Transaction for retrieving field triggers associated to an object given the type of trigger

    :param session: An ORM session
    :param type: The type of trigger involved in the lookup
    :param object_id: The object on which performing the lookup
    :return: A list of triggers descriptors
    """
    ret = []

    m = trigger_map[type]
    for x in session.query(models.FieldOption.field_id, models.FieldOption.id, m.sufficient) \
                    .filter(models.FieldOption.id == m.option_id, m.object_id == object_id):
        ret.append({'field': x[0], 'option': x[1], 'sufficient': x[2]})

    return ret


def db_prepare_contexts_serialization(session, contexts):
    """
    Transaction to prepare and optimize context serialization

    :param session: An ORM session
    :param contexts: The list of context for which preparing the serialization
    :return: The set of retrieved objects necessary for optimizing the serialization
    """
    data = {'imgs': {}, 'receivers': {}}

    contexts_ids = [c.id for c in contexts]

    if contexts_ids:
        for o in session.query(models.File).filter(models.File.name.in_(contexts_ids)):
            data['imgs'][o.name] = True

        for o in session.query(models.ReceiverContext).filter(models.ReceiverContext.context_id.in_(contexts_ids)).order_by(models.ReceiverContext.order):
            if o.context_id not in data['receivers']:
                data['receivers'][o.context_id] = []

            data['receivers'][o.context_id].append(o.receiver_id)

    return data


def db_prepare_receivers_serialization(session, receivers):
    """
    Transaction to prepare and optimize receiver serialization

    :param session: An ORM session
    :param receivers: The list of receivers for which preparing the serialization
    :return: The set of retrieved objects necessary for optimizing the serialization
    """
    data = {'imgs': {}}

    receivers_ids = [r.id for r in receivers]

    if receivers_ids:
        for o in session.query(models.File).filter(models.File.name.in_(receivers_ids)):
            data['imgs'][o.name] = True

    return data


def db_prepare_fields_serialization(session, fields):
    """
    Transaction to prepare and optimize fields serialization

    :param session: An ORM session
    :param fields: The list of receivers for which preparing the serialization
    :return: The set of retrieved objects necessary for optimizing the serialization
    """
    ret = {
        'fields': {},
        'attrs': {},
        'options': {}
    }

    fields_ids = []
    for f in fields:
        fields_ids.append(f.id)
        if f.template_id is not None:
            fields_ids.append(f.template_id)
        if f.template_override_id is not None:
            fields_ids.append(f.template_override_id)

    tmp = copy.deepcopy(fields_ids)
    while tmp:
        fs = session.query(models.Field).filter(models.Field.fieldgroup_id.in_(tmp))

        tmp = []
        for f in fs:
            tmp.append(f.id)
            if f.template_id is not None:
                tmp.append(f.template_id)
            if f.template_override_id is not None:
                tmp.append(f.template_override_id)

            if f.fieldgroup_id not in ret['fields']:
                ret['fields'][f.fieldgroup_id] = []
            ret['fields'][f.fieldgroup_id].append(f)

        fields_ids.extend(tmp)

    if fields_ids:
        objs = session.query(models.FieldAttr).filter(models.FieldAttr.field_id.in_(fields_ids))
        for obj in objs:
            if obj.field_id not in ret['attrs']:
                ret['attrs'][obj.field_id] = []
            ret['attrs'][obj.field_id].append(obj)

        objs = session.query(models.FieldOption)\
                    .filter(models.FieldOption.field_id.in_(fields_ids)) \
                    .order_by(models.FieldOption.order)
        for obj in objs:
            if obj.field_id not in ret['options']:
                ret['options'][obj.field_id] = []
            ret['options'][obj.field_id].append(obj)

    return ret


def db_serialize_node(session, tid, language):
    """
    Serialize the public node configuration.

    :param session: An ORM session
    :param tid: A tenant ID
    :param language: The language to be used during serialization
    :return: The serialization of the public node configuration
    """
    languages = db_get_languages(session, tid)
    ret = ConfigFactory(session, tid).serialize('public_node')
    ret.update(ConfigL10NFactory(session, tid,).serialize('public_node', language))

    ret['start_time'] = State.start_time
    ret['root_tenant'] = tid == 1
    ret['languages_enabled'] = languages if ret['wizard_done'] else list(LANGUAGES_SUPPORTED_CODES)
    ret['languages_supported'] = LANGUAGES_SUPPORTED

    for x in special_files:
        ret[x] = session.query(models.File.id).filter(models.File.tid == tid, models.File.name == x).one_or_none()

    if tid != 1:
        root_tenant_node = ConfigFactory(session, 1)

        for varname in ['version', 'version_db', 'latest_version']:
            ret[varname] = root_tenant_node.get_val(varname)

        if language not in languages:
            language = root_tenant_node.get_val('default_language')

        root_tenant_l10n = ConfigL10NFactory(session, 1)

        if ret['mode'] != 'default':
            ret['onionservice'] = ret['subdomain'] + '.' + root_tenant_node.get_val('onionservice')

        if ret['mode'] not in ['default', 'demo']:
            ret['disable_privacy_badge'] = root_tenant_node.get_val('disable_privacy_badge')
            ret['footer'] = root_tenant_l10n.get_val('footer', language)
            ret['whistleblowing_question'] = root_tenant_l10n.get_val('whistleblowing_question', language)
            ret['whistleblowing_button'] = root_tenant_l10n.get_val('whistleblowing_button', language)
            ret['disclaimer_text'] = root_tenant_l10n.get_val('disclaimer_text', language)

            for x in special_files:
                if not ret[x]:
                    ret[x] = session.query(models.File.id).filter(models.File.tid == 1, models.File.name == x).one_or_none()

    return ret


def serialize_context(session, context, language, data=None):
    """
    Serialize a context.

    :param session: An ORM session
    :param context: The context to be serialized
    :param language: The language to be used during serialization
    :param data: The dictionary of prefetched resources
    """
    ret = {
        'id': context.id,
        'hidden': context.hidden,
        'order': context.order,
        'tip_timetolive': context.tip_timetolive,
        'tip_reminder': context.tip_reminder,
        'select_all_receivers': context.select_all_receivers,
        'maximum_selectable_receivers': context.maximum_selectable_receivers,
        'allow_recipients_selection': context.allow_recipients_selection,
        'score_threshold_medium': context.score_threshold_medium,
        'score_threshold_high': context.score_threshold_high,
        'show_receivers_in_alphabetical_order': context.show_receivers_in_alphabetical_order,
        'show_steps_navigation_interface': context.show_steps_navigation_interface,
        'questionnaire_id': context.questionnaire_id,
        'additional_questionnaire_id': context.additional_questionnaire_id,
        'receivers': data['receivers'].get(context.id, []),
        'picture': data['imgs'].get(context.id, False)
    }

    return get_localized_values(ret, context, context.localized_keys, language)


def serialize_field_option(option, language):
    """
    Serialize a field option.

    :param option: The option to be serialized
    :param language: The language to be used during serialization
    :return: The serialized resource
    """
    ret = {
        'id': option.id,
        'order': option.order,
        'block_submission': option.block_submission,
        'score_points': option.score_points,
        'score_type': option.score_type,
        'trigger_receiver': option.trigger_receiver
    }

    return get_localized_values(ret, option, option.localized_keys, language)


def serialize_field_attr(attr, language):
    """
    Serialize a field attribute.

    :param attr: The option to be serialized
    :param language: The language to be used during serialization
    :return: The serialized resource
    """
    ret = {
        'name': attr.name,
        'type': attr.type,
        'value': attr.value
    }

    if ret['name'] == 'min_len' and ret['value'] == '-1':
        ret['value'] = '0'
    elif ret['name'] == 'max_len' and ret['value'] <= '-1':
        ret['value'] = '4096'

    if attr.type == 'localized':
        get_localized_values(ret, ret, ['value'], language)

    return ret


def serialize_field(session, tid, field, language, data=None, serialize_templates=False):
    """
    Serialize a field

    :param session: An ORM session
    :param tid: A tenant ID
    :param field: The option to be serialized
    :param language: The language to be used during serialization
    :param data: The dictionary of prefetched resources
    :param serialize_templates: A boolean to require template serialization
    :return: The serialized resource
    """
    if data is None:
        data = db_prepare_fields_serialization(session, [field])

    f_to_serialize = field
    if field.template_override_id is not None:
        f_to_serialize = session.query(models.Field).filter(models.Field.id == field.template_override_id).one_or_none()
    elif field.template_id is not None:
        f_to_serialize = session.query(models.Field).filter(models.Field.id == field.template_id).one_or_none()

    attrs = {}
    if field.template_id is None or field.template_id in default_questions:
        for attr in data['attrs'].get(field.id, {}):
            attrs[attr.name] = serialize_field_attr(attr, language)
    else:
        for attr in data['attrs'].get(field.template_id, {}):
            attrs[attr.name] = serialize_field_attr(attr, language)

    children = []
    if field.instance != 'reference' or serialize_templates:
        children = [serialize_field(session, tid, f, language, data, serialize_templates=serialize_templates) for f in data['fields'].get(f_to_serialize.id, [])]
        children.sort(key=lambda f: (f['y'], f['x']))

    # Enable voice features if questions of type voice are enabled
    if tid in State.tenants and field.type == 'voice':
        State.tenants[tid].microphone = True

    ret = {
        'id': field.id,
        'instance': field.instance,
        'editable': field.id not in default_questions and field.tid == tid,
        'type': f_to_serialize.type,
        'template_id': field.template_id if field.template_id else '',
        'template_override_id': field.template_override_id if field.template_override_id else '',
        'step_id': field.step_id if field.step_id else '',
        'fieldgroup_id': field.fieldgroup_id if field.fieldgroup_id else '',
        'multi_entry': field.multi_entry,
        'required': field.required,
        'attrs': attrs,
        'x': field.x,
        'y': field.y,
        'width': field.width,
        'triggered_by_score': field.triggered_by_score,
        'triggered_by_options': db_get_triggers_by_type(session, 'field', field.id),
        'options': [serialize_field_option(o, language) for o in data['options'].get(f_to_serialize.id, [])],
        'statistical': field.statistical,
        'children': children
    }

    return get_localized_values(ret, f_to_serialize, f_to_serialize.localized_keys, language)


def serialize_step(session, tid, step, language, serialize_templates=False):
    """
    Serialize a step.

    :param session: An ORM session
    :param tid: A tenant ID
    :param step: The option to be serialized
    :param language: The language to be used during serialization
    :param serialize_templates: A boolean to require template serialization
    :return: The serialized resource
    """
    children = session.query(models.Field).filter(models.Field.step_id == step.id)

    data = db_prepare_fields_serialization(session, children)

    children = [serialize_field(session, tid, f, language, data, serialize_templates) for f in children]
    children.sort(key=lambda f: (f['y'], f['x']))

    ret = {
        'id': step.id,
        'questionnaire_id': step.questionnaire_id,
        'order': step.order,
        'triggered_by_score': step.triggered_by_score,
        'triggered_by_options': db_get_triggers_by_type(session, 'step', step.id),
        'children': children
    }

    return get_localized_values(ret, step, step.localized_keys, language)


def serialize_questionnaire(session, tid, questionnaire, language, serialize_templates=False):
    """
    Serialize a questionnaire.

    :param session: An ORM session
    :param tid: A tenant ID
    :param questionnaire: A questionnaire model
    :param language: The language to be used during serialization
    :param serialize_templates: A boolean to require template serialization
    :return: The serialized resource
    """
    steps = session.query(models.Step).filter(models.Step.questionnaire_id == questionnaire.id,
                                              models.Questionnaire.id == questionnaire.id) \
                                      .order_by(models.Step.order)

    ret = {
        'id': questionnaire.id,
        'editable': questionnaire.id not in default_questionnaires and questionnaire.tid == tid,
        'name': questionnaire.name,
        'steps': [serialize_step(session, tid, s, language, serialize_templates=serialize_templates) for s in steps]
    }

    return get_localized_values(ret, questionnaire, questionnaire.localized_keys, language)


def serialize_receiver(session, user, language, data=None):
    """
    Serialize a receiver.

    :param session: An ORM session
    :param user: The model to be serialized
    :param language: The language to be used during serialization
    :param data: The dictionary of prefetched resources
    :return: The serialized resource
    """
    if data is None:
        data = db_prepare_receivers_serialization(session, [user])

    ret = {
        'id': user.id,
        'name': user.public_name,
        'forcefully_selected': user.forcefully_selected,
        'picture': data['imgs'].get(user.id, False)
    }

    if State.tenants[user.tid].cache.simplified_login:
        ret['username'] = user.username

    return get_localized_values(ret, user, user.localized_keys, language)


def db_get_questionnaires(session, tid, language, serialize_templates=False):
    """
    Transaction that serialize the list of public questionnaires

    :param session: An ORM session
    :param tid: The tenant ID
    :param language: The language to be used for the serialization
    :param serialize_templates: A boolean to require template serialization
    :return: A list of contexts descriptors
    """
    if tid in State.tenants:
        State.tenants[tid].microphone = False

    questionnaires = session.query(models.Questionnaire) \
                            .filter(models.Questionnaire.tid.in_({1, tid}),
                                    or_(models.Context.questionnaire_id == models.Questionnaire.id,
                                        models.Context.additional_questionnaire_id == models.Questionnaire.id),
                                    models.Context.tid == tid)

    return [serialize_questionnaire(session, tid, questionnaire, language, serialize_templates=serialize_templates) for questionnaire in questionnaires]


def db_get_contexts(session, tid, language):
    """
    Transaction that serialize the list of public contexts

    :param session: An ORM session
    :param tid: The tenant ID
    :param language: The language to be used for the serialization
    :return: A list of contexts descriptors
    """
    contexts = session.query(models.Context).filter(models.Context.tid == tid)

    data = db_prepare_contexts_serialization(session, contexts)

    return [serialize_context(session, context, language, data) for context in contexts]


def db_get_receivers(session, tid, language):
    """
    Transaction that serialize the list of public receivers

    :param session: An ORM session
    :param tid: The tenant ID
    :param language: The language to be used for the serialization
    :return: A list of receivers descriptors
    """
    receivers = session.query(models.User).filter(models.User.role == models.EnumUserRole.receiver.value,
                                                  models.User.tid == tid)
    data = db_prepare_receivers_serialization(session, receivers)

    return [serialize_receiver(session, receiver, language, data) for receiver in receivers]


@transact
def get_public_resources(session, tid, language):
    """
    Transaction that compose the public API

    :param session: An ORM session
    :param tid: The tenant ID
    :param language: The language to be used for serialization
    :return: The public API descriptor
    """

    return {
        'node': db_serialize_node(session, tid, language),
        'questionnaires': db_get_questionnaires(session, tid, language, True),
        'submission_statuses': db_get_submission_statuses(session, tid, language),
        'receivers': db_get_receivers(session, tid, language),
        'contexts': db_get_contexts(session, tid, language)
    }


class PublicResource(BaseHandler):
    """
    Handler responsible of serving the public API
    """
    check_roles = 'any'
    cache_resource = True

    def get(self):
        """
        Get the public resource
        """
        return get_public_resources(self.request.tid, self.request.language)
