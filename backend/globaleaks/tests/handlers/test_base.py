import json

from globaleaks.handlers.base import BaseHandler, content_disposition_attachment
from globaleaks.rest.errors import FileTooBig, InputValidationError
from globaleaks.tests import helpers

class BaseHandlerMock(BaseHandler):
    check_roles = 'any'


class TestBaseHandler(helpers.TestHandlerWithPopulatedDB):
    _handler = BaseHandlerMock

    def _upload_args(self, total_size, chunk=b'x', identifier=b'testfile',
                     chunk_number=b'1', total_chunks=b'2'):
        return {
            b'flowFilename': [b'test.txt'],
            b'flowTotalSize': [str(total_size).encode()],
            b'flowIdentifier': [identifier],
            b'flowChunkNumber': [chunk_number],
            b'flowTotalChunks': [total_chunks],
            b'file': [chunk],
        }

    def test_process_file_upload_rejects_size_above_limit(self):
        # A file just under (max + 1) MiB previously slipped through because the
        # size was floor-divided to whole MiB before comparison; it must now be
        # rejected against the byte-exact limit.
        handler = self.request(handler_cls=BaseHandlerMock)
        self.state.tenants[1].cache.maximum_filesize = 1
        handler.request.args = self._upload_args(total_size=2 * 1024 * 1024 - 1,
                                                 identifier=b'oversized')
        self.assertRaises(FileTooBig, handler.process_file_upload)

    def test_process_file_upload_accepts_size_at_limit(self):
        # A file exactly at the configured limit must still be accepted.
        handler = self.request(handler_cls=BaseHandlerMock)
        self.state.tenants[1].cache.maximum_filesize = 1
        handler.request.args = self._upload_args(total_size=1024 * 1024,
                                                 identifier=b'atlimit')
        self.assertIsNone(handler.process_file_upload())

    def test_content_disposition_plain_name(self):
        # A token-only ASCII name is emitted unquoted, with no filename*.
        self.assertEqual(content_disposition_attachment('normal.pdf'),
                         'attachment; filename=normal.pdf')

    def test_content_disposition_spoofing_is_neutralized(self):
        # An attacker-controlled name cannot break out of the quoted-string:
        # both `"` and `\` are backslash-escaped (Content-Disposition spoofing).
        self.assertEqual(content_disposition_attachment('evil"\\.pdf'),
                         'attachment; filename="evil\\"\\\\.pdf"')

    def test_content_disposition_unicode_gets_filename_star(self):
        # A non-ASCII name keeps an ASCII-folded fallback and a percent-encoded
        # RFC 5987 filename* for modern browsers.
        self.assertEqual(content_disposition_attachment('rapporto-€.pdf'),
                         "attachment; filename=rapporto-.pdf; filename*=UTF-8''rapporto-%E2%82%AC.pdf")

    def test_content_disposition_strips_crlf(self):
        # CR/LF must be removed to prevent HTTP response header injection.
        self.assertEqual(content_disposition_attachment('evil.pdf\r\nSet-Cookie: x=1'),
                         'attachment; filename="evil.pdfSet-Cookie: x=1"')

    def test_validate_request_valid1(self):
        dummy_message = {'spam': 'ham', 'firstd': {3: 4}, 'fields': "CIAOCIAO", 'nest': [{1: 2, 3: 4}]}
        dummy_request_template = {'spam': str, 'firstd': dict, 'fields': r'\w+', 'nest': [dict]}

        self.assertTrue(BaseHandler.validate_request(dummy_message, dummy_request_template))

    def test_validate_request_valid2(self):
        dummy_json = json.dumps({'spam': 'ham'})
        dummy_request_template = {'spam': str}

        self.assertEqual(json.loads(dummy_json), BaseHandler.validate_request(dummy_json, dummy_request_template))

    def test_validate_request_invalid(self):
        dummy_json = json.dumps({'spam': 'ham'})
        dummy_request_template = {'spam': dict}

        self.assertRaises(InputValidationError,
                          BaseHandler.validate_request, dummy_json, dummy_request_template)

    def test_validate_type_valid(self):
        self.assertTrue(BaseHandler.validate_type('foca', str))
        self.assertTrue(BaseHandler.validate_type(True, bool))
        self.assertTrue(BaseHandler.validate_type(4, int))
        self.assertTrue(BaseHandler.validate_type(u'foca', str))
        self.assertTrue(BaseHandler.validate_type(['foca', 'fessa'], list))
        self.assertTrue(BaseHandler.validate_type({'foca': 1}, dict))

    def test_validate_type_invalid(self):
        self.assertFalse(BaseHandler.validate_type(1, str))
        self.assertFalse(BaseHandler.validate_type(1, str))
        self.assertFalse(BaseHandler.validate_type(False, str))
        self.assertFalse(BaseHandler.validate_type({}, list))
        self.assertFalse(BaseHandler.validate_type(True, dict))

    def test_validate_python_type_valid(self):
        self.assertTrue(BaseHandler.validate_python_type('foca', str))
        self.assertTrue(BaseHandler.validate_python_type(True, bool))
        self.assertTrue(BaseHandler.validate_python_type(4, int))
        self.assertTrue(BaseHandler.validate_python_type(u'foca', str))
        self.assertTrue(BaseHandler.validate_python_type(None, dict))

    def test_validate_regexp_valid(self):
        self.assertTrue(BaseHandler.validate_regexp('Foca', r'\w+'))
        self.assertFalse(BaseHandler.validate_regexp('Foca', r'\d+'))
