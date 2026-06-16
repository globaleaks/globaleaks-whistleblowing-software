# Handlers dealing with user operations
import os
from nacl.encoding import Base32Encoder, Base64Encoder
from nacl.public import PrivateKey

from globaleaks import models
from globaleaks.handlers.operation import OperationHandler
from globaleaks.orm import db_log, transact
from globaleaks.rest import errors
from globaleaks.state import State
from globaleaks.transactions import db_get_user
from globaleaks.utils.crypto import GCE, sha256
from globaleaks.utils.fs import directory_traversal_check, srm
from globaleaks.utils.utility import datetime_now


@transact
def change_password(session, tid, user_session, password):
    user = db_get_user(session, tid, user_session.user_id)

    config = models.config.ConfigFactory(session, tid)

    key = Base64Encoder.decode(password.encode())
    hash = sha256(key).decode()

    # Check that the new password is different form the current password
    if user.hash == hash:
        raise errors.PasswordReuseError

    user.hash = hash
    user.password_change_date = datetime_now()
    user.password_change_needed = False

    cc = user_session.cc
    if config.get_val('encryption'):
        if not user.crypto_pub_key:
            # The first password change triggers the generation
            # of the user encryption private key and its backup
            user.crypto_pub_key = PrivateKey(user_session.cc, Base64Encoder).public_key.encode(Base64Encoder)
            user.crypto_bkp_key, user.crypto_rec_key = GCE.generate_recovery_key(user_session.cc)

        user.crypto_prv_key = Base64Encoder.encode(GCE.symmetric_encrypt(key, cc))

        root_config = models.config.ConfigFactory(session, 1)
        crypto_escrow_pub_key_tenant_1 = root_config.get_val('crypto_escrow_pub_key')
        if crypto_escrow_pub_key_tenant_1:
            user.crypto_escrow_bkp1_key = Base64Encoder.encode(GCE.asymmetric_encrypt(crypto_escrow_pub_key_tenant_1, cc))

        if tid != 1:
            crypto_escrow_pub_key_tenant_n = config.get_val('crypto_escrow_pub_key')
            if crypto_escrow_pub_key_tenant_n:
                user.crypto_escrow_bkp2_key = Base64Encoder.encode(GCE.asymmetric_encrypt(crypto_escrow_pub_key_tenant_n, cc))

    reset_token = user_session.properties.get('reset_token')
    if reset_token:
        filepath = os.path.abspath(os.path.join(State.settings.ramdisk_path, sha256(reset_token).decode()))
        directory_traversal_check(State.settings.ramdisk_path, filepath)
        srm(filepath)
        del user_session.properties['reset_token']

    # Once the forced/reset change is performed the session is no longer exempt
    # from confirmation: a subsequent voluntary change must prove the credential.
    user_session.properties.pop('password_change_needed', None)

    db_log(session, tid=tid, type='change_password', user_id=user.id, object_id=user.id)

    user_session.cc = cc


@transact
def get_users_names(session, tid):
    ret = {}

    for user_id, user_name in session.query(models.User.id, models.User.name) \
                                     .filter(models.User.tid == tid):
        ret[user_id] = user_name

    return ret


@transact
def get_recovery_key(session, tid, user_id, user_cc):
    """
    Transaction to get a user recovery key

    :param session: An ORM session
    :param tid: The tenant ID
    :param user_id: The user ID
    :param user_cc: The user key
    :return: The recovery key encoded base32
    """
    user = db_get_user(session, tid, user_id)

    if not user.crypto_rec_key:
        return ''

    user.clicked_recovery_key = True

    db_log(session, tid=tid, type='access_recovery_key', user_id=user.id)

    return Base32Encoder.encode(GCE.asymmetric_decrypt(user_cc, Base64Encoder.decode(user.crypto_rec_key.encode()))).replace(b'=', b'')


@transact
def enable_2fa(session, tid, user_id, obj_id, secret, token):
    """
    Transact for the first step of 2fa enrollment (completion)

    :param session: An ORM session
    :param tid: A tenant ID
    :param user_id: A user ID
    :param obj_id: A user ID
    :param secret: A two factor secret
    :param token: The current two factor token
    """
    user = db_get_user(session, tid, obj_id)

    try:
        State.totp_verify(secret, token)
    except Exception:
        raise errors.InvalidTwoFactorAuthCode

    user.two_factor_secret = secret

    db_log(session, tid=tid, type='enable_2fa', user_id=user_id, object_id=obj_id)


@transact
def disable_2fa(session, tid, user_id, obj_id):
    """
    Transaction for disabling the two factor authentication

    :param session: An ORM session
    :param tid: A tenant ID
    :param user_id: A user ID
    :param obj_id: A user ID
    """
    user = db_get_user(session, tid, obj_id)

    user.two_factor_secret = ''

    db_log(session, tid=tid, type='disable_2fa', user_id=user_id, object_id=obj_id)


@transact
def accepted_privacy_policy(session, tid, user_id):
    """
    Transaction for disabling the two factor authentication

    :param session:
    :param tid:
    :param user_id:
    """
    user = db_get_user(session, tid, user_id)
    user.accepted_privacy_policy = datetime_now()


class UserOperationHandler(OperationHandler):
    check_roles = 'user'

    @property
    def require_confirmation(self):
        # A voluntary password change requires confirmation of the current
        # credential; the forced and reset flows (flagged on the session) are
        # exempt, as the user does not know the current password.
        ops = ['disable_2fa', 'get_recovery_key']

        if not self.session.properties.get('password_change_needed'):
            ops.append('change_password')

        return ops

    def change_password(self, req_args, *args, **kwargs):
        return change_password(self.session.user_tid,
                               self.session,
                               req_args['password'])

    def get_users_names(self, req_args, *args, **kwargs):
        return get_users_names(self.session.user_tid)

    def get_recovery_key(self, req_args, *args, **kwargs):
        return get_recovery_key(self.session.user_tid,
                                self.session.user_id,
                                self.session.cc)

    def enable_2fa(self, req_args, *args, **kwargs):
        d = enable_2fa(self.session.user_tid,
                       self.session.user_id,
                       self.session.user_id,
                       req_args['secret'],
                       req_args['token'])

        def clear_require_two_factor(_):
            self.session.properties.pop('require_two_factor', None)

        d.addCallback(clear_require_two_factor)
        return d

    def disable_2fa(self, req_args, *args, **kwargs):
        return disable_2fa(self.session.user_tid,
                           self.session.user_id,
                           self.session.user_id)

    def accepted_privacy_policy(self, req_args, *args, **kwargs):
        return accepted_privacy_policy(self.session.user_tid,
                                       self.session.user_id)

    def operation_descriptors(self):
        if self.session.properties.get('reset_token') or \
           self.session.properties.get('password_change_needed'):
            # A session pending a forced/reset password change may only change the password
            return {'change_password': UserOperationHandler.change_password}

        if self.session.properties.get('require_two_factor'):
            # A session pending mandatory two-factor enrollment may only enable 2fa
            return {'enable_2fa': UserOperationHandler.enable_2fa}

        return {
            'change_password': UserOperationHandler.change_password,
            'get_users_names': UserOperationHandler.get_users_names,
            'get_recovery_key': UserOperationHandler.get_recovery_key,
            'enable_2fa': UserOperationHandler.enable_2fa,
            'disable_2fa': UserOperationHandler.disable_2fa,
            'accepted_privacy_policy': UserOperationHandler.accepted_privacy_policy
        }
