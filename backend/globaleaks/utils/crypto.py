import binascii
import hashlib
import os
import pyotp
import secrets
import string
import struct
import threading

from contextlib import nullcontext

from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import constant_time, hashes

from nacl.encoding import Base64Encoder
from nacl.pwhash import argon2id
from nacl.public import SealedBox, PrivateKey, PublicKey
from nacl.secret import SecretBox
from nacl.utils import EncryptedMessage
from nacl.utils import random as nacl_random

from typing import Any, Optional, Tuple, Union

# --- Optional SecretStream bindings (libsodium >= 1.0.14) ---
try:
    from nacl.bindings import (
        crypto_secretstream_xchacha20poly1305_init_push,
        crypto_secretstream_xchacha20poly1305_push,
        crypto_secretstream_xchacha20poly1305_state,
        crypto_secretstream_xchacha20poly1305_init_pull,
        crypto_secretstream_xchacha20poly1305_pull,
        crypto_secretstream_xchacha20poly1305_HEADERBYTES,
        crypto_secretstream_xchacha20poly1305_TAG_FINAL,
    )
    SECRETSTREAM_AVAILABLE = True
except Exception:
    SECRETSTREAM_AVAILABLE = False


crypto_backend = default_backend()
lock = threading.Lock()

# Message-level padding magic (for symmetric encryption)
MAGIC_PAD = b'\xda\x7a'

# Streaming v2 header
MAGIC = b'GCE\x00'
VERSION_V2 = 2


def _convert_to_bytes(arg: Union[bytes, str]) -> bytes:
    """
    Convert the argument to bytes if of string type
    :param arg: a string or a byte object
    :return: the converted byte object
    """
    if isinstance(arg, str):

        return arg.encode()
    return arg


def sha256(data: Union[bytes, str]) -> bytes:
    """
    Perform the sha256 of the passed data
    :param data: A data to be hashed
    :return: A hash value
    """
    return hashlib.sha256(_convert_to_bytes(data)).hexdigest().encode()


def generateRandomKey() -> str:
    """
    Return a random secret of 256bits (hex string).
    """
    return secrets.token_hex(32)


def generateRandomPassword(N: int) -> str:
    """
    Return a random password

    The random password generated have the following qualities:
       Is long at least 10 characters randomly choosen in a set of 72 accessible characters
       Contains at least a lowercase ascii letter
       Contains at least an uppercase ascii letter
       Contains at least a symbol in a selction of 10 common and accessible symbols
    """
    accessible_special_symbols = "!?@#+-/*="
    accessible_symbols_set = string.ascii_letters + string.digits + accessible_special_symbols

    password = ''.join(secrets.SystemRandom().choice(accessible_symbols_set) for _ in range(N - 4))
    password += secrets.SystemRandom().choice(string.ascii_lowercase)
    password += secrets.SystemRandom().choice(string.ascii_uppercase)
    password += secrets.SystemRandom().choice(string.digits)
    password += secrets.SystemRandom().choice(accessible_special_symbols)

    password = ''.join(secrets.SystemRandom().sample(password, N))

    return password


def totpVerify(secret: str, token: str) -> None:
    # RFC 6238: step size 30 sec; valid_window = 1; total size of the window: 1.30 sec
    if not pyotp.TOTP(secret).verify(token, valid_window=1):
        raise ValueError("Invalid TOTP token")


