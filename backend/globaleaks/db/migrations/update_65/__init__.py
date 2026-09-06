# -*- coding: UTF-8
import os
import shutil

from nacl.encoding import Base64Encoder

from globaleaks.db.migrations.update import MigrationBase
from globaleaks.models import Model
from globaleaks.models.enums import _Enum, EnumUserRole
from globaleaks.models.properties import Boolean, Column, DateTime, Enum, Integer, JSON, UnicodeText, uuid4
from globaleaks.settings import Settings
from globaleaks.utils.crypto import GCE
from globaleaks.utils.tls import gen_selfsigned_certificate
from globaleaks.utils.utility import datetime_never, datetime_now, datetime_null


class EnumMessageType(_Enum):
    whistleblower = 0
    receiver = 1


class CommentV64(Model):
    __tablename__ = 'comment'
    id = Column(UnicodeText(36), primary_key=True, default=uuid4)
    creation_date = Column(DateTime, default=datetime_now, nullable=False)
    internaltip_id = Column(UnicodeText(36), nullable=False, index=True)
    author_id = Column(UnicodeText(36))
    content = Column(UnicodeText, nullable=False)
    new = Column(Boolean, default=True, nullable=False)


class MessageV64(Model):
    __tablename__ = 'message'
    id = Column(UnicodeText(36), primary_key=True, default=uuid4)
    creation_date = Column(DateTime, default=datetime_now, nullable=False)
    receivertip_id = Column(UnicodeText(36), nullable=False, index=True)
    content = Column(UnicodeText, nullable=False)
    type = Column(Enum(EnumMessageType), nullable=False)
    new = Column(Boolean, default=True, nullable=False)


class IdentityAccessRequestV64(Model):
    __tablename__ = 'identityaccessrequest'
    id = Column(UnicodeText(36), primary_key=True, default=uuid4)
    receivertip_id = Column(UnicodeText(36), nullable=False, index=True)
    request_date = Column(DateTime, default=datetime_now, nullable=False)
    request_motivation = Column(UnicodeText, default='')
    reply_date = Column(DateTime, default=datetime_null, nullable=False)
    reply_user_id = Column(UnicodeText(36), default='', nullable=False)
    reply_motivation = Column(UnicodeText, default='', nullable=False)
    reply = Column(UnicodeText, default='pending', nullable=False)


class InternalFileV64(Model):
    __tablename__ = 'internalfile'
    id = Column(UnicodeText(36), primary_key=True, default=uuid4)
    creation_date = Column(DateTime, default=datetime_now, nullable=False)
    internaltip_id = Column(UnicodeText(36), nullable=False, index=True)
    name = Column(UnicodeText, nullable=False)
    filename = Column(UnicodeText, default='', nullable=False)
    content_type = Column(JSON, default='', nullable=False)
    size = Column(JSON, default='', nullable=False)
    new = Column(Boolean, default=True, nullable=False)


class InternalTipV64(Model):
    __tablename__ = 'internaltip'
    id = Column(UnicodeText(36), primary_key=True, default=uuid4)
    tid = Column(Integer, default=1, nullable=False)
    creation_date = Column(DateTime, default=datetime_now, nullable=False)
    update_date = Column(DateTime, default=datetime_now, nullable=False)
    context_id = Column(UnicodeText(36), nullable=False)
    progressive = Column(Integer, default=0, nullable=False)
    tor = Column(Boolean, default=False, nullable=False)
    mobile = Column(Boolean, default=False, nullable=False)
    score = Column(Integer, default=0, nullable=False)
    expiration_date = Column(DateTime, default=datetime_never, nullable=False)
    reminder_date = Column(DateTime, default=datetime_never, nullable=False)
    enable_whistleblower_identity = Column(Boolean, default=False, nullable=False)
    important = Column(Boolean, default=False, nullable=False)
    label = Column(UnicodeText, default='', nullable=False)
    last_access = Column(DateTime, default=datetime_now, nullable=False)
    status = Column(UnicodeText(36), nullable=True)
    substatus = Column(UnicodeText(36), nullable=True)
    receipt_hash = Column(UnicodeText(128), nullable=False)
    crypto_prv_key = Column(UnicodeText(84), default='', nullable=False)
    crypto_pub_key = Column(UnicodeText(56), default='', nullable=False)
    crypto_tip_pub_key = Column(UnicodeText(56), default='', nullable=False)
    crypto_tip_prv_key = Column(UnicodeText(84), default='', nullable=False)
    crypto_files_pub_key = Column(UnicodeText(56), default='', nullable=False)


class ReceiverTipV64(Model):
    __tablename__ = 'receivertip'
    id = Column(UnicodeText(36), primary_key=True, default=uuid4)
    internaltip_id = Column(UnicodeText(36), nullable=False)
    receiver_id = Column(UnicodeText(36), nullable=False, index=True)
    access_date = Column(DateTime, default=datetime_null, nullable=False)
    last_access = Column(DateTime, default=datetime_null, nullable=False)
    last_notification = Column(DateTime, default=datetime_null, nullable=False)
    new = Column(Boolean, default=True, nullable=False)
    enable_notifications = Column(Boolean, default=True, nullable=False)
    crypto_tip_prv_key = Column(UnicodeText(84), default='', nullable=False)
    crypto_files_prv_key = Column(UnicodeText(84), default='', nullable=False)



