# -*- coding: utf-8
import logging
import os
from twisted.internet.defer import inlineCallbacks, returnValue

from globaleaks import models
from globaleaks.db.appdata import load_appdata
from globaleaks.handlers.admin.node import db_admin_serialize_node
from globaleaks.handlers.admin.notification import db_get_notification
from globaleaks.handlers.operation import OperationHandler
from globaleaks.handlers.user.reset_password import db_generate_password_reset_token
from globaleaks.handlers.user import get_user
from globaleaks.handlers.user.operation import disable_2fa
from globaleaks.models import Config, InternalTip, User
from globaleaks.models.config import db_set_config_variable, ConfigFactory, ConfigL10NFactory
from globaleaks.orm import db_del, db_get, db_log, transact, tw
from globaleaks.rest import errors
from globaleaks.state import State
from globaleaks.transactions import db_get_user
from globaleaks.utils.crypto import Base64Encoder, GCE
from globaleaks.utils.onion import generate_onion_service_v3
from globaleaks.utils.templating import Templating
from globaleaks.utils.utility import datetime_now


@transact
def enable_encryption(session, tid):
    ConfigFactory(session, tid).set_val('encryption', True)


@transact
def check_hostname(session, tid, hostname):
    """
    Ensure the hostname does not collide across tenants or include an origin that it shouldn't.

    :param session: An ORM session
    :param tid: A tenant id
    :param hostname: The hostname to be evaluated
    """
    if hostname == '':
        return

    forbidden_endings = ['onion', 'localhost']

    for v in forbidden_endings:
        if hostname.endswith(v):
            raise errors.InputValidationError('Hostname contains a forbidden origin')

    existing_hostnames = {h.value for h in session.query(Config)
                                                  .filter(Config.tid != tid,
                                                          Config.var_name == 'hostname')}

    if hostname in existing_hostnames:
        raise errors.InputValidationError('Hostname already reserved')


@transact
def set_onion_service_info(session, tid, hostname, key):
    node = ConfigFactory(session, tid)
    node.set_val('onionservice', hostname)
    node.set_val('tor_onion_key', key)


@transact
def reset_submissions(session, tid, user_id):
    """
    Transaction to reset the submissions of the specified tenant

    :param session: An ORM session
    :param tid: A tenant ID
    :param user_id: The id of the user resetting submissions
    """
    session.query(Config).filter(Config.tid == tid, Config.var_name == 'counter_submissions').update({'value': 0})

    db_del(session, InternalTip, InternalTip.tid == tid)

    db_log(session, tid=tid, type='reset_reports', user_id=user_id)


@transact
def toggle_escrow(session, tid, user_session):
    root_config = ConfigFactory(session, 1)

    config = ConfigFactory(session, tid)
    escrow = config.get_val('crypto_escrow_pub_key') != ''

    if not escrow:
        crypto_escrow_prv_key, crypto_escrow_pub_key = GCE.generate_keypair()
        user = db_get(session, models.User, models.User.id == user_session.user_id)

        config.set_val('crypto_escrow_pub_key', crypto_escrow_pub_key)

        if user.tid == tid:
            user_session.ek = user.crypto_escrow_prv_key
            user.crypto_escrow_prv_key = Base64Encoder.encode(GCE.asymmetric_encrypt(user.crypto_pub_key, crypto_escrow_prv_key))

        crypto_escrow_bkp_key = Base64Encoder.encode(GCE.asymmetric_encrypt(crypto_escrow_pub_key, user_session.cc))

        if tid == 1:
            user.crypto_escrow_bkp1_key = crypto_escrow_bkp_key
            session.query(models.User).filter(models.User.id != user_session.user_id).update({'password_change_needed': True}, synchronize_session=False)
        else:
            user.crypto_escrow_bkp2_key = crypto_escrow_bkp_key
            root_config_escrow = root_config.get_val('crypto_escrow_pub_key')
            if root_config_escrow:
                config.set_val('crypto_escrow_prv_key', Base64Encoder.encode(GCE.asymmetric_encrypt(root_config_escrow, crypto_escrow_prv_key)))

            session.query(models.User).filter(models.User.tid == tid, models.User.id != user_session.user_id).update({'password_change_needed': True}, synchronize_session=False)


    else:
        if tid == 1:
            session.query(models.User).update({'crypto_escrow_bkp1_key': ''}, synchronize_session=False)
        else:
            session.query(models.User).update({'crypto_escrow_bkp2_key': ''}, synchronize_session=False)

        session.query(models.User).filter(models.User.tid == tid).update({'crypto_escrow_prv_key': ''}, synchronize_session=False)

        config.set_val('crypto_escrow_pub_key', '')
        config.set_val('crypto_escrow_prv_key', '')


