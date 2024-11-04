# -*- coding: utf-8
import logging

from globaleaks import models
from globaleaks.handlers.base import BaseHandler
from globaleaks.handlers.operation import OperationHandler
from globaleaks.models import fill_localized_keys, get_localized_values
from globaleaks.orm import db_add, db_del, db_get, transact, tw
from globaleaks.rest import requests, errors


def admin_serialize_context(session, context, language):
    """
    Serialize the specified context

    :param session: the session on which perform queries
    :param context: The object to be serialized
    :param language: the language in which to localize data.
    :return: a dictionary representing the serialization of the context.
    """
    receivers = [r[0] for r in session.query(models.ReceiverContext.receiver_id)
                                      .filter(models.ReceiverContext.context_id == context.id)
                                      .order_by(models.ReceiverContext.order)]

    picture = session.query(models.File).filter(models.File.name == context.id).one_or_none() is not None

    ret = {
        'id': context.id,
        'hidden': context.hidden,
        'tip_timetolive': context.tip_timetolive,
        'tip_reminder': context.tip_reminder,
        'select_all_receivers': context.select_all_receivers,
        'maximum_selectable_receivers': context.maximum_selectable_receivers,
        'allow_recipients_selection': context.allow_recipients_selection,
        'score_threshold_medium': context.score_threshold_medium,
        'score_threshold_high': context.score_threshold_high,
        'order': context.order,
        'show_receivers_in_alphabetical_order': context.show_receivers_in_alphabetical_order,
        'show_steps_navigation_interface': context.show_steps_navigation_interface,
        'questionnaire_id': context.questionnaire_id,
        'additional_questionnaire_id': context.additional_questionnaire_id,
        'receivers': receivers,
        'picture': picture
    }

    return get_localized_values(ret, context, context.localized_keys, language)


@transact
def get_contexts(session, tid, language):
    """
    Returns the context list.

    :param session: An ORM session
    :param tid: The tenant ID on which perform the lookup
    :param language: the language in which to localize data.
    :return: a dictionary representing the serialization of the contexts.
    """
    contexts = session.query(models.Context) \
                      .filter(models.Context.tid == tid) \
                      .order_by(models.Context.order)

    return [admin_serialize_context(session, context, language) for context in contexts]


def db_associate_context_receivers(session, context, receiver_ids):
    """
    Transaction for associating receivers to a context

    :param session: An ORM session
    :param context: The context on which associate the specified receivers
    :param receiver_ids: A list of receivers ids to be associated to the context
    """
    db_del(session, models.ReceiverContext, models.ReceiverContext.context_id == context.id)

    if not receiver_ids:
        return

    if not session.query(models.Context).filter(models.Context.id == context.id,
                                                models.Context.tid == models.User.tid,
                                                models.User.id.in_(receiver_ids)).count():
        raise errors.InputValidationError

    for i, receiver_id in enumerate(receiver_ids):
        session.add(models.ReceiverContext({'context_id': context.id,
                                            'receiver_id': receiver_id,
                                            'order': i}))


@transact
def get_context(session, tid, context_id, language):
    """
    Transaction for retrieving a context serialized in the specified language

    :param session: The ORM session
    :param tid: The tenant ID
    :param context_id: The contaxt ID
    :param language: The language to be used for the serialization
    :return: a context descriptor serialized in the specified language
    """
    context = session.query(models.Context).filter(models.Context.tid == tid, models.Context.id == context_id).one()

    return admin_serialize_context(session, context, language)


def fill_context_request(tid, request, language):
    """
    An utility function for correcting requests for context configuration

    :param tid: The tenant ID
    :param request: The request data
    :param language: The language of the request
    :return: The request data corrected in some values
    """
    request['tid'] = tid
    fill_localized_keys(request, models.Context.localized_keys, language)

    if not request['allow_recipients_selection']:
        request['select_all_receivers'] = True

    request['tip_timetolive'] = 0 if request['tip_timetolive'] < 0 else request['tip_timetolive']

    if request['select_all_receivers']:
        request['maximum_selectable_receivers'] = 0

    return request


def db_create_context(session, tid, user_session, request, language):
    """
    Transaction for creating a context

    :param session: An ORM session
    :param tid: The tenant ID
    :param user_session: The session of the user performing the operation
    :param request: The request data
    :param language: The request language
    :return: The created context
    """
    logging.debug(user_session)
    request = fill_context_request(tid, request, language)

    context = db_add(session, models.Context, request)

    db_associate_context_receivers(session, context, request['receivers'])

    return context


@transact
def create_context(session, tid, user_session, request, language):
    """
    Transaction for creating a context

    :param session: An ORM session
    :param tid: The tenant ID
    :param user_session: The session of the user performing the operation
    :param request: The request data
    :param language: The request language
    :return: A serialized descriptor of the context
    """
    context = db_create_context(session, tid, user_session, request, language)

    return admin_serialize_context(session, context, language)


def db_update_context(session, tid, context, request, language):
    """
    Transaction for updating a context

    :param session: An ORM session
    :param tid: The tenant ID
    :param context: The object to be updated
    :param request: The request data
    :param language: The request language
    :return: The updated context
    """
    request = fill_context_request(tid, request, language)

    context.update(request)

    db_associate_context_receivers(session, context, request['receivers'])

    return context


@transact
def update_context(session, tid, context_id, request, language):
    """
    Transaction for updating a context

    :param session: An ORM session
    :param tid: The tenant ID
    :param context_id: The ID of object to be updated
    :param request: The request data
    :param language: The request language
    :return: A serialized descriptor of the context
    """
    context = db_get(session,
                     models.Context,
                     (models.Context.tid == tid,
                      models.Context.id == context_id))
    context = db_update_context(session, tid, context, request, language)

    return admin_serialize_context(session, context, language)


@transact
def order_elements(session, tid, ids, *args, **kwargs):
    """
    Transaction for reodering context elements

    :param session:  An ORM session
    :param tid: The tenant ID
    :param ids: The ids of the contexts to be reordered
    """
    ctxs = session.query(models.Context).filter(models.Context.tid == tid)

    id_dict = {ctx.id: ctx for ctx in ctxs}

    for i, ctx_id in enumerate(ids):
        id_dict[ctx_id].order = i


class ContextsCollection(OperationHandler):
    check_roles = 'admin'
    invalidate_cache = True

    def get(self):
        """
        Return all the contexts.
        """
        return get_contexts(self.request.tid, self.request.language)

    def post(self):
        """
        Create a new context.
        """
        request = self.validate_request(self.request.content.read(),
                                        requests.AdminContextDesc)

        return create_context(self.request.tid, self.session, request, self.request.language)

    def order_elements(self, req_args, *args, **kwargs):
        return order_elements(self.request.tid, req_args['ids'])

    def operation_descriptors(self):
        return {
            'order_elements': ContextsCollection.order_elements
        }


class ContextInstance(BaseHandler):
    check_roles = 'admin'
    invalidate_cache = True

    def put(self, context_id):
        """
        Update the specified context.
        """
        request = self.validate_request(self.request.content.read(),
                                        requests.AdminContextDesc)

        return update_context(self.request.tid,
                              context_id,
                              request,
                              self.request.language)

    def delete(self, context_id):
        """
        Delete the specified context.
        """
        return tw(db_del,
                  models.Context,
                  (models.Context.tid == self.request.tid,
                   models.Context.id == context_id))
