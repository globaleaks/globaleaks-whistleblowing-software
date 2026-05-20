from twisted.internet.defer import inlineCallbacks, returnValue

from globaleaks import models
from globaleaks.handlers.base import BaseHandler
from globaleaks.handlers.operation import OperationHandler
from globaleaks.handlers.public import db_get_submission_status, \
    db_get_submission_statuses, serialize_submission_status, \
    serialize_submission_substatus
from globaleaks.models import fill_localized_keys
from globaleaks.orm import db_del, db_get, transact, tw
from globaleaks.rest import errors, requests


def db_update_status_model_from_request(model_obj, request, language):
    """
    Populates the model from the request, as well as setting default values

    :param model_obj: The object model
    :param request: The request data
    :param language: The language of the request
    """
    fill_localized_keys(request, models.SubmissionStatus.localized_keys, language)
    model_obj.update(request)


def db_create_submission_status(session, tid, request, language):
    """
    Transaction for registering a submission status creation

    :param session: An ORM session
    :param tid: The tenant ID
    :param request: The request data
    :param language: The language of the request
    :return: The serialized descriptor of the created submission status
    """
    new_status = models.SubmissionStatus()
    new_status.tid = tid

    db_update_status_model_from_request(new_status, request, language)
    session.add(new_status)
    session.flush()

    return serialize_submission_status(session, new_status, language)


def db_update_submission_status(session, tid, status_id, request, language):
    """
    Transaction for updating a submission status

    :param session: An ORM session
    :param tid: The tenant ID
    :param status_id: The ID of the object to be updated
    :param request: The request data
    :param language: The language of the request
    :return: The serialized descriptor of the updated object
    """
    status = db_get(session,
                    models.SubmissionStatus,
                    (models.SubmissionStatus.tid == tid,
                     models.SubmissionStatus.id == status_id))

    db_update_status_model_from_request(status, request, language)


def db_update_substatus_model_from_request(model_obj, request, language):
    """
    Populates the model from the request, as well as setting default values

    :param model_obj: The object model
    :param request: The request data
    :param language: The language of the request
    """
    fill_localized_keys(request, models.SubmissionSubStatus.localized_keys, language)
    model_obj.update(request)


def db_update_submission_substatus(session, tid, status_id, substatus_id, request, language):
    """
    Transaction for updating a submission substatus

    :param session: An ORM session
    :param tid: The tenant ID
    :param status_id: The ID of the status object to be updated
    :param substatus_id: The ID of the substatus object to be updated
    :param request: The request data
    :param language: The language of the request
    :return: The serialized descriptor of the updated object
    """
    substatus = db_get(session,
                       models.SubmissionSubStatus,
                       (models.SubmissionStatus.id == status_id,
                        models.SubmissionStatus.tid == tid,
                        models.SubmissionSubStatus.submissionstatus_id == models.SubmissionStatus.id,
                        models.SubmissionSubStatus.id == substatus_id))

    db_update_substatus_model_from_request(substatus, request, language)


def db_create_submission_substatus(session, tid, status_id, request, language):
    """
    Transaction for registering a submission substatus creation

    :param session: An ORM session
    :param tid: The tenant ID
    :param status_id: The ID of the parent status
    :param request: The request data
    :param language: The language of the request
    :return: The serialized descriptor of the created submission status
    """
    # Authorize: the parent status must belong to the requesting tenant
    db_get(session,
           models.SubmissionStatus,
           (models.SubmissionStatus.id == status_id,
            models.SubmissionStatus.tid == tid))

    substatus_obj = models.SubmissionSubStatus()
    substatus_obj.tid = tid
    substatus_obj.submissionstatus_id = status_id

    db_update_substatus_model_from_request(substatus_obj, request, language)

    session.add(substatus_obj)
    session.flush()

    return serialize_submission_substatus(substatus_obj, language)


@transact
def order_status_elements(session, handler, req_args, *args, **kwargs):
    """Sets the presentation order for status elements"""
    statuses = session.query(models.SubmissionStatus) \
                      .filter(models.SubmissionStatus.tid == handler.request.tid)

    id_dict = {status.id: status for status in statuses}
    ids = req_args['ids']

    for i, status_id in enumerate(ids):
        id_dict[status_id].order = i


@transact
def order_substatus_elements(session, handler, req_args, *args, **kwargs):
    """Sets presentation order for substatuses"""
    status_id = args[0]

    substatuses = session.query(models.SubmissionSubStatus) \
                         .filter(models.SubmissionSubStatus.tid == handler.request.tid,
                                 models.SubmissionSubStatus.submissionstatus_id == status_id)

    id_dict = {substatus.id: substatus for substatus in substatuses}
    ids = req_args['ids']

    for i, substatus_id in enumerate(ids):
        id_dict[substatus_id].order = i


class SubmissionStatusCollection(OperationHandler):
    check_roles = 'admin'
    invalidate_cache = True

    def get(self):
        return tw(db_get_submission_statuses, self.request.tid, self.request.language)

    def post(self):
        request = self.validate_request(self.request.content.read(),
                                        requests.SubmissionStatusDesc)

        return tw(db_create_submission_status, self.request.tid, request, self.request.language)

    def operation_descriptors(self):
        return {
            'order_elements': order_status_elements
        }


class SubmissionStatusInstance(BaseHandler):
    check_roles = 'admin'
    invalidate_cache = True

    def put(self, status_id):
        request = self.validate_request(self.request.content.read(),
                                        requests.SubmissionStatusDesc)

        return tw(db_update_submission_status, self.request.tid, status_id, request, self.request.language)

    def delete(self, status_id):
        return tw(db_del,
                  models.SubmissionStatus,
                  (models.SubmissionStatus.tid == self.request.tid,
                   models.SubmissionStatus.id == status_id))


class SubmissionSubStatusCollection(OperationHandler):
    """Manages substatuses for a given status"""
    check_roles = 'admin'
    invalidate_cache = True

    @inlineCallbacks
    def get(self, status_id):
        submission_status = yield tw(db_get_submission_status,
                                     self.request.tid,
                                     status_id,
                                     self.request.language)

        returnValue(submission_status['substatuses'])

    def post(self, status_id):
        request = self.validate_request(self.request.content.read(),
                                        requests.SubmissionSubStatusDesc)

        if request["tip_timetolive"] < -1:
            raise errors.ForbiddenOperation

        return tw(db_create_submission_substatus, self.request.tid, status_id, request, self.request.language)

    def operation_descriptors(self):
        return {
            'order_elements': order_substatus_elements,
        }


class SubmissionSubStatusInstance(BaseHandler):
    check_roles = 'admin'
    invalidate_cache = True

    def put(self, status_id, substatus_id):
        request = self.validate_request(self.request.content.read(),
                                        requests.SubmissionSubStatusDesc)

        return tw(db_update_submission_substatus,
                  self.request.tid,
                  status_id,
                  substatus_id,
                  request,
                  self.request.language)

    def delete(self, status_id, substatus_id):
        return tw(db_del,
                  models.SubmissionSubStatus,
                  (models.SubmissionSubStatus.tid == self.request.tid,
                   models.SubmissionSubStatus.id == substatus_id,
                   models.SubmissionSubStatus.submissionstatus_id == status_id))
