# -*- coding: UTF-8 -*-
from globaleaks.db.migrations.update import MigrationBase
from globaleaks.handlers.admin import tenant, user
from globaleaks.handlers.user import user_permissions
from globaleaks.models import Model
from globaleaks.models.config import get_default
from globaleaks.models.enums import EnumStateFile, EnumVisibility
from globaleaks.models.properties import *
from globaleaks.utils.utility import datetime_now, datetime_null


class Tenant_v_70(Model):
    __tablename__ = 'tenant'
    __table_args__ = {'sqlite_autoincrement': False}

    id = Column(Integer, primary_key=True, autoincrement=False)
    creation_date = Column(DateTime, default=datetime_now, nullable=False)
    active = Column(Boolean, default=False, nullable=False)


class Comment_v_70(Model):
    __tablename__ = 'comment'

    id = Column(UnicodeText(36), primary_key=True, default=uuid4)
    creation_date = Column(DateTime, default=datetime_now, nullable=False)
    internaltip_id = Column(UnicodeText(36), nullable=False, index=True)
    author_id = Column(UnicodeText(36))
    content = Column(UnicodeText, nullable=False)
    visibility = Column(Enum(EnumVisibility), default='public', nullable=False)
    new = Column(Boolean, default=True, nullable=False)


class InternalFile_v_70(Model):
    __tablename__ = 'internalfile'

    id = Column(UnicodeText(36), primary_key=True, default=uuid4)
    creation_date = Column(DateTime, default=datetime_now, nullable=False)
    internaltip_id = Column(UnicodeText(36), nullable=False, index=True)
    name = Column(UnicodeText, nullable=False)
    content_type = Column(JSON, default='', nullable=False)
    size = Column(JSON, default='', nullable=False)
    new = Column(Boolean, default=True, nullable=False)
    reference_id = Column(UnicodeText(36), default='', nullable=False)
    verification_date = Column(DateTime, nullable=True)
    state = Column(Enum(EnumStateFile), default='pending', nullable=False)


class ReceiverFile_v_70(Model):
    __tablename__ = 'receiverfile'

    id = Column(UnicodeText(36), primary_key=True, default=uuid4)
    internaltip_id = Column(UnicodeText(36), nullable=False, index=True)
    author_id = Column(UnicodeText(36))
    name = Column(UnicodeText, nullable=False)
    size = Column(Integer, nullable=False)
    content_type = Column(UnicodeText, nullable=False)
    creation_date = Column(DateTime, default=datetime_now, nullable=False)
    access_date = Column(DateTime, default=datetime_null, nullable=False)
    description = Column(UnicodeText, default="", nullable=False)
    visibility = Column(Enum(EnumVisibility), default='public', nullable=False)
    new = Column(Boolean, default=True, nullable=False)


class MigrationScript(MigrationBase):
    default_tenant_keys = ["subdomain", "onionservice", "https_admin", "https_analyst", "https_cert" ,"wizard_done", "uuid", "mode", "default_language", "name"]

    skip_count_check = {
        'Config': True,
        'ConfigL10N': True,
        'EnabledLanguage': True,
        'SubmissionStatus': True
    }

    def migrate_User(self):
        old_configs = self.session_old.query(self.model_from['User']).all()
        for old_obj in old_configs:
            user_desc = {
                'tid': getattr(old_obj, 'tid'),
                'name': getattr(old_obj, 'name'),
                'role': getattr(old_obj, 'role'),
                'roles': [getattr(old_obj, 'role')],
                'permissions': {}
            }

            for p in user_permissions:
                if getattr(old_obj, p, False):
                    user_desc['permissions'][p] = True

            new_profile = user.db_create_user_profile(self.session_new, user_desc.get("tid"), user_desc)

            new_obj = self.model_to['User']()
            for key in new_obj.__mapper__.column_attrs.keys():
                if hasattr(old_obj, key):
                    setattr(new_obj, key, getattr(old_obj, key))

            new_obj.profile_id = new_profile['id']
            self.session_new.add(new_obj)

    def migrate_Comment(self):
        old_comments = self.session_old.query(self.model_from['Comment']).all()
        new_comments = []

        for old_obj in old_comments:
            new_comment = self.model_to['Comment']()

            for key in new_comment.__mapper__.column_attrs.keys():
                if hasattr(old_obj, key):
                    setattr(new_comment, key, getattr(old_obj, key))

            new_comment.hash_sha256 = ''
            new_comment.hash_sha512 = ''

            new_comments.append(new_comment)

        self.session_new.add_all(new_comments)

    def migrate_InternalFile(self):
        old_rows = self.session_old.query(self.model_from['InternalFile']).all()

        for old in old_rows:
            new = self.model_to['InternalFile']()

            for col in new.__mapper__.column_attrs.keys():
                if hasattr(old, col):
                    setattr(new, col, getattr(old, col))

            new.hash_sha256 = ''
            new.hash_sha512 = ''

            self.session_new.add(new)

    def migrate_ReceiverFile(self):
        old_rows = self.session_old.query(self.model_from['ReceiverFile']).all()

        for old in old_rows:
            new = self.model_to['ReceiverFile']()

            for col in new.__mapper__.column_attrs.keys():
                if hasattr(old, col):
                    setattr(new, col, getattr(old, col))

            new.hash_sha256 = ''
            new.hash_sha512 = ''

            self.session_new.add(new)

    def migrate_Tenant(self):
        old_tenants = self.session_old.query(self.model_from['Tenant']).all()
        new_tenants = []
        for old_obj in old_tenants:
            new_tenant = self.model_to['Tenant']()
            for key in new_tenant.__mapper__.column_attrs.keys():
                setattr(new_tenant, key, getattr(old_obj, key, None))
            new_tenants.append(new_tenant)

        self.session_new.add_all(new_tenants)

    def epilogue(self):
        tenant.db_create(self.session_new, {'active': False, 'mode': 'default', 'profile': 'default', 'name': 'GLOBALEAKS', 'subdomain': ''}, False)
        self.entries_count['SubmissionStatus'] += 3
        self.entries_count['Tenant'] += 1