@transact
def toggle_user_escrow(session, tid, user_session, user_id):
    """
    Transaction to toggle key escrow access for user an user given its id

    :param session: An ORM session
    :param tid: A tenant ID
    :param user_session: The current user session
    :param user_id: The user for which togling the key escrow access
    """
    if user_session.user_id == user_id or not user_session.ek:
        return

    user = db_get_user(session, tid, user_id)
    if not user.crypto_pub_key:
        return

    if not user.crypto_escrow_prv_key:
        crypto_escrow_prv_key = GCE.asymmetric_decrypt(user_session.cc, Base64Encoder.decode(user_session.ek))

        if user_session.user_tid == 1 and tid != 1:
            crypto_escrow_prv_key = GCE.asymmetric_decrypt(crypto_escrow_prv_key, Base64Encoder.decode(ConfigFactory(session, tid).get_val('crypto_escrow_prv_key')))

        user.crypto_escrow_prv_key = Base64Encoder.encode(GCE.asymmetric_encrypt(user.crypto_pub_key, crypto_escrow_prv_key))
    else:
        user.crypto_escrow_prv_key = ''


@transact
def enable_user_permission_file_upload(session, tid, user_session):
    """
    Transaction to enable file upload permission for the current user session

    :param session: An ORM session
    :param tid: A tenant ID
    :param user_session: The current user session
    """
    user_session.permissions['can_upload_files'] = True


@transact
def disable_user_permission_file_upload(session, tid, user_session):
    """
    Transaction to disable file upload permission for the current user session

    :param session: An ORM session
    :param tid: A tenant ID
    :param user_session: The current user session
    """
    user_session.permissions['can_upload_files'] = False


def db_reset_smtp_settings(session, tid):
    config = ConfigFactory(session, tid)
    config.set_val('smtp_server', 'mail.globaleaks.org')
    config.set_val('smtp_port', 587)
    config.set_val('smtp_username', 'globaleaks')
    config.set_val('smtp_password', 'globaleaks')
    config.set_val('smtp_source_email', 'notifications@globaleaks.org')
    config.set_val('smtp_security', 'TLS')
    config.set_val('smtp_authentication', True)
    config.set_val('smtp2_server', '')
    config.set_val('smtp2_port', 587)
    config.set_val('smtp2_authentication', False)
    config.set_val('smtp2_username', '')
    config.set_val('smtp2_password', '')
    config.set_val('smtp2_source_email', '')
    config.set_val('smtp2_security', '')


@transact
def reset_smtp_settings(session, tid):
    return db_reset_smtp_settings(session, tid)


@transact
def reset_templates(session, tid):
    ConfigL10NFactory(session, tid).reset('notification', load_appdata())


def db_set_user_password(session, tid, user_session, user_id, password):
    user = db_get_user(session, tid, user_id)

    if password and (not user.crypto_pub_key or user_session.ek):
        if user.crypto_pub_key and user_session.ek:
            enc_key = GCE.derive_key(password.encode(), user.salt)
            crypto_escrow_prv_key = GCE.asymmetric_decrypt(user_session.cc, Base64Encoder.decode(user_session.ek))

            if user_session.user_tid == 1:
                user_cc = GCE.asymmetric_decrypt(crypto_escrow_prv_key, Base64Encoder.decode(user.crypto_escrow_bkp1_key))
            else:
                user_cc = GCE.asymmetric_decrypt(crypto_escrow_prv_key, Base64Encoder.decode(user.crypto_escrow_bkp2_key))

            user.crypto_prv_key = Base64Encoder.encode(GCE.symmetric_encrypt(enc_key, user_cc))

        if len(user.hash) != 44:
            user.salt = GCE.generate_salt()

        user.hash = GCE.hash_password(password, user.salt)
        user.password_change_date = datetime_now()
        user.password_change_needed = True

        db_log(session, tid=tid, type='change_password', user_id=user_session.user_id, object_id=user_id)


@transact
def set_user_password(session, tid, user_session, user_id, password):
  return db_set_user_password(session, tid, user_session, user_id, password)


def set_tmp_key(user_session, user, token):
    crypto_escrow_prv_key = GCE.asymmetric_decrypt(user_session.cc, Base64Encoder.decode(user_session.ek))

    if user_session.user_tid == 1:
        user_cc = GCE.asymmetric_decrypt(crypto_escrow_prv_key, Base64Encoder.decode(user.crypto_escrow_bkp1_key))
    else:
        user_cc = GCE.asymmetric_decrypt(crypto_escrow_prv_key, Base64Encoder.decode(user.crypto_escrow_bkp2_key))

    enc_key = GCE.derive_key(token, user.salt)
    key = Base64Encoder.encode(GCE.symmetric_encrypt(enc_key, user_cc))

    try:
        with open(os.path.abspath(os.path.join(State.settings.ramdisk_path, token)), "ab") as f:
            f.write(b":")
            f.write(key)
    except Exception as e:
        logging.debug(e)


