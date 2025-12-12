# -*- coding: UTF-8 -*-
from globaleaks.models.enums import EnumFieldInstance, EnumUserRole, EnumUserStatus
from globaleaks.db.migrations.update import MigrationBase
from globaleaks.models import Model
from globaleaks.models.properties import *
from globaleaks.utils.utility import datetime_now, datetime_null

class User_v_71(Model):
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
    change_email_address = Column(UnicodeText, default='', nullable=False)
    change_email_token = Column(UnicodeText, unique=True)
    change_email_date = Column(DateTime, default=datetime_null, nullable=False)
    notification = Column(Boolean, default=True, nullable=False)
    forcefully_selected = Column(Boolean, default=False, nullable=False)
    two_factor_secret = Column(UnicodeText(32), default='', nullable=False)
    reminder_date = Column(DateTime, default=datetime_null, nullable=False)
    profile_id = Column(Integer, default='', nullable=False)
    status = Column(Enum(EnumUserStatus), default='active', nullable=False)
    idp_id = Column(UnicodeText(18), default='', nullable=False)
    pgp_key_fingerprint = Column(UnicodeText, default='', nullable=False)
    pgp_key_public = Column(UnicodeText, default='', nullable=False)
    pgp_key_expiration = Column(DateTime, default=datetime_null, nullable=False)

    accepted_privacy_policy = Column(DateTime, default=datetime_null, nullable=False)
    clicked_recovery_key = Column(Boolean, default=False, nullable=False)

class UserProfile_v_71(Model):
    __tablename__ = 'user_profile'

    id = Column(UnicodeText(36), primary_key=True, default=uuid4)
    tid = Column(Integer, default=1, nullable=False)
    name = Column(UnicodeText, default='', nullable=False)
    role = Column(Enum(EnumUserRole), default='receiver', nullable=False)

class Field_v_71(Model):
    __tablename__ = 'field'

    id = Column(UnicodeText(36), primary_key=True, default=uuid4)
    tid = Column(Integer, default=1, nullable=False)
    x = Column(Integer, default=0, nullable=False)
    y = Column(Integer, default=0, nullable=False)
    width = Column(Integer, default=0, nullable=False)
    label = Column(JSON, default=dict, nullable=False)
    description = Column(JSON, default=dict, nullable=False)
    hint = Column(JSON, default=dict, nullable=False)
    placeholder = Column(JSON, default=dict, nullable=False)
    required = Column(Boolean, default=False, nullable=False)
    multi_entry = Column(Boolean, default=False, nullable=False)
    triggered_by_score = Column(Integer, default=0, nullable=False)
    step_id = Column(UnicodeText(36), index=True)
    fieldgroup_id = Column(UnicodeText(36), index=True)
    type = Column(UnicodeText, default='inputbox', nullable=False)
    instance = Column(Enum(EnumFieldInstance), default='instance', nullable=False)
    template_id = Column(UnicodeText(36), index=True)
    template_override_id = Column(UnicodeText(36), index=True)
    statistical = Column(Boolean, default=False, nullable=False)

class Questionnaire_v_71(Model):
    __tablename__ = 'questionnaire'

    id = Column(UnicodeText(36), primary_key=True, default=uuid4)
    tid = Column(Integer, default=1, nullable=False)
    name = Column(UnicodeText, default='', nullable=False)

class Step_v_71(Model):
    __tablename__ = 'step'

    id = Column(UnicodeText(36), primary_key=True, default=uuid4)
    questionnaire_id = Column(UnicodeText(36), nullable=False, index=True)
    label = Column(JSON, default=dict, nullable=False)
    description = Column(JSON, default=dict, nullable=False)
    triggered_by_score = Column(Integer, default=0, nullable=False)
    order = Column(Integer, default=0, nullable=False)


