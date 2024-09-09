# -*- coding: utf-8
# Implement a proof of work token to prevent resources exhaustion
from datetime import timedelta

from globaleaks.rest import errors
from globaleaks.utils.crypto import sha256, generateRandomKey
from globaleaks.utils.tempdict import TempDict
from globaleaks.utils.utility import datetime_now


class Token(object):
    def __init__(self, tid):
        self.tid = tid
        self.id = generateRandomKey().encode()
        self.session = None
        self.creation_date = datetime_now()

    def serialize(self):
        otp = CryptoOTP()
        return {
            # 'id': f"{self.id.decode()}:{otp.exec(self.id.decode())}",
            'id': self.id.decode(),
            'creation_date': self.creation_date,
            'complexity': 4
        }

    def validate(self, token_answer):
        try:
            key, answer = token_answer.split(b":")

            if not sha256(key + answer).endswith(b'00'):
                raise errors.InternalServerError("TokenFailure: Invalid Token")
        except:
            raise errors.InternalServerError("TokenFailure: Invalid token")


class TokenList(TempDict):
    def new(self, tid, session=None):
        token = Token(tid)

        if session is not None:
            token.session = session

        self[token.id] = token

        return token

    def get(self, key):
        ret = TempDict.get(self, key)
        if ret is None:
            raise errors.InternalServerError("TokenFailure: Invalid token")

        return ret

    def validate(self, token_answer):
        try:
            key, answer = token_answer.split(b":")
            token = self.pop(key)
            token.validate(token_answer)
        except:
            raise errors.InternalServerError("TokenFailure: Invalid token")

        return token

import hashlib
import asyncio
class CryptoOTP:
    def __init__(self):
        self.data = ""
        self.counter = 0

    def calculate_hash(self, hash_bytes: bytes) -> int:
        # Verifica se l'ultimo byte dell'hash è 0
        if hash_bytes[-1] == 0:
            return self.counter
        else:
            self.counter += 1
            return None  # Indica che è necessario continuare a lavorare

    @staticmethod
    def convert_string(string: str) -> bytes:
        # Converte una stringa in un array di byte
        return string.encode('utf-8')

    def search_collision(self) -> int:
        # Loop asincrono per trovare il valore che soddisfa la condizione
        while True:
            to_hash = self.convert_string(self.data + str(self.counter))
            hash_result = hashlib.sha256(to_hash).digest()

            result = self.calculate_hash(hash_result)
            if result is not None:
                return result  # Hash valido trovato

    def exec(self, data: str) -> int:
        # Inizializza i dati e il contatore
        self.data = data
        self.counter = 0

        return self.search_collision()
