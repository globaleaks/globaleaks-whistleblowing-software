import base64
import json
import time
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from twisted.internet import reactor
from twisted.internet.defer import inlineCallbacks, returnValue
from twisted.web.client import Agent, readBody
from twisted.web.http_headers import Headers


def b64d(data):
    """
    Decode a base64url encoded JWS/JWK value; the padding stripped as per
    RFC 7515 Appendix C is restored and any character outside the alphabet
    is rejected rather than silently ignored.
    """
    if isinstance(data, str):
        data = data.encode('utf-8')

    return base64.b64decode(data + b'=' * (-len(data) % 4), altchars=b'-_', validate=True)


def extract_bearer_token(request):
    """
    Extract the OIDC access token carried by the Authorization header
    """
    try:
        auth_header = request.getHeader('Authorization')
        if auth_header and auth_header.startswith('Bearer '):
            return auth_header[len('Bearer '):].strip()
    except:
        pass

    return None


def rsa_public_key(key):
    """
    Build an RSA public key from its JWK representation (RFC 7518 Section 6.3).
    """
    if key.get('kty') != 'RSA':
        raise Exception("Unsupported key type in JWKS")

    n = int.from_bytes(b64d(key['n']), 'big')
    e = int.from_bytes(b64d(key['e']), 'big')

    return rsa.RSAPublicNumbers(e, n).public_key()


class OIDCAuth(object):
    """
    Verifier for OIDC access tokens issued by the IdP configured on each tenant
    """
    check_roles = 'any'

    def __init__(self):
        # JWKS documents cached per issuer URL
        self.jwks = {}

        # JWKS endpoints resolved via OIDC discovery, cached per issuer URL
        self.jwks_uris = {}

    def discovery_url(self, issuer):
        return issuer.rstrip('/') + '/.well-known/openid-configuration'

    @inlineCallbacks
    def fetch_json(self, url):
        agent = Agent(reactor)
        response = yield agent.request(
            b'GET',
            url.encode('utf-8'),
            Headers({'User-Agent': ['Twisted Web Client']}),
            None
        )
        body = yield readBody(response)
        returnValue(json.loads(body.decode('utf-8')))

    @inlineCallbacks
    def fetch_jwks_uri(self, issuer):
        """
        Resolve the JWKS endpoint of an issuer via OIDC Discovery, so that any
        standard-compliant IdP is supported and not only those exposing the
        endpoint at a vendor specific path.
        """
        metadata = yield self.fetch_json(self.discovery_url(issuer))

        # OpenID Connect Discovery 1.0 requires the issuer advertised in the
        # metadata to match the one the document has been retrieved for.
        if metadata.get('issuer', '').rstrip('/') != issuer.rstrip('/'):
            raise Exception("The issuer advertised by the IdP does not match the configured one")

        jwks_uri = metadata.get('jwks_uri')
        if not jwks_uri:
            raise Exception("The configured issuer does not advertise a JWKS endpoint")

        returnValue(jwks_uri)

    @inlineCallbacks
    def fetch_jwks(self, issuer):
        if not issuer:
            return

        try:
            jwks_uri = self.jwks_uris.get(issuer)
            if not jwks_uri:
                jwks_uri = yield self.fetch_jwks_uri(issuer)
                self.jwks_uris[issuer] = jwks_uri

            self.jwks[issuer] = yield self.fetch_json(jwks_uri)
        except Exception:
            # Drop the cached endpoint so that the next refresh performs
            # discovery again; this recovers from IdP reconfigurations.
            self.jwks_uris.pop(issuer, None)
            raise

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

    def verify_token(self, token, issuer, client_id):
        if not issuer:
            raise Exception("No IdP issuer configured")

        if not client_id:
            raise Exception("No IdP client identifier configured")

        jwks = self.jwks.get(issuer)
        if not jwks:
            raise Exception("JWKS not available for the configured issuer")

        try:
            signing_input, encoded_signature = token.rsplit('.', 1)
            encoded_headers, encoded_claims = signing_input.split('.')
            headers = json.loads(b64d(encoded_headers))
            claims = json.loads(b64d(encoded_claims))
            signature = b64d(encoded_signature)
        except Exception:
            raise Exception("The token is malformed")

        # The signature algorithm is pinned to RS256 and never taken from the
        # token header, to avoid algorithm-confusion attacks.
        if headers.get('alg') != 'RS256':
            raise Exception("The token is not signed with the expected algorithm")

        key = None
        for jwk_key in jwks.get('keys', []):
            if jwk_key.get('kid') == headers.get('kid'):
                key = jwk_key
                break

        if key is None:
            raise Exception("Public key not found in JWKS")

        try:
            rsa_public_key(key).verify(signature,
                                       signing_input.encode('utf-8'),
                                       padding.PKCS1v15(),
                                       hashes.SHA256())
        except InvalidSignature:
            raise Exception("The token signature is not valid")

        if claims.get('iss') != issuer:
            raise Exception("The token has not been issued by the configured issuer")

        now = time.time()

        # A token carrying no expiration would be valid forever and is
        # therefore rejected even though RFC 7519 makes the claim optional.
        try:
            if float(claims['exp']) <= now:
                raise Exception("The token is expired")
        except (KeyError, TypeError, ValueError):
            raise Exception("The token does not declare a valid expiration")

        if 'nbf' in claims:
            try:
                if float(claims['nbf']) > now:
                    raise Exception("The token is not valid yet")
            except (TypeError, ValueError):
                raise Exception("The token does not declare a valid validity start")

        # The audience of an access token varies across IdPs: some issue it to
        # the client identifier, others (Keycloak by default) issue it to a
        # generic resource and carry the client identifier in 'azp'. Accepting
        # either, but requiring one of the two to match the configured client,
        # prevents tokens issued to a different client of the same issuer from
        # being replayed against GlobaLeaks.
        aud = claims.get('aud', [])
        if not isinstance(aud, list):
            aud = [aud]

        if client_id not in aud and claims.get('azp') != client_id:
            raise Exception("The token has not been issued for the configured client")

        return claims
