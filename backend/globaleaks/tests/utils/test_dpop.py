# -*- coding: utf-8 -*-
import base64
import hashlib
import json

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.asymmetric.utils import decode_dss_signature

from twisted.internet.defer import inlineCallbacks
from twisted.trial import unittest

from globaleaks.rest import errors
from globaleaks.state import State
from globaleaks.tests import helpers
from globaleaks.utils import dpop

HTM = 'POST'
HTU = '/api/auth/dpop'


def _b64url(data):
    return base64.urlsafe_b64encode(data).rstrip(b'=').decode()


def _int_to_b64url(value):
    return _b64url(value.to_bytes(dpop._P256_COORD_LEN, 'big'))


def make_key():
    """Return a fresh P-256 private key."""
    return ec.generate_private_key(ec.SECP256R1())


def public_jwk(private_key):
    """Build the public JWK (as embedded in a DPoP proof header) for a key."""
    numbers = private_key.public_key().public_numbers()
    return {
        'kty': 'EC',
        'crv': 'P-256',
        'x': _int_to_b64url(numbers.x),
        'y': _int_to_b64url(numbers.y),
    }


def make_proof(private_key=None, *, header=None, payload=None,
               htm=HTM, htu=HTU, iat=None, jti='jti-0', ath=None,
               signing_key=None):
    """
    Assemble a serialized DPoP proof, signing with raw (R||S) ES256.

    Any of the header/payload structures may be overridden to forge malformed
    proofs for negative tests.
    """
    if private_key is None:
        private_key = make_key()

    if header is None:
        header = {
            'typ': dpop.DPOP_TYP,
            'alg': dpop.DPOP_ALG,
            'jwk': public_jwk(private_key),
        }

    if payload is None:
        if iat is None:
            iat = dpop.now_epoch()

        payload = {'htm': htm, 'htu': htu, 'iat': iat, 'jti': jti}

        if ath is not None:
            payload['ath'] = ath

    header_b64 = _b64url(json.dumps(header).encode())
    payload_b64 = _b64url(json.dumps(payload).encode())
    signing_input = (header_b64 + '.' + payload_b64).encode()

    der = (signing_key or private_key).sign(signing_input, ec.ECDSA(hashes.SHA256()))
    r, s = decode_dss_signature(der)
    raw_sig = r.to_bytes(dpop._P256_COORD_LEN, 'big') + s.to_bytes(dpop._P256_COORD_LEN, 'big')

    return header_b64 + '.' + payload_b64 + '.' + _b64url(raw_sig)


