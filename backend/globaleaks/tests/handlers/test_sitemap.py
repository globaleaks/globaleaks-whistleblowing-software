import xml.etree.ElementTree as ET

from twisted.internet.defer import inlineCallbacks

from globaleaks.handlers import sitemap
from globaleaks.rest import errors
from globaleaks.state import State
from globaleaks.tests import helpers


class TestSitemapHandlerHandler(helpers.TestHandler):
    _handler = sitemap.SitemapHandler

    def test_get_with_indexing_disabled(self):
        handler = self.request()

        State.tenants[1].cache.allow_indexing = False

        return self.assertRaises(errors.ResourceNotFound, handler.get)

    @inlineCallbacks
    def test_get_with_indexing_enabled(self):
        handler = self.request()

        State.tenants[1].cache.allow_indexing = True
        State.tenants[1].cache.hostname = 'www.globaleaks.org'
        State.tenants[1].cache.languages_enabled = ['en', 'ar', 'it']
        State.tenants[1].cache.default_language = 'en'

        data = yield handler.get()

        self.assertEqual(handler.request.code, 200)

        # Validate that the generated XML is well-formatted
        ET.fromstring(data)  # noqa: S314 - parsing the server's own generated sitemap (trusted data) in a test

        # Check that the XML declaration is correct
        self.assertTrue(data.startswith("<?xml version='1.0' encoding='UTF-8' ?>"))

        # Check that the root <urlset> element is correctly formatted with namespaces
        self.assertIn("<urlset xmlns='http://www.sitemaps.org/schemas/sitemap/0.9'", data)
        self.assertIn("xmlns:xhtml='http://www.w3.org/1999/xhtml'", data)

        # Check that the <url> element contains the expected <loc>, <changefreq>, and <priority>
        self.assertIn("<url>", data)
        self.assertIn("<loc>https://www.globaleaks.org/#/</loc>", data)
        self.assertIn("<changefreq>weekly</changefreq>", data)
        self.assertIn("<priority>1.00</priority>", data)

        # Check that the alternate language links are present except for the default lang
        self.assertIn("<xhtml:link rel='alternate' hreflang='ar' href='https://www.globaleaks.org/#/?lang=ar' />", data)
        self.assertIn("<xhtml:link rel='alternate' hreflang='it' href='https://www.globaleaks.org/#/?lang=it' />", data)
        self.assertNotIn("<xhtml:link rel='alternate' hreflang='en' href='https://www.globaleaks.org/#/?lang=en' />", data)

        # Ensure the closing </urlset> is present
        self.assertIn("</urlset>", data)
