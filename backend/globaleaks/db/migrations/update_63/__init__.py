# -*- coding: UTF-8

from globaleaks.db.migrations.update import MigrationBase
from globaleaks.models import Model
from globaleaks.models.properties import Column, DateTime, Integer, UnicodeText
from globaleaks.utils.utility import datetime_now


class SubscriberV62(Model):
    __tablename__ = 'subscriber'
    tid = Column(Integer, primary_key=True)
    subdomain = Column(UnicodeText, unique=True, nullable=False)
    language = Column(UnicodeText(12), nullable=False)
    name = Column(UnicodeText, nullable=False)
    surname = Column(UnicodeText, nullable=False)
    role = Column(UnicodeText, default='', nullable=False)
    phone = Column(UnicodeText, default='', nullable=False)
    email = Column(UnicodeText, nullable=False)
    organization_name = Column(UnicodeText, default='', nullable=False)
    organization_type = Column(UnicodeText, default='', nullable=False)
    organization_tax_code = Column(UnicodeText, default='', nullable=False)
    organization_vat_code = Column(UnicodeText, default='', nullable=False)
    organization_location4 = Column(UnicodeText, default='', nullable=False)
    activation_token = Column(UnicodeText, unique=True, nullable=True)
    client_ip_address = Column(UnicodeText, nullable=False)
    client_user_agent = Column(UnicodeText, nullable=False)
    registration_date = Column(DateTime, default=datetime_now, nullable=False)
    tos1 = Column(UnicodeText, default='', nullable=False)
    tos2 = Column(UnicodeText, default='', nullable=False)


class MigrationScript(MigrationBase):
    converted_config = {
        'mode': lambda v: 'wbpa' if v == 'whistleblowing.it' else v
    }

    renamed_attrs = {
        'Subscriber': {'organization_location': 'organization_location4'}
    }

    converted_attrs = {
        'Subscriber': {'activation_token': lambda o: o.activation_token if o.activation_token else None}
    }
