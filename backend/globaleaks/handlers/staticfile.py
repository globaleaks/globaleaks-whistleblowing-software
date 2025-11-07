# Handler exposing application files
import os

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
                self.request.write(f.read().replace(b'randomCspNonce', self.request.nonce))
                return

        return self.write_file(filename, abspath)
