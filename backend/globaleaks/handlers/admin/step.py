from globaleaks import models
from globaleaks.handlers.admin.field import db_create_field, db_update_field, db_create_option_trigger, db_reset_option_triggers
from globaleaks.handlers.base import BaseHandler
from globaleaks.handlers.operation import OperationHandler
from globaleaks.handlers.public import serialize_step
from globaleaks.models import fill_localized_keys
from globaleaks.orm import db_add, db_del, db_get, transact, tw
from globaleaks.rest import requests, errors


def db_create_step(session, tid, request, language):
    """
    Transaction for creating a step

    :param session: An ORM session
    :param tid: A tenant ID
    :param request: The request data
    :param session: the session on which perform queries.
    :param language: the language of the specified steps.
    """
    fill_localized_keys(request, models.Step.localized_keys, language)

    # Authorize: the questionnaire must belong to the requesting tenant
    db_get(session,
           models.Questionnaire,
           (models.Questionnaire.id == request['questionnaire_id'],
            models.Questionnaire.tid == tid))

    step = db_add(session, models.Step, request)

    for trigger in request.get('triggered_by_options', []):
        db_create_option_trigger(session, tid, trigger['option'], 'step', step.id, trigger.get('sufficient', True))

    for c in request['children']:
        c['tid'] = tid
        c['step_id'] = step.id
        db_create_field(session, tid, c, language)

    return serialize_step(session, tid, step, language)


def db_update_step(session, tid, step_id, request, language):
    """
    Transaction for updating a step

    :param session: An ORM session
    :param tid: The tenant ID
    :param step_id: the step_id of the step to update
    :param request: the step definition dict
    :param language: the language of the step definition dict
    :return: a serialization of the object
    """
    # Authorize: the target questionnaire must belong to the requesting tenant
    db_get(session,
           models.Questionnaire,
           (models.Questionnaire.id == request['questionnaire_id'],
            models.Questionnaire.tid == tid))

    step = db_get(session,
                         models.Step,
                         (models.Step.id == step_id,
                          models.Questionnaire.id == models.Step.questionnaire_id,
                          models.Questionnaire.tid == tid))

    fill_localized_keys(request, models.Step.localized_keys, language)

    step.update(request)

    for child in request['children']:
        db_update_field(session, tid, child['id'], child, language)

    db_reset_option_triggers(session, 'step', step.id)

    for trigger in request.get('triggered_by_options', []):
        db_create_option_trigger(session, tid, trigger['option'], 'step', step.id, trigger.get('sufficient', True))

    return serialize_step(session, tid, step, language)


def db_delete_step(session, tid, step_id):
    questionnaire_ids = [qid for (qid,) in session.query(models.Questionnaire.id).filter(
        models.Questionnaire.tid == tid
    ).all()]

    db_del(session,
           models.Step,
           (models.Step.id == step_id,
            models.Step.questionnaire_id.in_(questionnaire_ids)))


@transact
def order_elements(session, handler, req_args, *args, **kwargs):
    steps = session.query(models.Step) \
                   .filter(models.Step.questionnaire_id == req_args['questionnaire_id'],
                           models.Questionnaire.id == req_args['questionnaire_id'],
                           models.Questionnaire.tid == handler.request.tid)

    id_dict = {step.id: step for step in steps}
    ids = req_args['ids']

    if len(ids) != len(id_dict) and set(ids) != set(id_dict):
        raise errors.InputValidationError('list does not contain all context ids')

    for i, step_id in enumerate(ids):
        id_dict[step_id].order = i


class StepCollection(OperationHandler):
    check_roles = 'admin'
    invalidate_cache = True

    def post(self):
        request = self.validate_request(self.request.content.read(),
                                        requests.AdminStepDesc)

        return tw(db_create_step, self.request.tid, request, self.request.language)

    def operation_descriptors(self):
        return {
            'order_elements': order_elements
        }


class StepInstance(BaseHandler):
    check_roles = 'admin'
    invalidate_cache = True

    def put(self, step_id):
        request = self.validate_request(self.request.content.read(),
                                        requests.AdminStepDesc)

        return tw(db_update_step, self.request.tid, step_id, request, self.request.language)

    def delete(self, step_id):
        return tw(db_delete_step, self.request.tid, step_id)
