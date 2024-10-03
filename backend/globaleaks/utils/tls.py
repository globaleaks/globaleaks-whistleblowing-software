# -*- coding: utf-8 -*-
import ipaddress
import re

from cryptography import x509
from cryptography.x509.oid import NameOID
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec, rsa
from cryptography.hazmat.backends import default_backend

from OpenSSL import SSL
from OpenSSL._util import lib as _lib
from OpenSSL.crypto import load_certificate, load_privatekey, FILETYPE_PEM, \
    dump_certificate_request, X509Req

from twisted.internet import ssl

from globaleaks.utils.utility import datetime_never, datetime_now
from globaleaks.utils.log import log


# OpenSSL mocks
SSL.OP_SINGLE_ECDH_USE = 0x00080000
SSL.OP_NO_RENEGOTIATION = 0x40000000
SSL.OP_PRIORITIZE_CHACHA = 0x00200000
SSL.OP_CLEANSE_PLAINTEXT = 0x00000002

TLS_CIPHER_LIST = b'TLS13-AES-256-GCM-SHA384:' \
                  b'TLS13-CHACHA20-POLY1305-SHA256:' \
                  b'TLS13-AES-128-GCM-SHA256:' \
                  b'ECDHE-ECDSA-AES256-GCM-SHA384:' \
                  b'ECDHE-RSA-AES256-GCM-SHA384:' \
                  b'ECDHE-ECDSA-CHACHA20-POLY1305:' \
                  b'ECDHE-RSA-CHACHA20-POLY1305:' \
                  b'ECDHE-ECDSA-AES128-GCM-SHA256:' \
                  b'ECDHE-RSA-AES128-GCM-SHA256'


trustRoot = ssl.platformTrust()


class ValidationException(Exception):
    pass


def gen_rsa_key(bits):
    key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=bits,
        backend=default_backend()
    )

    key = key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )

    return key


def gen_ecc_key():
    key = ec.generate_private_key(ec.SECP384R1(), default_backend())

    key = key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )

    return key


def gen_x509_csr_pem(key_pair, csr_fields, csr_sign_bits):
    req = gen_x509_csr(key_pair, csr_fields, csr_sign_bits)
    pem_csr = dump_certificate_request(SSL.FILETYPE_PEM, req)
    return pem_csr


def gen_selfsigned_certificate(hostname="127.0.0.1", ip="127.0.0.1"):
    """Generates self signed certificate for localhost and 127.0.0.1."""
    key = ec.generate_private_key(ec.SECP384R1(), default_backend())

    name = x509.Name([
        x509.NameAttribute(NameOID.COMMON_NAME, hostname)
    ])

    alt_names = [x509.DNSName(hostname)]

    alt_names.append(x509.DNSName(ip))
    alt_names.append(x509.IPAddress(ipaddress.ip_address(ip)))

    san = x509.SubjectAlternativeName(alt_names)

    # path_len=0 means this cert can only sign itself, not other certs.
    basic_contraints = x509.BasicConstraints(ca=True, path_length=0)

    cert = (
        x509.CertificateBuilder()
        .subject_name(name)
        .issuer_name(name)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(datetime_now())
        .not_valid_after(datetime_never())
        .add_extension(basic_contraints, False)
        .add_extension(san, False)
        .sign(key, hashes.SHA256(), default_backend())
    )

    cert_pem = cert.public_bytes(encoding=serialization.Encoding.PEM)

    key_pem = key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.TraditionalOpenSSL,
        encryption_algorithm=serialization.NoEncryption(),
    )

    return key_pem, cert_pem

def gen_x509_csr(key_pair, csr_fields, csr_sign_bits):
    """
    gen_x509_csr creates a certificate signature request by applying the passed
    fields to the subject of the request, attaches the public key's fingerprint
    and signs the request using the private key.

    csr_fields dictionary and generates a
    certificate request using the passed keypair. Note that the default digest
    is sha256.

    :param csr_sign_bits:
    :param key_pair: A key pair that will sign the request
    :type key_pair: :py:data:`OpenSSL.crypto.PKey` the key must have an attached
    private component.

    :param csr_fields: A certifcate issuer's details in X.509 Distinguished
    Name format.
    :type csr_fields: :py:data:`dict`
        C     - Country name
        ST    - State or province name
        L     - Locality name
        O     - Organization name
        OU    - Organizational unit name
        CN    - Common name
        emailAddress - E-mail address

    :rtype: A `pyopenssl.OpenSSL.crypto.X509Req`
    """
    req = X509Req()
    subj = req.get_subject()

    for field, value in csr_fields.items():
        if value:
            setattr(subj, field, value)

    prv_key = load_privatekey(SSL.FILETYPE_PEM, key_pair)

    req.set_pubkey(prv_key)
    req.sign(prv_key, 'sha'+str(csr_sign_bits))

    return req


def parse_issuer_name(x509):
    """Returns the issuer's name from a `OpenSSL.crypto.X509` cert"""
    name = x509.get_issuer()
    if name.O is not None:
        return name.organizationName
    elif name.OU is not None:
        return name.organizationalUnitName
    elif name.CN is not None:
        return name.commonName
    elif name.emailAddress is not None:
        return name.emailAddress
    else:
        return ''


def split_pem_chain(s):
    """Splits an ascii armored cert chain into a list of strings which could be valid certs"""
    gex_str = r"-----BEGIN CERTIFICATE-----\r?.+?\r?-----END CERTIFICATE-----\r?\n?"
    gex = re.compile(gex_str, re.DOTALL)

    try:
        if isinstance(s, bytes):
            s = s.decode()

        return [m.group(0) for m in gex.finditer(s)]
    except UnicodeDecodeError:
        return None


