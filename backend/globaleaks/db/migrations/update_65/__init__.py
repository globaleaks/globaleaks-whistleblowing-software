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


class Comment_v_64(Model):
    __tablename__ = 'comment'
    id = Column(UnicodeText(36), primary_key=True, default=uuid4)
    creation_date = Column(DateTime, default=datetime_now, nullable=False)
    internaltip_id = Column(UnicodeText(36), nullable=False, index=True)
    author_id = Column(UnicodeText(36))
    content = Column(UnicodeText, nullable=False)
    new = Column(Boolean, default=True, nullable=False)


class Message_v_64(Model):
    __tablename__ = 'message'
    id = Column(UnicodeText(36), primary_key=True, default=uuid4)
    creation_date = Column(DateTime, default=datetime_now, nullable=False)
    receivertip_id = Column(UnicodeText(36), nullable=False, index=True)
    content = Column(UnicodeText, nullable=False)
    type = Column(Enum(EnumMessageType), nullable=False)
    new = Column(Boolean, default=True, nullable=False)


class IdentityAccessRequest_v_64(Model):
    __tablename__ = 'identityaccessrequest'
    id = Column(UnicodeText(36), primary_key=True, default=uuid4)
    receivertip_id = Column(UnicodeText(36), nullable=False, index=True)
    request_date = Column(DateTime, default=datetime_now, nullable=False)
    request_motivation = Column(UnicodeText, default='')
    reply_date = Column(DateTime, default=datetime_null, nullable=False)
    reply_user_id = Column(UnicodeText(36), default='', nullable=False)
    reply_motivation = Column(UnicodeText, default='', nullable=False)
    reply = Column(UnicodeText, default='pending', nullable=False)


class InternalFile_v_64(Model):
    __tablename__ = 'internalfile'
    id = Column(UnicodeText(36), primary_key=True, default=uuid4)
    creation_date = Column(DateTime, default=datetime_now, nullable=False)
    internaltip_id = Column(UnicodeText(36), nullable=False, index=True)
    name = Column(UnicodeText, nullable=False)
    filename = Column(UnicodeText, default='', nullable=False)
    content_type = Column(JSON, default='', nullable=False)
    size = Column(JSON, default='', nullable=False)
    new = Column(Boolean, default=True, nullable=False)


class InternalTip_v_64(Model):
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


class ReceiverTip_v_64(Model):
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



class ReceiverFile_v_64(Model):
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


class SubmissionStatus_v_64(Model):
    __tablename__ = 'submissionstatus'
    id = Column(UnicodeText(36), primary_key=True, default=uuid4)
    tid = Column(Integer, primary_key=True, default=1)
    label = Column(JSON, default=dict, nullable=False)
    order = Column(Integer, default=0, nullable=False)


class SubmissionSubStatus_v_64(Model):
    __tablename__ = 'submissionsubstatus'
    id = Column(UnicodeText(36), primary_key=True, default=uuid4)
    tid = Column(Integer, primary_key=True, default=1)
    submissionstatus_id = Column(UnicodeText(36), nullable=False)
    label = Column(JSON, default=dict, nullable=False)
    order = Column(Integer, default=0, nullable=False)


class User_v_64(Model):
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


class WhistleblowerFile_v_64(Model):
    __tablename__ = 'receiverfile'
    id = Column(UnicodeText(36), primary_key=True, default=uuid4)
    filename = Column(UnicodeText(255), nullable=False)
    internalfile_id = Column(UnicodeText(36), nullable=False, index=True)
    receivertip_id = Column(UnicodeText(36), nullable=False, index=True)
    access_date = Column(DateTime, default=datetime_null, nullable=False)
    new = Column(Boolean, default=True, nullable=False)