@transact
def generate_password_reset_token(session, tid, user_session, user_id):
    user = session.query(User).filter(User.tid == tid, User.id == user_id).one_or_none()
    if user is None:
        return

    token = db_generate_password_reset_token(session, user)

    if user_session.ek and user.crypto_pub_key:
        set_tmp_key(user_session, user, token)

    db_log(session, tid=tid, type='send_password_reset_email', user_id=user_session.user_id, object_id=user_id)


class AdminOperationHandler(OperationHandler):
    """
    This interface exposes the enable to configure and verify the platform hostname
    """
    check_roles = 'admin'
    invalidate_cache = True

    require_confirmation = [
        'enable_encryption',
        'disable_2fa',
        'toggle_escrow',
        'toggle_user_escrow',
        'enable_user_permission_file_upload',
        'reset_submissions'
    ]

    def enable_encryption(self, req_args, *args, **kwargs):
        return enable_encryption(self.request.tid)

    def reset_smtp_settings(self, req_args, *args, **kwargs):
        return reset_smtp_settings(self.request.tid)

    def disable_2fa(self, req_args, *args, **kwargs):
        return disable_2fa(self.request.tid, self.session.user_id, req_args['value'])

    def set_user_password(self, req_args, *args, **kwargs):
        if self.session.user_id == req_args['user_id']:
            raise errors.ForbiddenOperation

        return set_user_password(self.request.tid,
                                 self.session,
                                 req_args['user_id'],
                                 req_args['password'])

    def send_password_reset_email(self, req_args, *args, **kwargs):
        if self.session.user_id == req_args['value']:
            raise errors.ForbiddenOperation

        return generate_password_reset_token(self.request.tid,
                                             self.session,
                                             req_args['value'])

    @inlineCallbacks
    def reset_onion_private_key(self, req_args, *args, **kargs):
        self.check_root_or_management_session()

        if self.state.tor:
            self.state.tor.unload_onion_service(self.request.tid)

        hostname, key = generate_onion_service_v3()
        yield set_onion_service_info(self.request.tid, hostname, key)

        if self.state.tor:
            yield self.state.tor.load_onion_service(self.request.tid, hostname, key)

        returnValue({
            'onionservice': hostname
        })

    def reset_submissions(self, req_args, *args, **kwargs):
        return reset_submissions(self.request.tid, self.session.user_id)

    @inlineCallbacks
    def set_hostname(self, req_args, *args, **kwargs):
        self.check_root_or_management_session()

        yield check_hostname(self.request.tid, req_args['value'])
        yield tw(db_set_config_variable, self.request.tid, 'hostname', req_args['value'])
        self.state.tenants[self.request.tid].cache.hostname = req_args['value']

    @inlineCallbacks
    def test_mail(self, req_args, *args, **kwargs):
        tid = self.request.tid
        language = self.state.tenants[tid].cache.default_language

        user = yield get_user(self.session.user_tid,
                              self.session.user_id,
                              language)

        data = {
            'type': 'admin_test',
            'node': (yield tw(db_admin_serialize_node, tid, language)),
            'notification': (yield tw(db_get_notification, tid, language)),
            'user': user,
        }

        subject, body = Templating().get_mail_subject_and_body(data)

        yield self.state.sendmail(tid, user['mail_address'], subject, body)

    def toggle_escrow(self, req_args, *args, **kwargs):
        return toggle_escrow(self.request.tid, self.session)

    def toggle_user_escrow(self, req_args, *args, **kwargs):
        return toggle_user_escrow(self.request.tid, self.session, req_args['value'])

    def enable_user_permission_file_upload(self, req_args, *args, **kwargs):
        return enable_user_permission_file_upload(self.request.tid, self.session)

    def disable_user_permission_file_upload(self, req_args, *args, **kwargs):
        return disable_user_permission_file_upload(self.request.tid, self.session)

    def reset_templates(self, req_args):
        return reset_templates(self.request.tid)

    def operation_descriptors(self):
        return {
            'enable_encryption': AdminOperationHandler.enable_encryption,
            'disable_2fa': AdminOperationHandler.disable_2fa,
            'reset_onion_private_key': AdminOperationHandler.reset_onion_private_key,
            'reset_smtp_settings': AdminOperationHandler.reset_smtp_settings,
            'reset_submissions': AdminOperationHandler.reset_submissions,
            'set_user_password': AdminOperationHandler.set_user_password,
            'send_password_reset_email': AdminOperationHandler.send_password_reset_email,
            'set_hostname': AdminOperationHandler.set_hostname,
            'test_mail': AdminOperationHandler.test_mail,
            'toggle_escrow': AdminOperationHandler.toggle_escrow,
            'toggle_user_escrow': AdminOperationHandler.toggle_user_escrow,
            'enable_user_permission_file_upload': AdminOperationHandler.enable_user_permission_file_upload,
            'disable_user_permission_file_upload': AdminOperationHandler.disable_user_permission_file_upload,
            'reset_templates': AdminOperationHandler.reset_templates
        }
