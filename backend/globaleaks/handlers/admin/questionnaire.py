from globaleaks import models
from globaleaks.handlers.admin.step import db_create_step
from globaleaks.handlers.base import BaseHandler
from globaleaks.handlers.public import serialize_questionnaire
from globaleaks.models import fill_localized_keys
from globaleaks.orm import db_add, db_del, db_get, transact, tw
from globaleaks.rest import requests
from globaleaks.utils.utility import uuid4
from globaleaks.state import State


def db_get_questionnaires(session, tid, language):
    """
    Transaction to retrieve the questionnnaires associated to a tenant

    :param session: the session on which perform queries.
    :param tid: A tenant ID
    :param language: The language to be used for the serialization
    :return: a dictionary representing the serialization of the questionnaires.
    """
    if tid in State.tenants and hasattr(State.tenants[tid].cache, 'ptid'):
        ptid = State.tenants[tid].cache.ptid
    else:
        ptid = None

    tenant_ids = {1, tid}
    if ptid:
        tenant_ids.add(ptid)

    questionnaires = session.query(models.Questionnaire).filter(models.Questionnaire.tid.in_(tenant_ids))

    return [serialize_questionnaire(session, tid, questionnaire, language) for questionnaire in questionnaires]


def db_get_questionnaire(session, tid, questionnaire_id, language, serialize_templates=False):
    questionnaire = db_get(session,
                           models.Questionnaire,
                           (models.Questionnaire.tid.in_({1, tid, State.tenants[tid].cache.ptid}),
                            models.Questionnaire.id == questionnaire_id))

    return serialize_questionnaire(session, tid, questionnaire, language, serialize_templates=serialize_templates)


def db_create_questionnaire(session, tid, user_session, questionnaire_dict, language):
    fill_localized_keys(questionnaire_dict,
                        models.Questionnaire.localized_keys, language)

    questionnaire_dict['tid'] = tid
    q = db_add(session, models.Questionnaire, questionnaire_dict)

    for step in questionnaire_dict.get('steps', []):
        step['questionnaire_id'] = q.id
        db_create_step(session, tid, step, language)

    return q


@transact
def create_questionnaire(session, tid, user_session, request, language):
    """
    Updates the specified questionnaire. If the key receivers is specified we remove
    the current receivers of the Questionnaire and reset set it to the new specified
    ones.

    :param session: An ORM session
    :param tid: A tenant ID
    :param user_session: The session of the user performing the operation
    :param request: The request data
    :param language: The language of the request
    :return: A serialized descriptor of the questionnaire
    """
    questionnaire = db_create_questionnaire(session, tid, user_session, request, language)

    return serialize_questionnaire(session, tid, questionnaire, language)


def db_update_questionnaire(session, tid, questionnaire_id, request, language):
    """
    Updates the specified questionnaire. If the key receivers is specified we remove
    the current receivers of the Questionnaire and reset set it to the new specified
    ones.

    :param session: An ORM session
    :param tid: A tenant ID
    :param questionnaire_id: The ID of the model to be updated
    :param request: The request data
    :param language: The language of the request
    :return: A serialized descriptor of the questionnaire
    """
    questionnaire = db_get(session,
                           models.Questionnaire,
                           (models.Questionnaire.tid == tid,
                            models.Questionnaire.id == questionnaire_id))

    fill_localized_keys(request, models.Questionnaire.localized_keys, language)

    questionnaire.update(request)

    return serialize_questionnaire(session, tid, questionnaire, language)


def _reidentify_field(field, new_step_id, id_map):
    """
    Give a field, its options and its attributes an identity of their own

    :param field: The field being imported
    :param new_step_id: The identity the step the field belongs to is imported under
    :param id_map: The map from the identities of the source to the imported ones
    """
    new_field_id = str(uuid4())
    id_map[field['id']] = new_field_id
    field['id'] = new_field_id
    field['step_id'] = new_step_id

    # Update option IDs
    for option in field.get('options', []):
        if 'id' in option:
            new_option_id = str(uuid4())
            id_map[option['id']] = new_option_id
            option['id'] = new_option_id

    # Update field attributes
    for attr in field.get('attrs', {}).values():
        if 'id' in attr:
            attr['id'] = str(uuid4())


def _remap_triggers(obj, id_map):
    """
    Point the triggers of a step or of a field to the imported fields and options

    :param obj: The step or the field carrying the triggers
    :param id_map: The map from the identities of the source to the imported ones
    """
    for trigger in obj.get('triggered_by_options', []):
        for key in ['field', 'option']:
            if trigger.get(key) in id_map:
                trigger[key] = id_map[trigger[key]]


def db_import_questionnaire(session, tid, questionnaire):
    """
    Duplicate questionnaire for a new tenant

    :param session: An ORM session
    :param tid: The new tenant ID
    :param questionnaire: Source questionnaire data
    """
    # Create a deep copy of the questionnaire to avoid modifying the original
    q = questionnaire.copy()

    # Generate new UUID for the questionnaire
    old_questionnaire_id = q['id']
    q['id'] = str(uuid4())

    # Update step IDs and field IDs
    id_map = {old_questionnaire_id: q['id']}

    for step in q['steps']:
        new_step_id = str(uuid4())
        id_map[step['id']] = new_step_id
        step['id'] = new_step_id
        step['questionnaire_id'] = q['id']

        for field in step['children']:
            _reidentify_field(field, new_step_id, id_map)

    # Update trigger references
    for step in q['steps']:
        _remap_triggers(step, id_map)

        for field in step['children']:
            _remap_triggers(field, id_map)

    # Create the new questionnaire in the database
    db_create_questionnaire(session, tid, None, q, 'en')

    # Imported under an identity of its own; the channels that referenced it are rewired by name
    return old_questionnaire_id, q['id']


