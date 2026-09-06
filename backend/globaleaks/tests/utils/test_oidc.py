import base64
import json
import time

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from twisted.internet import defer

from globaleaks.tests import helpers
from globaleaks.utils import oidc


ISSUER = "http://127.0.0.1:9090/realms/globaleaks"
CLIENT = "globaleaks"


def base64url(data):
    return base64.urlsafe_b64encode(data).rstrip(b'=')


class TestOIDCAuth(helpers.TestGL):
    """
    The identity token is the only thing that attests an authentication, and
    """
    def setUp(self):
        self.private_key = rsa.generate_private_key(public_exponent=65537,
                                                    key_size=2048)

        self.oidc = oidc.OIDCAuth()
        self.oidc.jwks = {ISSUER: {"keys": []}}

    def encode(self, payload, headers=None):
        """
        Sign a token with the key of this test, as the identity provider does
        """
        headers = dict(headers or {})
        headers.setdefault("kid", "test-key-id")
        headers.setdefault("alg", "RS256")
        headers.setdefault("typ", "JWT")

        segments = [base64url(json.dumps(headers).encode()),
                    base64url(json.dumps(payload).encode())]

        signature = self.private_key.sign(b'.'.join(segments),
                                          padding.PKCS1v15(),
                                          hashes.SHA256())

        segments.append(base64url(signature))

        return b'.'.join(segments).decode()

    def jwk(self):
        """
        The public key of this test, in the form the identity provider
        """
        numbers = self.private_key.public_key().public_numbers()

        def encode(value):
            return base64url(value.to_bytes((value.bit_length() + 7) // 8,
                                            'big')).decode()

        return {"kty": "RSA", "kid": "test-key-id", "use": "sig",
                "alg": "RS256", "n": encode(numbers.n), "e": encode(numbers.e)}

    def advertise(self):
        self.oidc.jwks = {ISSUER: {"keys": [self.jwk()]}}

    def refused(self, operation, expected, subject):
        """
        Assert that an operation is refused for the expected reason, naming the
        """
        try:
            operation()
        except Exception as e:
            self.assertRegex(str(e), expected,
                             f"{subject} is refused, but not because it is {expected}")
        else:
            self.fail(f"{subject} is accepted")

    def claims(self, **kwargs):
        payload = {"sub": "admin",
                   "email": "john.doe@example.com",
                   "iss": ISSUER,
                   "aud": CLIENT,
                   "azp": CLIENT,
                   "exp": time.time() + 3600,
                   "iat": time.time()}
        payload.update(kwargs)

        return {k: v for k, v in payload.items() if v is not None}

    def test_a_token_of_the_configured_issuer_and_client_is_accepted(self):
        self.advertise()

        claims = self.oidc.verify_token(self.encode(self.claims()), ISSUER, CLIENT)

        self.assertEqual(claims['sub'], 'admin')

    def test_a_token_audienced_to_the_client_is_accepted_without_azp(self):
        # An identity provider that does not issue the authorized party leaves
        # the audience to say who the token is for
        self.advertise()

        self.oidc.verify_token(self.encode(self.claims(aud=[CLIENT], azp=None)),
                               ISSUER, CLIENT)

    def test_the_token_is_refused(self):
        """
        The reasons a token is refused, one row each. The row is named in the
        """
        cases = [
            ("malformed",
             lambda: "not-a-token", {}, "malformed"),
            ("signed with an algorithm other than the expected one",
             lambda: self.encode(self.claims(), {"alg": "none"}), {}, "expected algorithm"),
            ("typed as an access token",
             lambda: self.encode(self.claims(), {"typ": "at+jwt"}), {}, "not an ID token"),
            ("signed by a key the provider does not advertise",
             lambda: self.encode(self.claims()),
             {"keys": [{"kid": "other-key-id", "alg": "RS256", "use": "sig"}]},
             "Public key not found"),
            ("tampered with after being signed",
             lambda: self.encode(self.claims())[:-3] + "XXX", {}, "signature is not valid"),
            ("expired",
             lambda: self.encode(self.claims(exp=time.time() - 3600)), {}, "expired"),
            ("carrying no expiration, which would make it valid forever",
             lambda: self.encode(self.claims(exp=None)), {}, "valid expiration"),
            ("valid only from a moment still to come",
             lambda: self.encode(self.claims(exp=time.time() + 7200,
                                             nbf=time.time() + 3600)), {}, "not valid yet"),
            ("issued by another issuer",
             lambda: self.encode(self.claims(iss=ISSUER + "-other")), {}, "configured issuer"),
            ("issued to another client",
             lambda: self.encode(self.claims(aud="another", azp="another")), {}, "configured client"),
            ("audienced to a resource, as the access tokens of the provider are",
             lambda: self.encode(self.claims(aud="account")), {}, "configured client"),
            ("authorized to a party other than the client",
             lambda: self.encode(self.claims(aud=[CLIENT], azp="another")), {}, "configured client")
        ]

        for reason, token, jwks, expected in cases:
            self.advertise()
            if jwks:
                self.oidc.jwks = {ISSUER: jwks}

            self.refused(lambda token=token: self.oidc.verify_token(token(), ISSUER, CLIENT),
                         expected, f"a token {reason}")

    def test_no_token_is_accepted_where_the_provider_is_not_configured(self):
        self.advertise()

        for issuer, client, expected in [(ISSUER, '', "No IdP client identifier"),
                                         ('', CLIENT, "No IdP issuer")]:
            self.assertRaisesRegex(Exception, expected, self.oidc.verify_token,
                                   self.encode(self.claims()), issuer, client)

    def test_the_endpoint_of_the_provider_is_reached_over_a_protected_transport(self):
        """
        The metadata of the provider are collected over HTTPS, so that whoever
        """
        oidc.validate_endpoint("https://idp.globaleaks.org/realms/globaleaks")
        oidc.validate_endpoint("http://127.0.0.1:9090/realms/globaleaks")

        for endpoint in ["http://idp.globaleaks.org/realms/globaleaks",
                         "file:///etc/passwd"]:
            self.refused(lambda endpoint=endpoint: oidc.validate_endpoint(endpoint),
                         "HTTPS", f"the endpoint {endpoint}")

    def test_the_metadata_of_another_issuer_are_refused(self):
        # A document is trusted for the issuer it has been retrieved for, and
        # names it: naming another one is how a provider would speak for one
        self.oidc.fetch_json = lambda url: defer.succeed({"issuer": "https://another.example.org"})

        return self.assertFailure(self.oidc.fetch_metadata(ISSUER), Exception)

    def test_a_document_larger_than_the_platform_accepts_is_dropped(self):
        # Whatever the provider answers is read into memory: a bound on it is
        # what keeps a provider from exhausting the platform
        collected = []
        within = oidc.BoundedBodyProtocol(1024)
        within.finished.addCallback(collected.append)
        within.dataReceived(b'{"issuer":')
        within.dataReceived(b'"globaleaks"}')
        within.connectionLost(None)

        self.assertEqual(collected, [b'{"issuer":"globaleaks"}'])

        refused = []
        beyond = oidc.BoundedBodyProtocol(8)
        beyond.finished.addErrback(refused.append)
        beyond.dataReceived(b'x' * 9)
        beyond.connectionLost(None)

        self.assertEqual(len(refused), 1)

    @defer.inlineCallbacks
    def test_the_client_is_validated_against_the_provider(self):
        """
        The client is probed with an authorization code that cannot be valid:
        """
        def answering(response):
            self.oidc.fetch_metadata = lambda issuer: defer.succeed(
                {"issuer": ISSUER, "token_endpoint": ISSUER + "/protocol/openid-connect/token"})
            self.oidc.post_form = lambda url, form: defer.succeed(response)

        # the code is refused, so the client exists and holds the code grant
        answering({"error": "invalid_grant"})
        yield self.oidc.validate_client(ISSUER, CLIENT)

        for _, response in [("unknown to the provider", {"error": "invalid_client"}),
                                 ("not allowed the code grant", {"error": "unauthorized_client"})]:
            answering(response)
            yield self.assertFailure(self.oidc.validate_client(ISSUER, CLIENT), Exception)

        yield self.assertFailure(self.oidc.validate_client(ISSUER, ""), Exception)
