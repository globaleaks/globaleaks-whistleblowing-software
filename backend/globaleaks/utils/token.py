# Implement a proof of work token to prevent resources exhaustion
from nacl.encoding import Base64Encoder

from globaleaks.rest import errors
from globaleaks.utils.crypto import GCE, generateRandomKey
from globaleaks.utils.tempdict import TempDict
from globaleaks.utils.utility import datetime_now


class Token:
    def __init__(self, tid):
        self.tid = tid
        self.id = generateRandomKey().encode()
        self.salt = generateRandomKey().encode()
        self.session = None
        self.creation_date = datetime_now()

    def serialize(self):
        return {
            'id': self.id.decode(),
            'salt': self.salt.decode(),
            'creation_date': self.creation_date
        }

    def validate(self, answer):
        try:
            if not Base64Encoder.decode(GCE.argon2id(self.id + answer, self.salt, 1, 1 << 20))[31] == 0:
                raise errors.InvalidPoW
        except Exception:
            raise errors.InvalidPoW


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
            raise errors.InvalidPoW

        return ret

    def validate(self, answer):
        try:
            key, answer = answer.split(b":")
            token = self.pop(key)
            token.validate(answer)
        except Exception:
            raise errors.InvalidPoW

        return token
