import copy

from twisted.internet.defer import inlineCallbacks

from globaleaks.handlers.admin import network
from globaleaks.tests import helpers


class TestNetworkInstance(helpers.TestHandlerWithPopulatedDB):
    _handler = network.NetworkInstance


    @inlineCallbacks
    def test_get(self):
        handler = self.request(role='admin')
        response = yield handler.get()

        self.assertTrue(isinstance(response, dict))
        self.assertEqual(response['reachable_via_web'], True)
        self.assertEqual(response['anonymize_outgoing_connections'], False)

    @inlineCallbacks
    def test_put(self):
        config = copy.deepcopy(self.dummy_network)
        config['ip_filter_custodian_enable'] = True
        config['ip_filter_custodian'] = '10.0.0.0/24'
        config['anonymize_outgoing_connection'] = True

        handler = self.request(config, role='admin')
        response = yield handler.put()

        self.assertTrue(isinstance(response, dict))
        self.assertEqual(response['reachable_via_web'], True)
        self.assertEqual(response['anonymize_outgoing_connections'], True)
