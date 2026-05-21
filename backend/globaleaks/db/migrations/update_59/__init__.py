# -*- coding: UTF-8
from globaleaks.db.migrations.update import MigrationBase
from globaleaks.models import Model
from globaleaks.models.properties import Boolean, Column, DateTime, UnicodeText, uuid4
from globaleaks.utils.utility import datetime_null


class ReceiverTip_v_58(Model):
    __tablename__ = 'receivertip'
    id = Column(UnicodeText(36), primary_key=True, default=uuid4)
    internaltip_id = Column(UnicodeText(36), nullable=False)
    receiver_id = Column(UnicodeText(36), nullable=False)
    access_date = Column(DateTime, default=datetime_null, nullable=False)
    last_access = Column(DateTime, default=datetime_null, nullable=False)
    important = Column(Boolean, default=False, nullable=False)
    label = Column(UnicodeText, default='', nullable=False)
    new = Column(Boolean, default=True, nullable=False)
    enable_notifications = Column(Boolean, default=True, nullable=False)
    crypto_tip_prv_key = Column(UnicodeText(84), default='', nullable=False)


class MigrationScript(MigrationBase):
    def migrate_InternalTip(self):
        for old_obj in self.session_old.query(self.model_from['InternalTip']):
            new_obj = self.model_to['InternalTip']()
            for key in new_obj.__mapper__.column_attrs.keys():
                setattr(new_obj, key, getattr(old_obj, key))

            for old_rtip in self.session_old.query(self.model_from['ReceiverTip']) \
                                            .filter(self.model_from['ReceiverTip'].internaltip_id == old_obj.id):
                new_obj.important = True if old_rtip.important else False
                new_obj.label = old_rtip.label if old_rtip.label else ''

            self.session_new.add(new_obj)
