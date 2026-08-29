# Handlers dealing with the exchanges established between the sites
from globaleaks import models
from globaleaks.handlers.admin.context import db_sync_derived_contexts
from globaleaks.handlers.base import BaseHandler
from globaleaks.models.config import ConfigFactory, DEFAULT_PROFILE_ID, \
                                     db_get_tid_by_uuid
from globaleaks.models.enums import EnumExchangeOwner, EnumExchangeType
from globaleaks.models.exchanges import db_exchange_owner_side, \
                                        db_get_exchange_channel
from globaleaks.orm import db_get, transact
from globaleaks.rest import errors, requests


def db_exchange_mode(session, exchange):
    """
    Return the mode of an exchange, the kind of objects it relates

    :param session: An ORM session
    :param exchange: The exchange
    :return: The mode of the exchange
    """
    sides = []
    for uuid in [exchange.source, exchange.target]:
        tid = db_get_tid_by_uuid(session, uuid)
        sides.append('profile' if tid is not None and tid >= DEFAULT_PROFILE_ID else 'site')

    return '-'.join(sides)


def serialize_exchange(session, exchange, language='en'):
    """
    Serialize an exchange for the administrators of the platform

    :param session: An ORM session
    :param exchange: The exchange
    :param language: The language the channel is named in
    :return: The serialized exchange
    """
    target_tid = db_get_tid_by_uuid(session, exchange.target)
    channel = db_get_exchange_channel(session, exchange, target_tid) \
        if target_tid is not None else None

    ret = {
        'id': exchange.id,
        'type': exchange.type,
        'mode': db_exchange_mode(session, exchange),
        'source': exchange.source,
        'target': exchange.target,
        'owner': db_exchange_owner_side(exchange),
        'channel': exchange.channel,
        'questionnaire': exchange.questionnaire,
        'request_questionnaire': exchange.request_questionnaire,
        # The channel is configured where it lives and is named here by the
        # name it carries there
        'channel_name': ''
    }

    if channel is not None:
        ret['channel_name'] = models.get_localized_values({}, channel, ['name'],
                                                          language)['name']

    return ret


def db_validate_sides(session, request):
    """
    Resolve the objects an exchange relates, refusing an unsound pair

    :param session: An ORM session
    :param request: The request data
    :return: The tenant IDs of the two sides of the exchange
    """
    source_tid = db_get_tid_by_uuid(session, request['source'])
    target_tid = db_get_tid_by_uuid(session, request['target'])

    if source_tid is None or target_tid is None or source_tid == target_tid:
        raise errors.InputValidationError("Invalid exchange")

    return source_tid, target_tid


def db_declare_channel(session, target_tid, name, language):
    """
    Declare on the destination of an exchange the channel it runs through

    :param session: An ORM session
    :param target_tid: The tenant ID of the destination of the exchange
    :param name: The name the channel is known by
    :param language: The language the channel is named in
    :return: The declared channel
    """
    channel = models.Context()
    channel.tid = target_tid
    channel.exchange = True
    channel.name = {language: name}
    channel.allow_recipients_selection = False
    channel.select_all_receivers = False
    channel.maximum_selectable_receivers = 0

    session.add(channel)
    session.flush()

    # A channel declared on a profile is a template: every site inheriting
    # from the profile derives its own from it
    if target_tid >= DEFAULT_PROFILE_ID:
        db_sync_derived_contexts(session, channel)

    return channel


def db_validate_channel(session, exchange, request, target_tid, language):
    """
    Name on an exchange the channel of its destination it runs through

    :param session: An ORM session
    :param exchange: The exchange
    :param request: The request data
    :param target_tid: The tenant ID of the destination of the exchange
    :param language: The language the request is written in
    """
    value = request.get('channel', '')

    if value and session.query(models.Context) \
                        .filter(models.Context.tid == target_tid,
                                models.Context.id == value,
                                models.Context.exchange == True) \
                        .one_or_none() is None:
        value = ''

    name = request.get('channel_name', '').strip()
    if not value and name:
        value = db_declare_channel(session, target_tid, name, language).id

    if not value:
        raise errors.InputValidationError("Invalid exchange channel")

    exchange.channel = value


def db_drop_exchange_channel(session, channel_id):
    """
    Drop the channel an exchange ran through, where nothing is left of it

    :param session: An ORM session
    :param channel_id: The channel the dropped exchange ran through
    """
    channel = session.query(models.Context) \
                     .filter(models.Context.id == channel_id) \
                     .one_or_none()

    if channel is None or not channel.exchange:
        return

    if session.query(models.Exchange) \
              .filter(models.Exchange.channel == channel_id).count():
        return

    # A channel of a profile is a template: it is dropped along with the
    # channels the sites derived from it
    channels = [channel] + session.query(models.Context) \
                                  .filter(models.Context.template_id == channel.id) \
                                  .all()

    for entry in channels:
        if session.query(models.InternalTip) \
                  .filter(models.InternalTip.context_id == entry.id).count():
            return

    for entry in channels:
        session.delete(entry)