@transact
def import_questionnaires(session, tid, questionnaire):
    """
    Duplicate questionnaire for a new tenant

    :param session: An ORM session
    :param tid: The new tenant ID
    :param questionnaire: Source questionnaire data
    :return: The identity the questionnaire had and the one it is imported under
    """
    return db_import_questionnaire(session, tid, questionnaire)


def _reidentify_duplicated_field(field, id_map):
    """
    Give a duplicated field, its options, its attributes and its children an identity of their own

    :param field: The field being duplicated
    :param id_map: The map from the identities of the source to the duplicated ones
    """
    new_child_id = uuid4()
    id_map[field['id']] = new_child_id
    field['id'] = new_child_id

    # Tweak the field in order to make a raw copy
    field['instance'] = 'instance'

    # Rewrite the option ID if it exists
    for option in field['options']:
        if option.get('id', None) is not None:
            new_option_id = uuid4()
            id_map[option['id']] = new_option_id
            option['id'] = new_option_id

    # And now we need to keep going down the latter
    for attr in field['attrs'].values():
        attr['id'] = uuid4()

    # Recursion!
    for child in field['children']:
        child['field_id'] = new_child_id
        _reidentify_duplicated_field(child, id_map)


def _rewire_triggers(obj, id_map):
    """
    Point the triggers of a duplicated step or field to the duplicated fields and options

    :param obj: The step or the field carrying the triggers
    :param id_map: The map from the identities of the source to the duplicated ones
    """
    for trigger in obj.get('triggered_by_options', []):
        trigger['field'] = id_map[trigger['field']]
        trigger['option'] = id_map[trigger['option']]


def _rewire_field_triggers(field, id_map):
    """
    Point the triggers of a duplicated field and of its children to the duplicated ones

    :param field: The field carrying the triggers
    :param id_map: The map from the identities of the source to the duplicated ones
    """
    _rewire_triggers(field, id_map)

    # Recursion!
    for child in field['children']:
        _rewire_field_triggers(child, id_map)


@transact
def duplicate_questionnaire(session, tid, user_session, questionnaire_id, new_name):
    """
    Transaction for duplicating an existing questionnaire

    :param session: An ORM session
    :param tid: A tnenat ID
    :param user_session: The session of the user performing the operation
    :param questionnaire_id A questionnaire ID
    :param new_name: The name to be assigned to the new questionnaire
    """
    id_map = {}
    questionnaire = session.query(models.Questionnaire).filter(models.Questionnaire.id == questionnaire_id).first()

    if questionnaire and questionnaire.tid > 1000000:
        q = db_get_questionnaire(session, questionnaire.tid, questionnaire_id, None, False)
    else:
        q = db_get_questionnaire(session, tid, questionnaire_id, None, False)

    # We need to change the primary key references and so this can be reimported
    # as a new questionnaire
    q['id'] = uuid4()

    # Step1: replacement of IDs; each step has a UUID that needs to be replaced
    for step in q['steps']:
        new_step_id = uuid4()
        id_map[step['id']] = new_step_id
        step['id'] = new_step_id

        # Each field has a UUID that needs to be replaced
        for field in step['children']:
            field['step_id'] = step['id']
            _reidentify_duplicated_field(field, id_map)

    # Step2: fix of fields triggers following IDs replacement
    for step in q['steps']:
        # Fix triggers references
        _rewire_triggers(step, id_map)

        for field in step['children']:
            _rewire_field_triggers(field, id_map)

    q['name'] = new_name

    db_create_questionnaire(session, tid, user_session, q, None)


class QuestionnairesCollection(BaseHandler):
    check_roles = 'admin'
    require_permission = 'can_manage_questionnaires'
    invalidate_cache = True

    def get(self):
        """
        Return all the questionnaires.
        """
        return tw(db_get_questionnaires, self.request.tid, self.request.language)

    def post(self):
        """
        Create a new questionnaire.
        """
        if self.request.multilang:
            language = None
            validator = requests.AdminQuestionnaireDescRaw
        else:
            language = self.request.language
            validator = requests.AdminQuestionnaireDesc

        request = self.validate_request(self.request.content.read(), validator)

        return create_questionnaire(self.request.tid, self.session, request, language)


class QuestionnaireInstance(BaseHandler):
    check_roles = 'admin'
    require_permission = 'can_manage_questionnaires'
    invalidate_cache = True

    def get(self, questionnaire_id):
        """
        Export questionnaire JSON
        """
        return tw(db_get_questionnaire, self.request.tid, questionnaire_id, None)

    def put(self, questionnaire_id):
        """
        Update the specified questionnaire.
        """
        request = self.validate_request(self.request.content.read(),
                                        requests.AdminQuestionnaireDesc)

        return tw(db_update_questionnaire,
                  self.request.tid,
                  questionnaire_id,
                  request,
                  self.request.language)

    def delete(self, questionnaire_id):
        """
        Delete the specified questionnaire.
        """
        return tw(db_del,
                  models.Questionnaire,
                  (models.Questionnaire.tid == self.request.tid,
                   models.Questionnaire.id == questionnaire_id))


class QuestionnareDuplication(BaseHandler):
    check_roles = 'admin'
    require_permission = 'can_manage_questionnaires'
    invalidate_cache = True

    def post(self):
        """
        Duplicates a questionnaire
        """

        request = self.validate_request(self.request.content.read(),
                                        requests.QuestionnaireDuplicationDesc)

        return duplicate_questionnaire(self.request.tid,
                                       self.session,
                                       request['questionnaire_id'],
                                       request['new_name'])
