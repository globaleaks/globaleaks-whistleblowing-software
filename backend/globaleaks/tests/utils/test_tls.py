import os

from cryptography import x509
from cryptography.hazmat.primitives import serialization

from OpenSSL import crypto, SSL
from OpenSSL.crypto import load_certificate, FILETYPE_PEM

from twisted.trial import unittest

from globaleaks.tests import helpers
from globaleaks.utils import tls




class TestObjectValidators(unittest.TestCase):
    def __init__(self, *args, **kwargs):
        super(TestObjectValidators, self).__init__(*args, **kwargs)
        self.test_data_dir = os.path.join(helpers.DATA_DIR, 'https')

        self.invalid_files = [
            'empty.txt',
            # Invalid pem string
            'noise.pem',
            # Raw bytes
            'bytes.out',
            # A certificate signing request
            'random_csr.pem',
            # Mangled ASN.1 RSA key
            'garbage_key.pem',
            # DER formatted key
            'rsa_key.der',
            # PKCS8 encrypted private key
            'rsa_key_monalisa_pass.pem'
        ]

    def setUp(self):
        self.cfg = {
            'key': '',
            'cert': '',
            'chain': '',
            'ssl_intermediate': '',
            'https_enabled': False,
            'hostname': '127.0.0.1:9999',
        }

    def test_private_key_invalid(self):
        pkv = tls.KeyValidator()

        for fname in self.invalid_files:
            p = os.path.join(self.test_data_dir, 'invalid', fname)
            with open(p, 'rb') as f:
                self.cfg['ssl_key'] = f.read()
            ok, err = pkv.validate(self.cfg)
            self.assertFalse(ok)
            self.assertIsNotNone(err)

    def test_private_key_valid(self):
        pkv = tls.KeyValidator()

        good_keys = [
            'key.pem'
        ]

        for fname in good_keys:
            p = os.path.join(self.test_data_dir, 'valid', fname)
            with open(p, 'r') as f:
                self.cfg['ssl_key'] = f.read()
            ok, err = pkv.validate(self.cfg)
            self.assertTrue(ok)
            self.assertIsNone(err)

    def test_cert_invalid(self):
        crtv = tls.CertValidator()

        self.cfg['ssl_key'] = helpers.HTTPS_DATA['key']

        for fname in self.invalid_files:
            p = os.path.join(self.test_data_dir, 'invalid', fname)
            with open(p, 'rb') as f:
                self.cfg['ssl_cert'] = f.read()
            ok, err = crtv.validate(self.cfg)
            self.assertFalse(ok)
            self.assertIsNotNone(err)

    def test_cert_valid(self):
        crtv = tls.CertValidator()

        good_certs = [
            'cert.pem'
        ]

        self.cfg['ssl_key'] = helpers.HTTPS_DATA['key']

        for fname in good_certs:
            p = os.path.join(self.test_data_dir, 'valid', fname)
            with open(p, 'rb') as f:
                self.cfg['ssl_cert'] = f.read()
            ok, err = crtv.validate(self.cfg)
            self.assertTrue(ok)
            self.assertIsNone(err)

    def test_duplicated_cert_as_chain(self):
        chn_v = tls.ChainValidator()

        self.cfg['ssl_key'] = helpers.HTTPS_DATA['key'].encode()
        self.cfg['ssl_cert'] = helpers.HTTPS_DATA['cert'].encode()

        self.cfg['ssl_intermediate'] = helpers.HTTPS_DATA['cert'].encode()

        ok, err = chn_v.validate(self.cfg)
        self.assertFalse(ok)
        self.assertIsNotNone(err)

    def test_chain_valid(self):
        chn_v = tls.ChainValidator()

        self.cfg['ssl_key'] = helpers.HTTPS_DATA['key'].encode()
        self.cfg['ssl_cert'] = helpers.HTTPS_DATA['cert'].encode()

        p = os.path.join(self.test_data_dir, 'valid', 'chain.pem')
        with open(p, 'rb') as f:
            self.cfg['ssl_intermediate'] = f.read()

        ok, err = chn_v.validate(self.cfg)
        self.assertTrue(ok)
        self.assertIsNone(err)

    def test_check_expiration(self):
        chn_v = tls.ChainValidator()

        self.cfg['ssl_key'] = helpers.HTTPS_DATA['key'].encode()

        p = os.path.join(self.test_data_dir, 'invalid/expired_cert_with_valid_prv.pem')
        with open(p, 'rb') as f:
            self.cfg['ssl_cert'] = f.read()

        ok, err = chn_v.validate(self.cfg, check_expiration=True)
        self.assertFalse(ok)
        self.assertTrue(isinstance(err, tls.ValidationException))

    def test_get_issuer_name(self):
        test_cases = [
            ('invalid/le-staging-chain.pem', 'Fake LE Root X1'),
            ('invalid/glbc_le_stage_cert.pem', 'Fake LE Intermediate X1'),
            ('invalid/expired_cert.pem', 'Zintermediate'),
            ('valid/cert.pem', 'Whistleblowing Solutions I.S. S.r.l.'),
        ]
        for cert_path, issuer_name in test_cases:
            p = os.path.join(self.test_data_dir, cert_path)
            with open(p, 'r') as f:
                x509 = crypto.load_certificate(FILETYPE_PEM, f.read())

            res = tls.parse_issuer_name(x509)

            self.assertEqual(res, issuer_name)

    def test_split_pem_chain(self):
        test_cases = [
            ('invalid/bytes.out', 0),
            ('invalid/garbage_key.pem', 0),
            ('invalid/glbc_le_stage_cert.pem', 1),
            ('invalid/expired_cert.pem', 1),
            ('invalid/le-staging-chain.pem', 1),
            ('valid/chain.pem', 2),
        ]

        for chain_path, chain_len in test_cases:
            p = os.path.join(self.test_data_dir, chain_path)
            with open(p, 'rb') as f:
                chain = tls.split_pem_chain(f.read())

            calced_chain_len = 0
            if chain is not None:
                calced_chain_len = len(chain)

            self.assertEqual(calced_chain_len, chain_len)


