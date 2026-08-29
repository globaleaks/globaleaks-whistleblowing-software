# Queries over the exchanges established between the sites of a platform
from sqlalchemy import or_

from globaleaks.models import Context, Exchange
from globaleaks.models.config import ConfigFactory, DEFAULT_PROFILE_ID, db_get_pid


def db_get_tenant_uuid(session, tid):
    """
    Return the UUID a tenant is designated by in the exchanges

    :param session: An ORM session
    :param tid: The tenant ID
    :return: The UUID of the tenant
    """
    return ConfigFactory(session, tid).get_val('uuid')


def db_get_tenant_identities(session, tid):
    """
    Return the UUIDs a tenant is named by in the exchanges, by precedence

    :param session: An ORM session
    :param tid: The tenant ID
    :return: The UUIDs naming the tenant, the most specific one first
    """
    if tid >= DEFAULT_PROFILE_ID:
        return []

    identities = [db_get_tenant_uuid(session, tid)]

    pid = db_get_pid(session, tid)
    if pid is not None:
        identities.append(db_get_tenant_uuid(session, pid))

    return identities


def _side_rank(identities, side):
    """
    Return how specifically a side of an exchange names a tenant

    :param identities: The UUIDs naming the tenant, the most specific one first
    :param side: The UUID the exchange names on that side
    :return: The rank of the match, 0 when the side does not name the tenant
    """
    return len(identities) - identities.index(side) if side in identities else 0


def db_forget_exchanges(session, tids):
    """
    Drop the exchanges the objects about to depart were a side of

    :param session: An ORM session
    :param tids: The tenant IDs of the objects departing
    :return: The number of the exchanges dropped
    """
    identities = [identity for identity in
                  (db_get_tenant_uuid(session, tid) for tid in tids)
                  if identity]

    if not identities:
        return 0

    return session.query(Exchange) \
                  .filter(or_(Exchange.source.in_(identities),
                              Exchange.target.in_(identities))) \
                  .delete(synchronize_session=False)


def db_get_exchanges(session, type):
    """
    Return the exchanges of a type established on the platform

    :param session: An ORM session
    :param type: The type of the exchanges
    :return: The list of the exchanges
    """
    return session.query(Exchange).filter(Exchange.type == type).all()


def db_match_exchanges(session, type, source_tid, target_tid):
    """
    Return the exchanges of a type relating two tenants

    :param session: An ORM session
    :param type: The type of the exchanges
    :param source_tid: The tenant ID of the tenant that files
    :param target_tid: The tenant ID of the tenant that receives
    :return: The exchanges relating the two tenants, the most specific first
    """
    source_identities = db_get_tenant_identities(session, source_tid)
    target_identities = db_get_tenant_identities(session, target_tid)

    matched = []
    for exchange in db_get_exchanges(session, type):
        rank = _side_rank(source_identities, exchange.source) * \
               _side_rank(target_identities, exchange.target)

        if rank:
            matched.append((rank, exchange))

    return [exchange for _, exchange in sorted(matched, key=lambda entry: -entry[0])]


def db_match_exchange(session, type, source_tid, target_tid, exchange_id=None):
    """
    Return the exchange of a type a report between two tenants runs under

    :param session: An ORM session
    :param type: The type of the exchange
    :param source_tid: The tenant ID of the tenant that files
    :param target_tid: The tenant ID of the tenant that receives
    :param exchange_id: The exchange chosen by the sender, if any
    :return: The exchange relating the two tenants or None
    """
    matched = db_match_exchanges(session, type, source_tid, target_tid)

    if exchange_id:
        matched = [exchange for exchange in matched if exchange.id == exchange_id]

    return matched[0] if matched else None


def db_exchange_incoming_enabled(session, type, tid):
    """
    Check whether any exchange of a type lets a tenant receive from another

    :param session: An ORM session
    :param type: The type of the exchanges
    :param tid: The tenant ID
    :return: True when the tenant is the destination of at least one exchange
    """
    identities = db_get_tenant_identities(session, tid)

    return any(exchange.target in identities
               for exchange in db_get_exchanges(session, type))


def db_exchange_outgoing_enabled(session, type, tid):
    """
    Check whether any exchange of a type lets a tenant file towards another

    :param session: An ORM session
    :param type: The type of the exchanges
    :param tid: The tenant ID
    :return: True when the tenant is the source of at least one exchange
    """
    identities = db_get_tenant_identities(session, tid)

    return any(exchange.source in identities
               for exchange in db_get_exchanges(session, type))


def db_exchange_owner_side(exchange):
    """
    Return the side of an exchange the report it creates belongs to

    :param exchange: The exchange
    :return: Either 'source' or 'target'
    """
    if exchange.type == 'communication':
        return 'source'

    return 'target'


def db_get_exchange_owner_tid(session, exchange, source_tid, target_tid):
    """
    Return the tenant the report an exchange creates belongs to

    :param session: An ORM session
    :param exchange: The exchange
    :param source_tid: The tenant ID of the tenant that files
    :param target_tid: The tenant ID of the tenant that receives
    :return: The tenant ID of the owner of the report
    """
    return source_tid if db_exchange_owner_side(exchange) == 'source' else target_tid


def db_resolve_channel(session, tid, channel_id):
    """
    Return the channel of a site an exchange runs through, following the derivation

    :param session: An ORM session
    :param tid: The tenant ID of the site
    :param channel_id: The channel named by the exchange
    :return: The channel of the site or None
    """
    if not channel_id:
        return None

    channel = session.query(Context) \
                     .filter(Context.tid == tid,
                             Context.id == channel_id) \
                     .one_or_none()

    if channel is None:
        channel = session.query(Context) \
                         .filter(Context.tid == tid,
                                 Context.template_id == channel_id) \
                         .first()

    return channel


def db_get_exchange_channel(session, exchange, tid):
    """
    Return the channel an exchange runs through on a site

    :param session: An ORM session
    :param exchange: The exchange
    :param tid: The tenant ID of the site the channel is looked for on
    :return: The channel of the exchange on the site or None
    """
    if exchange is None:
        return None

    return db_resolve_channel(session, tid, exchange.channel)


def db_is_exchange_channel(session, context):
    """
    Check whether a channel receives what the other sites file on this one

    :param session: An ORM session
    :param context: The channel
    :return: True when the channel receives what the other sites file
    """
    return context.exchange


def db_exchange_types_of_channel(session, context):
    """
    Return the kinds of exchange running through a channel

    :param session: An ORM session
    :param context: The channel
    :return: The kinds of the exchanges running through it, in order
    """
    named = [context.id]
    if context.template_id:
        named.append(context.template_id)

    return sorted({entry[0] for entry in
                   session.query(Exchange.type)
                          .filter(Exchange.channel.in_(named))})


def db_channel_of_an_exchange(session, context):
    """
    Check whether an exchange runs through a channel

    :param session: An ORM session
    :param context: The channel
    :return: True when an exchange of the platform runs through the channel
    """
    return len(db_exchange_types_of_channel(session, context)) > 0


def db_get_exchange_channel_ids(session, tid):
    """
    Return the ids of the channels of a site the exchanges run through

    :param session: An ORM session
    :param tid: The tenant ID
    :return: A set of context IDs
    """
    identities = db_get_tenant_identities(session, tid)

    channels = set()
    for type in ['transmission', 'communication']:
        for exchange in db_get_exchanges(session, type):
            if exchange.target not in identities:
                continue

            channel = db_resolve_channel(session, tid, exchange.channel)
            if channel is not None:
                channels.add(channel.id)

    return channels
