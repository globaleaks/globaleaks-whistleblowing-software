# -*- coding: utf-8
from globaleaks import models
from globaleaks.handlers.admin.step import db_create_step
from globaleaks.handlers.base import BaseHandler
from globaleaks.handlers.public import serialize_questionnaire
from globaleaks.models import fill_localized_keys
from globaleaks.orm import db_add, db_del, db_get, transact, tw
from globaleaks.rest import requests
from globaleaks.utils.utility import uuid4


def db_get_questionnaires(session, tid, language):
    """
    Transaction to retrieve the questionnnaires associated to a tenant

    :param session: the session on which perform queries.
    :param tid: A tenant ID
    :param language: The language to be used for the serialization
    :return: a dictionary representing the serialization of the questionnaires.
    """
    questionnaires = session.query(models.Questionnaire).filter(models.Questionnaire.tid.in_({1, tid}))

    return [serialize_questionnaire(session, tid, questionnaire, language) for questionnaire in questionnaires]


def db_get_questionnaire(session, tid, questionnaire_id, language, serialize_templates=False):
    questionnaire = db_get(session,
                           models.Questionnaire,
                           (models.Questionnaire.tid.in_({1, tid}),
                            models.Questionnaire.id == questionnaire_id))

    return serialize_questionnaire(session, tid, questionnaire, language, serialize_templates=serialize_templates)


def db_create_questionnaire(session, tid, user_session, questionnaire_dict, language):
    fill_localized_keys(questionnaire_dict,
                        models.Questionnaire.localized_keys, language)

    questionnaire_dict['tid'] = tid
    q = db_add(session, models.Questionnaire, questionnaire_dict)

    steps = questionnaire_dict.get('steps', [])

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


@transact
def duplicate_questionnaire(session, tid, user_session, questionnaire_id, new_name):
    """
    Transaction for duplicating an existing questionnaire

    :param session: An ORM session
    :param tid: A tnenat ID
    :param questionnaire_id A questionnaire ID
    :param new_name: The name to be assigned to the new questionnaire
    """
    id_map = {}

    q = db_get_questionnaire(session, tid, questionnaire_id, None, False)

    # We need to change the primary key references and so this can be reimported
    # as a new questionnaire
    q['id'] = uuid4()

    # Each step has a UUID that needs to be replaced

    def fix_field_pass_1(field):
        new_child_id = uuid4()
        id_map[field['id']] = new_child_id
        field['id'] = new_child_id

        # Tweak the field in order to make a raw copy
        field['instance'] = 'instance'

        # Rewrite the option ID if it exists
        for option in field['options']:
            option_id = option.get('id', None)
            if option_id is not None:
                new_option_id = uuid4()
                id_map[option['id']] = new_option_id
                option['id'] = new_option_id

        # And now we need to keep going down the latter
        for attr in field['attrs'].values():
            attr['id'] = uuid4()

        # Recursion!
        for child in field['children']:
            child['field_id'] = new_child_id
            fix_field_pass_1(child)

    def fix_field_pass_2(field):
        # Fix triggers references
        for trigger in field.get('triggered_by_options', []):
            trigger['field'] = id_map[trigger['field']]
            trigger['option'] = id_map[trigger['option']]

        # Recursion!
        for child in field['children']:
            fix_field_pass_2(child)

    # Step1: replacement of IDs
    for step in q['steps']:
        new_step_id = uuid4()
        id_map[step['id']] = new_step_id
        step['id'] = new_step_id

        # Each field has a UUID that needs to be replaced
        for field in step['children']:
            field['step_id'] = step['id']
            fix_field_pass_1(field)

    # Step2: fix of fields triggers following IDs replacement
    for step in q['steps']:
        # Fix triggers references
        for trigger in step.get('triggered_by_options', []):
            trigger['field'] = id_map[trigger['field']]
            trigger['option'] = id_map[trigger['option']]

        for field in step['children']:
            fix_field_pass_2(field)

    q['name'] = new_name

    db_create_questionnaire(session, tid, user_session, q, None)


class QuestionnairesCollection(BaseHandler):
    check_roles = ['admin', 'receiver']
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
