# -*- coding: UTF-8 -*-
"""
Migration 70 -> 71: the schema of the new-stable branch.

From 70 on, every installation - stable or ANAC fork - holds the same data in
the same conventions; the migration introduces what new-stable adds on top of
them, feature by feature:

- Tenants and user profiles: the permissions of an account move from the
  columns of the account to a profile of its own; the tenant used as the
  default profile of the platform is created; the counter of the tenants is
  initialized.
- Per-area administrative permissions: every administrator receives the whole
  set of the area permissions, as it administered every area so far; the
  permission can_edit_general_settings of the recipients becomes the area
  permission can_manage_settings.
- Auditor role: the role 4 of the fork was the accreditor, the operator
  approving the signups; in new-stable the role 4 is the auditor and the
  signups are approved by the administrators of the sites. The accreditors
  become administrators confined to the sites.
- Progressive notification: tip_expiration_threshold is expressed in days
  chosen among a fixed set instead of a free number of hours.
- Hashing of the evidences, support requests, statistical reports, closure
  questionnaire, channel slug, secondary SMTP, backup, antivirus: the new
  columns and tables take their defaults.
"""
from sqlalchemy import func

from globaleaks.db.migrations.update import MigrationBase
from globaleaks.handlers.admin import tenant
from globaleaks.models import Model, admin_permissions
from globaleaks.models.config import db_set_config_variable, get_default
from globaleaks.models.enums import EnumStateFile, EnumUserRole, EnumVisibility
from globaleaks.models.properties import *
from globaleaks.utils.utility import datetime_never, datetime_now, datetime_null


# The threshold of the report expiration alert is expressed in days and is
# chosen among a fixed set of values, where it used to be a free number of
# hours. The configured values are converted rather than reset, so that a
# platform keeps alerting on the same horizon it was set to: leaving them
# untouched would read 72 hours as 72 days and silence the alert for good.
EXPIRATION_ALERT_DAYS = [3, 7, 14, 28]


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


class InternalTipAnswers_v_70(Model):
    __tablename__ = 'internaltipanswers'

    internaltip_id = Column(UnicodeText(36), primary_key=True)
    questionnaire_hash = Column(UnicodeText(64), primary_key=True)
    creation_date = Column(DateTime, default=datetime_now, nullable=False)
    answers = Column(JSON, default=dict, nullable=False)
    stat_answers = Column(JSON, default=dict, nullable=False)


class InternalTipData_v_70(Model):
    __tablename__ = 'internaltipdata'

    internaltip_id = Column(UnicodeText(36), primary_key=True)
    key = Column(UnicodeText, primary_key=True)
    creation_date = Column(DateTime, default=datetime_now, nullable=False)
    value = Column(JSON, default=dict, nullable=False)


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


class Context_v_70(Model):
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


class InternalTip_v_70(Model):
    __tablename__ = 'internaltip'

    id = Column(UnicodeText(36), primary_key=True, default=uuid4)
    tid = Column(Integer, default=1, nullable=False)
    creation_date = Column(DateTime, default=datetime_now, nullable=False)
    update_date = Column(DateTime, default=datetime_now, nullable=False)
    context_id = Column(UnicodeText(36), nullable=False)
    operator_id = Column(UnicodeText(33), default='', nullable=False)
    progressive = Column(Integer, default=0, nullable=False)
    access_count = Column(Integer, default=0, nullable=False)
    tor = Column(Boolean, default=False, nullable=False)
    mobile = Column(Boolean, default=False, nullable=False)
    score = Column(Integer, default=0, nullable=False)
    expiration_date = Column(DateTime, default=datetime_never, nullable=False)
    reminder_date = Column(DateTime, default=datetime_never, nullable=False)
    enable_whistleblower_identity = Column(Boolean, default=False, nullable=False)
    important = Column(Boolean, default=False, nullable=False)
    label = Column(UnicodeText, default='', nullable=False)
    last_access = Column(DateTime, default=datetime_now, nullable=False)
    status = Column(UnicodeText(36))
    substatus = Column(UnicodeText(36))
    receipt_change_needed = Column(Boolean, default=False, nullable=False)
    receipt_hash = Column(UnicodeText(64), nullable=False)
    crypto_prv_key = Column(UnicodeText(84), default='', nullable=False)
    crypto_pub_key = Column(UnicodeText(56), default='', nullable=False)
    crypto_tip_pub_key = Column(UnicodeText(56), default='', nullable=False)
    crypto_tip_prv_key = Column(UnicodeText(84), default='', nullable=False)
    deprecated_crypto_files_pub_key = Column(UnicodeText(56), default='', nullable=False)


