import re

from sqlalchemy.sql.expression import not_

from globaleaks import models
from globaleaks.handlers.base import BaseHandler
from globaleaks.handlers.operation import OperationHandler
from globaleaks.models import fill_localized_keys, get_localized_values
from globaleaks.models.exchanges import db_channel_of_an_exchange, \
                                        db_exchange_types_of_channel, \
                                        db_get_exchange_channel_ids, \
                                        db_is_exchange_channel
from globaleaks.models.config import DEFAULT_PROFILE_ID, \
    db_get_profile_children
from globaleaks.orm import db_add, db_del, db_get, transact
from globaleaks.rest import requests, errors


# The configuration a derived channel inherits from its template
CONTEXT_TEMPLATE_COLUMNS = [
    'show_steps_navigation_interface',
    'allow_recipients_selection',
    'maximum_selectable_receivers',
    'select_all_receivers',
    'tip_timetolive',
    'tip_reminder',
    'name',
    'description',
    'show_receivers_in_alphabetical_order',
    'score_threshold_high',
    'score_threshold_medium',
    'questionnaire_id',
    'additional_questionnaire_id',
    'slug',
    'hidden',
    'order',
    'exchange',
    'internally_available',
    'provide_access_code'
]


def db_derive_context(session, tid, template):
    """
    Create on a tenant the channel derived from a channel of its profile

    :param session: An ORM session
    :param tid: The tenant ID of the tenant deriving the channel
    :param template: The channel of the profile to derive from
    :return: The derived channel
    """
    context = models.Context()
    context.tid = tid
    context.template_id = template.id
    for column in CONTEXT_TEMPLATE_COLUMNS:
        setattr(context, column, getattr(template, column))

    session.add(context)
    session.flush()

    return context


def db_sync_derived_contexts(session, template):
    """
    Align to a channel of a profile the channels the tenants derived from it

    The channels of a tenant profile are templates: the tenants using the
    profile hold a derived channel for each of them, that inherits its
    configuration and follows its updates. The receivers of a derived channel
    are not part of the template: they belong to the tenant and are associated
    through the user profiles.

    :param session: An ORM session
    :param template: The channel of the profile
    """
    for child_tid in db_get_profile_children(session, template.tid):
        derived = session.query(models.Context) \
                         .filter(models.Context.tid == child_tid,
                                 models.Context.template_id == template.id) \
                         .one_or_none()
        if derived is None:
            db_derive_context(session, child_tid, template)
            continue

        for column in CONTEXT_TEMPLATE_COLUMNS:
            setattr(derived, column, getattr(template, column))


def normalize_context_slug(slug):
    return re.sub(r'[^a-z0-9]+', '-', (slug or '').lower()).strip('-')


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
        'slug': context.slug,
        'template_id': context.template_id,
        # The user profiles whose users receive on the channel
        'profiles': [p[0] for p in session.query(models.UserProfileContext.profile_id)
                                          .filter(models.UserProfileContext.context_id == context.id)],
        'exchange': context.exchange,
        'internally_available': context.internally_available,
        'provide_access_code': context.provide_access_code,
        # A channel an exchange runs through is not dropped while it does,
        # and is known on the site by the kinds of exchange it carries
        'exchange_in_use': db_channel_of_an_exchange(session, context),
        'exchange_types': db_exchange_types_of_channel(session, context),
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


def db_associate_context_profiles(session, context, profile_ids):
    """
    Name on a channel the user profiles whose users receive on it

    A user profile carries its users to the channels that name it: the users
    holding it become recipients of them, on the tenant the profile lives on
    and on every tenant inheriting from it, and lose them where the channel
    stops naming the profile. The reports already received stay with their
    recipients: naming a profile decides the reports to come, never the ones
    at rest.

    :param session: An ORM session
    :param context: The channel
    :param profile_ids: The user profiles whose users receive on the channel
    """
    from globaleaks.handlers.admin.user_profile import db_local_context_of

    if profile_ids is None:
        return

    requested = set(profile_ids)

    # A channel names the user profiles of the tenant it lives on
    valid_ids = {p.id for p in session.query(models.UserProfile)
                                      .filter(models.UserProfile.tid == context.tid)}
    if requested - valid_ids:
        raise errors.InputValidationError("Invalid user profile reference")

    associations = session.query(models.UserProfileContext) \
                          .filter(models.UserProfileContext.context_id == context.id) \
                          .all()

    current = {association.profile_id for association in associations}

    for association in associations:
        if association.profile_id not in requested:
            session.delete(association)

    for profile_id in requested - current:
        session.add(models.UserProfileContext({'profile_id': profile_id,
                                               'context_id': context.id}))

    for profile_id in requested ^ current:
        attaching = profile_id in requested

        for user in session.query(models.User) \
                           .filter(models.User.profile_id == profile_id,
                                   models.User.role == 'receiver'):
            local = db_local_context_of(session, user.tid, context.id)
            if local is None:
                continue

            attached = session.query(models.ReceiverContext) \
                              .filter(models.ReceiverContext.context_id == local.id,
                                      models.ReceiverContext.receiver_id == user.id)

            if attaching and not attached.count():
                session.add(models.ReceiverContext({'context_id': local.id,
                                                    'receiver_id': user.id,
                                                    'order': 0}))
            elif not attaching:
                attached.delete()


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

    # While it is expected in the future to possibly allow a user to be
    # enabled on channels of multiple tenants, for the moment it is safer
    # to strictly limit associations to users belonging to the same tenant.
    valid_receivers = session.query(models.User.id).filter(
        models.User.id.in_(receiver_ids),
        models.User.tid == context.tid
    ).count()

    if valid_receivers != len(receiver_ids):
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


