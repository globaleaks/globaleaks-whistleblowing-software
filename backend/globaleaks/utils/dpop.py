#
# Verification of DPoP proofs (RFC 9449 - OAuth 2.0 Demonstrating Proof of
# Possession). GlobaLeaks binds every session to an ECDSA P-256 key pair that
# the client generates at login with WebCrypto (non-extractable private key).
# Each request carries a `DPoP` header: a JWS (ES256) whose header embeds the
# public JWK and whose payload proves possession of the matching private key for
# the specific HTTP method and path.
#
# Variation from RFC 9449: the proof binds only the request path (htu) and not
# the full request URI (scheme + host + path). While the GlobaLeaks threat model
# recommends against fronting the service with reverse proxies, in practice it is
# widely deployed behind them (TLS terminators, load balancers, onion/reverse
# proxies) that rewrite the scheme and Host the backend observes so that they no
# longer match the origin the browser signed. Binding scheme/host would make
# every such deployment fail verification for no security gain: the proof's job
# is to bind a request to its session key, and the session is already statically
# bound to a tenant server-side, so the scheme/host carry no authorization the
# path does not.
import base64
import calendar
import hashlib
import json
from types import SimpleNamespace

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.asymmetric.utils import encode_dss_signature
from cryptography.hazmat.primitives.constant_time import bytes_eq

from globaleaks.rest import errors
from globaleaks.utils.utility import datetime_now

# Acceptance window for the proof `iat` claim, in seconds. A proof may be at
# most PROOF_MAX_AGE seconds old and at most PROOF_MAX_FUTURE seconds in the
# future (to tolerate limited clock skew between client and server).
PROOF_MAX_AGE = 120
PROOF_MAX_FUTURE = 30

# Required JOSE header values for a DPoP proof.
DPOP_TYP = 'dpop+jwt'
DPOP_ALG = 'ES256'

# P-256 field/coordinate size in bytes; a raw ES256 signature is exactly twice
# this (R || S).
_P256_COORD_LEN = 32


def b64url_decode(data):
    """Decode unpadded base64url (str or bytes) to bytes."""
    if isinstance(data, str):
        data = data.encode()

    return base64.urlsafe_b64decode(data + b'=' * (-len(data) % 4))


def b64url_encode(data):
    """Encode bytes to unpadded base64url (str)."""
    return base64.urlsafe_b64encode(data).rstrip(b'=').decode()


def now_epoch():
    """Current time as Unix epoch seconds, honoring the naive-UTC convention."""
    return calendar.timegm(datetime_now().utctimetuple())


def compute_ath(access_token):
    """Compute the RFC 9449 `ath` claim: base64url(SHA-256(access_token))."""
    if isinstance(access_token, str):
        access_token = access_token.encode()

    return b64url_encode(hashlib.sha256(access_token).digest())


def jwk_thumbprint(jwk):
    """
    Compute the RFC 7638 JWK thumbprint of an EC public key as base64url.

    For kty=EC the canonical JSON contains exactly the members crv, kty, x, y
    in lexicographic order, with no whitespace.
    """
    canonical = '{{"crv":"{}","kty":"EC","x":"{}","y":"{}"}}'.format(jwk['crv'], jwk['x'], jwk['y'])
    return b64url_encode(hashlib.sha256(canonical.encode()).digest())


def jwk_to_public_key(jwk):
    """Build a cryptography EC public key from a P-256 public JWK."""
    try:
        x = int.from_bytes(b64url_decode(jwk['x']), 'big')
        y = int.from_bytes(b64url_decode(jwk['y']), 'big')
        return ec.EllipticCurvePublicNumbers(x, y, ec.SECP256R1()).public_key()
    except Exception:
        raise errors.InvalidDPoP


