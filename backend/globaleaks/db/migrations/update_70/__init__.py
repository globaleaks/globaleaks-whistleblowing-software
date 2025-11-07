from globaleaks.db.migrations.update import MigrationBase
from globaleaks.models import Model, EnumUserRole
from globaleaks.models.properties import *
from globaleaks.utils.utility import datetime_now, datetime_null


from globaleaks.db.migrations.update import MigrationBase


class InternalTipAnswers_v_69(Model):
    """
    This is the internal representation of Tip Questionnaire Answers
    """
    __tablename__ = 'internaltipanswers'

    internaltip_id = Column(UnicodeText(36), primary_key=True)
    questionnaire_hash = Column(UnicodeText(64), primary_key=True)
    creation_date = Column(DateTime, default=datetime_now, nullable=False)
    answers = Column(UnicodeText, default='{}', nullable=False)
    stat_answers = Column(UnicodeText, default='{}', nullable=False)


class User_v_69(Model):
    """
    This model keeps track of users.
    """
    __tablename__ = 'user'

    id = Column(UnicodeText(36), primary_key=True, default=uuid4)
    tid = Column(Integer, default=1, nullable=False)
    creation_date = Column(DateTime, default=datetime_now, nullable=False)
    username = Column(UnicodeText, default='', nullable=False)
    salt = Column(UnicodeText(24), default='', nullable=False)
    hash = Column(UnicodeText(64), default='', nullable=False)
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
    crypto_global_stat_prv_key = Column(UnicodeText(84), default='', nullable=True)
    crypto_escrow_prv_key = Column(UnicodeText(84), default='', nullable=False)
    crypto_escrow_bkp1_key = Column(UnicodeText(84), default='', nullable=False)
    crypto_escrow_bkp2_key = Column(UnicodeText(84), default='', nullable=False)
    crypto_global_stat_prv_key = Column(UnicodeText(84), default='', nullable=True)
    change_email_address = Column(UnicodeText, default='', nullable=False)
    change_email_token = Column(UnicodeText, unique=True)
    change_email_date = Column(DateTime, default=datetime_null, nullable=False)
    notification = Column(Boolean, default=True, nullable=False)
    forcefully_selected = Column(Boolean, default=False, nullable=False)
    can_delete_submission = Column(Boolean, default=False, nullable=False)
    can_postpone_expiration = Column(Boolean, default=True, nullable=False)
    can_grant_access_to_reports = Column(Boolean, default=False, nullable=False)
    can_transfer_access_to_reports = Column(Boolean, default=False, nullable=False)
    can_download_infected = Column(Boolean, default=False, nullable=False)
    can_redact_information = Column(Boolean, default=False, nullable=False)
    can_mask_information = Column(Boolean, default=True, nullable=False)
    can_reopen_reports = Column(Boolean, default=True, nullable=False)
    can_edit_general_settings = Column(Boolean, default=False, nullable=False)
    readonly = Column(Boolean, default=False, nullable=False)
    two_factor_secret = Column(UnicodeText(32), default='', nullable=False)
    reminder_date = Column(DateTime, default=datetime_null, nullable=False)
    pgp_key_fingerprint = Column(UnicodeText, default='', nullable=False)
    pgp_key_public = Column(UnicodeText, default='', nullable=False)
    pgp_key_expiration = Column(DateTime, default=datetime_null, nullable=False)
    accepted_privacy_policy = Column(DateTime, default=datetime_null, nullable=False)
    clicked_recovery_key = Column(Boolean, default=False, nullable=False)


class MigrationScript(MigrationBase):
    renamed_attrs = {
        'User': {'crypto_stat_prv_key': 'crypto_global_stat_prv_key'},
    }

    def migrate_Config(self):
        for old_obj in self.session_old.query(self.model_from['Config']):
            new_obj = self.model_to['Config']()
            for key in new_obj.__mapper__.column_attrs.keys():
                setattr(new_obj, key, getattr(old_obj, key))

            if old_obj.var_name == 'crypto_global_stat_prv_key':
                new_obj.var_name = 'crypto_stat_prv_key'
                new_obj.value = old_obj.value
            elif old_obj.var_name == 'crypto_global_stat_pub_key':
                new_obj.var_name = 'crypto_stat_pub_key'
                new_obj.value = old_obj.value

            self.session_new.add(new_obj)