class _StreamingEncryptionObject(object):
    """
    Streaming encrypt/decrypt with:
        - v1 streaming (SecretBox chunked format)
        - v2 streaming (SecretStream)
    """

    PADDING_FRACTION = 0.05
    PADDING_MIN = 8
    PADDING_MAX = 65535

    def __init__(self, mode: str, user_key: Union[bytes, str], filepath: str) -> None:
        self.mode = mode
        self.user_key = user_key
        self.filepath = filepath

        self.key: Optional[bytes] = None
        self.partial_nonce: Optional[bytes] = None
        self.EOF = False
        self.index = 0
        self.use_secretstream = False
        self.version: Optional[int] = None

        self.fd = open(filepath, 'wb' if mode == 'ENCRYPT' else 'rb')  # noqa: SIM115 - long-lived handle for streaming (de)cryption, closed explicitly
        if mode == 'ENCRYPT':
            self._init_encrypt()
        else:
            self._init_decrypt()

    def _pad_bytes(self, data: bytes) -> bytes:
        data = _convert_to_bytes(data)
        n = len(data)
        max_pad = min(max(int(n * self.PADDING_FRACTION), self.PADDING_MIN), self.PADDING_MAX)
        pad_len = secrets.randbelow(max_pad + 1)
        padding = os.urandom(pad_len)
        trailer = struct.pack(">H", pad_len)
        return data + padding + trailer

    def _strip_padded_bytes(self, data: bytes) -> bytes:
        if len(data) < 2:
            return data
        pad_len = struct.unpack(">H", data[-2:])[0]
        if pad_len > len(data) - 2 or pad_len > self.PADDING_MAX:
            return data
        return data[:-(2 + pad_len)]

    def _init_encrypt(self) -> None:
        self.key = nacl_random(32)
        self.partial_nonce = nacl_random(16)
        if SECRETSTREAM_AVAILABLE:
            self.version = 2
            self.use_secretstream = True
            self._write_header_v2()
        else:
            self.version = 1
            self._write_header_v1()

    def _write_header_v1(self) -> None:
        self.fd.write(_GCE.asymmetric_encrypt(self.user_key, self.key))
        self.fd.write(self.partial_nonce)
        self.box = SecretBox(self.key)
        self.index = 0

    def _write_header_v2(self) -> None:
        self.fd.write(MAGIC)
        self.fd.write(struct.pack('>B', VERSION_V2))
        self.fd.write(_GCE.asymmetric_encrypt(self.user_key, self.key))
        self.fd.write(self.partial_nonce)
        self.ss_state = crypto_secretstream_xchacha20poly1305_state()
        self.fd.write(crypto_secretstream_xchacha20poly1305_init_push(self.ss_state, self.key))

    def _read_header_v1(self) -> None:
        sealed = self.fd.read(80)
        if len(sealed) != 80:
            raise ValueError("Corrupted v1 header")
        self.key = _GCE.asymmetric_decrypt(self.user_key, sealed)
        self.partial_nonce = self.fd.read(16)
        if len(self.partial_nonce) != 16:
            raise ValueError("Corrupted v1 header: nonce")
        self.box = SecretBox(self.key)
        self.index = 0

    def _read_header_v2(self) -> None:
        version = self.fd.read(1)
        if len(version) != 1 or version[0] != VERSION_V2:
            raise ValueError("Unsupported or corrupted v2 header")
        sealed = self.fd.read(80)
        if len(sealed) != 80:
            raise ValueError("Corrupted v2 header: sealed key")
        self.key = _GCE.asymmetric_decrypt(self.user_key, sealed)
        self.partial_nonce = self.fd.read(16)
        if len(self.partial_nonce) != 16:
            raise ValueError("Corrupted v2 header: nonce")
        ss_header = self.fd.read(crypto_secretstream_xchacha20poly1305_HEADERBYTES)
        if len(ss_header) != crypto_secretstream_xchacha20poly1305_HEADERBYTES:
            raise ValueError("Corrupted v2 header: SS header")
        self.ss_state = crypto_secretstream_xchacha20poly1305_state()
        crypto_secretstream_xchacha20poly1305_init_pull(self.ss_state, ss_header, self.key)

    def _init_decrypt(self) -> None:
        if self.fd.read(len(MAGIC)) == MAGIC:
            if not SECRETSTREAM_AVAILABLE:
                raise RuntimeError("SecretStream ciphertext but SECRETSTREAM unavailable")
            self.version = 2
            self.use_secretstream = True
            self._read_header_v2()
        else:
            self.version = 1
            self.fd.seek(0)
            self._read_header_v1()

    def fullNonce(self, i: int) -> bytes:
        return self.partial_nonce + struct.pack('<Q', i)

    def lastFullNonce(self) -> bytes:
        return self.partial_nonce + struct.pack('>Q', 1)

    def getNextNonce(self, last: int) -> bytes:
        nonce = self.lastFullNonce() if last else self.fullNonce(self.index)
        self.index += 1
        return nonce

    def _encrypt_chunk_v1(self, chunk: bytes, last: int) -> None:
        chunk_nonce = self.getNextNonce(last)
        self.fd.write(struct.pack('>B', last))
        self.fd.write(struct.pack('>I', len(chunk)))
        self.fd.write(self.box.encrypt(chunk, chunk_nonce).ciphertext)

    def _encrypt_chunk_v2(self, chunk: bytes, last: int) -> None:
        chunk = self._pad_bytes(chunk)
        tag = crypto_secretstream_xchacha20poly1305_TAG_FINAL if last else 0
        frame = crypto_secretstream_xchacha20poly1305_push(self.ss_state, chunk, b"", tag)
        self.fd.write(struct.pack('>I', len(frame)))
        self.fd.write(frame)

    def encrypt_chunk(self, chunk: bytes, last: int = 0) -> None:
        chunk = _convert_to_bytes(chunk)
        (self._encrypt_chunk_v2 if self.use_secretstream else self._encrypt_chunk_v1)(chunk, last)

    def _decrypt_chunk_v1(self) -> Tuple[int, bytes]:
        last_flag = self.fd.read(1)
        if not last_flag:
            self.EOF = True
            return 1, b''
        last = struct.unpack('>B', last_flag)[0]
        self.EOF = bool(last)
        len_b = self.fd.read(4)
        if len(len_b) < 4:
            raise ValueError("Corrupted v1 stream: missing length")
        chunk_len = struct.unpack('>I', len_b)[0]
        ct = self.fd.read(chunk_len + 16)
        if len(ct) < chunk_len + 16:
            raise ValueError("Corrupted v1 stream: truncated ciphertext")
        return last, self.box.decrypt(ct, self.getNextNonce(last))

    def _decrypt_chunk_v2(self) -> Tuple[int, bytes]:
        sz = self.fd.read(4)
        if not sz:
            self.EOF = True
            return 1, b''
        if len(sz) < 4:
            raise ValueError("Corrupted v2 stream: frame size")
        frame_len = struct.unpack('>I', sz)[0]
        frame = self.fd.read(frame_len)
        if len(frame) < frame_len:
            raise ValueError("Corrupted v2 stream: truncated frame")
        msg, tag = crypto_secretstream_xchacha20poly1305_pull(self.ss_state, frame, b"")
        last = int(tag == crypto_secretstream_xchacha20poly1305_TAG_FINAL)
        self.EOF = bool(last)
        return last, self._strip_padded_bytes(msg)

    def decrypt_chunk(self) -> Tuple[int, bytes]:
        return (self._decrypt_chunk_v2 if self.use_secretstream else self._decrypt_chunk_v1)()

    def read(self, a: int) -> bytes:
        return b'' if self.EOF else self.decrypt_chunk()[1]

    def close(self) -> None:
        if self.fd is not None:
            self.fd.close()
            self.fd = None

    def __enter__(self) -> '_StreamingEncryptionObject':
        return self

    def __exit__(self, exc_type: Optional[Any], exc_val: Optional[Any], exc_tb: Optional[Any]) -> None:
        self.close()