class TestDPoPHelpers(unittest.TestCase):
    def test_b64url_roundtrip(self):
        for data in [b'', b'a', b'ab', b'abc', b'abcd', b'\x00\xff\xfe']:
            self.assertEqual(dpop.b64url_decode(dpop.b64url_encode(data)), data)

    def test_b64url_encode_is_unpadded(self):
        self.assertNotIn('=', dpop.b64url_encode(b'abc'))

    def test_b64url_decode_accepts_str_and_bytes(self):
        encoded = dpop.b64url_encode(b'hello')
        self.assertEqual(dpop.b64url_decode(encoded), b'hello')
        self.assertEqual(dpop.b64url_decode(encoded.encode()), b'hello')

    def test_b64url_decode_tolerates_missing_padding(self):
        # 'YQ' is base64url for b'a' and would need one '=' of padding.
        self.assertEqual(dpop.b64url_decode('YQ'), b'a')

    def test_now_epoch_is_int(self):
        self.assertIsInstance(dpop.now_epoch(), int)

    def test_compute_ath_known_value(self):
        token = 'access-token'
        expected = _b64url(hashlib.sha256(token.encode()).digest())
        self.assertEqual(dpop.compute_ath(token), expected)

    def test_compute_ath_str_and_bytes_match(self):
        self.assertEqual(dpop.compute_ath('tok'), dpop.compute_ath(b'tok'))

    def test_jwk_thumbprint_matches_rfc7638(self):
        jwk = public_jwk(make_key())
        canonical = '{"crv":"P-256","kty":"EC","x":"%s","y":"%s"}' % (jwk['x'], jwk['y'])
        expected = _b64url(hashlib.sha256(canonical.encode()).digest())
        self.assertEqual(dpop.jwk_thumbprint(jwk), expected)

    def test_jwk_thumbprint_is_stable(self):
        jwk = public_jwk(make_key())
        self.assertEqual(dpop.jwk_thumbprint(jwk), dpop.jwk_thumbprint(dict(jwk)))

    def test_jwk_thumbprint_differs_per_key(self):
        self.assertNotEqual(dpop.jwk_thumbprint(public_jwk(make_key())),
                            dpop.jwk_thumbprint(public_jwk(make_key())))

    def test_jwk_to_public_key_valid(self):
        key = make_key()
        public_key = dpop.jwk_to_public_key(public_jwk(key))
        self.assertEqual(public_key.public_numbers(), key.public_key().public_numbers())

    def test_jwk_to_public_key_invalid_raises(self):
        self.assertRaises(errors.InvalidDPoP, dpop.jwk_to_public_key,
                          {'x': 'not-base64!!', 'y': 'also-bad'})

    def test_jwk_to_public_key_point_not_on_curve(self):
        # x=y=0 is not a valid point on P-256.
        bad = {'x': _int_to_b64url(0), 'y': _int_to_b64url(0)}
        self.assertRaises(errors.InvalidDPoP, dpop.jwk_to_public_key, bad)

    def test_verify_es256_wrong_signature_length(self):
        key = make_key()
        self.assertRaises(errors.InvalidDPoP, dpop._verify_es256,
                          key.public_key(), b'\x00' * 10, b'data')

    def test_verify_es256_invalid_signature(self):
        key = make_key()
        self.assertRaises(errors.InvalidDPoP, dpop._verify_es256,
                          key.public_key(), b'\x01' * (2 * dpop._P256_COORD_LEN), b'data')

    def test_verify_es256_valid_signature(self):
        key = make_key()
        der = key.sign(b'data', ec.ECDSA(hashes.SHA256()))
        r, s = decode_dss_signature(der)
        raw = r.to_bytes(32, 'big') + s.to_bytes(32, 'big')
        # Should not raise.
        dpop._verify_es256(key.public_key(), raw, b'data')

    def test_str_eq(self):
        self.assertTrue(dpop._str_eq('abc', 'abc'))
        self.assertFalse(dpop._str_eq('abc', 'abd'))
        self.assertFalse(dpop._str_eq('abc', 'ab'))
        self.assertFalse(dpop._str_eq(None, 'abc'))
        self.assertFalse(dpop._str_eq(123, '123'))


