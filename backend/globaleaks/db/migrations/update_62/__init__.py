# -*- coding: UTF-8
from globaleaks.models import Model
from globaleaks.models.enums import EnumUserRole
from globaleaks.models.properties import Boolean, Column, DateTime, Enum, Integer, JSON, UnicodeText, uuid4
from globaleaks.db.migrations.update import MigrationBase
from globaleaks.utils.utility import datetime_now, datetime_null


class AuditLog_v_61(Model):
    __tablename__ = 'auditlog'

    id = Column(UnicodeText, primary_key=True, default=uuid4)
    tid = Column(Integer, default=1)
    date = Column(DateTime, default=datetime_now, nullable=False)
    type = Column(UnicodeText(24), default='', nullable=False)
    user_id = Column(UnicodeText(36), nullable=True)
    object_id = Column(UnicodeText(36), nullable=True)
    data = Column(JSON, nullable=True)


class Context_v_61(Model):
    __tablename__ = 'context'

    id = Column(UnicodeText(36), primary_key=True, default=uuid4)
    tid = Column(Integer, default=1, nullable=False)
    show_steps_navigation_interface = Column(Boolean, default=True, nullable=False)
    allow_recipients_selection = Column(Boolean, default=False, nullable=False)
    maximum_selectable_receivers = Column(Integer, default=0, nullable=False)
    select_all_receivers = Column(Boolean, default=True, nullable=False)
    tip_timetolive = Column(Integer, default=90, nullable=False)
    name = Column(JSON, default=dict, nullable=False)
    description = Column(JSON, default=dict, nullable=False)
    show_receivers_in_alphabetical_order = Column(Boolean, default=True, nullable=False)
    score_threshold_high = Column(Integer, default=0, nullable=False)
    score_threshold_medium = Column(Integer, default=0, nullable=False)
    questionnaire_id = Column(UnicodeText(36), default='default', nullable=False)
    additional_questionnaire_id = Column(UnicodeText(36))
    status = Column(Integer, default=2, nullable=False)
    order = Column(Integer, default=0, nullable=False)


class ReceiverTip_v_61(Model):
    __tablename__ = 'receivertip'

    id = Column(UnicodeText(36), primary_key=True, default=uuid4)
    internaltip_id = Column(UnicodeText(36), nullable=False)
    receiver_id = Column(UnicodeText(36), nullable=False, index=True)
    access_date = Column(DateTime, default=datetime_null, nullable=False)
    last_access = Column(DateTime, default=datetime_null, nullable=False)
    new = Column(Boolean, default=True, nullable=False)
    enable_notifications = Column(Boolean, default=True, nullable=False)
    crypto_tip_prv_key = Column(UnicodeText(84), default='', nullable=False)
    crypto_files_prv_key = Column(UnicodeText(84), default='', nullable=False)


class User_v_61(Model):
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
    state = Column(Integer, default=1, nullable=False)
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
    can_postpone_expiration = Column(Boolean, default=False, nullable=False)
    can_grant_access_to_reports = Column(Boolean, default=False, nullable=False)
    can_edit_general_settings = Column(Boolean, default=False, nullable=False)
    readonly = Column(Boolean, default=False, nullable=False)
    two_factor_secret = Column(UnicodeText(32), default='', nullable=False)
    reminder_date = Column(DateTime, default=datetime_null, nullable=False)
    pgp_key_fingerprint = Column(UnicodeText, default='', nullable=False)
    pgp_key_public = Column(UnicodeText, default='', nullable=False)
    pgp_key_expiration = Column(DateTime, default=datetime_null, nullable=False)
    clicked_recovery_key = Column(Boolean, default=False, nullable=False)


class MigrationScript(MigrationBase):
    def migrate_AuditLog(self):
        for old_obj in self.session_old.query(self.model_from['AuditLog']):
            new_obj = self.model_to['AuditLog']()
            for key in new_obj.__mapper__.column_attrs.keys():
                if key != 'id':
                    setattr(new_obj, key, getattr(old_obj, key))

            self.session_new.add(new_obj)

    def migrate_Context(self):
        for old_obj in self.session_old.query(self.model_from['Context']):
            new_obj = self.model_to['Context']()
            for key in new_obj.__mapper__.column_attrs.keys():
                if key == 'hidden':
                    setattr(new_obj, key, getattr(old_obj, 'status') != 'enabled')
                else:
                    setattr(new_obj, key, getattr(old_obj, key))

            self.session_new.add(new_obj)

    def migrate_InternalTip(self):
        ctx_ids = [c[0] for c in self.session_old.query(self.model_from['Context'].id).all()]

        for old_obj in self.session_old.query(self.model_from['InternalTip']):
            new_obj = self.model_to['InternalTip']()
            for key in new_obj.__mapper__.column_attrs.keys():
                if key == 'context_id' and old_obj.context_id not in ctx_ids:
                    setattr(new_obj, key, ctx_ids[0])
                else:
                    setattr(new_obj, key, getattr(old_obj, key))

            self.session_new.add(new_obj)

    def migrate_User(self):
        for old_obj in self.session_old.query(self.model_from['User']):
            new_obj = self.model_to['User']()
            for key in new_obj.__mapper__.column_attrs.keys():
                if key == 'enabled':
                    setattr(new_obj, key, getattr(old_obj, 'state') == 1)
                else:
                    setattr(new_obj, key, getattr(old_obj, key))

            self.session_new.add(new_obj)