class _GCE(object):
    options = {
        'OPSLIMIT': 16,
        'MEMLIMIT': 27  # 128MB
    }

    @staticmethod
    def check_equality(user_hash, hash) -> bool:
        """
        Perform hash check for match with a provided hash.
        """
        user_hash = _convert_to_bytes(user_hash)
        x = _convert_to_bytes(hash)

        return constant_time.bytes_eq(user_hash, x)

    @staticmethod
    def generate_receipt() -> str:
        """
        Return a random receipt of 16 digits.
        """
        return f"{secrets.randbelow(10**16):016d}"

    @staticmethod
    def generate_salt(seed: str = '') -> str:
        """
        Return a salt with 128 bits of entropy.
        """
        if seed:
            salt = hashlib.sha256(seed.encode()).digest()[:16]
        else:
            salt = nacl_random(16)

        return Base64Encoder.encode(salt).decode()

    @staticmethod
    def generate_key() -> bytes:
        """
        Generate a 256 bit key.
        """
        return nacl_random(32)

    @staticmethod
    def argon2id(password: str, salt: str, opslimit: int = 16, memlimit: int = 1 << 27) -> str:
        """
        Return the hash of a password.
        """
        password = _convert_to_bytes(password)
        salt = _convert_to_bytes(salt)

        salt_dec = Base64Encoder.decode(salt)

        # The global lock serializes the memory-hard KDFs (login and key
        # derivation, 128MiB each) so that concurrent requests cannot pile up
        # their allocations and exhaust memory. The proof-of-work token verify
        # uses a tiny 1MiB cost and runs on the reactor thread: it must not
        # contend on that lock, otherwise an in-flight password KDF held in the
        # thread pool would stall the single-threaded event loop for its whole
        # duration. libsodium's kdf is itself thread-safe, so the cheap path is
        # safe to run unlocked.
        ctx = lock if memlimit > (1 << 20) else nullcontext()
        with ctx:
            hashv = argon2id.kdf(
                32,
                password,
                salt_dec[0:16],
                opslimit=opslimit,
                memlimit=memlimit
            )

        return Base64Encoder.encode(hashv).decode()

    @staticmethod
    def derive_key(password: Union[bytes, str], salt: str) -> bytes:
        """
        Perform key derivation from a user password.
        """
        return _GCE.argon2id(password, salt, _GCE.options['OPSLIMIT'], 1 << _GCE.options['MEMLIMIT'])

    @staticmethod
    def calculate_key_and_hash(password: Union[bytes, str], salt: str) -> Tuple[bytes, bytes]:
        """
        Calculate and returns password key derivation and key hashing.
        """
        key = Base64Encoder.decode(
            _GCE.argon2id(password.encode(), salt, _GCE.options['OPSLIMIT'] + 1, 1 << _GCE.options['MEMLIMIT'])
        )
        hashv = _GCE.argon2id(password, salt, _GCE.options['OPSLIMIT'], 1 << _GCE.options['MEMLIMIT'])
        return key, hashv

    @staticmethod
    def generate_keypair() -> Tuple[bytes, bytes]:
        """
        Generate a curve25519 keypair.
        """
        prv_key = PrivateKey.generate()
        return prv_key.encode(Base64Encoder), prv_key.public_key.encode(Base64Encoder)

    @staticmethod
    def generate_recovery_key(prv_key: bytes) -> Tuple[bytes, bytes]:
        rec_key = _GCE.generate_key()
        pub_key = PrivateKey(prv_key, Base64Encoder).public_key.encode(Base64Encoder)
        bkp_key = _GCE.symmetric_encrypt(rec_key, prv_key)
        rec_key_enc = _GCE.asymmetric_encrypt(pub_key, rec_key)
        return Base64Encoder.encode(bkp_key), Base64Encoder.encode(rec_key_enc)

    @staticmethod
    def _pad_for_messages(data: bytes) -> bytes:
        """
        Reuses the same unified padding logic as streaming v2.
        Format:
            data || padding || pad_len(2B)
        """
        data = _convert_to_bytes(data)
        n = len(data)

        frac = _StreamingEncryptionObject.PADDING_FRACTION
        pmin = _StreamingEncryptionObject.PADDING_MIN
        pmax = _StreamingEncryptionObject.PADDING_MAX

        max_pad = int(n * frac)
        if max_pad < pmin:
            max_pad = pmin
        if max_pad > pmax:
            max_pad = pmax

        pad_len = secrets.randbelow(max_pad + 1)
        padding = os.urandom(pad_len)
        trailer = struct.pack(">H", pad_len)

        return data + padding + trailer

    @staticmethod
    def _strip_message_padding(data: bytes) -> bytes:
        """
        Remove padding if valid, else treat as legacy.
        """
        if len(data) < 2:
            return data

        pad_len = struct.unpack(">H", data[-2:])[0]

        if pad_len > _StreamingEncryptionObject.PADDING_MAX:
            return data
        if pad_len > len(data) - 2:
            return data

        return data[:-(2 + pad_len)]

    @staticmethod
    def symmetric_encrypt(key: bytes, data: bytes) -> EncryptedMessage:
        """
        Encrypt data with SecretBox, using unified padding.
        """
        key_b = _convert_to_bytes(key)
        if len(key_b) != 32:
            # allow user to pass base64 string
            try:
                key_b = Base64Encoder.decode(key_b)
            except Exception:
                raise ValueError("SecretBox key must be 32 bytes")

        padded = _GCE._pad_for_messages(_convert_to_bytes(data))
        nonce = nacl_random(24)
        return SecretBox(key_b).encrypt(padded, nonce)

    @staticmethod
    def symmetric_decrypt(key: bytes, data: bytes) -> bytes:
        key_b = _convert_to_bytes(key)
        if len(key_b) != 32:
            try:
                key_b = Base64Encoder.decode(key_b)
            except Exception:
                raise ValueError("SecretBox key must be 32 bytes")

        plaintext = SecretBox(key_b).decrypt(_convert_to_bytes(data))
        return _GCE._strip_message_padding(plaintext)

    @staticmethod
    def asymmetric_encrypt(pub_key: Union[bytes, str], data: Union[bytes, str]) -> bytes:
        """
        Perform asymmetric encryption using libsodium sealedbox (Curve25519, XSalsa20-Poly1305).
        """
        pub = PublicKey(pub_key, Base64Encoder)
        return SealedBox(pub).encrypt(_convert_to_bytes(data))

    @staticmethod
    def asymmetric_decrypt(prv_key: bytes, data: bytes) -> bytes:
        """
        Perform asymmetric decryption using libsodium sealedbox (Curve25519, XSalsa20-Poly1305).
        """
        prv = PrivateKey(prv_key, Base64Encoder)
        return SealedBox(prv).decrypt(_convert_to_bytes(data))

    @staticmethod
    def streaming_encryption_open(mode: str, user_key: Union[bytes, str], filepath: str) -> _StreamingEncryptionObject:
        return _StreamingEncryptionObject(mode, user_key, filepath)


GCE = _GCE()
