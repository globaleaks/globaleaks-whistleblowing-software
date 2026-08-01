import base64
import json
import time
from urllib.parse import urlparse
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from twisted.internet import reactor
from twisted.internet.defer import Deferred, inlineCallbacks, returnValue
from twisted.internet.protocol import Protocol
from twisted.web.http_headers import Headers


# Timeout applied to every request performed towards an identity provider
REQUEST_TIMEOUT = 15

# Maximum size accepted for the documents published by an identity provider
MAX_RESPONSE_SIZE = 1024 * 1024


def validate_endpoint(url):
    """
    Validate an endpoint published by an identity provider

    OpenID Connect Discovery 1.0 requires the published endpoints to be HTTPS;
    plain HTTP is accepted only towards the loopback interface, so that a local
    identity provider can still be used on development and testing setups.

    :param url: The URL of the endpoint
    """
    parsed = urlparse(url)

    if parsed.scheme == 'https':
        return

    if parsed.scheme == 'http' and parsed.hostname in ['127.0.0.1', '::1', 'localhost']:
        return

    raise Exception("The endpoints of the IdP are required to be reached via HTTPS")


class BoundedBodyProtocol(Protocol):
    """
    Protocol collecting a response body up to a maximum size, dropping the
    connection when the limit is exceeded or when the caller gives up, so that
    an identity provider cannot exhaust the resources of the platform
    """
    def __init__(self, max_size):
        self.max_size = max_size
        self.chunks = []
        self.size = 0
        self.finished = Deferred(lambda _: self.stop())

    def stop(self):
        if self.transport is not None:
            self.transport.stopProducing()

    def dataReceived(self, data):
        self.size += len(data)

        if self.size > self.max_size:
            self.stop()
            return

        self.chunks.append(data)

    def connectionLost(self, reason):
        if self.finished.called:
            return

        if self.size > self.max_size:
            self.finished.errback(Exception("The document published by the IdP is too big"))
        else:
            self.finished.callback(b''.join(self.chunks))


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

        # Metadata documents resolved via OIDC discovery, cached per issuer URL
        self.metadata = {}

    def discovery_url(self, issuer):
        return issuer.rstrip('/') + '/.well-known/openid-configuration'

    @inlineCallbacks
    def fetch_json(self, url):
        """
        Fetch a JSON document published by an identity provider

        The request is performed with the agent of the platform, so that the
        configured anonymization of the outgoing connections is honored, and is
        bounded in time and in size, so that an unresponsive or malicious
        identity provider cannot exhaust the resources of the platform.

        :param url: The URL of the document
        :return: The fetched document
        """
        validate_endpoint(url)

        # Imported here as the state imports this module at load time
        from globaleaks.state import State

        headers = {'User-Agent': ['Twisted Web Client']}

        response = yield State.get_agent().request(b'GET',
                                                   url.encode('utf-8'),
                                                   Headers(headers),
                                                   None).addTimeout(REQUEST_TIMEOUT, reactor)

        protocol = BoundedBodyProtocol(MAX_RESPONSE_SIZE)
        response.deliverBody(protocol)

        # The timeout cancels the collection of the body, dropping the
        # connection with an identity provider that stopped responding
        body = yield protocol.finished.addTimeout(REQUEST_TIMEOUT, reactor)

        returnValue(json.loads(body.decode('utf-8')))

    @inlineCallbacks
    def fetch_metadata(self, issuer):
        """
        Resolve the endpoints of an issuer via OIDC Discovery, so that any
        standard-compliant IdP is supported and not only those exposing the
        endpoints at a vendor specific path.

        :param issuer: The issuer to be resolved
        :return: The metadata published by the issuer
        """
        metadata = self.metadata.get(issuer)
        if metadata is not None:
            returnValue(metadata)

        metadata = yield self.fetch_json(self.discovery_url(issuer))

        # OpenID Connect Discovery 1.0 requires the issuer advertised in the
        # metadata to match the one the document has been retrieved for.
        if metadata.get('issuer', '').rstrip('/') != issuer.rstrip('/'):
            raise Exception("The issuer advertised by the IdP does not match the configured one")

        self.metadata[issuer] = metadata

        returnValue(metadata)

    @inlineCallbacks
    def fetch_jwks(self, issuer):
        if not issuer:
            return

        try:
            metadata = yield self.fetch_metadata(issuer)

            jwks_uri = metadata.get('jwks_uri')
            if not jwks_uri:
                raise Exception("The configured issuer does not advertise a JWKS endpoint")

            self.jwks[issuer] = yield self.fetch_json(jwks_uri)
        except Exception:
            # Drop the cached metadata so that the next refresh performs
            # discovery again; this recovers from IdP reconfigurations.
            self.metadata.pop(issuer, None)
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
