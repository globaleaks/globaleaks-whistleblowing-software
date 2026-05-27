from twisted.internet.defer import inlineCallbacks, returnValue

from globaleaks.handlers.base import BaseHandler
from globaleaks.models.config import ConfigFactory
from globaleaks.orm import db_log, tw
from globaleaks.rest import requests
from globaleaks.utils.ip import parse_csv_ip_ranges_to_ip_networks


def db_admin_serialize_network(session, tid):
    """
    Transaction for fetching the network configuration as admin

    :param session: An ORM session
    :param tid: A tenant ID
    :return: Return the serialized configuration for the specified tenant
    """
    return ConfigFactory(session, tid).serialize('admin_network')


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
    for k in ['admin', 'analyst', 'custodian', 'receiver']:
        if 'ip_filter_' + k in request and request['ip_filter_' + k + '_enable'] and request['ip_filter_' + k]:
            parse_csv_ip_ranges_to_ip_networks(request['ip_filter_' + k])

    ConfigFactory(session, tid).update('admin_network', request)

    db_log(session, tid=tid, type='update_network', user_id=user_session.user_id)

    return db_admin_serialize_network(session, tid)


class NetworkInstance(BaseHandler):
    check_roles = 'admin'
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

        returnValue(ret)