class ReceiverFileV64(Model):
    __tablename__ = 'whistleblowerfile'
    id = Column(UnicodeText(36), primary_key=True, default=uuid4)
    receivertip_id = Column(UnicodeText(36), nullable=False, index=True)
    name = Column(UnicodeText, nullable=False)
    filename = Column(UnicodeText(255), unique=True, nullable=False)
    size = Column(Integer, nullable=False)
    content_type = Column(UnicodeText, nullable=False)
    creation_date = Column(DateTime, default=datetime_now, nullable=False)
    access_date = Column(DateTime, default=datetime_null, nullable=False)
    description = Column(UnicodeText, nullable=False)
    new = Column(Boolean, default=True, nullable=False)


class UserV64(Model):
    __tablename__ = 'user'
    id = Column(UnicodeText(36), primary_key=True, default=uuid4)
    tid = Column(Integer, default=1, nullable=False)
    creation_date = Column(DateTime, default=datetime_now, nullable=False)
    username = Column(UnicodeText, default='', nullable=False)
    salt = Column(UnicodeText(24), default='', nullable=False)
    password = Column(UnicodeText, default='', nullable=False)
    name = Column(UnicodeText, default='', nullable=False)
    description = Column(JSON, default=dict, nullable=False)
    public_name = Column(UnicodeText, default='', nullable=False)
    role = Column(Enum(EnumUserRole), default='receiver', nullable=False)
    enabled = Column(Boolean, default=True, nullable=False)
    last_login = Column(DateTime, default=datetime_null, nullable=False)
    mail_address = Column(UnicodeText, default='', nullable=False)
    language = Column(UnicodeText(12), nullable=False)
    password_change_needed = Column(Boolean, default=True, nullable=False)
    password_change_date = Column(DateTime, default=datetime_null, nullable=False)
    crypto_prv_key = Column(UnicodeText(84), default='', nullable=False)
    crypto_pub_key = Column(UnicodeText(56), default='', nullable=False)
    crypto_rec_key = Column(UnicodeText(80), default='', nullable=False)
    crypto_bkp_key = Column(UnicodeText(84), default='', nullable=False)
    crypto_escrow_prv_key = Column(UnicodeText(84), default='', nullable=False)
    crypto_escrow_bkp1_key = Column(UnicodeText(84), default='', nullable=False)
    crypto_escrow_bkp2_key = Column(UnicodeText(84), default='', nullable=False)
    change_email_address = Column(UnicodeText, default='', nullable=False)
    change_email_token = Column(UnicodeText, unique=True, nullable=True)
    change_email_date = Column(DateTime, default=datetime_null, nullable=False)
    notification = Column(Boolean, default=True, nullable=False)
    forcefully_selected = Column(Boolean, default=False, nullable=False)
    can_delete_submission = Column(Boolean, default=False, nullable=False)
    can_postpone_expiration = Column(Boolean, default=True, nullable=False)
    can_grant_access_to_reports = Column(Boolean, default=False, nullable=False)
    can_edit_general_settings = Column(Boolean, default=False, nullable=False)
    readonly = Column(Boolean, default=False, nullable=False)
    two_factor_secret = Column(UnicodeText(32), default='', nullable=False)
    reminder_date = Column(DateTime, default=datetime_null, nullable=False)
    pgp_key_fingerprint = Column(UnicodeText, default='', nullable=False)
    pgp_key_public = Column(UnicodeText, default='', nullable=False)
    pgp_key_expiration = Column(DateTime, default=datetime_null, nullable=False)
    clicked_recovery_key = Column(Boolean, default=False, nullable=False)


class WhistleblowerFileV64(Model):
    __tablename__ = 'receiverfile'
    id = Column(UnicodeText(36), primary_key=True, default=uuid4)
    filename = Column(UnicodeText(255), nullable=False)
    internalfile_id = Column(UnicodeText(36), nullable=False, index=True)
    receivertip_id = Column(UnicodeText(36), nullable=False, index=True)
    access_date = Column(DateTime, default=datetime_null, nullable=False)
    new = Column(Boolean, default=True, nullable=False)


