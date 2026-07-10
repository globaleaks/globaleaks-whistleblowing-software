from globaleaks.handlers.user import UserInstance
from globaleaks.rest import errors
from globaleaks.tests import helpers


class TestDPoPEnforcement(helpers.TestHandlerWithPopulatedDB):
    """Strict per-request DPoP (RFC 9449) enforcement on authenticated requests."""
    _handler = UserInstance

    def test_missing_proof_rejected(self):
        handler = self.request(role='receiver')
        del handler.request.headers[b'dpop']
        self.assertRaises(errors.InvalidDPoP, handler.get)

    def test_malformed_proof_rejected(self):
        handler = self.request(role='receiver')
        handler.request.headers[b'dpop'] = b'not-a-valid-jwt'
        self.assertRaises(errors.InvalidDPoP, handler.get)

    def test_wrong_ath_rejected(self):
        # A proof whose ath binds it to a different session token is rejected.
        handler = self.request(role='receiver')
        handler.request.headers[b'dpop'] = helpers.make_dpop_proof(
            'GET', helpers.dpop_htu(handler.request), session_id='another-session-id')
        self.assertRaises(errors.InvalidDPoP, handler.get)

    def test_wrong_method_rejected(self):
        handler = self.request(role='receiver')
        handler.request.headers[b'dpop'] = helpers.make_dpop_proof(
            'DELETE', helpers.dpop_htu(handler.request),
            session_id=handler.session_id_cleartext)
        self.assertRaises(errors.InvalidDPoP, handler.get)
