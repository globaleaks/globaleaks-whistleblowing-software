import filecmp
import os
import secrets

from nacl.encoding import Base64Encoder
from nacl.secret import SecretBox
from nacl.utils import random as nacl_random

import globaleaks.utils.crypto as crypto

from globaleaks.settings import Settings
from globaleaks.tests import helpers

CHUNK_SIZE = 4096
password = b'password'
message = b'message'
salt = 'wHMeI9jZ1/hVAfpJliXC3Q=='


class TestCryptoUtils(helpers.TestGL):
    def test_sha256_with_string(self):
        # Known input and output
        input_data = "hello world"
        expected_hash = b'b94d27b9934d3e08a52e52d7da7dabfac484efe37a5380ee9088f7ace2efcde9'
        self.assertEqual(crypto.sha256(input_data), expected_hash)

    def test_sha256_with_bytes(self):
        input_data = b"hello world"
        expected_hash = b'b94d27b9934d3e08a52e52d7da7dabfac484efe37a5380ee9088f7ace2efcde9'
        self.assertEqual(crypto.sha256(input_data), expected_hash)

    def test_sha256_empty_string(self):
        input_data = ""
        expected_hash = b'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855'
        self.assertEqual(crypto.sha256(input_data), expected_hash)

    def test_generate_key(self):
        crypto.GCE.generate_key()

    def test_generate_keypair(self):
        key = crypto.GCE.generate_key()
        prv_key, pub_key = crypto.GCE.generate_keypair()
        prv_key_enc = crypto.GCE.symmetric_encrypt(key, prv_key)
        self.assertEqual(prv_key, crypto.GCE.symmetric_decrypt(key, prv_key_enc))

    def test_derive_key(self):
        crypto.GCE.derive_key(password, salt)

    def test_recovery_key(self):
        prv_key, _ = crypto.GCE.generate_keypair()
        bck_key, rec_key = crypto.GCE.generate_recovery_key(prv_key)
        plain_rec_key = crypto.GCE.asymmetric_decrypt(prv_key, Base64Encoder.decode(rec_key))
        x = crypto.GCE.symmetric_decrypt(plain_rec_key, Base64Encoder.decode(bck_key))
        self.assertEqual(x, prv_key)

    #
    # ─────────────────────────────────────────────────────────────
    #   SYMMETRIC ENCRYPTION (PADDING) TESTS
    # ─────────────────────────────────────────────────────────────
    #

    def test_symmetric_padding_roundtrip(self):
        key = crypto.GCE.generate_key()
        msg = b"hello padded symmetric"
        enc = crypto.GCE.symmetric_encrypt(key, msg)
        dec = crypto.GCE.symmetric_decrypt(key, enc)
        self.assertEqual(dec, msg)

    def test_symmetric_padding_changes_ciphertext_size(self):
        """Repeated symmetric encryptions must produce variable ciphertext sizes."""
        key = crypto.GCE.generate_key()
        msg = b"same message"
        sizes = {len(crypto.GCE.symmetric_encrypt(key, msg)) for _ in range(5)}
        self.assertGreater(len(sizes), 1)

    def test_symmetric_v1_backward_compatibility(self):
        """Decrypting v1 ciphertext (no padding) must still work."""
        key = nacl_random(32)
        msg = b"v1 symmetric ciphertext"
        v1_enc = SecretBox(key).encrypt(msg)
        dec = crypto.GCE.symmetric_decrypt(key, v1_enc)
        self.assertEqual(dec, msg)

    #
    # ─────────────────────────────────────────────────────────────
    #   STREAMING V1 TESTS (SecretBox-based, no padding)
    # ─────────────────────────────────────────────────────────────
    #

    def test_streaming_v1_encrypt_decrypt(self):
        """Force v1 mode by disabling SecretStream and perform roundtrip."""
        old_flag = crypto.SECRETSTREAM_AVAILABLE
        crypto.SECRETSTREAM_AVAILABLE = False

        try:
            prv, pub = crypto.GCE.generate_keypair()

            plain = os.path.join(Settings.tmp_path, "v1_plain")
            enc = os.path.join(Settings.tmp_path, "v1_enc")
            dec = os.path.join(Settings.tmp_path, "v1_dec")

            with open(plain, "wb") as f:
                f.write(os.urandom(1_000_000))  # 1 MB

            # encrypt
            with open(plain, "rb") as inp, crypto.GCE.streaming_encryption_open("ENCRYPT", pub, enc) as seo:
                chunk = inp.read(CHUNK_SIZE)
                while True:
                    nxt = inp.read(CHUNK_SIZE)
                    if not nxt:
                        seo.encrypt_chunk(chunk, 1)
                        break
                    seo.encrypt_chunk(chunk, 0)
                    chunk = nxt

            # decrypt
            with open(dec, "wb") as out, crypto.GCE.streaming_encryption_open("DECRYPT", prv, enc) as sdo:
                while True:
                    last, data = sdo.decrypt_chunk()
                    out.write(data)
                    if last:
                        break

            self.assertTrue(filecmp.cmp(plain, dec))
        finally:
            crypto.SECRETSTREAM_AVAILABLE = old_flag

    #
    # ─────────────────────────────────────────────────────────────
    #   STREAMING V2 TESTS (SecretStream-based, WITH padding)
    # ─────────────────────────────────────────────────────────────
    #

    def _stream_encrypt(self, pub, src, dst):
        with open(src, "rb") as inp, crypto.GCE.streaming_encryption_open("ENCRYPT", pub, dst) as enc:
            chunk = inp.read(CHUNK_SIZE)
            while True:
                nxt = inp.read(CHUNK_SIZE)
                if not nxt:
                    enc.encrypt_chunk(chunk, 1)
                    break
                enc.encrypt_chunk(chunk, 0)
                chunk = nxt

    def _stream_decrypt(self, prv, src, dst):
        with open(dst, "wb") as out, crypto.GCE.streaming_encryption_open("DECRYPT", prv, src) as dec:
            while True:
                last, data = dec.decrypt_chunk()
                out.write(data)
                if last:
                    break

    def test_streaming_v2_roundtrip(self):
        """Normal v2 roundtrip with padding enabled."""
        if not crypto.SECRETSTREAM_AVAILABLE:
            self.skipTest("v2 streaming unavailable")

        prv, pub = crypto.GCE.generate_keypair()

        plain = os.path.join(Settings.tmp_path, "v2_plain")
        enc = os.path.join(Settings.tmp_path, "v2_enc")
        dec = os.path.join(Settings.tmp_path, "v2_dec")

        with open(plain, "wb") as f:
            f.write(os.urandom(2_000_000))  # 2 MB

        self._stream_encrypt(pub, plain, enc)
        self._stream_decrypt(prv, enc, dec)

        self.assertTrue(filecmp.cmp(plain, dec))

    def test_streaming_v2_padding_varies_ciphertext_size(self):
        """Per-chunk padding must cause ciphertext size variability."""
        if not crypto.SECRETSTREAM_AVAILABLE:
            self.skipTest("v2 streaming unavailable")

        prv, pub = crypto.GCE.generate_keypair()

        plain = os.path.join(Settings.tmp_path, "v2pad_plain")
        with open(plain, "wb") as f:
            f.write(b"A" * 30000)

        sizes = set()
        for i in range(4):
            enc = os.path.join(Settings.tmp_path, f"v2pad_enc_{i}")
            self._stream_encrypt(pub, plain, enc)
            sizes.add(os.path.getsize(enc))

        self.assertGreater(len(sizes), 1)

    #
    # ─────────────────────────────────────────────────────────────
    #   STREAMING V2 NEGATIVE TESTS
    # ─────────────────────────────────────────────────────────────
    #

    def test_streaming_v2_truncated_ciphertext_fails(self):
        if not crypto.SECRETSTREAM_AVAILABLE:
            self.skipTest("v2 streaming unavailable")

        prv, pub = crypto.GCE.generate_keypair()

        plain = os.path.join(Settings.tmp_path, "v2trunc_plain")
        enc = os.path.join(Settings.tmp_path, "v2trunc_enc")
        with open(plain, "wb") as f:
            f.write(os.urandom(500_000))

        self._stream_encrypt(pub, plain, enc)

        # truncate last bytes
        with open(enc, "rb") as f:
            data = f.read()
        with open(enc, "wb") as f:
            f.write(data[:-20])

        dec = os.path.join(Settings.tmp_path, "v2trunc_dec")

        with self.assertRaises(Exception):
            self._stream_decrypt(prv, enc, dec)

    def test_streaming_v2_corrupt_ciphertext_fails(self):
        if not crypto.SECRETSTREAM_AVAILABLE:
            self.skipTest("v2 streaming unavailable")

        prv, pub = crypto.GCE.generate_keypair()

        plain = os.path.join(Settings.tmp_path, "v2corr_plain")
        enc = os.path.join(Settings.tmp_path, "v2corr_enc")

        with open(plain, "wb") as f:
            f.write(os.urandom(600_000))

        self._stream_encrypt(pub, plain, enc)

        # Corrupt a random non-header byte
        with open(enc, "rb") as f:
            data = bytearray(f.read())

        idx = 100 + secrets.randbelow(len(data) - 100)
        data[idx] ^= 0xAA

        with open(enc, "wb") as f:
            f.write(data)

        dec = os.path.join(Settings.tmp_path, "v2corr_dec")

        with self.assertRaises(Exception):
            self._stream_decrypt(prv, enc, dec)

