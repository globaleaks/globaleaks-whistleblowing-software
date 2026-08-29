from twisted.internet.defer import inlineCallbacks, succeed

from globaleaks.jobs.oidc import OIDC
from globaleaks.state import State
from globaleaks.tests import helpers


class TestOIDC(helpers.TestGLWithPopulatedDB):
    """
    The job keeps the signing keys of the identity providers fresh: it refreshes
    """
    @inlineCallbacks
    def test_refreshes_each_configured_issuer_once_and_forgets_the_others(self):
        fetched = []

        def fetch_jwks(issuer):
            fetched.append(issuer)
            return succeed(None)

        State.oidcauth.fetch_jwks = fetch_jwks
        State.oidcauth.jwks = {'https://gone.example': {}, 'https://idp.example': {}}
        State.oidcauth.metadata = {'https://gone.example': {}, 'https://idp.example': {}}

        # Two tenants on the same identity provider, one signup provider, one
        # tenant that has configured an issuer but not enabled it
        State.tenants[1].cache.idp = True
        State.tenants[1].cache.idp_issuer = 'https://idp.example'
        State.tenants[2].cache.idp = True
        State.tenants[2].cache.idp_issuer = 'https://idp.example'
        State.tenants[2].cache.signup_idp = True
        State.tenants[2].cache.signup_idp_issuer = 'https://signup-idp.example'
        State.tenants[3].cache.idp = False
        State.tenants[3].cache.idp_issuer = 'https://disabled.example'

        yield OIDC().operation()

        self.assertEqual(sorted(fetched), ['https://idp.example', 'https://signup-idp.example'])
        self.assertNotIn('https://gone.example', State.oidcauth.jwks)
        self.assertNotIn('https://gone.example', State.oidcauth.metadata)
        self.assertIn('https://idp.example', State.oidcauth.jwks)