class MigrationScript(MigrationBase):
    renamed_attrs = {
        'ReceiverTip': {'deprecated_crypto_files_prv_key': 'crypto_files_prv_key'},
    }

    skip_count_check = {
        'Config': True
    }

    def migrate_User(self):
        for old_obj in self.session_old.query(self.model_from['User']):
            new_obj = self.model_to['User']()

            for key in new_obj.__mapper__.column_attrs.keys():
                if key == 'hash':
                    setattr(new_obj, key, getattr(old_obj, 'password'))
                elif key in old_obj.__mapper__.column_attrs.keys():
                    setattr(new_obj, key, getattr(old_obj, key))

            self.session_new.add(new_obj)

    def migrate_IdentityAccessRequest(self):
        for old_obj, rtip in self.session_old.query(self.model_from['IdentityAccessRequest'], self.model_from['ReceiverTip']) \
                                            .filter(self.model_from['IdentityAccessRequest'].receivertip_id == self.model_from['ReceiverTip'].id):
            new_obj = self.model_to['IdentityAccessRequest']()
            for key in new_obj.__mapper__.column_attrs.keys():
                if key == 'internaltip_id':
                    setattr(new_obj, key, rtip.internaltip_id)
                    setattr(new_obj, 'request_user_id', rtip.receiver_id)
                elif key in old_obj.__mapper__.column_attrs.keys():
                    setattr(new_obj, key, getattr(old_obj, key))

            self.session_new.add(new_obj)

    def migrate_InternalFile(self):
        for old_obj in self.session_old.query(self.model_from['InternalFile']):
            srcpath = os.path.abspath(os.path.join(Settings.attachments_path, old_obj.filename))
            dstpath = os.path.abspath(os.path.join(Settings.attachments_path, old_obj.id))

            # written on one line to not impact test coverage
            os.path.exists(srcpath) and shutil.move(srcpath, dstpath)

            new_obj = self.model_to['InternalFile']()
            for key in new_obj.__mapper__.column_attrs.keys():
                if key in old_obj.__mapper__.column_attrs.keys():
                    setattr(new_obj, key, getattr(old_obj, key))

            self.session_new.add(new_obj)

    def migrate_InternalTip(self):
        for old_obj in self.session_old.query(self.model_from['InternalTip']):
            new_obj = self.model_to['InternalTip']()
            for key in new_obj.__mapper__.column_attrs.keys():
                if key in old_obj.__mapper__.column_attrs.keys():
                    setattr(new_obj, key, getattr(old_obj, key))
                elif key == 'deprecated_crypto_files_pub_key':
                    new_obj.deprecated_crypto_files_pub_key = old_obj.crypto_files_pub_key

            if new_obj.crypto_tip_pub_key and new_obj.label:
                new_obj.label = Base64Encoder.encode(GCE.asymmetric_encrypt(new_obj.crypto_tip_pub_key, new_obj.label))

            self.session_new.add(new_obj)

    def migrate_WhistleblowerFile(self):
        self.entries_count['WhistleblowerFile'] = 0
        for old_obj, old_ifile in self.session_old.query(self.model_from['WhistleblowerFile'], self.model_from['InternalFile']) \
                                                  .filter(self.model_from['WhistleblowerFile'].internalfile_id == self.model_from['InternalFile'].id):
            new_obj = self.model_to['WhistleblowerFile']()
            for key in new_obj.__mapper__.column_attrs.keys():
                if key in old_obj.__mapper__.column_attrs.keys():
                    setattr(new_obj, key, getattr(old_obj, key))

            if old_obj.filename != old_ifile.filename:
                srcpath = os.path.abspath(os.path.join(Settings.attachments_path, old_obj.filename))
                dstpath = os.path.abspath(os.path.join(Settings.attachments_path, old_obj.id))
                os.path.exists(srcpath) and shutil.move(srcpath, dstpath)

            self.session_new.add(new_obj)
            self.entries_count['WhistleblowerFile'] += 1

    def migrate_ReceiverFile(self):
        for old_obj, r in self.session_old.query(self.model_from['ReceiverFile'], self.model_from['ReceiverTip']) \
                                          .filter(self.model_from['ReceiverFile'].receivertip_id == self.model_from['ReceiverTip'].id):
            new_obj = self.model_to['ReceiverFile']()
            for key in new_obj.__mapper__.column_attrs.keys():
                if key == 'internaltip_id':
                    setattr(new_obj, key, r.internaltip_id)
                elif key in old_obj.__mapper__.column_attrs.keys():
                    setattr(new_obj, key, getattr(old_obj, key))

            srcpath = os.path.abspath(os.path.join(Settings.attachments_path, old_obj.filename))
            dstpath = os.path.abspath(os.path.join(Settings.attachments_path, old_obj.id))
            os.path.exists(srcpath) and shutil.move(srcpath, dstpath)

            self.session_new.add(new_obj)

    def epilogue(self):
        key, cert = gen_selfsigned_certificate()

        new_conf = self.model_to['Config']()
        new_conf.var_name = 'https_selfsigned_key'
        new_conf.value = key
        self.session_new.add(new_conf)

        new_conf = self.model_to['Config']()
        new_conf.var_name = 'https_selfsigned_cert'
        new_conf.value = cert
        self.session_new.add(new_conf)

        self.entries_count['Config'] += 2

        m = self.model_from['Message']
        i = self.model_from['InternalTip']
        r = self.model_from['ReceiverTip']
        for m, i, r in self.session_old.query(m, i, r) \
                                       .filter(m.receivertip_id == r.id,
                                               r.internaltip_id == i.id):
            new_obj = self.model_to['Comment']()
            for key in new_obj.__mapper__.column_attrs.keys():
                if key == 'internaltip_id':
                    setattr(new_obj, key, i.id)
                elif key == 'author_id':
                    if m.type == 'receiver':
                        setattr(new_obj, key, r.id)
                elif key in m.__mapper__.column_attrs.keys():
                    setattr(new_obj, key, getattr(m, key))

            self.session_new.add(new_obj)
            self.entries_count['Comment'] += 1

        for old_obj in self.session_old.query(self.model_from['Tenant']):
            srcpath = os.path.abspath(os.path.join(Settings.working_path, 'scripts', str(old_obj.id)))
            new_obj = self.model_to['File']()
            new_obj.tid = old_obj.id
            new_obj.id = uuid4()
            new_obj.name = 'script'
            dstpath = os.path.abspath(os.path.join(Settings.files_path, new_obj.id))
            os.path.exists(srcpath) and shutil.move(srcpath, dstpath) and self.session_new.add(new_obj)
            self.entries_count['File'] += 1 if os.path.exists(dstpath) else 0

        try:
            shutil.rmtree(os.path.abspath(os.path.join(Settings.working_path, 'scripts')))
        except Exception:
            pass

        for iar, itip in self.session_new.query(self.model_to['IdentityAccessRequest'], self.model_to['InternalTip']) \
                                   .filter(self.model_to['IdentityAccessRequest'].internaltip_id == self.model_to['InternalTip'].id):
            for custodian in self.session_new.query(self.model_to['User']) \
                                             .filter(self.model_to['User'].tid == itip.tid, self.model_to['User'].role == 'custodian'):
                iarc = self.model_to['IdentityAccessRequestCustodian']()
                iarc.identityaccessrequest_id = iar.id
                iarc.custodian_id = custodian.id
                self.session_new.add(iarc)
                self.entries_count['IdentityAccessRequestCustodian'] += 1