class TestKeyGeneration(unittest.TestCase):
    def test_gen_rsa_key_returns_valid_pem(self):
        """gen_rsa_key produces a parseable RSA private key in PEM form."""
        # Use 2048 to keep the test fast (4096 is too slow for CI)
        pem = tls.gen_rsa_key(2048)
        self.assertIn(b'-----BEGIN PRIVATE KEY-----', pem)
        key = serialization.load_pem_private_key(pem, password=None)
        # Should be usable as an RSA key
        self.assertEqual(key.key_size, 2048)

    def test_gen_ecc_key_returns_valid_pem(self):
        """gen_ecc_key produces a parseable EC private key on SECP384R1."""
        pem = tls.gen_ecc_key()
        self.assertIn(b'-----BEGIN PRIVATE KEY-----', pem)
        key = serialization.load_pem_private_key(pem, password=None)
        self.assertEqual(key.curve.name, 'secp384r1')


class TestSelfSignedCertificate(unittest.TestCase):
    def test_gen_selfsigned_certificate_default(self):
        """The default self-signed cert validates for 127.0.0.1 / localhost."""
        key_pem, cert_pem = tls.gen_selfsigned_certificate()
        self.assertIn(b'-----BEGIN CERTIFICATE-----', cert_pem)
        cert = x509.load_pem_x509_certificate(cert_pem)
        cn = cert.subject.get_attributes_for_oid(x509.NameOID.COMMON_NAME)[0].value
        self.assertEqual(cn, "127.0.0.1")

    def test_gen_selfsigned_certificate_custom_hostname(self):
        key_pem, cert_pem = tls.gen_selfsigned_certificate("test.local", "10.0.0.1")
        cert = x509.load_pem_x509_certificate(cert_pem)
        cn = cert.subject.get_attributes_for_oid(x509.NameOID.COMMON_NAME)[0].value
        self.assertEqual(cn, "test.local")
        san = cert.extensions.get_extension_for_class(x509.SubjectAlternativeName).value
        names = san.get_values_for_type(x509.DNSName)
        self.assertIn("test.local", names)


class TestX509CSR(unittest.TestCase):
    def test_gen_x509_csr_pem_contains_subject_fields(self):
        """gen_x509_csr_pem produces a parseable CSR and copies subject fields."""
        key_pem = tls.gen_rsa_key(2048)
        csr_fields = {
            'C': 'IT',
            'ST': 'Lombardia',
            'L': 'Milano',
            'O': 'TestOrg',
            'OU': 'TestUnit',
            'CN': 'example.test',
            'emailAddress': 'admin@example.test',
        }
        # sha256 → bits = 256
        csr_pem = tls.gen_x509_csr_pem(key_pem, csr_fields, 256)
        self.assertIn(b'-----BEGIN CERTIFICATE REQUEST-----', csr_pem)

        csr = x509.load_pem_x509_csr(csr_pem)
        subj = {attr.oid._name: attr.value for attr in csr.subject}
        self.assertEqual(subj.get('commonName'), 'example.test')
        self.assertEqual(subj.get('organizationName'), 'TestOrg')
        self.assertEqual(subj.get('countryName'), 'IT')

    def test_gen_x509_csr_skips_empty_fields(self):
        """Empty values in csr_fields must not be applied to the subject."""
        key_pem = tls.gen_rsa_key(2048)
        csr_fields = {'CN': 'only.cn', 'O': ''}  # empty O is skipped
        csr_pem = tls.gen_x509_csr_pem(key_pem, csr_fields, 256)
        csr = x509.load_pem_x509_csr(csr_pem)
        names = [attr.oid._name for attr in csr.subject]
        self.assertIn('commonName', names)
        self.assertNotIn('organizationName', names)


