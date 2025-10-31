import binascii
import os
import pyotp
import random
import secrets
import string
import struct
import threading
import hashlib

from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import constant_time, hashes

from nacl.encoding import Base64Encoder
from nacl.pwhash import argon2id
from nacl.public import SealedBox, PrivateKey, PublicKey
from nacl.secret import SecretBox
from nacl.utils import EncryptedMessage
from nacl.utils import random as nacl_random

from typing import Any, Optional, Tuple, Union


crypto_backend = default_backend()
lock = threading.Lock()

def _convert_to_bytes(arg: Union[bytes, str]) -> bytes:
    """
    Convert the argument to bytes if of string type
    :param arg: a string or a byte object
    :return: the converted byte object
    """
    if isinstance(arg, str):
        arg = arg.encode()

    return arg


def sha256(data: Union[bytes, str]) -> bytes:
    """
    Perform the sha256 of the passed data
    :param data: A data to be hashed
    :return: A hash value
    """
    h = hashes.Hash(hashes.SHA256(), backend=crypto_backend)
    h.update(_convert_to_bytes(data))
    return binascii.b2a_hex(h.finalize())

def sha512(data: Union[bytes, str]) -> bytes:
    """
    Perform the sha512 of the passed data
    :param data: A data to be hashed
    :return: A hash value
    """
    h = hashes.Hash(hashes.SHA512(), backend=crypto_backend)
    h.update(_convert_to_bytes(data))
    return binascii.b2a_hex(h.finalize())

def generateRandomKey() -> str:
    """
    Return a random secret of 256bits
    """
    return nacl_random(32).hex()


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

    password = ''.join(secrets.SystemRandom().choice(accessible_symbols_set) for _ in range(N-4))
    password += secrets.SystemRandom().choice(string.ascii_lowercase)
    password += secrets.SystemRandom().choice(string.ascii_uppercase)
    password += secrets.SystemRandom().choice(string.digits)
    password += secrets.SystemRandom().choice(accessible_special_symbols)

    password = ''.join(random.sample(password, N))

    return password


def totpVerify(secret: str, token: str) -> None:
    # RFC 6238: step size 30 sec; valid_window = 1; total size of the window: 1.30 sec
    if not pyotp.TOTP(secret).verify(token, valid_window=1):
        raise Error


class _StreamingEncryptionObject(object):
    def __init__(self, mode: str, user_key: Union[bytes, str], filepath: str) -> None:
        self.mode = mode
        self.user_key = user_key
        self.filepath = filepath
        self.key = None
        self.EOF = False

        self.index = 0

        if self.mode == 'ENCRYPT':
            self.fd = open(filepath, 'wb')
            self.key = nacl_random(32)
            self.partial_nonce = nacl_random(16)
            key = _GCE.asymmetric_encrypt(self.user_key, self.key)
            self.fd.write(key)
            self.fd.write(self.partial_nonce)
        else:
            self.fd = open(filepath, 'rb')
            x = self.fd.read(80)
            self.key = _GCE.asymmetric_decrypt(self.user_key, x)
            self.partial_nonce = self.fd.read(16)

        self.box = SecretBox(self.key)

    def fullNonce(self, i: int) -> bytes:
        return self.partial_nonce + struct.pack('<Q', i)

    def lastFullNonce(self) -> bytes:
        return self.partial_nonce + struct.pack('>Q', 1)

    def getNextNonce(self, last: int) -> bytes:
        if last:
            chunkNonce = self.lastFullNonce()
        else:
            chunkNonce = self.fullNonce(self.index)

        self.index += 1

        return chunkNonce

    def encrypt_chunk(self, chunk: bytes, last: int = 0) -> None:
        chunkNonce = self.getNextNonce(last)
        self.fd.write(struct.pack('>B', last))
        self.fd.write(struct.pack('>I', len(chunk)))
        self.fd.write(self.box.encrypt(chunk, chunkNonce)[24:])

    def decrypt_chunk(self) -> Tuple[int, bytes]:
        last = struct.unpack('>B', self.fd.read(1))[0]
        if last:
            self.EOF = True

        chunkNonce = self.getNextNonce(last)
        chunkLen = struct.unpack('>I', self.fd.read(4))[0]
        chunk = self.fd.read(chunkLen + 16)
        return last, self.box.decrypt(chunk, chunkNonce)

    def read(self, a: int) -> bytes:
        if not self.EOF:
            return self.decrypt_chunk()[1]

    def close(self) -> None:
        if self.fd is not None:
            self.fd.close()
            self.fd = None

    def __enter__(self) -> '_StreamingEncryptionObject':
        return self

    def __exit__(self, exc_type: Optional[Any], exc_val: Optional[Any], exc_tb: Optional[Any]) -> None:
        self.close()

    def __del__(self) -> None:
        self.close()


