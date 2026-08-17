import copy
from nacl.utils import random as nacl_random
from globaleaks.settings import Settings
from globaleaks.state import State
from globaleaks.utils.crypto import sha256, GCE
from globaleaks.utils.objectdict import ObjectDict
from globaleaks.utils.tempdict import TempDict
from globaleaks.utils.utility import uuid4


class Session(dict):
    def __init__(self, tid, user_id, user_tid, user_username, user_role, cc='', ek='', roles=None,
                 permissions=None, sk=''):
        if isinstance(sk, bytes):
            sk = sk.decode()

        dict.__init__(self, {
          'id': nacl_random(32).hex(),
          'cc': cc,
          'ek': ek,
          'sk': sk,
          'expireCall': None
        })

        self.attrs = {
            'tid': tid,
            'user_id': user_id,
            'user_tid': user_tid,
            'username': user_username,
            'role': user_role,
            'idp_id': '',
            'roles': roles or [],
            'files': [],
            'token': State.tokens.new(tid),
            'properties': {},
            'permissions': ObjectDict(),
            # RFC 9449 DPoP binding: thumbprint (jkt) of the client public key
            # bound to this session.
            'dpop_jkt': ''
        }

        if permissions:
            self.attrs['permissions'] = permissions

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
        session.sk = GCE.symmetric_encrypt(key, self.sk)
        return session

    def decrypt(self, key):
        key = bytes.fromhex(key)
        self.cc = GCE.symmetric_decrypt(key, self.cc)
        self.ek = GCE.symmetric_decrypt(key, self.ek)
        self.sk = GCE.symmetric_decrypt(key, self.sk).decode()

    def getTime(self):
        return self.expireCall.getTime() if self.expireCall else 0

    def has_permission(self, permission):
        return self.permissions.get(permission, False)

    def serialize(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'username': self.username,
            'role': self.role,
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

    def revoke_user(self, user_tid, user_id):
        for k, v in list(self.items()):
            if v.user_tid == user_tid and v.user_id == user_id:
                del self[k]

    def new(self, tid, user_id, user_tid, user_username, user_role, cc='', ek='', roles=None,
            permissions=None, sk='', dpop_jkt=''):
        self.revoke(tid, user_id)
        session = Session(tid, user_id, user_tid, user_username, user_role,
                          cc, ek, roles, permissions, sk)
        session.dpop_jkt = dpop_jkt
        encrypted_session = session.encrypt()
        self[encrypted_session.id] = encrypted_session
        return session

    def regenerate(self, session, dpop_jkt=None):
        del self[session.id]
        session.id = nacl_random(32).hex()
        # A regenerated session (e.g. cross-tenant handoff) is presented by a
        # freshly loaded client with a new key pair: rebind the thumbprint so
        # the handoff is bound to the new key.
        if dpop_jkt is not None:
            session.dpop_jkt = dpop_jkt
        encrypted_session = session.encrypt()
        self[encrypted_session.id] = encrypted_session
        return session


Sessions = SessionsFactory(timeout=Settings.authentication_lifetime)


def initialize_submission_session(tid, dpop_jkt=''):
    prv_key, pub_key = GCE.generate_keypair()
    return Sessions.new(tid, uuid4(), tid, 'whistleblower', 'whistleblower', prv_key, dpop_jkt=dpop_jkt)
