from twisted.internet.defer import inlineCallbacks

from globaleaks.handlers.base import BaseHandler
from globaleaks.models.config import ConfigFactory
from globaleaks.orm import db_log, tw
from globaleaks.rest import requests
from globaleaks.utils.ip import parse_csv_ip_ranges_to_ip_networks
from globaleaks.utils.onion import generate_onion_service_v3


def db_admin_serialize_network(session, tid):
    """
    Transaction for fetching the network configuration as admin

    :param session: An ORM session
    :param tid: A tenant ID
    :return: Return the serialized configuration for the specified tenant
    """
    node = ConfigFactory(session, tid)
    ret = node.serialize('admin_network')

    # A site holding no key publishes no onion service of its own, whatever the variable says
    ret['onionservice_enable'] = ret['onionservice_enable'] and bool(node.get_val('tor_onion_key'))

    return ret


def db_update_network(session, tid, user_session, request):
    """
    Transaction to update the node configuration

    :param session: An ORM session
    :param tid: A tenant ID
    :param user_session: The current user session
    :param request: The request data
    :return: Return the serialized configuration for the specified tenant
    """
    # Validate the IP addresses/ranges
    for k in ['admin', 'analyst', 'auditor', 'custodian', 'receiver']:
        if 'ip_filter_' + k in request and request['ip_filter_' + k + '_enable'] and request['ip_filter_' + k]:
            parse_csv_ip_ranges_to_ip_networks(request['ip_filter_' + k])

    node = ConfigFactory(session, tid)
    node.update('admin_network', request)

    # A site enabled the first time is given the key of its onion service then
    if node.get_val('onionservice_enable') and not node.get_val('tor_onion_key'):
        onionservice, key = generate_onion_service_v3()
        node.set_val('onionservice', onionservice)
        node.set_val('tor_onion_key', key)

    db_log(session, tid=tid, type='update_network', user_id=user_session.user_id)

    return db_admin_serialize_network(session, tid)


class NetworkInstance(BaseHandler):
    check_roles = 'admin'
    require_permission = 'can_manage_network'
    root_tenant_or_management_only = True
    invalidate_cache = True

    def get(self):
        """
        Get the network infos.
        """
        return tw(db_admin_serialize_network,
                  self.request.tid)

    @inlineCallbacks
    def put(self):
        """
        Update the network infos.
        """
        request = yield self.validate_request(self.request.content.read(),
                                              requests.AdminNetworkDesc)

        ret = yield tw(db_update_network,
                           self.request.tid,
                           self.session,
                           request)

        return ret
