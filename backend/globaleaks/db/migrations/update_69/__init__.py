from globaleaks.db.migrations.update import MigrationBase
from globaleaks.models import Model, EnumSubscriberStatus, EnumStateFile, EnumVisibility, EnumUserRole, EnumUserStatus
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


class InternalFile_v_68(Model):
    """
    This model keeps track of submission files
    """
    __tablename__ = 'internalfile'

    id = Column(UnicodeText(36), primary_key=True, default=uuid4)
    creation_date = Column(DateTime, default=datetime_now, nullable=False)
    # filename = Column(UnicodeText, default='', nullable=False)
    internaltip_id = Column(UnicodeText(36), nullable=False, index=True)
    name = Column(UnicodeText, nullable=False)
    content_type = Column(JSON, default='', nullable=False)
    size = Column(JSON, default='', nullable=False)
    new = Column(Boolean, default=True, nullable=False)
    reference_id = Column(UnicodeText(36), default='', nullable=False)


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

    def epilogue(self):
        new_configuration = self.model_to['Config']()
        new_configuration.var_name = 'url_file_analysis'
        new_configuration.value = 'http://localhost/api/v1/scan'
        self.session_new.add(new_configuration)

        self.entries_count['Config'] += 1