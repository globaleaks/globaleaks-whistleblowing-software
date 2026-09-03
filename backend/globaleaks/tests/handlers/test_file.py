from twisted.internet.defer import inlineCallbacks

from globaleaks.handlers import file
from globaleaks.handlers.admin import file as admin_file
from globaleaks.rest.errors import ResourceNotFound
from globaleaks.tests import helpers


class TestFileInstance(helpers.TestHandler):
    _handler = file.FileHandler

    @inlineCallbacks
    def test_get(self):
        handler = self.request()
        yield self.assertFailure(handler.get('custom'), ResourceNotFound)

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