class User_v_70(Model):
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
    default_tenant_keys = ["subdomain", "onionservice", "https_admin", "https_analyst", "https_cert" ,"wizard_done", "uuid", "mode", "default_language", "name"]

    skip_count_check = {
        'Config': True,
        'ConfigL10N': True,
        'EnabledLanguage': True,
        'SubmissionStatus': True
    }

    # The permissions of a user moved from columns on the account to a profile
    # of its own: each existing account keeps its exact permissions by receiving
    # a personal profile that replicates them, so the migration changes where the
    # permissions are stored, never which ones an account holds.
    PROFILE_PERMISSIONS = [
        'can_delete_submission',
        'can_postpone_expiration',
        'can_grant_access_to_reports',
        'can_transfer_access_to_reports',
        'can_redact_information',
        'can_mask_information',
        'can_reopen_reports'
    ]

    # Per-area administrative permissions: the permission letting a recipient
    # edit the general settings is the area permission of the settings.
    RENAMED_PERMISSIONS = {
        'can_edit_general_settings': 'can_manage_settings'
    }

    # Auditor role: before 71 the role 4 is the accreditor of the ANAC fork.
    ACCREDITOR_ROLE = EnumUserRole.auditor.name
    ACCREDITOR_PERMISSIONS = ['can_manage_sites']

    def user_permissions(self, old_obj):
        """
        Return the permissions the profile of an account is granted
        """
        if old_obj.role == self.ACCREDITOR_ROLE:
            return self.ACCREDITOR_PERMISSIONS

        permissions = [p for p in self.PROFILE_PERMISSIONS if getattr(old_obj, p, False)]

        permissions += [new for old, new in self.RENAMED_PERMISSIONS.items() if getattr(old_obj, old, False)]

        if old_obj.role == EnumUserRole.admin.name:
            permissions += admin_permissions

        return permissions

    def migrate_User(self):
        from globaleaks.models import UserProfile, UserProfileRole, UserProfilePermission

        for old_obj in self.session_old.query(self.model_from['User']):
            new_obj = self.copy('User', old_obj)

            if old_obj.role == self.ACCREDITOR_ROLE:
                new_obj.role = EnumUserRole.admin.name

            # The personal profile carries the id of the account it belongs to,
            # so the account and its profile are bound one to one.
            new_obj.profile_id = old_obj.id
            new_obj.status = 'active'
            new_obj.idp_id = ''
            new_obj.crypto_support_prv_key = ''

            profile = UserProfile()
            profile.id = old_obj.id
            profile.tid = old_obj.tid
            profile.name = old_obj.name
            profile.role = new_obj.role
            self.session_new.add(profile)

            role = UserProfileRole()
            role.profile_id = old_obj.id
            role.role = new_obj.role
            self.session_new.add(role)

            for permission in self.user_permissions(old_obj):
                p = UserProfilePermission()
                p.profile_id = old_obj.id
                p.permission = permission
                self.session_new.add(p)

            self.session_new.add(new_obj)

    converted_config = {
        'tip_expiration_threshold': lambda v: MigrationScript.hours_to_alert_days(v)
    }

    @staticmethod
    def hours_to_alert_days(hours):
        """
        Convert a threshold expressed in hours into the closest of the values
        the interface now offers. A threshold of 0 keeps disabling the alert.
        """
        try:
            hours = int(hours)
        except (TypeError, ValueError):
            return 3

        if hours <= 0:
            return 0

        days = hours / 24

        return min(EXPIRATION_ALERT_DAYS, key=lambda d: abs(d - days))

    def epilogue(self):
        tenant.db_create(self.session_new, {'active': False, 'mode': 'default', 'profile': 'default', 'name': 'GLOBALEAKS', 'subdomain': ''}, False)
        self.entries_count['SubmissionStatus'] += 3
        self.entries_count['Tenant'] += 1

        # The tenants counter is introduced along the profiles counter but is
        # not written by the creation of the default profile: initialize it to
        # the highest ordinary tenant id, so that the tenants created after the
        # migration are not assigned the id of an existing tenant
        max_tid = self.session_new.query(func.max(self.model_to['Tenant'].id)) \
                                  .filter(self.model_to['Tenant'].id < tenant.DEFAULT_PROFILE_ID).scalar()
        db_set_config_variable(self.session_new, 1, 'counter_tenants', max_tid or 1)
