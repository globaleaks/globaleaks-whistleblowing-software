from globaleaks.handlers.admin import l10n as admin_l10n
from globaleaks.tests import helpers
from twisted.internet.defer import inlineCallbacks

empty_texts = {}


custom_texts1 = {
    '12345': '54321'
}


custom_texts2 = {
    '12345': '54321'
}


class TestAdminL10NHandler(helpers.TestHandler):
    _handler = admin_l10n.AdminL10NHandler

    @inlineCallbacks
    def test_get(self):
        handler = self.request(role='admin')

        response = yield handler.get(lang='en')

        self.assertEqual(response, {})

    @inlineCallbacks
    def test_put(self):
        check = yield admin_l10n.get(1, 'en')
        self.assertEqual(empty_texts, check)

        handler = self.request(custom_texts1, role='admin')
        yield handler.put(lang='en')
        check = yield admin_l10n.get(1, 'en')
        self.assertEqual(custom_texts1, check)

        handler = self.request(custom_texts1, role='admin')
        yield handler.put(lang='en')
        check = yield admin_l10n.get(1, 'en')
        self.assertEqual(custom_texts2, check)

    @inlineCallbacks
    def test_delete(self):
        yield self.test_put()

        check = yield admin_l10n.get(1, 'en')
        self.assertEqual(custom_texts1, check)

        handler = self.request({}, role='admin')
        handler.delete(lang='en')

        check = yield admin_l10n.get(1, 'en')
        self.assertEqual(empty_texts, check)