class MigrationScript(MigrationBase):
    renamed_attrs = {
        'InternalTip': {'deprecated_crypto_files_pub_key': 'crypto_files_pub_key'},
        'ReceiverTip': {'deprecated_crypto_files_prv_key': 'crypto_files_prv_key'},
        'User': {'hash': 'password'}
    }

    skip_count_check = {
        'Config': True
    }

    def migrate_identity_access_request(self):
        for old_obj, rtip in self.session_old.query(self.model_from['IdentityAccessRequest'], self.model_from['ReceiverTip']) \
                                            .filter(self.model_from['IdentityAccessRequest'].receivertip_id == self.model_from['ReceiverTip'].id):
            new_obj = self.copy('IdentityAccessRequest', old_obj)
            new_obj.internaltip_id = rtip.internaltip_id
            new_obj.request_user_id = rtip.receiver_id

            self.session_new.add(new_obj)

    def migrate_internal_file(self):
        for old_obj in self.session_old.query(self.model_from['InternalFile']):
            srcpath = os.path.abspath(os.path.join(Settings.attachments_path, old_obj.filename))
            dstpath = os.path.abspath(os.path.join(Settings.attachments_path, old_obj.id))

            # written on one line to not impact test coverage
            os.path.exists(srcpath) and shutil.move(srcpath, dstpath)

            self.session_new.add(self.copy('InternalFile', old_obj))

    def migrate_internal_tip(self):
        for old_obj in self.session_old.query(self.model_from['InternalTip']):
            new_obj = self.copy('InternalTip', old_obj)

            if new_obj.crypto_tip_pub_key and new_obj.label:
                new_obj.label = Base64Encoder.encode(GCE.asymmetric_encrypt(new_obj.crypto_tip_pub_key, new_obj.label))

            self.session_new.add(new_obj)

    def migrate_whistleblower_file(self):
        self.entries_count['WhistleblowerFile'] = 0
        for old_obj, old_ifile in self.session_old.query(self.model_from['WhistleblowerFile'], self.model_from['InternalFile']) \
                                                  .filter(self.model_from['WhistleblowerFile'].internalfile_id == self.model_from['InternalFile'].id):
            new_obj = self.copy('WhistleblowerFile', old_obj)

            if old_obj.filename != old_ifile.filename:
                srcpath = os.path.abspath(os.path.join(Settings.attachments_path, old_obj.filename))
                dstpath = os.path.abspath(os.path.join(Settings.attachments_path, old_obj.id))
                os.path.exists(srcpath) and shutil.move(srcpath, dstpath)

            self.session_new.add(new_obj)
            self.entries_count['WhistleblowerFile'] += 1

    def migrate_receiver_file(self):
        for old_obj, r in self.session_old.query(self.model_from['ReceiverFile'], self.model_from['ReceiverTip']) \
                                          .filter(self.model_from['ReceiverFile'].receivertip_id == self.model_from['ReceiverTip'].id):
            new_obj = self.copy('ReceiverFile', old_obj)
            new_obj.internaltip_id = r.internaltip_id

            srcpath = os.path.abspath(os.path.join(Settings.attachments_path, old_obj.filename))
            dstpath = os.path.abspath(os.path.join(Settings.attachments_path, old_obj.id))
            os.path.exists(srcpath) and shutil.move(srcpath, dstpath)

            self.session_new.add(new_obj)

    def epilogue(self):
        key, cert = gen_selfsigned_certificate()

        self.add_entry('Config', self.model_to['Config']({'tid': 1, 'var_name': 'https_selfsigned_key', 'value': key}))
        self.add_entry('Config', self.model_to['Config']({'tid': 1, 'var_name': 'https_selfsigned_cert', 'value': cert}))

        message_model = self.model_from['Message']
        internal_tip_model = self.model_from['InternalTip']
        receiver_tip_model = self.model_from['ReceiverTip']
        for m, i, r in self.session_old.query(message_model, internal_tip_model, receiver_tip_model) \
                                       .filter(message_model.receivertip_id == receiver_tip_model.id,
                                               receiver_tip_model.internaltip_id == internal_tip_model.id):
            new_obj = self.copy('Comment', m)
            new_obj.internaltip_id = i.id
            new_obj.author_id = r.id if m.type == 'receiver' else None

            self.add_entry('Comment', new_obj)

        for old_obj in self.session_old.query(self.model_from['Tenant']):
            srcpath = os.path.abspath(os.path.join(Settings.working_path, 'scripts', str(old_obj.id)))
            new_obj = self.model_to['File']()
            new_obj.tid = old_obj.id
            new_obj.id = uuid4()
            new_obj.name = 'script'
            dstpath = os.path.abspath(os.path.join(Settings.files_path, new_obj.id))
            os.path.exists(srcpath) and shutil.move(srcpath, dstpath) and self.session_new.add(new_obj)
            self.entries_count['File'] += 1 if os.path.exists(dstpath) else 0

        shutil.rmtree(os.path.abspath(os.path.join(Settings.working_path, 'scripts')), ignore_errors=True)

        for iar, itip in self.session_new.query(self.model_to['IdentityAccessRequest'], self.model_to['InternalTip']) \
                                   .filter(self.model_to['IdentityAccessRequest'].internaltip_id == self.model_to['InternalTip'].id):
            for custodian in self.session_new.query(self.model_to['User']) \
                                             .filter(self.model_to['User'].tid == itip.tid, self.model_to['User'].role == 'custodian'):
                iarc = self.model_to['IdentityAccessRequestCustodian']()
                iarc.identityaccessrequest_id = iar.id
                iarc.custodian_id = custodian.id
                self.add_entry('IdentityAccessRequestCustodian', iarc)