def _verify_es256(public_key, signature, signing_input):
    """Verify a raw (R||S) ES256 signature; raise InvalidDPoP on failure."""
    if len(signature) != 2 * _P256_COORD_LEN:
        raise errors.InvalidDPoP

    r = int.from_bytes(signature[:_P256_COORD_LEN], 'big')
    s = int.from_bytes(signature[_P256_COORD_LEN:], 'big')

    try:
        public_key.verify(encode_dss_signature(r, s), signing_input, ec.ECDSA(hashes.SHA256()))
    except InvalidSignature:
        raise errors.InvalidDPoP


def _str_eq(a, b):
    """Constant-time comparison of two strings."""
    if not isinstance(a, str):
        return False

    return bytes_eq(a.encode(), b.encode())


def parse_and_verify(proof, htm, htu, *, thumbprint=None, ath=None, now=None):
    """
    Parse and cryptographically verify a DPoP proof without replay protection.

    Validates the JOSE header, the ES256 signature against the embedded public
    JWK, and the htm/htu/iat claims (plus ath/thumbprint when provided).

    :return: a (thumbprint, jti) tuple, where thumbprint is the RFC 7638
             thumbprint of the proof's public key.
    :raises errors.InvalidDPoP: on any malformed or invalid proof.
    """
    if not proof:
        raise errors.InvalidDPoP

    if isinstance(proof, bytes):
        proof = proof.decode()

    parts = proof.split('.')
    if len(parts) != 3:
        raise errors.InvalidDPoP

    try:
        header = json.loads(b64url_decode(parts[0]))
        payload = json.loads(b64url_decode(parts[1]))
        signature = b64url_decode(parts[2])
    except Exception:
        raise errors.InvalidDPoP

    if not isinstance(header, dict) or not isinstance(payload, dict):
        raise errors.InvalidDPoP

    # JOSE header
    if header.get('typ') != DPOP_TYP or header.get('alg') != DPOP_ALG:
        raise errors.InvalidDPoP

    jwk = header.get('jwk')
    if not isinstance(jwk, dict) or \
       jwk.get('kty') != 'EC' or jwk.get('crv') != 'P-256' or \
       not isinstance(jwk.get('x'), str) or not isinstance(jwk.get('y'), str) or \
       'd' in jwk:
        # The proof must embed only the public key (RFC 9449 4.3): reject a JWK
        # that carries the private component.
        raise errors.InvalidDPoP

    # Signature
    public_key = jwk_to_public_key(jwk)
    _verify_es256(public_key, signature, (parts[0] + '.' + parts[1]).encode())

    # Claims: method and URI binding
    if str(payload.get('htm', '')).upper() != htm.upper():
        raise errors.InvalidDPoP

    if payload.get('htu') != htu:
        raise errors.InvalidDPoP

    # Claims: freshness
    iat = payload.get('iat')
    if not isinstance(iat, int) or isinstance(iat, bool):
        raise errors.InvalidDPoP

    if now is None:
        now = now_epoch()

    if iat < now - PROOF_MAX_AGE or iat > now + PROOF_MAX_FUTURE:
        raise errors.InvalidDPoP

    jti = payload.get('jti')
    if not isinstance(jti, str) or not jti:
        raise errors.InvalidDPoP

    # Claims: token binding
    if ath is not None and not _str_eq(payload.get('ath', ''), ath):
        raise errors.InvalidDPoP

    # Key binding
    tp = jwk_thumbprint(jwk)
    if thumbprint is not None and not _str_eq(tp, thumbprint):
        raise errors.InvalidDPoP

    return tp, jti


def verify_dpop_proof(proof, htm, htu, *, thumbprint=None, ath=None):
    """
    Fully verify a DPoP proof, including single-use (jti) replay protection.

    :return: the RFC 7638 thumbprint of the proof's public key.
    :raises errors.InvalidDPoP: on any malformed, invalid or replayed proof.
    """
    tp, jti = parse_and_verify(proof, htm, htu, thumbprint=thumbprint, ath=ath)

    # Imported lazily to avoid a circular import (state imports handlers utils).
    from globaleaks.state import State  # noqa: PLC0415

    if jti in State.dpop_jti:
        raise errors.InvalidDPoP

    State.dpop_jti[jti] = SimpleNamespace()

    return tp
