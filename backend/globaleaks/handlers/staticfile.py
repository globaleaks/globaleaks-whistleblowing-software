# Handler exposing application files
import os

from globaleaks import get_language_direction
from globaleaks.handlers.base import BaseHandler
from globaleaks.utils.fs import directory_traversal_check


class StaticFileHandler(BaseHandler):
    check_roles = 'any'
    allowed_mimetypes = [
        'text/css',
        'text/html',
        'text/javascript'
    ]

    def __init__(self, state, request):
        BaseHandler.__init__(self, state, request)

        self.root = "%s%s" % (os.path.abspath(state.settings.client_path), "/")

    def get(self, filename):
        abspath = os.path.abspath(os.path.join(self.root, filename))
        directory_traversal_check(self.root, abspath)

        if filename == 'index.html':
            with open(abspath, 'rb') as f:
                data = f.read()
                data = data.replace(b'lang="lang"', b'lang="' + self.request.language.encode() + b'"')
                data = data.replace(b'dir="dir"', b'dir="' + get_language_direction(self.request.language).encode() + b'"')
                data = data.replace(b'randomCspNonce', self.request.nonce)
                self.request.write(data)
                return

        return self.write_file(filename, abspath)
