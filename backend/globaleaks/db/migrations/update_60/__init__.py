# -*- coding: UTF-8
from globaleaks.db.migrations.update import MigrationBase
from globaleaks.models import Model
from globaleaks.models.properties import Boolean, Column, DateTime, Integer, UnicodeText, uuid4
from globaleaks.utils.crypto import GCE
from globaleaks.utils.utility import datetime_never, datetime_now, datetime_null


class InternalTip_v_59(Model):
    __tablename__ = 'internaltip'
    id = Column(UnicodeText(36), primary_key=True, default=uuid4)
    tid = Column(Integer, default=1, nullable=False)
    creation_date = Column(DateTime, default=datetime_now, nullable=False)
    update_date = Column(DateTime, default=datetime_now, nullable=False)
    context_id = Column(UnicodeText(36), nullable=False)
    progressive = Column(Integer, default=0, nullable=False)
    tor = Column(Boolean, default=False, nullable=False)
    mobile = Column(Boolean, default=False, nullable=False)
    score = Column(Integer, default=0, nullable=False)
    expiration_date = Column(DateTime, default=datetime_never, nullable=False)
    enable_whistleblower_identity = Column(Boolean, default=False, nullable=False)
    important = Column(Boolean, default=False, nullable=False)
    label = Column(UnicodeText, default='', nullable=False)
    wb_last_access = Column(DateTime, default=datetime_now, nullable=False)
    status = Column(UnicodeText(36), nullable=True)
    substatus = Column(UnicodeText(36), nullable=True)
    crypto_tip_pub_key = Column(UnicodeText(56), default='', nullable=False)


class ReceiverTip_v_59(Model):
    __tablename__ = 'receivertip'
    id = Column(UnicodeText(36), primary_key=True, default=uuid4)
    internaltip_id = Column(UnicodeText(36), nullable=False)
    receiver_id = Column(UnicodeText(36), nullable=False, index=True)
    access_date = Column(DateTime, default=datetime_null, nullable=False)
    last_access = Column(DateTime, default=datetime_null, nullable=False)
    new = Column(Boolean, default=True, nullable=False)
    enable_notifications = Column(Boolean, default=True, nullable=False)
    crypto_tip_prv_key = Column(UnicodeText(84), default='', nullable=False)


class WhistleblowerTip_v_59(Model):
    __tablename__ = 'whistleblowertip'
    id = Column(UnicodeText(36), primary_key=True, default=uuid4)
    tid = Column(Integer, default=1, nullable=False)
    receipt_hash = Column(UnicodeText(128), nullable=False)
    crypto_prv_key = Column(UnicodeText(84), default='', nullable=False)
    crypto_pub_key = Column(UnicodeText(56), default='', nullable=False)
    crypto_tip_prv_key = Column(UnicodeText(84), default='', nullable=False)



class MigrationScript(MigrationBase):
    def migrate_InternalTip(self):
        wbtips_by_id = {}
        for old_obj in self.session_old.query(self.model_from['WhistleblowerTip']):
            wbtips_by_id[old_obj.id] = old_obj

        for old_obj in self.session_old.query(self.model_from['InternalTip']):
            new_obj = self.model_to['InternalTip']()
            for key in new_obj.__mapper__.column_attrs.keys():
                if key == 'crypto_files_pub_key':
                    new_obj.crypto_files_pub_key = old_obj.crypto_tip_pub_key
                elif key == 'last_access':
                    new_obj.last_access = old_obj.wb_last_access
                elif key not in old_obj.__mapper__.column_attrs.keys():
                    if old_obj.id in wbtips_by_id:
                       setattr(new_obj, key, getattr(wbtips_by_id[old_obj.id], key))
                else:
                    setattr(new_obj, key, getattr(old_obj, key))

                if not new_obj.receipt_hash:
                    new_obj.receipt_hash = GCE.generate_receipt()

            self.session_new.add(new_obj)
