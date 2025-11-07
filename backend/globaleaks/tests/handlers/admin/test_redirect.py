from twisted.internet.defer import inlineCallbacks

from globaleaks.handlers.admin.redirect import RedirectCollection, RedirectInstance
from globaleaks.tests import helpers

class TestRedirectCollection(helpers.TestHandlerWithPopulatedDB):
    _handler = RedirectCollection

    @inlineCallbacks
    def test_get(self):
        n = 3

        for i in range(n):
            yield self._create_redirect()

        handler = self.request(role='admin')
        response = yield handler.get()

        self.assertEqual(len(response), n)

    @inlineCallbacks
    def test_post(self):
        handler = self.request(self.get_dummy_redirect(), role='admin')
        redirect = yield handler.post()

        self.assertEqual(redirect['path1'], '/old')
        self.assertEqual(redirect['path2'], '/new')

    @inlineCallbacks
    def _create_redirect(self):
        handler = self.request(self.get_dummy_redirect(), role='admin')
        return (yield handler.post())


class TestRedirectInstance(helpers.TestHandlerWithPopulatedDB):
    _handler = RedirectInstance

    @inlineCallbacks
    def setUp(self):
        yield helpers.TestHandlerWithPopulatedDB.setUp(self)
        self._handler = RedirectCollection
        self.redirect = yield TestRedirectCollection._create_redirect(self)
        self._handler = RedirectInstance
        self.handler = self.request(self.redirect, role='admin')

    def test_delete(self):
        return self.handler.delete(self.redirect['id'])