class TestParseIssuerName(unittest.TestCase):
    """parse_issuer_name has 4 sequential branches: O / OU / CN / emailAddress."""

    def _cert_with_issuer(self, **fields):
        """Build a self-signed cert whose subject (== issuer) contains the given fields."""
        from cryptography.hazmat.primitives.asymmetric import ec
        from cryptography.hazmat.primitives import hashes
        from cryptography.hazmat.backends import default_backend

        oid_map = {
            'O': x509.NameOID.ORGANIZATION_NAME,
            'OU': x509.NameOID.ORGANIZATIONAL_UNIT_NAME,
            'CN': x509.NameOID.COMMON_NAME,
            'emailAddress': x509.NameOID.EMAIL_ADDRESS,
        }
        attrs = [x509.NameAttribute(oid_map[k], v) for k, v in fields.items()]
        name = x509.Name(attrs)
        key = ec.generate_private_key(ec.SECP256R1(), default_backend())

        from globaleaks.utils.utility import datetime_now, datetime_never
        cert = (
            x509.CertificateBuilder()
            .subject_name(name)
            .issuer_name(name)
            .public_key(key.public_key())
            .serial_number(x509.random_serial_number())
            .not_valid_before(datetime_now())
            .not_valid_after(datetime_never())
            .sign(key, hashes.SHA256(), default_backend())
        )
        pem = cert.public_bytes(serialization.Encoding.PEM)
        return load_certificate(FILETYPE_PEM, pem)

    def test_parse_issuer_name_with_O(self):
        x = self._cert_with_issuer(O='Acme Corp', CN='cn.example')
        self.assertEqual(tls.parse_issuer_name(x), 'Acme Corp')

    def test_parse_issuer_name_with_OU_only(self):
        x = self._cert_with_issuer(OU='Engineering')
        self.assertEqual(tls.parse_issuer_name(x), 'Engineering')

    def test_parse_issuer_name_with_CN_only(self):
        x = self._cert_with_issuer(CN='cn.example')
        self.assertEqual(tls.parse_issuer_name(x), 'cn.example')

    def test_parse_issuer_name_with_email_only(self):
        x = self._cert_with_issuer(emailAddress='ca@example.test')
        self.assertEqual(tls.parse_issuer_name(x), 'ca@example.test')


class TestSplitPemChain(unittest.TestCase):
    def test_split_pem_chain_handles_bytes(self):
        _, cert_pem = tls.gen_selfsigned_certificate()
        chain = tls.split_pem_chain(cert_pem)
        self.assertEqual(len(chain), 1)
        self.assertIn('-----BEGIN CERTIFICATE-----', chain[0])

    def test_split_pem_chain_handles_str(self):
        _, cert_pem = tls.gen_selfsigned_certificate()
        chain = tls.split_pem_chain(cert_pem.decode())
        self.assertEqual(len(chain), 1)

    def test_split_pem_chain_multiple_certs(self):
        _, c1 = tls.gen_selfsigned_certificate("a.test", "127.0.0.1")
        _, c2 = tls.gen_selfsigned_certificate("b.test", "127.0.0.2")
        chain = tls.split_pem_chain(c1 + c2)
        self.assertEqual(len(chain), 2)

    def test_split_pem_chain_empty(self):
        self.assertEqual(tls.split_pem_chain(b''), [])

    def test_split_pem_chain_invalid_unicode(self):
        """Raw bytes that can't decode as UTF-8 → returns None."""
        self.assertIsNone(tls.split_pem_chain(b'\xff\xfe\x00\x01garbage'))


class TestTLSContexts(unittest.TestCase):
    def test_new_tls_server_context_returns_ssl_context(self):
        ctx = tls.new_tls_server_context()
        self.assertIsInstance(ctx, SSL.Context)

    def test_new_tls_client_context_returns_ssl_context(self):
        ctx = tls.new_tls_client_context()
        self.assertIsInstance(ctx, SSL.Context)

    def test_TLSClientContextFactory_getContext(self):
        f = tls.TLSClientContextFactory()
        self.assertIsInstance(f.getContext(), SSL.Context)

    def test_TLSServerContextFactory_with_selfsigned(self):
        key_pem, cert_pem = tls.gen_selfsigned_certificate()
        f = tls.TLSServerContextFactory(key_pem, cert_pem, b'')
        self.assertIsInstance(f.getContext(), SSL.Context)

    def test_TLSServerContextFactory_with_intermediate(self):
        """Exercising the intermediate-chain loop path."""
        key_pem, cert_pem = tls.gen_selfsigned_certificate()
        # Use the cert itself as a fake intermediate chain (single PEM)
        f = tls.TLSServerContextFactory(key_pem, cert_pem, cert_pem)
        self.assertIsInstance(f.getContext(), SSL.Context)
