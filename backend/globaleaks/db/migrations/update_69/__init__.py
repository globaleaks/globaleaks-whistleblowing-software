# -*- coding: UTF-8 -*-
from globaleaks import models
from globaleaks.db.migrations.update import MigrationBase
from globaleaks.models import Model
from globaleaks.models.properties import *
from globaleaks.utils.utility import datetime_now
from globaleaks.models.config_desc import ConfigDescriptor
from globaleaks.models.config import get_default
from globaleaks.db.appdata import load_appdata
from sqlalchemy import tuple_

class Tenant_v_68(Model):
    __tablename__ = 'tenant'
    __table_args__ = {'sqlite_autoincrement': False}

    id = Column(Integer, primary_key=True, autoincrement=False)
    creation_date = Column(DateTime, default=datetime_now, nullable=False)
    active = Column(Boolean, default=False, nullable=False)

class MigrationScript(MigrationBase):
    default_tenant_keys = ["subdomain", "onionservice", "https_admin", "https_analyst", "https_cert" ,"wizard_done", "uuid", "mode", "default_language", "name"]

    def migrate_Tenant(self):

        old_tenants = self.session_old.query(self.model_from['Tenant']).all()
        new_tenants = []
        for old_obj in old_tenants:
            new_tenant = self.model_to['Tenant']()
            for key in new_tenant.__mapper__.column_attrs.keys():
                setattr(new_tenant, key, getattr(old_obj, key, None))
            new_tenants.append(new_tenant)
    
        defualt_tenant = self.model_to['Tenant']()
        defualt_tenant.id = 1000001
        defualt_tenant.active = False
        new_tenants.append(defualt_tenant)

        self.session_new.add_all(new_tenants)
        self.entries_count['Tenant'] = len(new_tenants)
    
    def migrate_Config(self):

        old_configs = self.session_old.query(self.model_from['Config']).all()
        new_configs = []
        for old_obj in old_configs:
            new_obj = self.model_to['Config']()
            for key in new_obj.__mapper__.column_attrs.keys():
                setattr(new_obj, key, getattr(old_obj, key))
            new_configs.append(new_obj)
        self.session_new.bulk_save_objects(new_configs)

        variables = {name: get_default(desc.default) for name, desc in ConfigDescriptor.items()}

        variables.update({
            'tenant_counter': self.session_old.query(self.model_from['Tenant']).count(),
            'profile_counter': 1000000
        })

        merged_configs = []
        for var_name, value in variables.items():
            new_config = self.model_to['Config']()
            new_config.tid = 1 if var_name in ['tenant_counter', 'profile_counter'] else 1000001
            new_config.var_name = var_name
            new_config.value = value
            merged_configs.append(new_config)

        self.session_new.bulk_save_objects(merged_configs)
        self.entries_count['Config'] += len(merged_configs)

        default_config = {entry.var_name: entry.value for entry in self.session_new.query(self.model_to['Config']).filter_by(tid=1000001).all()}
        tenant_configs = self.session_new.query(self.model_to['Config'].tid,self.model_to['Config'].var_name,self.model_to['Config'].value).filter(self.model_to['Config'].tid.notin_([1000001, 1])).all()
    
        to_delete = []
        for tid, var_name, value in tenant_configs:
            if var_name in default_config and value == default_config[var_name] and var_name not in self.default_tenant_keys:
                to_delete.append((tid, var_name))
    
        if to_delete:
            self.session_new.query(self.model_to['Config']).filter(tuple_(self.model_to['Config'].tid, self.model_to['Config'].var_name).in_(to_delete)).delete(synchronize_session=False)
            self.entries_count['Config'] -= len(to_delete)

    def migrate_ConfigL10N(self):

        old_configs = self.session_old.query(self.model_from['ConfigL10N']).all()
        new_configs = []
        for old_obj in old_configs:
            new_obj = self.model_to['ConfigL10N']()
            for key in new_obj.__mapper__.column_attrs.keys():
                setattr(new_obj, key, getattr(old_obj, key))
            new_configs.append(new_obj)
        self.session_new.bulk_save_objects(new_configs)
    
        models.config.add_new_lang(self.session_new, 1000001, 'en', load_appdata())
        self.entries_count['ConfigL10N'] += 72
        self.entries_count['EnabledLanguage'] += 1
    
        default_config = {(entry.var_name, entry.lang): entry.value for entry in self.session_new.query(self.model_to['ConfigL10N']).filter_by(tid=1000001).all()}
        tenant_configs = self.session_new.query(self.model_to['ConfigL10N'].tid,self.model_to['ConfigL10N'].var_name,self.model_to['ConfigL10N'].lang,self.model_to['ConfigL10N'].value).filter(self.model_to['ConfigL10N'].tid.notin_([1000001, 1])).all()
    
        to_delete = []
        for tid, var_name, lang, value in tenant_configs:
            if (var_name, lang) in default_config and value == default_config[(var_name, lang)] and var_name not in self.default_tenant_keys:
                to_delete.append((tid, var_name, lang))
    
        if to_delete:
            self.session_new.query(self.model_to['ConfigL10N']).filter(tuple_(self.model_to['ConfigL10N'].tid, self.model_to['ConfigL10N'].var_name, self.model_to['ConfigL10N'].lang).in_(to_delete)).delete(synchronize_session=False)
            self.entries_count['ConfigL10N'] -= len(to_delete)