class TestParseAndVerify(unittest.TestCase):
    def setUp(self):
        self.key = make_key()
        self.now = dpop.now_epoch()

    def parse(self, proof, **kwargs):
        kwargs.setdefault('now', self.now)
        return dpop.parse_and_verify(proof, HTM, HTU, **kwargs)

    def test_valid_proof(self):
        proof = make_proof(self.key, iat=self.now, jti='abc')
        tp, jti = self.parse(proof)
        self.assertEqual(tp, dpop.jwk_thumbprint(public_jwk(self.key)))
        self.assertEqual(jti, 'abc')

    def test_valid_proof_bytes_input(self):
        proof = make_proof(self.key, iat=self.now).encode()
        tp, _ = self.parse(proof)
        self.assertEqual(tp, dpop.jwk_thumbprint(public_jwk(self.key)))

    def test_htm_case_insensitive(self):
        proof = make_proof(self.key, iat=self.now, htm='post')
        # Should not raise despite lowercase method.
        self.parse(proof)

    def test_thumbprint_binding_ok(self):
        proof = make_proof(self.key, iat=self.now)
        tp = dpop.jwk_thumbprint(public_jwk(self.key))
        self.parse(proof, thumbprint=tp)

    def test_thumbprint_binding_mismatch(self):
        proof = make_proof(self.key, iat=self.now)
        self.assertRaises(errors.InvalidDPoP, self.parse,
                          proof, thumbprint='wrong-thumbprint')

    def test_ath_binding_ok(self):
        ath = dpop.compute_ath('token')
        proof = make_proof(self.key, iat=self.now, ath=ath)
        self.parse(proof, ath=ath)

    def test_ath_binding_mismatch(self):
        proof = make_proof(self.key, iat=self.now, ath=dpop.compute_ath('token'))
        self.assertRaises(errors.InvalidDPoP, self.parse,
                          proof, ath=dpop.compute_ath('other'))

    def test_ath_missing_when_required(self):
        proof = make_proof(self.key, iat=self.now)
        self.assertRaises(errors.InvalidDPoP, self.parse,
                          proof, ath=dpop.compute_ath('token'))

    def test_empty_proof(self):
        self.assertRaises(errors.InvalidDPoP, self.parse, '')
        self.assertRaises(errors.InvalidDPoP, self.parse, None)

    def test_wrong_number_of_parts(self):
        self.assertRaises(errors.InvalidDPoP, self.parse, 'a.b')
        self.assertRaises(errors.InvalidDPoP, self.parse, 'a.b.c.d')

    def test_non_base64_segments(self):
        self.assertRaises(errors.InvalidDPoP, self.parse, '!!!.@@@.###')

    def test_header_not_json_object(self):
        proof = make_proof(self.key, iat=self.now, header=['not', 'a', 'dict'])
        self.assertRaises(errors.InvalidDPoP, self.parse, proof)

    def test_payload_not_json_object(self):
        proof = make_proof(self.key, iat=self.now, payload=[1, 2, 3])
        self.assertRaises(errors.InvalidDPoP, self.parse, proof)

    def _header_with(self, **overrides):
        header = {
            'typ': dpop.DPOP_TYP,
            'alg': dpop.DPOP_ALG,
            'jwk': public_jwk(self.key),
        }
        header.update(overrides)
        return header

    def test_wrong_typ(self):
        proof = make_proof(self.key, iat=self.now, header=self._header_with(typ='jwt'))
        self.assertRaises(errors.InvalidDPoP, self.parse, proof)

    def test_wrong_alg(self):
        proof = make_proof(self.key, iat=self.now, header=self._header_with(alg='RS256'))
        self.assertRaises(errors.InvalidDPoP, self.parse, proof)

    def test_jwk_missing(self):
        header = {'typ': dpop.DPOP_TYP, 'alg': dpop.DPOP_ALG}
        proof = make_proof(self.key, iat=self.now, header=header)
        self.assertRaises(errors.InvalidDPoP, self.parse, proof)

    def test_jwk_wrong_kty(self):
        jwk = public_jwk(self.key)
        jwk['kty'] = 'RSA'
        proof = make_proof(self.key, iat=self.now, header=self._header_with(jwk=jwk))
        self.assertRaises(errors.InvalidDPoP, self.parse, proof)

    def test_jwk_wrong_crv(self):
        jwk = public_jwk(self.key)
        jwk['crv'] = 'P-384'
        proof = make_proof(self.key, iat=self.now, header=self._header_with(jwk=jwk))
        self.assertRaises(errors.InvalidDPoP, self.parse, proof)

    def test_jwk_non_string_coordinates(self):
        jwk = public_jwk(self.key)
        jwk['x'] = 123
        proof = make_proof(self.key, iat=self.now, header=self._header_with(jwk=jwk))
        self.assertRaises(errors.InvalidDPoP, self.parse, proof)

    def test_jwk_with_private_component_rejected(self):
        jwk = public_jwk(self.key)
        jwk['d'] = 'secret'
        proof = make_proof(self.key, iat=self.now, header=self._header_with(jwk=jwk))
        self.assertRaises(errors.InvalidDPoP, self.parse, proof)

    def test_signature_from_other_key(self):
        # Header embeds self.key's JWK but the proof is signed by a different key.
        other = make_key()
        proof = make_proof(self.key, iat=self.now, signing_key=other)
        self.assertRaises(errors.InvalidDPoP, self.parse, proof)

    def test_tampered_payload(self):
        proof = make_proof(self.key, iat=self.now)
        header_b64, payload_b64, sig_b64 = proof.split('.')
        forged = json.loads(dpop.b64url_decode(payload_b64))
        forged['jti'] = 'tampered'
        payload_b64 = _b64url(json.dumps(forged).encode())
        self.assertRaises(errors.InvalidDPoP, self.parse,
                          header_b64 + '.' + payload_b64 + '.' + sig_b64)

    def test_wrong_htm(self):
        proof = make_proof(self.key, iat=self.now, htm='GET')
        self.assertRaises(errors.InvalidDPoP, self.parse, proof)

    def test_wrong_htu(self):
        proof = make_proof(self.key, iat=self.now, htu='/api/evil')
        self.assertRaises(errors.InvalidDPoP, self.parse, proof)

    def test_iat_not_int(self):
        proof = make_proof(self.key, payload={'htm': HTM, 'htu': HTU,
                                              'iat': 'soon', 'jti': 'x'})
        self.assertRaises(errors.InvalidDPoP, self.parse, proof)

    def test_iat_bool_rejected(self):
        proof = make_proof(self.key, payload={'htm': HTM, 'htu': HTU,
                                              'iat': True, 'jti': 'x'})
        self.assertRaises(errors.InvalidDPoP, self.parse, proof)

    def test_iat_too_old(self):
        proof = make_proof(self.key, iat=self.now - dpop.PROOF_MAX_AGE - 1)
        self.assertRaises(errors.InvalidDPoP, self.parse, proof)

    def test_iat_too_far_in_future(self):
        proof = make_proof(self.key, iat=self.now + dpop.PROOF_MAX_FUTURE + 1)
        self.assertRaises(errors.InvalidDPoP, self.parse, proof)

    def test_iat_at_window_edges_ok(self):
        self.parse(make_proof(self.key, iat=self.now - dpop.PROOF_MAX_AGE))
        self.parse(make_proof(self.key, iat=self.now + dpop.PROOF_MAX_FUTURE))

    def test_iat_defaults_to_now_when_not_provided(self):
        # parse_and_verify computes now via now_epoch() when now is None.
        proof = make_proof(self.key, iat=dpop.now_epoch())
        dpop.parse_and_verify(proof, HTM, HTU)

    def test_jti_missing(self):
        proof = make_proof(self.key, payload={'htm': HTM, 'htu': HTU, 'iat': self.now})
        self.assertRaises(errors.InvalidDPoP, self.parse, proof)

    def test_jti_empty(self):
        proof = make_proof(self.key, iat=self.now, jti='')
        self.assertRaises(errors.InvalidDPoP, self.parse, proof)

    def test_jti_not_string(self):
        proof = make_proof(self.key, payload={'htm': HTM, 'htu': HTU,
                                              'iat': self.now, 'jti': 1})
        self.assertRaises(errors.InvalidDPoP, self.parse, proof)


