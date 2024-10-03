# -*- coding: UTF-8

from globaleaks.db.migrations.update import MigrationBase
from globaleaks.models import Model
from globaleaks.models.properties import *
from globaleaks.utils.utility import datetime_now


class Subscriber_v_62(Model):
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
    def migrate_Config(self):
        for old_obj in self.session_old.query(self.model_from['Config']):
            new_obj = self.model_to['Config']()
            for key in new_obj.__mapper__.column_attrs.keys():
                setattr(new_obj, key, getattr(old_obj, key))

            if old_obj.var_name == 'mode':
                if old_obj.value == 'whistleblowing.it':
                    new_obj.value = 'wbpa'

            self.session_new.add(new_obj)

    def migrate_Subscriber(self):
        for old_obj in self.session_old.query(self.model_from['Subscriber']):
            new_obj = self.model_to['Subscriber']()
            for key in new_obj.__mapper__.column_attrs.keys():
                if key == 'activation_token' and old_obj.activation_token == '':
                    new_obj.activation_token = None

                if key == 'organization_location':
                    setattr(new_obj, 'organization_location', getattr(old_obj, 'organization_location4'))
                else:
                    setattr(new_obj, key, getattr(old_obj, key))

            self.session_new.add(new_obj)
