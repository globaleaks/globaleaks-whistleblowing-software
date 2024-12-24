from globaleaks import models
from globaleaks.models.enums import EnumFieldInstance
from globaleaks.utils.crypto import GCE, Base64Encoder
from globaleaks.db.migrations.update import MigrationBase
from globaleaks.models import Model, EnumVisibility, EnumUserRole
from globaleaks.models.properties import *
from globaleaks.utils.utility import datetime_now, datetime_null


class Subscriber_v_68(Model):
    __tablename__ = 'subscriber'

    tid = Column(Integer, primary_key=True)
    subdomain = Column(UnicodeText, unique=True, nullable=False)
    language = Column(UnicodeText(12), nullable=False)
    name = Column(UnicodeText, nullable=False)
    surname = Column(UnicodeText, nullable=False)
    phone = Column(UnicodeText, default='', nullable=False)
    email = Column(UnicodeText, nullable=False)
    organization_name = Column(UnicodeText, default='', nullable=False)
    organization_tax_code = Column(UnicodeText, unique=True, nullable=True)
    organization_vat_code = Column(UnicodeText, unique=True, nullable=True)
    organization_location = Column(UnicodeText, default='', nullable=False)
    activation_token = Column(UnicodeText, unique=True)
    client_ip_address = Column(UnicodeText, nullable=False)
    client_user_agent = Column(UnicodeText, nullable=False)
    registration_date = Column(DateTime, default=datetime_now, nullable=False)
    tos1 = Column(UnicodeText, default='', nullable=False)
    tos2 = Column(UnicodeText, default='', nullable=False)


class Tenant_v_68(Model):
    __tablename__ = 'tenant'

    id = Column(Integer, primary_key=True)
    creation_date = Column(DateTime, default=datetime_now, nullable=False)
    active = Column(Boolean, default=False, nullable=False)


class Field_v_68(Model):
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
    instance = Column(Enum(EnumFieldInstance),
                      default='instance', nullable=False)
    template_id = Column(UnicodeText(36), index=True)
    template_override_id = Column(UnicodeText(36), index=True)


class InternalFile_v_68(Model):
    """
    This model keeps track of submission files
    """
    __tablename__ = 'internalfile'

    id = Column(UnicodeText(36), primary_key=True, default=uuid4)
    creation_date = Column(DateTime, default=datetime_now, nullable=False)
    internaltip_id = Column(UnicodeText(36), nullable=False, index=True)
    name = Column(UnicodeText, nullable=False)
    content_type = Column(JSON, default='', nullable=False)
    size = Column(JSON, default='', nullable=False)
    new = Column(Boolean, default=True, nullable=False)
    reference_id = Column(UnicodeText(36), default='', nullable=False)

class InternalTipAnswers_v_68(Model):
    """
    This is the internal representation of Tip Questionnaire Answers
    """
    __tablename__ = 'internaltipanswers'

    internaltip_id = Column(UnicodeText(36), primary_key=True)
    questionnaire_hash = Column(UnicodeText(64), primary_key=True)
    creation_date = Column(DateTime, default=datetime_now, nullable=False)
    answers = Column(JSON, default=dict, nullable=False)

class Mail_v_68(Model):
    __tablename__ = 'mail'

    id = Column(UnicodeText(36), primary_key=True, default=uuid4)
    tid = Column(Integer, default=1, nullable=False)
    creation_date = Column(DateTime, default=datetime_now, nullable=False)
    address = Column(UnicodeText, nullable=False)
    subject = Column(UnicodeText, nullable=False)
    body = Column(UnicodeText, nullable=False)


class ReceiverFile_v_68(Model):
    """
    This models stores metadata of files uploaded by recipients intended to bes
    delivered to the whistleblower. This file is not encrypted and nor is it
    integrity checked in any meaningful way.
    """
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


class User_v_68(Model):
    """
    This model keeps track of users.
    """
    __tablename__ = 'user'

    id = Column(UnicodeText(36), primary_key=True, default=uuid4)
    tid = Column(Integer, default=1, nullable=False)
    creation_date = Column(DateTime, default=datetime_now, nullable=False)
    username = Column(UnicodeText, default='', nullable=False)
    salt = Column(UnicodeText(24), default='', nullable=False)
    hash = Column(UnicodeText(44), default='', nullable=False)
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

    # BEGIN of PGP key fields
    pgp_key_fingerprint = Column(UnicodeText, default='', nullable=False)
    pgp_key_public = Column(UnicodeText, default='', nullable=False)
    pgp_key_expiration = Column(DateTime, default=datetime_null, nullable=False)
    # END of PGP key fields

    accepted_privacy_policy = Column(DateTime, default=datetime_null, nullable=False)
    clicked_recovery_key = Column(Boolean, default=False, nullable=False)