class _GCE(object):
    options = {
        'OPSLIMIT': 16,
        'MEMLIMIT': 27 # 128MB
    }

    @staticmethod
    def check_equality(user_hash, hash) -> bool:
        """
        Perform hash check for match with a provided hash
        """
        user_hash = _convert_to_bytes(user_hash)
        x = _convert_to_bytes(hash)

        return constant_time.bytes_eq(x, user_hash)

    @staticmethod
    def generate_receipt() -> str:
        """
        Return a random receipt of 16 digits
        """
        return ''.join(random.SystemRandom().choice(string.digits) for _ in range(16))

    @staticmethod
    def generate_salt(seed: str = '') -> str:
        """
        Return a salt with 128 bits of entropy.
        """
        random_bytes = nacl_random(16)
        deterministic_bytes = hashlib.sha256(seed.encode()).digest()[:16]

        return Base64Encoder.encode(deterministic_bytes if seed else random_bytes).decode()

    @staticmethod
    def generate_key() -> bytes:
        """
        Generate a 256 bit key
        """
        return nacl_random(32)

    @staticmethod
    def argon2id(password: str, salt: str, opslimit: 16, memlimit: int = 1 << 27) -> bytes:
        """
        Return the hash a password
        """
        password = _convert_to_bytes(password)
        salt = _convert_to_bytes(salt)

        lock.acquire()

        try:
            salt = Base64Encoder.decode(salt)
            hash = argon2id.kdf(32, password, salt[0:16],
                                opslimit=opslimit,
                                memlimit=memlimit)
            return Base64Encoder.encode(hash).decode()
        finally:
            lock.release()

    @staticmethod
    def derive_key(password: Union[bytes, str], salt: str) -> bytes:
        """
        Perform key derivation from a user password
        """
        return _GCE.argon2id(password, salt, _GCE.options['OPSLIMIT'], 1 << _GCE.options['MEMLIMIT'])

    @staticmethod
    def calculate_key_and_hash(password: Union[bytes, str], salt: str) -> Tuple[bytes, bytes]:
        """
        Calculate and returns password key derivation and key hashing
        """
        return Base64Encoder.decode(_GCE.argon2id(password.encode(), salt, _GCE.options['OPSLIMIT'] + 1, 1 << _GCE.options['MEMLIMIT'])), \
               _GCE.argon2id(password, salt, _GCE.options['OPSLIMIT'], 1 << _GCE.options['MEMLIMIT'])

    @staticmethod
    def generate_keypair() -> Tuple[bytes, bytes]:
        """
        Generate a curve25519 keypair
        """
        prv_key = PrivateKey.generate()

        return prv_key.encode(Base64Encoder), \
               prv_key.public_key.encode(Base64Encoder)

    @staticmethod
    def generate_recovery_key(prv_key: bytes) -> Tuple[bytes, bytes]:
        rec_key = _GCE.generate_key()
        pub_key = PrivateKey(prv_key, Base64Encoder).public_key.encode(Base64Encoder)
        bkp_key = _GCE.symmetric_encrypt(rec_key, prv_key)
        rec_key = _GCE.asymmetric_encrypt(pub_key, rec_key)
        return Base64Encoder.encode(bkp_key), Base64Encoder.encode(rec_key)

    @staticmethod
    def symmetric_encrypt(key: bytes, data: bytes) -> EncryptedMessage:
        """
        Perform symmetric encryption using libsodium secretbox (XSalsa20-Poly1305))
        """
        nonce = nacl_random(24)
        data = _convert_to_bytes(data)
        return SecretBox(key).encrypt(data, nonce)

    @staticmethod
    def symmetric_decrypt(key: bytes, data: bytes) -> bytes:
        """
        Perform symmetric decryption using libsodium secretbox (XSalsa20-Poly1305)
        """
        data = _convert_to_bytes(data)
        return SecretBox(key).decrypt(data)

    @staticmethod
    def asymmetric_encrypt(pub_key: Union[bytes, str], data: Union[bytes, str]) -> bytes:
        """
        Perform asymmetric encryption using libsodium sealedbox (Curve25519, XSalsa20-Poly1305)
        """
        pub_key = PublicKey(pub_key, Base64Encoder)
        data = _convert_to_bytes(data)
        return SealedBox(pub_key).encrypt(data)

    @staticmethod
    def asymmetric_decrypt(prv_key: bytes, data: bytes) -> bytes:
        """
        Perform asymmetric decryption using libsodium sealedbox (Curve25519, XSalsa20-Poly1305)
        """
        prv_key = PrivateKey(prv_key, Base64Encoder)
        data = _convert_to_bytes(data)
        return SealedBox(prv_key).decrypt(data)

    @staticmethod
    def streaming_encryption_open(mode: str, user_key: Union[bytes, str], filepath: str) -> '_StreamingEncryptionObject':
        return _StreamingEncryptionObject(mode, user_key, filepath)


GCE = _GCE()
