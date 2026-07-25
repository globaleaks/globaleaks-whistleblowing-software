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
        # A session bearing token must only be minted for a request that proved
        # possession of the session key. The token path is exempt from the DPoP
        # check, so minting from a token carried session would let a single
        # captured token be renewed indefinitely, outliving the session it was
        # derived from.
        session = None if self.session_from_token else self.session

        return State.tokens.new(self.request.tid, session).serialize()