class MigrationScript(MigrationBase):

    def add_global_stat_prv_key_to_users(self, global_stat_prv_key):
        users = self.session_new.query(self.model_from['User']) \
                                .filter(self.model_from['User'].tid == 1)\
                                .filter(self.model_from['User'].role.in_([EnumUserRole.admin.name, EnumUserRole.analyst.name]))

        for user in users:
            crypto_stat_key = Base64Encoder.encode(
                GCE.asymmetric_encrypt(user.crypto_pub_key, global_stat_prv_key)).decode()
            self.session_new.query(models.User) \
                                .filter(models.User.id == user.id)\
                                .update({'crypto_global_stat_prv_key': crypto_stat_key})

    def add_global_stat_keys(self):
        global_stat_prv_key, global_stat_pub_key = GCE.generate_keypair()
        global_stat_pub_key_config = self.model_to['Config']()
        global_stat_pub_key_config.var_name = 'global_stat_pub_key'
        global_stat_pub_key_config.value = global_stat_pub_key
        global_stat_pub_key_config.tid = 1
        self.session_new.add(global_stat_pub_key_config)
        self.entries_count['Config'] += 1
        self.add_global_stat_prv_key_to_users(global_stat_prv_key)
        
    def add_file_analisys_configs(self):
        antivirus_clamd_ip_config = self.model_to['Config']()
        antivirus_clamd_ip_config.var_name = 'antivirus_clamd_ip'
        antivirus_clamd_ip_config.value = 'localhost'
        antivirus_clamd_ip_config.tid = 1
        self.session_new.add(antivirus_clamd_ip_config)
        self.entries_count['Config'] += 1
        antivirus_clamd_port_config = self.model_to['Config']()
        antivirus_clamd_port_config.var_name = 'antivirus_clamd_port'
        antivirus_clamd_port_config.value = 3310
        antivirus_clamd_port_config.tid = 1
        self.session_new.add(antivirus_clamd_port_config)
        self.entries_count['Config'] += 1
        antivirus_enabled_config = self.model_to['Config']()
        antivirus_enabled_config.var_name = 'antivirus_enabled'
        antivirus_enabled_config.value = True
        antivirus_enabled_config.tid = 1
        self.session_new.add(antivirus_enabled_config)
        self.entries_count['Config'] += 1

    def add_external_organization_configs(self):
        add_config = self.model_to['Config']()
        add_config.var_name = 'max_msg_external_to_whistle'
        add_config.value = 1
        add_config.tid = 1
        self.session_new.add(add_config)
        self.entries_count['Config'] += 1

        add_config = self.model_to['Config']()
        add_config.var_name = 'max_msg_external_to_whistle_not_aff'
        add_config.value = 1
        add_config.tid = 1
        self.session_new.add(add_config)
        self.entries_count['Config'] += 1

        forwarding_enabled = self.model_to['Config']()
        forwarding_enabled.var_name = 'forwarding_enabled'
        forwarding_enabled.value = False
        forwarding_enabled.tid = 1
        self.session_new.add(forwarding_enabled)
        self.entries_count['Config'] += 1

        proxy_idp_enabled_config = self.model_to['Config']()
        proxy_idp_enabled_config.var_name = 'proxy_idp_enabled'
        proxy_idp_enabled_config.value = True
        proxy_idp_enabled_config.tid = 1
        self.session_new.add(proxy_idp_enabled_config)
        self.entries_count['Config'] += 1


    def add_smtp2_mail_configs(self):
        for i in ['smtp2_password', 'smtp2_port', 'smtp2_security', 'smtp2_server', 'smtp2_source_email', 'smtp2_username', 'smtp2_authentication', 'smtp2_enabled']:
            smtp_2_config = self.model_to['Config']()
            smtp_2_config.var_name = i
            smtp_2_config.value = '' if i not in ['smtp2_port', 'smtp2_enabled', 'smtp2_authentication'] else 0
            smtp_2_config.tid = 1
            self.session_new.add(smtp_2_config)
            self.entries_count['Config'] += 1

        for lan in ['en', 'it']:

            template_mail_config = self.model_to['ConfigL10N']()
            template_mail_config.tid = 1
            template_mail_config.lang = lan
            template_mail_config.var_name = 'new_user_recipient_signup_external_organization_alert_mail_title'
            template_mail_config.value = 'Access instructions'
            template_mail_config.update_date = datetime_now()
            self.session_new.add(template_mail_config)
            self.entries_count['ConfigL10N'] += 1

            template_mail_config = self.model_to['ConfigL10N']()
            template_mail_config.tid = 1
            template_mail_config.lang = lan
            template_mail_config.var_name = 'new_user_recipient_signup_external_organization_alert_mail_template'
            template_mail_config.value = 'Dear {RecipientName},\nYour platform {ExternalOrganizationName} is now accessible at:\n{Url}\nTo log in, visit:\n{LoginUrl}\nUsers credentials:\n{RecipientCredentials}\nFor the user documentation, visit:\n{DocumentationUrl}\nKind regards,\n{NodeName}'
            template_mail_config.update_date = datetime_now()
            self.session_new.add(template_mail_config)
            self.entries_count['ConfigL10N'] += 1

            template_mail_config = self.model_to['ConfigL10N']()
            template_mail_config.tid = 1
            template_mail_config.lang = lan
            template_mail_config.var_name = 'new_user_admin_signup_external_organization_alert_mail_title'
            template_mail_config.value = 'Access instructions'
            template_mail_config.update_date = datetime_now()
            self.session_new.add(template_mail_config)
            self.entries_count['ConfigL10N'] += 1

            template_mail_config = self.model_to['ConfigL10N']()
            template_mail_config.tid = 1
            template_mail_config.lang = lan
            template_mail_config.var_name = 'new_user_admin_signup_external_organization_alert_mail_template'
            template_mail_config.value = 'Dear {Name},\nYour platform {ExternalOrganizationName} is now accessible at:\n{Url}\nTo log in, visit:\n{LoginUrl}\nUsers credentials:\n{AdminCredentials}\nFor the user documentation, visit:\n{DocumentationUrl}\nKind regards,\n{NodeName}'
            template_mail_config.update_date = datetime_now()
            self.session_new.add(template_mail_config)
            self.entries_count['ConfigL10N'] += 1

            template_mail_config = self.model_to['ConfigL10N']()
            template_mail_config.tid = 1
            template_mail_config.lang = lan
            template_mail_config.var_name = 'accreditor_signup_external_organization_alert_mail_template'
            template_mail_config.value = 'A new external organization has been accredited.\n\nAccreditation data:\n\nid: {AccreditationId}\n\nName: {AccreditationName}\n\nStatus: {AccreditationStatus}\n\nregards,\n\n{NodeName}'
            template_mail_config.update_date = datetime_now()
            self.session_new.add(template_mail_config)
            self.entries_count['ConfigL10N'] += 1

            template_mail_config = self.model_to['ConfigL10N']()
            template_mail_config.tid = 1
            template_mail_config.lang = lan
            template_mail_config.var_name = 'accreditor_signup_external_organization_alert_mail_title'
            template_mail_config.value = 'An new external organization has been accredited.'
            template_mail_config.update_date = datetime_now()
            self.session_new.add(template_mail_config)
            self.entries_count['ConfigL10N'] += 1

            template_mail_config = self.model_to['ConfigL10N']()
            template_mail_config.tid = 1
            template_mail_config.lang = lan
            template_mail_config.var_name = 'sign_up_external_organization_mail_title'
            template_mail_config.value = 'external organization confirm accreditation'
            template_mail_config.update_date = datetime_now()
            self.session_new.add(template_mail_config)
            self.entries_count['ConfigL10N'] += 1

            template_mail_config = self.model_to['ConfigL10N']()
            template_mail_config.tid = 1
            template_mail_config.lang = lan
            template_mail_config.var_name = 'sign_up_external_organization_mail_template'
            template_mail_config.value = 'Dear {RecipientName},\n\nYour accreditation request is in status: {AccreditationStatus}\n\nClick the link to confirm the request:\n\n{ActivationUrl}\n\nKind regards,\n\n{NodeName}'
            template_mail_config.update_date = datetime_now()
            self.session_new.add(template_mail_config)
            self.entries_count['ConfigL10N'] += 1

            template_mail_config = self.model_to['ConfigL10N']()
            template_mail_config.tid = 1
            template_mail_config.lang = lan
            template_mail_config.var_name = 'sign_up_external_organization_info_mail_title'
            template_mail_config.value = 'external organization request accreditation'
            template_mail_config.update_date = datetime_now()
            self.session_new.add(template_mail_config)
            self.entries_count['ConfigL10N'] += 1

            template_mail_config = self.model_to['ConfigL10N']()
            template_mail_config.tid = 1
            template_mail_config.lang = lan
            template_mail_config.var_name = 'sign_up_external_organization_info_mail_template'
            template_mail_config.value = 'Dear {RecipientName},\n\nYour accreditation request is in status: {AccreditationStatus}\n\n{AccreditationMotivationText}\n\nKind regards,\n\n{NodeName}'
            template_mail_config.update_date = datetime_now()
            self.session_new.add(template_mail_config)
            self.entries_count['ConfigL10N'] += 1

            template_mail_config = self.model_to['ConfigL10N']()
            template_mail_config.tid = 1
            template_mail_config.lang = lan
            template_mail_config.var_name = 'close_forwarding_external_organization_mail_title'
            template_mail_config.value = 'Closed forwarding'
            template_mail_config.update_date = datetime_now()
            self.session_new.add(template_mail_config)
            self.entries_count['ConfigL10N'] += 1

            template_mail_config = self.model_to['ConfigL10N']()
            template_mail_config.tid = 1
            template_mail_config.lang = lan
            template_mail_config.var_name = 'close_forwarding_external_organization_mail_template'
            template_mail_config.value = 'Dear {RecipientName},\nThe forwarded submission with ID {OriginalTipId} to the external organization {ExternalOrganizationName} has been closed.\nFor the user documentation, visit:\n{DocumentationUrl}\nKind regards,\n{NodeName}'
            template_mail_config.update_date = datetime_now()
            self.session_new.add(template_mail_config)
            self.entries_count['ConfigL10N'] += 1

            template_mail_config = self.model_to['ConfigL10N']()
            template_mail_config.tid = 1
            template_mail_config.lang = lan
            template_mail_config.var_name = 'delete_user_external_organization_mail_title'
            template_mail_config.value = 'User deleted'
            template_mail_config.update_date = datetime_now()
            self.session_new.add(template_mail_config)
            self.entries_count['ConfigL10N'] += 1

            template_mail_config = self.model_to['ConfigL10N']()
            template_mail_config.tid = 1
            template_mail_config.lang = lan
            template_mail_config.var_name = 'delete_user_external_organization_mail_template'
            template_mail_config.value = 'Dear {Username},\nYour account associated with the external organization {ExternalOrganizationName} has been deleted.\nFor the user documentation, visit:\n{DocumentationUrl}\nKind regards,\n{NodeName}'
            template_mail_config.update_date = datetime_now()
            self.session_new.add(template_mail_config)
            self.entries_count['ConfigL10N'] += 1

    def add_backup_configs(self):
        backup_enabled_config = self.model_to['Config']()
        backup_enabled_config.var_name = 'backup_enabled'
        backup_enabled_config.value = False
        backup_enabled_config.tid = 1
        self.session_new.add(backup_enabled_config)
        self.entries_count['Config'] += 1

        backup_time_config = self.model_to['Config']()
        backup_time_config.var_name = 'backup_time'
        backup_time_config.value = '2:00'
        backup_time_config.tid = 1
        self.session_new.add(backup_time_config)
        self.entries_count['Config'] += 1

        backup_path_config = self.model_to['Config']()
        backup_path_config.var_name = 'backup_path'
        backup_path_config.value = '/var/backup/'
        backup_path_config.tid = 1
        self.session_new.add(backup_path_config)
        self.entries_count['Config'] += 1

    def epilogue(self):
        self.add_external_organization_configs()
        self.add_file_analisys_configs()
        self.add_global_stat_keys()
        self.add_backup_configs()
        self.add_smtp2_mail_configs()
