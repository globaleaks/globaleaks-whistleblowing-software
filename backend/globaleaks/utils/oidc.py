import json
from jose import jwt, jwk
from jose.utils import base64url_decode
from twisted.internet import reactor
from twisted.internet.defer import inlineCallbacks, returnValue
from twisted.web.client import Agent, readBody
from twisted.web.http_headers import Headers


class OIDCAuth(object):
    """
    Login handler for internal users
    """
    check_roles = 'any'

    jwks_url = 'http://127.0.0.1:9090/realms/globaleaks/protocol/openid-connect/certs'
    issuer = 'http://127.0.0.1:9090/realms/globaleaks'
    audience = 'account'


    def __init__(self):
        self.jwks = None

    @inlineCallbacks
    def fetch_jwks(self):
        agent = Agent(reactor)
        response = yield agent.request(
            b'GET',
            self.jwks_url.encode('utf-8'),
            Headers({'User-Agent': ['Twisted Web Client']}),
            None
        )
        body = yield readBody(response)
        self.jwks = json.loads(body.decode('utf-8'))

    def verify_token(self, token):
        headers = jwt.get_unverified_headers(token)
        kid = headers.get('kid')
        algorithm = headers.get('alg', 'RS256')

        key = None
        for jwk_key in self.jwks['keys']:
            if jwk_key['kid'] == kid:
                key = jwk_key
                break

        if key is None:
            raise Exception("Public key not found in JWKS")

        public_key = jwk.construct(key)

        message, encoded_signature = token.rsplit('.', 1)

        decoded_signature = base64url_decode(encoded_signature.encode('utf-8'))

        public_key.verify(message.encode('utf-8'), decoded_signature)

        return jwt.decode(token, public_key, algorithms=[algorithm], audience=self.audience, issuer=self.issuer)
