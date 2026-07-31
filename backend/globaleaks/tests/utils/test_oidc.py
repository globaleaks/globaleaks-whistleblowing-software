import base64
import datetime
import json
from jose import jwt
from jose.exceptions import ExpiredSignatureError, JWTError
from twisted.trial import unittest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import hashes

from unittest.mock import patch

from globaleaks.tests import helpers
from globaleaks.utils import oidc


class Test_OIDCAuth(helpers.TestGL):
    def setUp(self):
        # Generate the RSA private key
        self.private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048
        )

        # Serialize the private key (we won't use it directly in the test but for key generation)
        self.private_pem = self.private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        )

        # Serialize the public key, which will be used to create the JWK
        self.public_pem = self.private_key.public_key().public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        )

        # OIDC metadata
        self.issuer = "http://127.0.0.1:9090/realms/globaleaks"
        self.audience = "account"
        self.client_id = "globaleaks"

        self.oidc = oidc.OIDCAuth()
        self.oidc.jwks = {self.issuer: {"keys": []}}

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
            "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=1),
            "iat": datetime.datetime.utcnow(),
            "nonce": "random_nonce_value"
        }

        header = {
            "kid": "test-key-id",
            "alg": "RS256",
            "typ": "JWT"
        }

        return jwt.encode(payload, self.private_pem, algorithm="RS256", headers=header)

    def base64url_encode(self, data):
        """
        Encodes data in base64url encoding.
        """
        return base64.urlsafe_b64encode(data).rstrip(b'=')

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

        self.oidc.verify_token(valid_token, self.issuer, self.client_id)

    def test_invalid_token_format(self):
        """
        Test that the validator correctly raises an error for invalid token format.
        """
        # Provide an invalid JWT format (less than 3 parts)
        invalid_token = "invalid_token_format"

        # Mock the JWKS response with the generated key
        jwk_key = self.generate_jwk()
        self.oidc.jwks = {self.issuer: {"keys": [jwk_key]}}

        self.assertRaises(JWTError, self.oidc.verify_token, invalid_token, self.issuer, self.client_id)

    def test_no_key_in_jwks(self):
        """
        Test the case where the JWKS does not contain the key ID (kid) from the JWT.
        """
        # Generate a valid JWT token using the private key
        valid_token = self.generate_valid_token()

        # Mock a JWKS response without the correct key ID
        self.oidc.jwks = {self.issuer: {"keys": [{"kid": "other-key-id", "alg": "RS256", "use": "sig"}]}}

        self.assertRaises(Exception, self.oidc.verify_token, valid_token, self.issuer, self.client_id)

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

        self.assertRaises(JWTError, self.oidc.verify_token, invalid_token, self.issuer, self.client_id)

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
            "exp": datetime.datetime.utcnow() - datetime.timedelta(hours=1),  # Set expiration in the past
            "iat": datetime.datetime.utcnow(),
            "nonce": "random_nonce_value"
        }

        # Use the same private key to generate an expired token
        expired_token = jwt.encode(expired_payload, self.private_pem, algorithm="RS256", headers={"kid": "test-key-id"})

        # Mock the JWKS response with the generated key
        jwk_key = self.generate_jwk()
        self.oidc.jwks = {self.issuer: {"keys": [jwk_key]}}

        self.assertRaises(ExpiredSignatureError, self.oidc.verify_token, expired_token, self.issuer, self.client_id)

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
            "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=1),
            "iat": datetime.datetime.utcnow()
        }

        token = jwt.encode(payload, self.private_pem, algorithm="RS256", headers={"kid": "test-key-id"})

        self.oidc.jwks = {self.issuer: {"keys": [self.generate_jwk()]}}

        self.assertRaises(Exception, self.oidc.verify_token, token, self.issuer, self.client_id)

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
            "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=1),
            "iat": datetime.datetime.utcnow()
        }

        token = jwt.encode(payload, self.private_pem, algorithm="RS256", headers={"kid": "test-key-id"})

        self.oidc.jwks = {self.issuer: {"keys": [self.generate_jwk()]}}

        self.oidc.verify_token(token, self.issuer, self.client_id)

    def test_no_client_id_configured(self):
        """
        Test that no token is accepted when no client identifier is configured.
        """
        valid_token = self.generate_valid_token()

        self.oidc.jwks = {self.issuer: {"keys": [self.generate_jwk()]}}

        self.assertRaises(Exception, self.oidc.verify_token, valid_token, self.issuer, '')
