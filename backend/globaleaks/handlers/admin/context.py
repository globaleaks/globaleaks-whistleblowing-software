from globaleaks import models
from globaleaks.handlers.base import BaseHandler
from globaleaks.handlers.operation import OperationHandler
from globaleaks.models import fill_localized_keys, get_localized_values
from globaleaks.orm import db_add, db_del, db_get, db_log, transact, tw
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
    Returns the context list (excluding deleted contexts).

    :param session: An ORM session
    :param tid: The tenant ID on which perform the lookup
    :param language: the language in which to localize data.
    :return: a dictionary representing the serialization of the contexts.
    """
    contexts = session.query(models.Context) \
                      .filter(models.Context.tid == tid,
                              models.Context.deleted == False) \
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


def db_get_context_stats(session, tid, context_id):
    """
    Get statistics about a context's reports.

    :param session: An ORM session
    :param tid: A tenant ID
    :param context_id: A context ID
    :return: Dictionary with open_reports, total_reports counts, and last_update timestamp
    """
    from sqlalchemy import func

    total_reports = session.query(models.InternalTip).filter(
        models.InternalTip.tid == tid,
        models.InternalTip.context_id == context_id
    ).count()

    open_reports = session.query(models.InternalTip).filter(
        models.InternalTip.tid == tid,
        models.InternalTip.context_id == context_id,
        models.InternalTip.status != 'closed'
    ).count()

    # Get the latest update timestamp from reports in this context
    last_update = session.query(func.max(models.InternalTip.update_date)).filter(
        models.InternalTip.tid == tid,
        models.InternalTip.context_id == context_id
    ).scalar()

    return {
        'open_reports': open_reports,
        'total_reports': total_reports,
        'last_update': last_update.isoformat() if last_update else None
    }


@transact
def get_context_stats(session, tid, context_id):
    return db_get_context_stats(session, tid, context_id)


def db_delete_context(session, tid, user_session, context_id, expected_open=None, expected_total=None, expected_last_update=None):
    """
    Soft delete a context after validating stats.

    Instead of deleting the context, this marks it as deleted and removes
    all recipient associations while preserving the reports.

    :param session: An ORM session
    :param tid: The tenant ID
    :param user_session: The user session
    :param context_id: The context ID to delete
    :param expected_open: Expected open reports count
    :param expected_total: Expected total reports count
    :param expected_last_update: Expected last update timestamp
    """
    context = db_get(session,
                     models.Context,
                     (models.Context.tid == tid,
                      models.Context.id == context_id))

    # Get context stats before deletion for audit log
    stats = db_get_context_stats(session, tid, context_id)

    # If expected stats were provided, validate they match current stats
    # This prevents race conditions where reports change between viewing stats and confirming deletion
    if expected_open is not None and expected_total is not None:
        stats_changed = (
            stats['open_reports'] != expected_open or
            stats['total_reports'] != expected_total or
            stats['last_update'] != expected_last_update
        )
        if stats_changed:
            raise errors.ContextStatsChanged

    # Soft delete: mark context as deleted
    context.deleted = True

    # Remove all recipient associations
    db_del(session, models.ReceiverContext, models.ReceiverContext.context_id == context_id)

    # Log the deletion
    db_log(session, tid=tid, type='delete_context', user_id=user_session.user_id, object_id=context_id, data=stats)


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
        Soft delete the specified context.

        Query parameters:
          - expected_open: Expected open reports count (optional, for race condition prevention)
          - expected_total: Expected total reports count (optional, for race condition prevention)
          - expected_last_update: Expected last update timestamp (optional, for race condition prevention)
        """
        expected_open = self.request.args.get(b'expected_open', [None])[0]
        expected_total = self.request.args.get(b'expected_total', [None])[0]
        expected_last_update = self.request.args.get(b'expected_last_update', [None])[0]

        if expected_open is not None:
            expected_open = int(expected_open)
        if expected_total is not None:
            expected_total = int(expected_total)
        if expected_last_update is not None:
            expected_last_update = expected_last_update.decode('utf-8') if isinstance(expected_last_update, bytes) else expected_last_update

        return tw(db_delete_context, self.request.tid, self.session, context_id, expected_open, expected_total, expected_last_update)


class ContextStats(BaseHandler):
    check_roles = 'admin'

    def get(self, context_id):
        """
        Retrieve statistics about a context's reports.
        """
        return get_context_stats(self.request.tid, context_id)
