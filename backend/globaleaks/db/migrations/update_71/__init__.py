# -*- coding: UTF-8 -*-
import enum

from globaleaks.db.migrations.update import MigrationBase
from globaleaks.handlers.admin import tenant, user
from globaleaks.handlers.user import user_permissions
from globaleaks.models import Model
from globaleaks.models.config import get_default
from globaleaks.models.enums import _Enum, EnumUserRole
from globaleaks.models.properties import *
from globaleaks.utils.utility import datetime_now, datetime_null


# Old enum for User status (v70)
class EnumUserStatus_v_70(_Enum):
    active = 0
    suspend = 1


class Tenant_v_70(Model):
    __tablename__ = 'tenant'
    __table_args__ = {'sqlite_autoincrement': False}

    id = Column(Integer, primary_key=True, autoincrement=False)
    creation_date = Column(DateTime, default=datetime_now, nullable=False)
    active = Column(Boolean, default=False, nullable=False)


class Context_v_70(Model):
    """
    Context model before adding status field
    """
    __tablename__ = 'context'

    id = Column(UnicodeText(36), primary_key=True, default=uuid4)
    tid = Column(Integer, default=1, nullable=False)
    show_steps_navigation_interface = Column(Boolean, default=True, nullable=False)
    allow_recipients_selection = Column(Boolean, default=False, nullable=False)
    maximum_selectable_receivers = Column(Integer, default=0, nullable=False)
    select_all_receivers = Column(Boolean, default=True, nullable=False)
    tip_timetolive = Column(Integer, default=90, nullable=False)
    tip_reminder = Column(Integer, default=0, nullable=False)
    name = Column(JSON, default=dict, nullable=False)
    description = Column(JSON, default=dict, nullable=False)
    show_receivers_in_alphabetical_order = Column(Boolean, default=True, nullable=False)
    score_threshold_high = Column(Integer, default=0, nullable=False)
    score_threshold_medium = Column(Integer, default=0, nullable=False)
    questionnaire_id = Column(UnicodeText(36), default='default', nullable=False, index=True)
    additional_questionnaire_id = Column(UnicodeText(36), index=True)
    hidden = Column(Boolean, default=False, nullable=False)
    order = Column(Integer, default=0, nullable=False)


class User_v_70(Model):
    """
    User model with old status enum values
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
    change_email_address = Column(UnicodeText, default='', nullable=False)
    change_email_token = Column(UnicodeText, unique=True)
    change_email_date = Column(DateTime, default=datetime_null, nullable=False)
    notification = Column(Boolean, default=True, nullable=False)
    forcefully_selected = Column(Boolean, default=False, nullable=False)
    two_factor_secret = Column(UnicodeText(32), default='', nullable=False)
    reminder_date = Column(DateTime, default=datetime_null, nullable=False)
    profile_id = Column(Integer, default='', nullable=False)
    status = Column(Enum(EnumUserStatus_v_70), default='active', nullable=False)
    idp_id = Column(UnicodeText(18), default='', nullable=False)
    pgp_key_fingerprint = Column(UnicodeText, default='', nullable=False)
    pgp_key_public = Column(UnicodeText, default='', nullable=False)
    pgp_key_expiration = Column(DateTime, default=datetime_null, nullable=False)
    accepted_privacy_policy = Column(DateTime, default=datetime_null, nullable=False)
    clicked_recovery_key = Column(Boolean, default=False, nullable=False)


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
                if hasattr(old_obj, p) and getattr(old_obj, p, False):
                    user_desc['permissions'][p] = True

            new_profile = user.db_create_user_profile(self.session_new, user_desc.get("tid"), user_desc)

            new_obj = self.model_to['User']()
            for key in new_obj.__mapper__.column_attrs.keys():
                if key == 'status':
                    # Migrate status based on both old status and enabled fields
                    # Priority: if enabled=False, user is disabled regardless of old status
                    old_enabled = getattr(old_obj, 'enabled', True)
                    old_status = getattr(old_obj, 'status', None)

                    if not old_enabled:
                        new_obj.status = 'disabled'
                    elif old_status is not None:
                        if hasattr(old_status, 'name'):
                            old_status = old_status.name
                        if old_status == 'suspend':
                            new_obj.status = 'disabled'
                        else:
                            new_obj.status = 'enabled'
                    else:
                        new_obj.status = 'enabled'
                elif key == 'enabled':
                    # Skip the old enabled field - it's now handled by status
                    continue
                elif hasattr(old_obj, key):
                    setattr(new_obj, key, getattr(old_obj, key))

            new_obj.profile_id = new_profile['id']
            self.session_new.add(new_obj)

    def migrate_Context(self):
        old_contexts = self.session_old.query(self.model_from['Context']).all()
        for old_obj in old_contexts:
            new_obj = self.model_to['Context']()
            for key in new_obj.__mapper__.column_attrs.keys():
                if key == 'status':
                    # Set status based on old hidden field
                    if getattr(old_obj, 'hidden', False):
                        new_obj.status = 'hidden'
                    else:
                        new_obj.status = 'enabled'
                elif key == 'hidden':
                    # Skip the old hidden field - it's now handled by status
                    continue
                elif hasattr(old_obj, key):
                    setattr(new_obj, key, getattr(old_obj, key))
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
