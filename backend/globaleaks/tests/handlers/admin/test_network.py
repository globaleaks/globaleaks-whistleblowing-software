import copy

from twisted.internet.defer import inlineCallbacks

from globaleaks.handlers.admin import network
from globaleaks.models.config import ConfigFactory
from globaleaks.orm import tw
from globaleaks.tests import helpers


class TestNetworkInstance(helpers.TestHandlerWithPopulatedDB):
    _handler = network.NetworkInstance


    @inlineCallbacks
    def test_get(self):
        handler = self.request(role='admin')
        response = yield handler.get()

        self.assertTrue(isinstance(response, dict))
        self.assertEqual(response['onionservice_enable'], True)
        self.assertEqual(response['reachable_via_web'], True)
        self.assertEqual(response['anonymize_outgoing_connections'], False)

    @inlineCallbacks
    def test_put(self):
        config = copy.deepcopy(self.dummyNetwork)
        config['ip_filter_custodian_enable'] = True
        config['ip_filter_custodian'] = '10.0.0.0/24'
        config['anonymize_outgoing_connection'] = True

        handler = self.request(config, role='admin')
        response = yield handler.put()

        self.assertTrue(isinstance(response, dict))
        self.assertEqual(response['reachable_via_web'], True)
        self.assertEqual(response['anonymize_outgoing_connections'], True)

    @inlineCallbacks
    def test_toggle_onion_service(self):
        handler = self.request(role='admin')
        original = yield handler.get()

        for enabled in [False, True]:
            config = copy.deepcopy(self.dummyNetwork)
            config['onionservice_enable'] = enabled
            handler = self.request(config, role='admin')
            response = yield handler.put()
            self.assertEqual(response['onionservice_enable'], enabled)
            self.assertEqual(response['onionservice'], original['onionservice'])

            response = yield self.request(role='admin').get()
            self.assertEqual(response['onionservice_enable'], enabled)

    @inlineCallbacks
    def test_toggle_is_tenant_scoped(self):
        config = copy.deepcopy(self.dummyNetwork)
        config['onionservice_enable'] = False
        handler = self.request(config, tid=2, role='admin')
        response = yield handler.put()
        self.assertFalse(response['onionservice_enable'])
        root = yield self.request(role='admin').get()
        self.assertTrue(root['onionservice_enable'])

    @inlineCallbacks
    def test_enabling_a_site_without_key_gives_it_one(self):
        def drop_key(session):
            node = ConfigFactory(session, 1)
            node.set_val('onionservice', '')
            node.set_val('tor_onion_key', '')

        yield tw(drop_key)

        response = yield self.request(role='admin').get()
        self.assertFalse(response['onionservice_enable'])
        self.assertEqual(response['onionservice'], '')

        config = copy.deepcopy(self.dummyNetwork)
        config['onionservice_enable'] = True
        response = yield self.request(config, role='admin').put()
        self.assertTrue(response['onionservice_enable'])
        self.assertTrue(response['onionservice'].endswith('.onion'))
