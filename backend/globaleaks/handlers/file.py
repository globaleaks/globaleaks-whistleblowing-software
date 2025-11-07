# Handlers exposing customization files
import os
import urllib

from twisted.internet.defer import inlineCallbacks

from globaleaks.handlers.admin.file import get_file_id_by_name
from globaleaks.handlers.base import BaseHandler
from globaleaks.utils.fs import directory_traversal_check


appfiles = {
    'favicon': ('favicon.ico', ['image/x-icon'], 'images/favicon.ico'),
    'logo': ('logo.webp', ['image/gif', 'image/jpeg', 'image/png', 'image/webp'], 'images/logo.webp'),
    'css': ('custom.css', ['text/css'], 'data/empty.txt'),
    'script': ('script.js', ['text/javascript'], 'data/empty.txt')
}

class FileHandler(BaseHandler):
    """
    Handler that provide public access to configuration files
    """
    check_roles = 'any'

    allowed_mimetypes = [
        'audio/mpeg',
        'font/ttf',
        'font/woff',
        'font/woff2',
        'image/gif',
        'image/jpeg',
        'image/png',
        'image/webp',
        'image/x-icon',
        'text/css',
        'video/mp4'
    ]

    # Note: This set of mime types intentionally differs from the mime
    #       types accepted by the admin handler.
    #       For example it intentionally do not include application/pdf
    #       to ensure file download is enforced on PDF files.

    @inlineCallbacks
    def get(self, name):
        path = os.path.abspath(os.path.join(self.state.settings.files_path, 'not-existent-file'))

        name = urllib.parse.unquote(name)

        id = yield get_file_id_by_name(self.request.tid, name)
        if not id and self.request.tid != 1:
            id = yield get_file_id_by_name(1, name)

        if id:
            path = os.path.abspath(os.path.join(self.state.settings.files_path, id))
            directory_traversal_check(self.state.settings.files_path, path)
        elif name in appfiles:
            path = os.path.abspath(os.path.join(self.state.settings.client_path, appfiles[name][2]))
            directory_traversal_check(self.state.settings.client_path, path)

        if name in appfiles:
            filename = appfiles[name][0]
            self.allowed_mimetypes = appfiles[name][1]
        else:
            filename = name

        yield self.write_file(filename, path)
