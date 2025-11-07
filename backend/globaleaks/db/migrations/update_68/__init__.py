# -*- coding: UTF-8
from globaleaks.models.enums import EnumUserRole
from globaleaks.db.migrations.update import MigrationBase
from globaleaks.models import Model
from globaleaks.models.properties import *
from globaleaks.utils.utility import datetime_now, datetime_null

class Subscriber_v_67(Model):
    __tablename__ = 'subscriber'

    tid = Column(Integer, primary_key=True)
    subdomain = Column(UnicodeText, unique=True, nullable=False)
    language = Column(UnicodeText(12), nullable=False)
    name = Column(UnicodeText, nullable=False)
    surname = Column(UnicodeText, nullable=False)
    phone = Column(UnicodeText, default='', nullable=False)
    email = Column(UnicodeText, nullable=False)
    organization_name = Column(UnicodeText, default='', nullable=False)
    organization_tax_code = Column(UnicodeText, default='', nullable=False)
    organization_vat_code = Column(UnicodeText, default='', nullable=False)
    organization_location = Column(UnicodeText, default='', nullable=False)
    activation_token = Column(UnicodeText, unique=True)
    client_ip_address = Column(UnicodeText, nullable=False)
    client_user_agent = Column(UnicodeText, nullable=False)
    registration_date = Column(DateTime, default=datetime_now, nullable=False)
    tos1 = Column(UnicodeText, default='', nullable=False)
    tos2 = Column(UnicodeText, default='', nullable=False)


class MigrationScript(MigrationBase):
    def migrate_Subscriber(self):
        used_values = {}

        for old_obj in self.session_old.query(self.model_from['Subscriber']):
            new_obj = self.model_to['Subscriber']()
            for key in new_obj.__mapper__.column_attrs.keys():
                value = getattr(old_obj, key)
                if key.endswith('_code'):
                    if value == '':
                        value = None
                    else:
                        if value in used_values:
                            used_values[value] += 1
                            value = value + "_" + str(used_values[value])
                        else:
                            used_values[value] = 0

                setattr(new_obj, key, value)

            self.session_new.add(new_obj)
