import json
from jose import jwt, jwk
from twisted.internet import reactor
from twisted.internet.defer import inlineCallbacks
from twisted.web.client import Agent, readBody
from twisted.web.http_headers import Headers


class OIDCAuth(object):
    """
    Verifier for OIDC access tokens issued by the IdP configured on each tenant
    """
    check_roles = 'any'
    audience = 'account'

    def __init__(self):
        # JWKS documents cached per issuer URL
        self.jwks = {}

    def certs_url(self, issuer):
        return issuer.rstrip('/') + '/protocol/openid-connect/certs'

    @inlineCallbacks
    def fetch_jwks(self, issuer):
        if not issuer:
            return

        agent = Agent(reactor)
        response = yield agent.request(
            b'GET',
            self.certs_url(issuer).encode('utf-8'),
            Headers({'User-Agent': ['Twisted Web Client']}),
            None
        )
        body = yield readBody(response)
        self.jwks[issuer] = json.loads(body.decode('utf-8'))

    @inlineCallbacks
    def validate_issuer(self, issuer):
        """
        Validate an issuer server-side by fetching its JWKS; this both verifies
        that the IdP is reachable/usable and warms the cache so that tokens can
        be verified immediately without waiting for the periodic refresh.
        """
        if not issuer:
            raise Exception("No IdP issuer configured")

        yield self.fetch_jwks(issuer)

        if not self.jwks.get(issuer, {}).get('keys'):
            raise Exception("The configured issuer did not return a valid JWKS")

    def verify_token(self, token, issuer):
        if not issuer:
            raise Exception("No IdP issuer configured")

        jwks = self.jwks.get(issuer)
        if not jwks:
            raise Exception("JWKS not available for the configured issuer")

        headers = jwt.get_unverified_headers(token)
        kid = headers.get('kid')

        key = None
        for jwk_key in jwks['keys']:
            if jwk_key['kid'] == kid:
                key = jwk_key
                break

        if key is None:
            raise Exception("Public key not found in JWKS")

        public_key = jwk.construct(key)

        # The signature algorithm is pinned to RS256 and never taken from the
        # token header, to avoid algorithm-confusion attacks. jwt.decode verifies
        # the signature, the expiration, the audience and the issuer.
        return jwt.decode(token, public_key, algorithms=['RS256'], audience=self.audience, issuer=issuer)
