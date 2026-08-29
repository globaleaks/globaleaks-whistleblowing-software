from twisted.internet.defer import inlineCallbacks

from globaleaks.handlers.admin import file
from globaleaks.rest import errors
from globaleaks.tests import helpers

files = [
    {'handler': 'css', 'name': 'file.css'},
    {'handler': 'script', 'name': 'file.js'},
    {'handler': 'logo', 'name': 'file.png'},
    {'handler': 'favicon', 'name': 'file.ico'},
    {'handler': 'custom', 'name': 'file.txt'},
]

permissions = {'can_upload_files': True}


class TestFileInstance(helpers.TestHandler):
    _handler = file.FileInstance

    @inlineCallbacks
    def test_post_prevent_unauthorized_admin_uploads(self):
        for f in files:
            handler = self.request({}, role='admin', attachment=self.get_dummy_attachment(f['name']))
            if f['handler'] == 'logo':
                yield handler.post(f['handler'])
            else:
                yield self.assertFailure(handler.post(f['handler']), errors.InvalidAuthentication)

    @inlineCallbacks
    def test_post_prevent_wrong_filetypes(self):
        for f in files:
            handler = self.request({}, role='admin', permissions=permissions, attachment=self.get_dummy_attachment(f['name'] + ".wrong.ext"))
            yield self.assertFailure(handler.post(f['handler']), errors.InputValidationError)

    @inlineCallbacks
    def test_post_accepts_correct_files(self):
        for f in files:
            handler = self.request({}, role='admin', permissions=permissions, attachment=self.get_dummy_attachment(f['name']))
            yield handler.post(f['handler'])

    @inlineCallbacks
    def test_post_prevent_unauthorized_recipients_to_upload_any_file(self):
        for f in files:
            handler = self.request({}, role='receiver', attachment=self.get_dummy_attachment(f['name']))
            yield self.assertFailure(handler.post(f['handler']), errors.InvalidAuthentication)

    @inlineCallbacks
    def test_post_enable_authorized_recipients_to_upload_the_logo_and_only_it(self):
        for f in files:
            handler = self.request({}, role='receiver', permissions={'can_manage_settings': True}, attachment=self.get_dummy_attachment(f['name']))
            if f['handler'] == 'logo':
                yield handler.post(f['handler'])
            else:
                yield self.assertFailure(handler.post(f['handler']), errors.InvalidAuthentication)

    @inlineCallbacks
    def test_post_duplicated(self):
        handler = self.request({}, role='admin', permissions=permissions, attachment=self.get_dummy_attachment(files[0]['name']))
        yield handler.post(files[0]['handler'])
        yield handler.post(files[0]['handler'])


    @inlineCallbacks
    def test_delete(self):
        handler = self.request({}, role='admin', permissions=permissions, attachment=self.get_dummy_attachment(files[0]['name']))
        file_id = yield handler.post(files[0]['handler'])
        yield handler.delete(file_id)


class TestFileCollection(helpers.TestHandler):
    _handler = file.FileCollection

    @inlineCallbacks
    def test_get(self):
        self._handler = file.FileInstance

        for f in files:
            handler = self.request({}, role='admin', permissions=permissions, attachment=self.get_dummy_attachment(f['name']))
            yield handler.post(f['handler'])

        self._handler = file.FileCollection
        handler = self.request(role='admin', permissions=permissions)
        response = yield handler.get()

        self.assertEqual(len(response), 5)