class MigrationScript(MigrationBase):
   
    skip_count_check = {
        'Config': True,
        'ConfigL10N': True,
        'EnabledLanguage': True,
        'User': True,
        'Field': True,
        'Questionnaire': True,
        'Step': True
    }

    def migrate_Config(self):
        for old_obj in self.session_old.query(self.model_from['Config']):
            new_obj = self.model_to['Config']()
            for key in new_obj.__mapper__.column_attrs.keys():
                if hasattr(old_obj, key):
                    setattr(new_obj, key, getattr(old_obj, key))
                elif key == 'etag':
                    # Add etag for new schema since old doesn't have it
                    setattr(new_obj, key, str(uuid4()))
            
            self.session_new.add(new_obj)

    def migrate_User(self):
        for old_obj in self.session_old.query(self.model_from['User']):
            new_obj = self.model_to['User']()
            for key in new_obj.__mapper__.column_attrs.keys():
                if hasattr(old_obj, key):
                    setattr(new_obj, key, getattr(old_obj, key))
                elif key == 'etag':
                    # Add etag for new schema since old doesn't have it
                    setattr(new_obj, key, str(uuid4()))
            
            self.session_new.add(new_obj)

    def migrate_UserProfile(self):
        for old_obj in self.session_old.query(self.model_from['UserProfile']):
            new_obj = self.model_to['UserProfile']()
            for key in new_obj.__mapper__.column_attrs.keys():
                if hasattr(old_obj, key):
                    setattr(new_obj, key, getattr(old_obj, key))
                elif key == 'etag':
                    # Add etag for new schema since old doesn't have it
                    setattr(new_obj, key, str(uuid4()))
            
            self.session_new.add(new_obj)

    def migrate_Field(self):
        for old_obj in self.session_old.query(self.model_from['Field']):
            new_obj = self.model_to['Field']()
            for key in new_obj.__mapper__.column_attrs.keys():
                if hasattr(old_obj, key):
                    setattr(new_obj, key, getattr(old_obj, key))
                elif key == 'etag':
                    # Add etag for new schema since old doesn't have it
                    setattr(new_obj, key, str(uuid4()))
            
            self.session_new.add(new_obj)

    def migrate_Questionnaire(self):
        for old_obj in self.session_old.query(self.model_from['Questionnaire']):
            new_obj = self.model_to['Questionnaire']()
            for key in new_obj.__mapper__.column_attrs.keys():
                if hasattr(old_obj, key):
                    setattr(new_obj, key, getattr(old_obj, key))
                elif key == 'etag':
                    # Add etag for new schema since old doesn't have it
                    setattr(new_obj, key, str(uuid4()))
            
            self.session_new.add(new_obj)

    def migrate_Step(self):
        for old_obj in self.session_old.query(self.model_from['Step']):
            new_obj = self.model_to['Step']()
            for key in new_obj.__mapper__.column_attrs.keys():
                if hasattr(old_obj, key):
                    setattr(new_obj, key, getattr(old_obj, key))
                elif key == 'etag':
                    # Add etag for new schema since old doesn't have it
                    setattr(new_obj, key, str(uuid4()))
            
            self.session_new.add(new_obj)

    def epilogue(self):
        """
        Optional post-migration operations
        """
        pass
   
    # skip_count_check = {
    #     'Config': True,
    #     'ConfigL10N': True,
    #     'EnabledLanguage': True,
    #     'User': True,
    #     'Field': True,
    #     'Questionnaire': True,
    #     'Step': True
    # }

    # def migrate_Config(self):
    #     for old_obj in self.session_old.query(self.model_from['Config']):
    #         new_obj = self.model_to['Config']()
    #         for key in new_obj.__mapper__.column_attrs.keys():
    #             setattr(new_obj, key, getattr(old_obj, key))

    #         # if not old_obj.etag:
    #         #     new_obj.etag = uuid4()

    #         self.session_new.add(new_obj)

    # def migrate_User(self):
    #     for old_obj in self.session_old.query(self.model_from['User']):
    #         new_obj = self.model_to['User']()
    #         for key in new_obj.__mapper__.column_attrs.keys():
    #             setattr(new_obj, key, getattr(old_obj, key))

    #         if not old_obj.etag:
    #             new_obj.etag = uuid4()

    #         self.session_new.add(new_obj)

    # def migrate_UserProfile(self):
    #     print("llllllllll")
    #     print("llllllllll")
    #     print("llllllllll")
    #     print("llllllllll")
    #     for old_obj in self.session_old.query(self.model_from['UserProfile']):
    #         new_obj = self.model_to['UserProfile']()
    #         for key in new_obj.__mapper__.column_attrs.keys():
    #             setattr(new_obj, key, getattr(old_obj, key))

    #         if not old_obj.etag:
    #             new_obj.etag = uuid4()

    #         self.session_new.add(new_obj)

    # def migrate_Field(self):
    #     print('bbbbbbbbbb')
    #     print('bbbbbbbbbb')
    #     print('bbbbbbbbbb')
    #     print('bbbbbbbbbb')
    #     print('bbbbbbbbbb')
    #     for old_obj in self.session_old.query(self.model_from['Field']):
    #         new_obj = self.model_to['Field']()
    #         for key in new_obj.__mapper__.column_attrs.keys():
    #             setattr(new_obj, key, getattr(old_obj, key))

    #         if not old_obj.etag:
    #             new_obj.etag = uuid4()

    #         self.session_new.add(new_obj)

    # def migrate_Questionnaire(self):
    #     for old_obj in self.session_old.query(self.model_from['Questionnaire']):
    #         new_obj = self.model_to['Questionnaire']()
    #         for key in new_obj.__mapper__.column_attrs.keys():
    #             setattr(new_obj, key, getattr(old_obj, key))

    #         if not old_obj.etag:
    #             new_obj.etag = uuid4()

    #         self.session_new.add(new_obj)

    # def migrate_Step(self):
    #     for old_obj in self.session_old.query(self.model_from['Step']):
    #         new_obj = self.model_to['Step']()
    #         for key in new_obj.__mapper__.column_attrs.keys():
    #             setattr(new_obj, key, getattr(old_obj, key))

    #         if not old_obj.etag:
    #             new_obj.etag = uuid4()

    #         self.session_new.add(new_obj)

    # def epilogue(self):
    #     """
    #     Optional post-migration operations
    #     """
    #     pass