def db_validate_configuration(session, exchange, request, source_tid, target_tid, language):
    """
    Write on an exchange what the platform decides of it

    :param session: An ORM session
    :param exchange: The exchange
    :param request: The request data
    :param source_tid: The tenant ID of the origin of the exchange
    :param target_tid: The tenant ID of the destination of the exchange
    :param language: The language the request is written in
    """
    def designated(value, tid):
        if not value or session.query(models.Questionnaire) \
                               .filter(models.Questionnaire.tid.in_({1, tid}),
                                       models.Questionnaire.id == value) \
                               .one_or_none() is None:
            return ''

        return value

    # The questionnaire composes what the exchange creates in place of the one
    # of the channel: it is the only way of shaping what the sender keeps, and is
    # therefore a questionnaire of the site the reports live on
    owner_tid = source_tid \
        if db_exchange_owner_side(exchange) == EnumExchangeOwner.source.name \
        else target_tid
    exchange.questionnaire = designated(request.get('questionnaire', ''), owner_tid)

    # The request is filed on the destination and is composed with a
    # questionnaire of it; a transmission is never demanded, being asked of a
    # report that already exists
    exchange.request_questionnaire = '' \
        if exchange.type == EnumExchangeType.communication.name else \
        designated(request.get('request_questionnaire', ''), target_tid)


@transact
def get_exchanges(session, language='en'):
    return [serialize_exchange(session, exchange, language)
            for exchange in session.query(models.Exchange)]


@transact
def create(session, request, language='en'):
    """
    Establish an exchange between two objects of the platform
    """
    if request['type'] not in EnumExchangeType.keys():
        raise errors.InputValidationError("Invalid exchange type")

    source_tid, target_tid = db_validate_sides(session, request)

    exchange = models.Exchange()
    exchange.type = request['type']
    exchange.source = request['source']
    exchange.target = request['target']

    db_validate_channel(session, exchange, request, target_tid, language)
    db_validate_configuration(session, exchange, request, source_tid, target_tid, language)

    # An exchange whose reports live on the destination starts out composing
    # them the way its channel composes what is filed on it: the configuration
    # then varies the one without touching the other
    if not exchange.questionnaire and \
            db_exchange_owner_side(exchange) == EnumExchangeOwner.target.name:
        channel = db_get_exchange_channel(session, exchange, target_tid)
        if channel is not None:
            exchange.questionnaire = channel.questionnaire_id

    session.add(exchange)
    session.flush()

    return serialize_exchange(session, exchange, language)


@transact
def update(session, exchange_id, request, language='en'):
    """
    Update what the platform decides of an exchange
    """
    exchange = db_get(session, models.Exchange,
                      models.Exchange.id == exchange_id)

    source_tid = db_get_tid_by_uuid(session, exchange.source)
    target_tid = db_get_tid_by_uuid(session, exchange.target)
    if source_tid is None or target_tid is None:
        raise errors.InputValidationError("Invalid exchange")

    db_validate_configuration(session, exchange, request, source_tid, target_tid, language)

    return serialize_exchange(session, exchange, language)


@transact
def delete(session, exchange_id):
    """
    Drop an exchange
    """
    exchange = db_get(session, models.Exchange,
                      models.Exchange.id == exchange_id)

    channel_id = exchange.channel

    session.delete(exchange)
    session.flush()

    db_drop_exchange_channel(session, channel_id)


class ExchangeCollection(BaseHandler):
    """
    Handler listing and establishing the exchanges between the sites
    """
    check_roles = 'admin'
    require_permission = 'can_manage_sites'
    root_tenant_only = True
    invalidate_cache = True

    def get(self):
        return get_exchanges(self.request.language)

    def post(self):
        request = self.validate_request(self.request.content.read(),
                                        requests.AdminExchangeDesc)

        return create(request, self.request.language)


class ExchangeInstance(BaseHandler):
    """
    Handler configuring and dropping an exchange between two sites
    """
    check_roles = 'admin'
    require_permission = 'can_manage_sites'
    root_tenant_only = True
    invalidate_cache = True

    def put(self, exchange_id):
        request = self.validate_request(self.request.content.read(),
                                        requests.AdminExchangeConfigDesc)

        return update(exchange_id, request, self.request.language)

    def delete(self, exchange_id):
        return delete(exchange_id)
