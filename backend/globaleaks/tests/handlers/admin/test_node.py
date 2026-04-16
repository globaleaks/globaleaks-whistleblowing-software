from twisted.internet.defer import inlineCallbacks

from globaleaks import __version__
from globaleaks.handlers.admin import node
from globaleaks.rest.errors import InputValidationError
from globaleaks.tests import helpers


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
        self.dummyNode['comment_period_after_closure_days'] = 21

        handler = self.request(self.dummyNode, role='admin')
        response = yield handler.put()
        self.assertTrue(isinstance(response, dict))
        self.assertTrue(response['version'], __version__)
        self.assertEqual(response['custom_support_url'], 'https://www.globaleaks.org')
        self.assertEqual(response['comment_period_after_closure_days'], 21)

    @inlineCallbacks
    def test_get_includes_comment_period_after_closure_days(self):
        handler = self.request(role='admin')
        response = yield handler.get()

        self.assertEqual(response['comment_period_after_closure_days'], 14)

    @inlineCallbacks
    def test_put_update_node_invalid_lang(self):
        self.dummyNode['languages_enabled'] = ["en", "shit"]
        handler = self.request(self.dummyNode, role='admin')

        yield self.assertFailure(handler.put(), InputValidationError)

    @inlineCallbacks
    def test_put_update_node_languages(self):
        # this tests start setting en as the only enabled language and
        # ends keeping enabled only french.
        self.dummyNode['languages_enabled'] = ["en"]
        self.dummyNode['default_language'] = "en"
        handler = self.request(self.dummyNode, role='admin')
        yield handler.put()

        self.dummyNode['languages_enabled'] = ["fr"]
        self.dummyNode['default_language'] = "fr"
        handler = self.request(self.dummyNode, role='admin')
        yield handler.put()

    @inlineCallbacks
    def test_update_ignored_fields(self):
        self.dummyNode['version'] = 'xxx'

        handler = self.request(self.dummyNode, role='admin')

        resp = yield handler.put()

        self.assertNotEqual('version', resp['version'])
