from globaleaks.handlers import l10n
from globaleaks.handlers.admin import l10n as admin_l10n
from globaleaks.tests import helpers
from twisted.internet.defer import inlineCallbacks

custom_texts = {
    '12345': '54321'
}


class TestL10NHandler(helpers.TestHandler):
    _handler = l10n.L10NHandler

    @inlineCallbacks
    def test_get(self):
        handler = self.request()
        response = yield handler.get('unexistent')
        self.assertEqual(response, {})

        handler = self.request()
        response = yield handler.get(lang='en')
        self.assertNotIn('12345', response)

        self._handler = admin_l10n.AdminL10NHandler
        handler = self.request(custom_texts, role='admin')
        yield handler.put(lang='en')

        self._handler = l10n.L10NHandler
        handler = self.request()
        response = yield handler.get(lang='en')
        self.assertIn('12345', response)
        self.assertEqual('54321', response['12345'])