class TestVerifyDPoPProof(helpers.TestGL):
    @inlineCallbacks
    def setUp(self):
        yield helpers.TestGL.setUp(self)
        self.key = make_key()
        State.dpop_jti.clear()

    def test_valid_proof_returns_thumbprint(self):
        proof = make_proof(self.key, jti='unique-1')
        tp = dpop.verify_dpop_proof(proof, HTM, HTU)
        self.assertEqual(tp, dpop.jwk_thumbprint(public_jwk(self.key)))

    def test_jti_is_recorded(self):
        proof = make_proof(self.key, jti='unique-2')
        dpop.verify_dpop_proof(proof, HTM, HTU)
        self.assertIn('unique-2', State.dpop_jti)

    def test_replay_is_rejected(self):
        proof = make_proof(self.key, jti='replayed')
        dpop.verify_dpop_proof(proof, HTM, HTU)
        self.assertRaises(errors.InvalidDPoP,
                          dpop.verify_dpop_proof, proof, HTM, HTU)

    def test_distinct_jti_accepted(self):
        dpop.verify_dpop_proof(make_proof(self.key, jti='a'), HTM, HTU)
        # A second, distinct proof from the same key is accepted.
        dpop.verify_dpop_proof(make_proof(self.key, jti='b'), HTM, HTU)

    def test_invalid_proof_does_not_record_jti(self):
        proof = make_proof(self.key, jti='bad', htm='GET')
        self.assertRaises(errors.InvalidDPoP,
                          dpop.verify_dpop_proof, proof, HTM, HTU)
        self.assertNotIn('bad', State.dpop_jti)
