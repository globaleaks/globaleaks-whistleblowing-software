# -*- coding: utf-8 -*-
import copy
from nacl.utils import random as nacl_random
from globaleaks.settings import Settings
from globaleaks.state import State
from globaleaks.utils.crypto import sha256, GCE
from globaleaks.utils.tempdict import TempDict
from globaleaks.utils.utility import datetime_now, uuid4


class Session(dict):
    def __init__(self, tid, user_id, user_tid, user_role, cc='', ek=''):
        dict.__init__(self, {
          'id': nacl_random(32).hex(),
          'cc': cc,
          'ek': ek,
          'expireCall': None
        })

        self.attrs = {
            'tid': tid,
            'user_id': user_id,
            'user_tid': user_tid,
            'user_role': user_role,
            'ratelimit_time': datetime_now(),
            'ratelimit_count': 0,
            'files': [],
            'token': State.tokens.new(tid),
            'properties': {},
            'permissions': {}
        }

    def __getattr__(self, name):
        if name in self or name == 'attrs':
            return self[name]
        elif name in self.attrs:
            return self.attrs[name]
        else:
            raise AttributeError

    def __setattr__(self, name, value):
        if name in self or name == 'attrs':
            self[name] = value
        else:
            self.attrs[name] = value

    def encrypt(self):
        session = copy.copy(self)
        key = bytes.fromhex(self.id)
        session.id = sha256(self.id)
        session.cc = GCE.symmetric_encrypt(key, self.cc)
        session.ek = GCE.symmetric_encrypt(key, self.ek)
        return session

    def decrypt(self, key):
        key = bytes.fromhex(key)
        self.cc = GCE.symmetric_decrypt(key, self.cc)
        self.ek = GCE.symmetric_decrypt(key, self.ek)

    def getTime(self):
        return self.expireCall.getTime() if self.expireCall else 0

    def has_permission(self, permission):
        return self.permissions.get(permission, False)

    def serialize(self):
        return {
            'id': self.id,
            'role': self.user_role,
            'user_id': self.user_id,
            'session_expiration': self.getTime(),
            'properties': self.properties,
            'permissions': self.permissions,
            'token': self.token.serialize()
        }


class SessionsFactory(TempDict):
    """Extends TempDict to provide session management functions ontop of temp session keys"""
    reset_timeout_on_access = False

    def get(self, key):
        session = TempDict.get(self, sha256(key))

        if session is not None:
            decrypted_copy = copy.copy(session)
            decrypted_copy.decrypt(key)
            return decrypted_copy

    def revoke(self, tid, user_id):
        for k, v in list(self.items()):
            if v.tid == tid and v.user_id == user_id:
                del self[k]

    def new(self, tid, user_id, user_tid, user_role, cc='', ek=''):
        self.revoke(tid, user_id)
        session = Session(tid, user_id, user_tid, user_role, cc, ek)
        encrypted_session = session.encrypt()
        self[encrypted_session.id] = encrypted_session
        return session

    def regenerate(self, session):
        del self[session.id]
        session.id = nacl_random(32).hex()
        encrypted_session = session.encrypt()
        self[encrypted_session.id] = encrypted_session
        return session


Sessions = SessionsFactory(timeout=Settings.authentication_lifetime)


def initialize_submission_session(tid):
    prv_key, pub_key = GCE.generate_keypair()
    return Sessions.new(tid, uuid4(), tid, 'whistleblower', prv_key)
