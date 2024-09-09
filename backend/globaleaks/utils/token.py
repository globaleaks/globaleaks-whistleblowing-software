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
        return {
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