def new_tls_server_context():
    ctx = SSL.Context(SSL.SSLv23_METHOD)

    ctx.set_options(SSL.OP_NO_SSLv2 |
                    SSL.OP_NO_SSLv3 |
                    SSL.OP_NO_TLSv1 |
                    SSL.OP_NO_TLSv1_1 |
                    SSL.OP_CIPHER_SERVER_PREFERENCE |
                    SSL.OP_PRIORITIZE_CHACHA |
                    SSL.OP_SINGLE_ECDH_USE |
                    SSL.OP_NO_COMPRESSION |
                    SSL.OP_NO_RENEGOTIATION)

    ctx.set_mode(SSL.MODE_RELEASE_BUFFERS)
    ctx.set_session_cache_mode(SSL.SESS_CACHE_SERVER)

    ctx.set_cipher_list(TLS_CIPHER_LIST)

    return ctx


def new_tls_client_context():
    ctx = SSL.Context(SSL.SSLv23_METHOD)

    ctx.set_options(SSL.OP_NO_SSLv2 |
                    SSL.OP_NO_SSLv3 |
                    SSL.OP_NO_TLSv1 |
                    SSL.OP_NO_TLSv1_1 |
                    SSL.OP_SINGLE_ECDH_USE |
                    SSL.OP_NO_COMPRESSION |
                    SSL.OP_NO_RENEGOTIATION |
                    SSL.OP_CLEANSE_PLAINTEXT)

    ctx.set_mode(SSL.MODE_RELEASE_BUFFERS)
    ctx.set_session_cache_mode(SSL.SESS_CACHE_OFF)

    # It'd be nice if pyOpenSSL let us pass None here for this behavior (as
    # the underlying OpenSSL API call allows NULL to be passed).  It
    # doesn't, so we'll supply a function which does the same thing.
    def _verifyCallback(conn, cert, errno, depth, ok):
        if not ok:
            log.err("Unable to verify validity of certificate: %s" % cert.get_subject())

        return ok

    ctx.set_verify(SSL.VERIFY_PEER, _verifyCallback)
    ctx.set_verify_depth(100)

    trustRoot._addCACertsToContext(ctx)

    return ctx


class TLSServerContextFactory(ssl.ContextFactory):
    def __init__(self, key, certificate, intermediate):
        """
        :param key: String representation of the private key
        :param certificate: String representation of the certificate
        :param intermediate: String representation of the intermediate file
        """
        self.ctx = new_tls_server_context()

        x509 = load_certificate(FILETYPE_PEM, certificate)
        self.ctx.use_certificate(x509)

        if intermediate:
            for c in split_pem_chain(intermediate):
                x509 = load_certificate(FILETYPE_PEM, c)
                self.ctx.add_extra_chain_cert(x509)

        key = load_privatekey(FILETYPE_PEM, key)
        self.ctx.use_privatekey(key)

        try:
            _lib.SSL_CTX_set_ecdh_auto(self.ctx._context, 1)  # pylint: disable=no-member
        except AttributeError:
            # The function is present and should be run only in older version of OpenSSL
            pass

    def getContext(self):
        return self.ctx


class TLSClientContextFactory(ssl.ClientContextFactory):
    def getContext(self):
        return new_tls_client_context()


class CtxValidator(object):
    parents = []

    def _validate_parents(self, cfg, ctx, check_expiration):
        for parent in self.parents:
            p_v = parent()
            p_v._validate(cfg, ctx, check_expiration)

    def _validate(self, cfg, ctx, check_expiration):
        raise NotImplementedError()

    def validate(self, cfg, check_expiration=True):
        """
        Checks the validity of the passed config for usage in an OpenSSLContext

        :param cfg: A `dict` composed of SSL material
        :param must_be_disabled: A flag to toggle checking of https_enabled
        :param check_expiration: A flag to toggle certificate expiration checks

        :rtype: A tuple of (Bool, Exception) where True, None signifies success

        """
        ctx = new_tls_server_context()

        try:
            self._validate_parents(cfg, ctx, check_expiration)
            self._validate(cfg, ctx, check_expiration)
        except Exception as err:
            return False, err

        return True, None


class KeyValidator(CtxValidator):
    parents = []

    def _validate(self, cfg, ctx, check_expiration):
        raw_str = cfg['ssl_key']
        if not raw_str:
            raise ValidationException('No private key is set')

        # Note that the empty string here prevents valid PKCS8 encrypted
        # keys from being used instead of plain pem keys.
        key = load_privatekey(FILETYPE_PEM, raw_str, passphrase=b"")

        ctx.use_privatekey(key)


class CertValidator(CtxValidator):
    parents = [KeyValidator]

    def _validate(self, cfg, ctx, check_expiration):
        if not cfg['hostname']:
            raise ValidationException('No hostname set')

        certificate = cfg['ssl_cert']
        if not certificate:
            raise ValidationException('There is no certificate')

        certs = split_pem_chain(certificate)
        if len(certs) != 1:
            raise ValidationException('Invalid certificate')

        x509 = load_certificate(FILETYPE_PEM, certificate)

        if check_expiration and x509.has_expired():
            raise ValidationException('The certficate has expired')

        ctx.use_certificate(x509)

        ctx.check_privatekey()


class ChainValidator(CtxValidator):
    parents = [KeyValidator, CertValidator]

    def _validate(self, cfg, ctx, check_expiration):
        store = ctx.get_cert_store()

        chain = split_pem_chain(cfg['ssl_intermediate'])

        if cfg['ssl_intermediate'] == cfg['ssl_cert']:
            raise ValidationException('Invalid certificate chain')

        for cert in chain:
            x509 = load_certificate(FILETYPE_PEM, cert)

            if check_expiration and x509.has_expired():
                raise ValidationException('An intermediate certificate has expired')

            store.add_cert(x509)
