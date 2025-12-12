from twisted.internet.defer import inlineCallbacks

from globaleaks import __version__
from globaleaks.handlers.admin import node
from globaleaks.rest.errors import InputValidationError
from globaleaks.tests import helpers
from globaleaks.models import config
from globaleaks.orm import tw

class TestNodeInstance(helpers.TestHandlerWithPopulatedDB):
    _handler = node.NodeInstance

    @inlineCallbacks
    def test_get(self):
        handler = self.request(role='admin')
        response = yield handler.get()

        self.assertTrue(response['version'], __version__)

    @inlineCallbacks
    def test_put_update_node(self):
        self.dummyNode['custom_support_url'] = 'https://www.globaleaks.org'
        self.dummyNode['etag'] = yield tw(config.db_get_config_variable, 1, 'etag')

        handler = self.request(self.dummyNode, role='admin')
        response = yield handler.put()
        self.assertTrue(isinstance(response, dict))
        self.assertTrue(response['version'], __version__)
        self.assertEqual(response['custom_support_url'], 'https://www.globaleaks.org')

    @inlineCallbacks
    def test_put_update_node_invalid_lang(self):
        self.dummyNode['languages_enabled'] = ["en", "shit"]
        self.dummyNode['etag'] = yield tw(config.db_get_config_variable, 1, 'etag')

        handler = self.request(self.dummyNode, role='admin')

        yield self.assertFailure(handler.put(), InputValidationError)

    @inlineCallbacks
    def test_put_update_node_languages(self):
        # this tests start setting en as the only enabled language and
        # ends keeping enabled only french.
        self.dummyNode['languages_enabled'] = ["en"]
        self.dummyNode['default_language'] = "en"
        self.dummyNode['etag'] = yield tw(config.db_get_config_variable, 1, 'etag')

        handler = self.request(self.dummyNode, role='admin')
        yield handler.put()

        self.dummyNode['languages_enabled'] = ["fr"]
        self.dummyNode['default_language'] = "fr"
        self.dummyNode['etag'] = yield tw(config.db_get_config_variable, 1, 'etag')
        handler = self.request(self.dummyNode, role='admin')
        yield handler.put()

    @inlineCallbacks
    def test_update_ignored_fields(self):
        self.dummyNode['version'] = 'xxx'
        self.dummyNode['etag'] = yield tw(config.db_get_config_variable, 1, 'etag')

        handler = self.request(self.dummyNode, role='admin')

        resp = yield handler.put()

        self.assertNotEqual('version', resp['version'])

    @inlineCallbacks
    def test_put_update_node_concurrent_update(self):
        self.dummyNode['etag'] = yield tw(config.db_get_config_variable, 1, 'etag')

        old_payload = self.dummyNode

        self.dummyNode['custom_support_url'] = 'https://updated-by-tab2.org'
        new_payload = self.dummyNode

        new_handler = self.request(new_payload, role='admin')
        yield new_handler.put()

        old_handler = self.request(old_payload, role='admin')

        failure = yield self.assertFailure(old_handler.put(), Exception)

        self.assertEqual(failure.reason, "CONCURRENT_UPDATE")
