from twisted.internet.defer import inlineCallbacks
from twisted.trial import unittest

from globaleaks import to_bcp47
from globaleaks.handlers.staticfile import StaticFileHandler
from globaleaks.rest import errors
from globaleaks.tests import helpers


class TestToBcp47(unittest.TestCase):
    def test_plain_language_is_unchanged(self):
        self.assertEqual(to_bcp47('en'), 'en')
        self.assertEqual(to_bcp47('it'), 'it')

    def test_region_underscore_becomes_hyphen(self):
        self.assertEqual(to_bcp47('pt_BR'), 'pt-BR')
        self.assertEqual(to_bcp47('zh_TW'), 'zh-TW')
        self.assertEqual(to_bcp47('nb_NO'), 'nb-NO')
        self.assertEqual(to_bcp47('fa_AF'), 'fa-AF')

    def test_modifier_codes_map_to_bcp47_subtags(self):
        self.assertEqual(to_bcp47('ca@valencia'), 'ca-valencia')
        self.assertEqual(to_bcp47('sr_ME@latin'), 'sr-Latn-ME')
        self.assertEqual(to_bcp47('sr_RS@latin'), 'sr-Latn-RS')
        self.assertEqual(to_bcp47('ug@Latin'), 'ug-Latn')
        self.assertEqual(to_bcp47('ug@Cyrl'), 'ug-Cyrl')

    def test_result_never_contains_posix_separators(self):
        from globaleaks import LANGUAGES_SUPPORTED_CODES
        for code in LANGUAGES_SUPPORTED_CODES:
            tag = to_bcp47(code)
            self.assertNotIn('_', tag)
            self.assertNotIn('@', tag)


class TestStaticFileHandler(helpers.TestHandler):
    _handler = StaticFileHandler

    @inlineCallbacks
    def test_get_existent(self):
        handler = self.request()

        # Mock the nonce used for this request
        handler.request.nonce = b'secureNonce123'

        # Call the handler: the empty filename maps to the '/' entry point,
        # which serves index.html with the per-request substitutions applied.
        yield handler.get('')

        # Get response body and decode
        body = handler.request.getResponseBody().decode()

        # Ensure it's HTML and the nonce was injected
        self.assertIn('nonce="secureNonce123"', body)

    @inlineCallbacks
    def test_get_index_ltr_language(self):
        handler = self.request()
        handler.request.language = 'en'

        yield handler.get('')

        body = handler.request.getResponseBody().decode()

        self.assertIn('lang="en"', body)
        self.assertIn('dir="ltr"', body)

    @inlineCallbacks
    def test_get_index_rtl_language(self):
        handler = self.request()
        handler.request.language = 'ar'

        yield handler.get('')

        body = handler.request.getResponseBody().decode()

        self.assertIn('lang="ar"', body)
        self.assertIn('dir="rtl"', body)

    @inlineCallbacks
    def test_get_index_regional_language_is_emitted_as_bcp47(self):
        handler = self.request()
        handler.request.language = 'pt_BR'

        yield handler.get('')

        body = handler.request.getResponseBody().decode()

        # The internal POSIX code 'pt_BR' must be emitted as the BCP 47 tag
        # 'pt-BR' so that the HTML lang attribute is valid.
        self.assertIn('lang="pt-BR"', body)
        self.assertNotIn('lang="pt_BR"', body)

    def test_get_unexistent(self):
        handler = self.request()
        return self.assertRaises(errors.ResourceNotFound, handler.get, 'unexistent')
