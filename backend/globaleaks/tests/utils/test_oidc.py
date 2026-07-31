import base64
import json
import time
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding, rsa

from globaleaks.tests import helpers
from globaleaks.utils import oidc


class Test_OIDCAuth(helpers.TestGL):
    def setUp(self):
        # Generate the RSA private key
        self.private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048
        )

        # OIDC metadata
        self.issuer = "http://127.0.0.1:9090/realms/globaleaks"
        self.audience = "account"
        self.client_id = "globaleaks"

        self.oidc = oidc.OIDCAuth()
        self.oidc.jwks = {self.issuer: {"keys": []}}

    def base64url_encode(self, data):
        """
        Encodes data in base64url encoding.
        """
        return base64.urlsafe_b64encode(data).rstrip(b'=')

    def encode_token(self, payload, headers=None):
        """
        Signs a JWT with the dynamically created private key; this is the
        counterpart of the verification implemented in globaleaks.utils.oidc.
        """
        headers = headers or {}
        headers.setdefault("kid", "test-key-id")
        headers.setdefault("alg", "RS256")
        headers.setdefault("typ", "JWT")

        segments = [
            self.base64url_encode(json.dumps(headers).encode('utf-8')),
            self.base64url_encode(json.dumps(payload).encode('utf-8'))
        ]

        signing_input = b'.'.join(segments)

        signature = self.private_key.sign(signing_input,
                                          padding.PKCS1v15(),
                                          hashes.SHA256())

        segments.append(self.base64url_encode(signature))

        return b'.'.join(segments).decode('utf-8')

    def generate_valid_token(self):
        """
        Generates a valid JWT token signed with the dynamically created private key.
        """
        payload = {
            "sub": "admin",
            "name": "John Doe",
            "email": "john.doe@example.com",
            "iss": self.issuer,
            "aud": self.audience,
            "azp": self.client_id,
            "exp": time.time() + 3600,
            "iat": time.time(),
            "nonce": "random_nonce_value"
        }

        return self.encode_token(payload)

    def generate_jwk(self):
        """
        Generates a JSON Web Key (JWK) from the public key.
        """
        # Extract public key numbers
        public_numbers = self.private_key.public_key().public_numbers()
        n = public_numbers.n
        e = public_numbers.e

        # Convert numbers to bytes
        n_bytes = n.to_bytes((n.bit_length() + 7) // 8, byteorder='big')
        e_bytes = e.to_bytes((e.bit_length() + 7) // 8, byteorder='big')

        # Base64url encode the modulus and exponent
        n_base64 = self.base64url_encode(n_bytes).decode('utf-8')
        e_base64 = self.base64url_encode(e_bytes).decode('utf-8')

        # Create JWK structure
        jwk = {
            "kty": "RSA",
            "kid": "test-key-id",  # A unique key ID for the key
            "use": "sig",  # The key is used for signing
            "alg": "RS256",  # RSA-SHA256 algorithm
            "n": n_base64,
            "e": e_base64
        }

        return jwk

    def test_validate_token(self):
        """
        Test JWT validation using a mocked JWKS response containing the dynamically generated key.
        """
        # Generate a valid JWT token using the private key
        valid_token = self.generate_valid_token()

        # Generate the JWK from the public key
        jwk_key = self.generate_jwk()

        # Mock the JWKS response with the generated key
        self.oidc.jwks = {self.issuer: {"keys": [jwk_key]}}

        claims = self.oidc.verify_token(valid_token, self.issuer, self.client_id)

        self.assertEqual(claims['sub'], 'admin')

    def test_invalid_token_format(self):
        """
        Test that the validator correctly raises an error for invalid token format.
        """
        # Provide an invalid JWT format (less than 3 parts)
        invalid_token = "invalid_token_format"

        # Mock the JWKS response with the generated key
        jwk_key = self.generate_jwk()
        self.oidc.jwks = {self.issuer: {"keys": [jwk_key]}}

        self.assertRaisesRegex(Exception, "malformed", self.oidc.verify_token, invalid_token, self.issuer, self.client_id)

    def test_no_key_in_jwks(self):
        """
        Test the case where the JWKS does not contain the key ID (kid) from the JWT.
        """
        # Generate a valid JWT token using the private key
        valid_token = self.generate_valid_token()

        # Mock a JWKS response without the correct key ID
        self.oidc.jwks = {self.issuer: {"keys": [{"kid": "other-key-id", "alg": "RS256", "use": "sig"}]}}

        self.assertRaisesRegex(Exception, "Public key not found", self.oidc.verify_token, valid_token, self.issuer, self.client_id)

    def test_invalid_signature(self):
        """
        Test that the token is rejected if the signature is invalid.
        """
        # Generate a valid JWT token
        valid_token = self.generate_valid_token()

        # Modify the token slightly to invalidate the signature
        invalid_token = valid_token[:-3] + "XXX"  # Change the 3 characters

        # Mock the JWKS response with the generated key
        jwk_key = self.generate_jwk()
        self.oidc.jwks = {self.issuer: {"keys": [jwk_key]}}

        self.assertRaisesRegex(Exception, "signature is not valid", self.oidc.verify_token, invalid_token, self.issuer, self.client_id)

    def test_token_signed_by_another_key(self):
        """
        Test that a token signed by a key different from the one advertised in
        the JWKS is rejected.
        """
        valid_token = self.generate_valid_token()

        # Advertise a JWK carrying the key id of the token but the public key
        # of a different key pair
        self.private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)

        self.oidc.jwks = {self.issuer: {"keys": [self.generate_jwk()]}}

        self.assertRaisesRegex(Exception, "signature is not valid", self.oidc.verify_token, valid_token, self.issuer, self.client_id)

    def test_token_signed_with_an_unexpected_algorithm(self):
        """
        Test that the algorithm is never taken from the token header: a token
        declaring a different algorithm is rejected instead of being verified
        with the algorithm it declares.
        """
        payload = {
            "sub": "admin",
            "iss": self.issuer,
            "aud": self.audience,
            "azp": self.client_id,
            "exp": time.time() + 3600
        }

        token = self.encode_token(payload, {"alg": "none"})

        self.oidc.jwks = {self.issuer: {"keys": [self.generate_jwk()]}}

        self.assertRaisesRegex(Exception, "expected algorithm", self.oidc.verify_token, token, self.issuer, self.client_id)

    def test_expired_signature(self):
        """
        Test that an expired token is rejected by the validator.
        """
        # Generate an expired JWT token
        expired_payload = {
            "sub": "admin",
            "name": "John Doe",
            "email": "john.doe@example.com",
            "iss": self.issuer,
            "aud": self.audience,
            "azp": self.client_id,
            "exp": time.time() - 3600,  # Set expiration in the past
            "iat": time.time(),
            "nonce": "random_nonce_value"
        }

        # Use the same private key to generate an expired token
        expired_token = self.encode_token(expired_payload)

        # Mock the JWKS response with the generated key
        jwk_key = self.generate_jwk()
        self.oidc.jwks = {self.issuer: {"keys": [jwk_key]}}

        self.assertRaisesRegex(Exception, "expired", self.oidc.verify_token, expired_token, self.issuer, self.client_id)

    def test_token_without_expiration(self):
        """
        Test that a token carrying no expiration is rejected: it would
        otherwise be accepted forever.
        """
        payload = {
            "sub": "admin",
            "iss": self.issuer,
            "aud": self.audience,
            "azp": self.client_id
        }

        token = self.encode_token(payload)

        self.oidc.jwks = {self.issuer: {"keys": [self.generate_jwk()]}}

        self.assertRaisesRegex(Exception, "valid expiration", self.oidc.verify_token, token, self.issuer, self.client_id)

    def test_token_not_yet_valid(self):
        """
        Test that a token whose validity starts in the future is rejected.
        """
        payload = {
            "sub": "admin",
            "iss": self.issuer,
            "aud": self.audience,
            "azp": self.client_id,
            "exp": time.time() + 7200,
            "nbf": time.time() + 3600
        }

        token = self.encode_token(payload)

        self.oidc.jwks = {self.issuer: {"keys": [self.generate_jwk()]}}

        self.assertRaisesRegex(Exception, "not valid yet", self.oidc.verify_token, token, self.issuer, self.client_id)

    def test_token_issued_by_another_issuer(self):
        """
        Test that a token issued by an issuer different from the configured
        one is rejected.
        """
        payload = {
            "sub": "admin",
            "iss": "http://127.0.0.1:9090/realms/another",
            "aud": self.audience,
            "azp": self.client_id,
            "exp": time.time() + 3600
        }

        token = self.encode_token(payload)

        self.oidc.jwks = {self.issuer: {"keys": [self.generate_jwk()]}}

        self.assertRaisesRegex(Exception, "configured issuer", self.oidc.verify_token, token, self.issuer, self.client_id)

    def test_token_issued_to_another_client(self):
        """
        Test that a token issued by the same issuer to a different client is
        rejected: the generic audience used by some IdPs is shared across all
        the clients of the same realm and is therefore not sufficient on its own.
        """
        payload = {
            "sub": "admin",
            "email": "john.doe@example.com",
            "iss": self.issuer,
            "aud": self.audience,
            "azp": "another-client",
            "exp": time.time() + 3600,
            "iat": time.time()
        }

        token = self.encode_token(payload)

        self.oidc.jwks = {self.issuer: {"keys": [self.generate_jwk()]}}

        self.assertRaisesRegex(Exception, "configured client", self.oidc.verify_token, token, self.issuer, self.client_id)

    def test_token_audienced_to_the_configured_client(self):
        """
        Test that a token whose audience is the configured client is accepted
        also when the IdP does not issue the 'azp' claim.
        """
        payload = {
            "sub": "admin",
            "email": "john.doe@example.com",
            "iss": self.issuer,
            "aud": [self.client_id],
            "exp": time.time() + 3600,
            "iat": time.time()
        }

        token = self.encode_token(payload)

        self.oidc.jwks = {self.issuer: {"keys": [self.generate_jwk()]}}

        self.oidc.verify_token(token, self.issuer, self.client_id)

    def test_no_client_id_configured(self):
        """
        Test that no token is accepted when no client identifier is configured.
        """
        valid_token = self.generate_valid_token()

        self.oidc.jwks = {self.issuer: {"keys": [self.generate_jwk()]}}

        self.assertRaisesRegex(Exception, "No IdP client identifier", self.oidc.verify_token, valid_token, self.issuer, '')
