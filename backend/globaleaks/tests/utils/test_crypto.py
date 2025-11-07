import filecmp
import os

from nacl.encoding import Base64Encoder

from globaleaks.settings import Settings
from globaleaks.tests import helpers
from globaleaks.utils.crypto import GCE, sha256

CHUNK_SIZE = 4096
password = b'password'
message = b'message'
salt = 'wHMeI9jZ1/hVAfpJliXC3Q=='
hash_argon2 = '83xya+Pxc3w4d7Ry2LHUE28qLVP2Sa4DULo8joMrpL8='


class TestCryptoUtils(helpers.TestGL):
    def test_sha256_with_string(self):
        # Known input and output
        input_data = "hello world"
        expected_hash = b'b94d27b9934d3e08a52e52d7da7dabfac484efe37a5380ee9088f7ace2efcde9'
        self.assertEqual(sha256(input_data), expected_hash)

    def test_sha256_with_bytes(self):
        input_data = b"hello world"
        expected_hash = b'b94d27b9934d3e08a52e52d7da7dabfac484efe37a5380ee9088f7ace2efcde9'
        self.assertEqual(sha256(input_data), expected_hash)

    def test_sha256_empty_string(self):
        input_data = ""
        expected_hash = b'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855'
        self.assertEqual(sha256(input_data), expected_hash)

    def test_generate_key(self):
        GCE.generate_key()

    def test_generate_keypair(self):
        key = GCE.generate_key()
        prv_key, pub_key = GCE.generate_keypair()
        prv_key_enc = GCE.symmetric_encrypt(key, prv_key)
        self.assertEqual(prv_key, GCE.symmetric_decrypt(key, prv_key_enc))

    def test_derive_key(self):
        GCE.derive_key(password, salt)

    def test_crypto_generate_key_encrypt_decrypt_key(self):
        enc_key = GCE.generate_key()
        enc = GCE.symmetric_encrypt(enc_key, message)
        dec = GCE.symmetric_decrypt(enc_key, enc)
        self.assertEqual(dec, message)

    def test_crypto_generate_encrypt_decrypt_message(self):
        prv_key, pub_key = GCE.generate_keypair()
        enc = GCE.asymmetric_encrypt(pub_key, message)
        dec = GCE.asymmetric_decrypt(prv_key, enc)
        self.assertEqual(dec, message)

    def test_check_equality(self):
        self.assertTrue(GCE.check_equality(password, password))
        self.assertFalse(GCE.check_equality(password, 'different_data'))

    def test_encrypt_and_decrypt_file(self):
        prv_key, pub_key = GCE.generate_keypair()

        # Create a 10MB random file in Settings.tmp_path
        a = os.path.join(Settings.tmp_path, 'test_input_10mb.bin')
        with open(a, 'wb') as f:
            f.write(os.urandom(10 * 1024 * 1024))  # 10MB of random data

        b = os.path.join(Settings.tmp_path, 'encrypted_output')
        c = os.path.join(Settings.tmp_path, 'decrypted_output')

        # Encrypt the file
        with open(a, 'rb') as input_fd, GCE.streaming_encryption_open('ENCRYPT', pub_key, b) as seo:
            chunk = input_fd.read(CHUNK_SIZE)
            while True:
                x = input_fd.read(CHUNK_SIZE)
                if not x:
                    seo.encrypt_chunk(chunk, 1)
                    break
                seo.encrypt_chunk(chunk, 0)
                chunk = x

        # Decrypt the file
        with open(c, 'wb') as output_fd, GCE.streaming_encryption_open('DECRYPT', prv_key, b) as seo:
            while True:
                last, data = seo.decrypt_chunk()
                output_fd.write(data)
                if last:
                    break

        # Check that encryption changed the file and decryption restored it
        self.assertFalse(filecmp.cmp(a, b, False))
        self.assertTrue(filecmp.cmp(a, c, False))

    def test_recovery_key(self):
        prv_key, _ = GCE.generate_keypair()
        bck_key, rec_key = GCE.generate_recovery_key(prv_key)
        plain_rec_key = GCE.asymmetric_decrypt(prv_key, Base64Encoder.decode(rec_key))
        x = GCE.symmetric_decrypt(plain_rec_key, Base64Encoder.decode(bck_key))
        self.assertEqual(x, prv_key)
