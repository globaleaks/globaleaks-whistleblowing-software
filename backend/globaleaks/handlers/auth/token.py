# Handler implementing pre/post submission tokens for implementing rate limiting on whistleblower operations
from globaleaks.handlers.base import BaseHandler
from globaleaks.state import State


class TokenHandler(BaseHandler):
    """
    This class implement the handler for requesting a token.
    """
    check_roles = 'any'

    def post(self):
        """
        This API create a Token, a temporary memory only object able to
        keep track and limit user actions.
        """
        return State.tokens.new(self.request.tid, self.session).serialize()
