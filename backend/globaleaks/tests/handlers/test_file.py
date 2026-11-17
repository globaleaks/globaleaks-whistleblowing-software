import os

from twisted.internet.defer import inlineCallbacks

from globaleaks.handlers import file
from globaleaks.handlers.admin import file as admin_file
from globaleaks.rest.errors import ResourceNotFound
from globaleaks.state import State
from globaleaks.tests import helpers


class TestFileInstance(helpers.TestHandler):
    _handler = file.FileHandler

    @inlineCallbacks
    def test_get(self):
        handler = self.request()
        yield self.assertFailure(handler.get(u'custom'), ResourceNotFound)

        self._handler = admin_file.FileInstance
        handler = self.request({}, role='admin', permissions={'can_upload_files': True})
        yield handler.post('custom')

        self._handler = admin_file.FileCollection
        handler = self.request(role='admin')
        x = yield handler.get()

        self._handler = file.FileHandler
        handler = self.request()
        x = yield handler.get(x[0]['name'])

        self.assertIsNone(x)

    def served_path(self, handler):
        """
        Record the path of the file a handler serves
        """
        served = []
        handler.write_file = lambda filename, path: served.append(path)
        return served

    @inlineCallbacks
    def test_the_logo_of_the_dark_theme_is_the_globaleaks_logo_in_negative(self):
        handler = self.request()
        served = self.served_path(handler)
        yield handler.get('logo-dark')

        self.assertTrue(served[0].endswith(os.path.join('images', 'logo-white.webp')))

    @inlineCallbacks
    def test_a_site_with_a_logo_of_its_own_shows_it_in_the_dark_theme(self):
        self._handler = admin_file.FileInstance
        handler = self.request({}, role='admin', permissions={'can_upload_files': True}, attachment=self.get_dummy_attachment('file.png'))
        yield handler.post('logo')

        self._handler = file.FileHandler
        handler = self.request()
        served = self.served_path(handler)
        yield handler.get('logo-dark')

        self.assertTrue(served[0].startswith(os.path.abspath(State.settings.files_path)))

    @inlineCallbacks
    def test_a_site_with_a_logo_for_the_dark_theme_shows_that_one_in_it(self):
        self._handler = admin_file.FileInstance
        handler = self.request({}, role='admin', permissions={'can_upload_files': True}, attachment=self.get_dummy_attachment('file.png'))
        yield handler.post('logo')
        handler = self.request({}, role='admin', permissions={'can_upload_files': True}, attachment=self.get_dummy_attachment('file.png'))
        logo_dark_id = yield handler.post('logo-dark')

        self._handler = file.FileHandler
        handler = self.request()
        served = self.served_path(handler)
        yield handler.get('logo-dark')

        self.assertEqual(served[0], os.path.abspath(os.path.join(State.settings.files_path, logo_dark_id)))
