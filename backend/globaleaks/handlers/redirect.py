# Handlers implementing special redirects
from globaleaks.handlers.base import BaseHandler


url_map = {
    '/admin': '/#/admin',
    '/login': '/#/login',
    '/submission': '/#/submission'
}


class SpecialRedirectHandler(BaseHandler):
    """
    Handler that implements the platform special redirects
    """
    check_roles = 'any'

    def get(self, path):
        if path not in url_map:
            self.redirect('/')
            return
        self.redirect(url_map[path])