def check_context_questionnaire_association(session, tid, request):
    """
    Ensure the questionnaire ids referenced by a context request belong to the
    requesting tenant (or to the platform-wide tenant 1).

    :param session: An ORM session
    :param tid: The tenant ID
    :param request: The request data to be verified
    """
    for key in ('questionnaire_id', 'additional_questionnaire_id'):
        qid = request.get(key, '')
        if not qid:
            continue

        if session.query(models.Questionnaire).filter(
                models.Questionnaire.id == qid,
                not_(models.Questionnaire.tid.in_({1, tid}))).count():
            raise errors.InputValidationError


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
    request['slug'] = normalize_context_slug(request.get('slug', ''))

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

    check_context_questionnaire_association(session, tid, request)

    context = db_add(session, models.Context, request)

    db_associate_context_receivers(session, context, request['receivers'])
    db_associate_context_profiles(session, context, request.get('profiles'))

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

    # The channels of a tenant profile are templates: the tenants using the
    # profile derive a channel from each of them
    if tid >= DEFAULT_PROFILE_ID:
        db_sync_derived_contexts(session, context)

    return admin_serialize_context(session, context, language)


def db_update_exchange_channel(session, tid, context, request, language):
    """
    Update a channel of the exchanges with what is decided of it

    Such a channel carries the name the exchanges running through it are known
    by on this side, the recipients that take part in them and, where the
    reports live here, the questionnaire composing them and how long they
    last. What a channel configures for the reporting people has no part in
    it: they neither reach it nor are offered it, and it is not written here.

    :param session: An ORM session
    :param tid: The tenant ID
    :param context: The channel
    :param request: The request data
    :param language: The request language
    """
    fill_localized_keys(request, ['name'], language)

    check_context_questionnaire_association(session, tid, request)

    context.name = request['name']
    context.questionnaire_id = request.get('questionnaire_id') or 'default'
    context.tip_timetolive = max(0, request.get('tip_timetolive', 0))
    context.tip_reminder = max(0, request.get('tip_reminder', 0))

    db_associate_context_receivers(session, context, request['receivers'])
    db_associate_context_profiles(session, context, request.get('profiles'))


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

    check_context_questionnaire_association(session, tid, request)

    context.update(request)

    db_associate_context_receivers(session, context, request['receivers'])
    db_associate_context_profiles(session, context, request.get('profiles'))

    return context


@transact
def update_context(session, tid, context_id, request, language, root_session=False):
    """
    Transaction for updating a context

    :param session: An ORM session
    :param tid: The tenant ID
    :param context_id: The ID of object to be updated
    :param request: The request data
    :param language: The request language
    :param root_session: Whether the operation is performed by the
        administrators of the platform
    :return: A serialized descriptor of the context
    """
    context = db_get(session,
                     models.Context,
                     (models.Context.tid == tid,
                      models.Context.id == context_id))

    # A channel of the exchanges belongs to the exchanges that run through it:
    # it is configured by the administrators of the platform, that established
    # them, entering the site holding it. The administrators of the site read
    # it where it lives but do not write it
    if db_is_exchange_channel(session, context) and not root_session:
        raise errors.ForbiddenOperation

    # The configuration of a derived channel is inherited from its template
    # and is never written directly: only its receivers belong to the tenant
    if context.template_id:
        db_associate_context_receivers(session, context, request['receivers'])
        return admin_serialize_context(session, context, language)

    # A channel of the exchanges carries the name they are known by, the
    # recipients that take part in them and the questionnaire and the
    # retention of what lives here: the rest of what a channel configures is
    # for the reporting people, that do not reach it, and is not written here
    if db_is_exchange_channel(session, context):
        db_update_exchange_channel(session, tid, context, request, language)

        if tid >= DEFAULT_PROFILE_ID:
            db_sync_derived_contexts(session, context)

        return admin_serialize_context(session, context, language)

    context = db_update_context(session, tid, context, request, language)

    if tid >= DEFAULT_PROFILE_ID:
        db_sync_derived_contexts(session, context)

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


@transact
def delete_context(session, tid, context_id, root_session=False):
    context = db_get(session,
                     models.Context,
                     (models.Context.tid == tid,
                      models.Context.id == context_id))

    # The channel derived from a channel of the profile of the tenant follows
    # its template and is never deleted directly
    if context.template_id:
        raise errors.ForbiddenOperation

    # A channel of the exchanges is dropped by the administrators of the
    # platform, as it is configured by them
    if context.exchange and not root_session:
        raise errors.ForbiddenOperation

    # The template is deleted with the channels derived from it: none of them
    # can be deleted while an exchange runs through it or while it holds
    # reports
    contexts = [context] + session.query(models.Context) \
                                  .filter(models.Context.template_id == context_id) \
                                  .all()

    for c in contexts:
        if c.id in db_get_exchange_channel_ids(session, c.tid):
            raise errors.ForbiddenOperation


        # TODO: After release 5.1.0 it will be possible to delete this code
        if session.query(models.InternalTip).filter(models.InternalTip.context_id == c.id).count():
            raise errors.ForbiddenOperation

    for c in contexts:
        session.delete(c)


class ContextsCollection(OperationHandler):
    check_roles = 'admin'
    require_permission = 'can_manage_channels'
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
    require_permission = 'can_manage_channels'
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
                              self.request.language,
                              self.root_or_management_session())

    def delete(self, context_id):
        """
        Delete the specified context.
        """
        self.check_confirmation()

        return delete_context(self.request.tid, context_id,
                              self.root_or_management_session())
