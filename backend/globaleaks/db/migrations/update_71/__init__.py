# -*- coding: UTF-8 -*-
from globaleaks.db.migrations.update import MigrationBase
from globaleaks.handlers.admin import tenant, user
from globaleaks.handlers.user import user_permissions
from globaleaks.models import Model
from globaleaks.models.config import get_default
from globaleaks.models.properties import *
from globaleaks.utils.utility import datetime_now


class Tenant_v_70(Model):
    __tablename__ = 'tenant'
    __table_args__ = {'sqlite_autoincrement': False}

    id = Column(Integer, primary_key=True, autoincrement=False)
    creation_date = Column(DateTime, default=datetime_now, nullable=False)
    active = Column(Boolean, default=False, nullable=False)


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
                if getattr(old_obj, p):
                    user_desc['permissions'][p] = True

            new_profile = user.db_create_user_profile(self.session_new, user_desc.get("tid"), user_desc)

            new_obj = self.model_to['User']()
            for key in new_obj.__mapper__.column_attrs.keys():
                if hasattr(old_obj, key):
                    setattr(new_obj, key, getattr(old_obj, key))

            new_obj.profile_id = new_profile['id']
            self.session_new.add(new_obj)

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
