# -*- coding: UTF-8
import os

from nacl.encoding import Base64Encoder

from globaleaks.db.migrations.update import MigrationBase
from globaleaks.handlers.admin.file import special_files
from globaleaks.models import Model
from globaleaks.models.properties import Column, Integer, UnicodeText, uuid4
from globaleaks.state import State


class File_v_53(Model):
    __tablename__ = 'file'
    tid = Column(Integer, primary_key=True, default=1)
    id = Column(UnicodeText(36), primary_key=True, default=uuid4)
    name = Column(UnicodeText, default='', nullable=False)
    data = Column(UnicodeText, default='', nullable=False)


class MigrationScript(MigrationBase):
    def migrate_File(self):
        for old_obj in self.session_old.query(self.model_from['File']):
            new_obj = self.model_to['File']()
            for key in new_obj.__mapper__.column_attrs.keys():
                if hasattr(old_obj, key):
                    setattr(new_obj, key, getattr(old_obj, key))

            if old_obj.id in special_files:
                new_obj.id = uuid4()
                new_obj.name = old_obj.id

                data = Base64Encoder.decode(old_obj.data)

                filepath = os.path.join(State.settings.files_path, new_obj.id)
                with open(filepath, 'wb') as out_file:
                    out_file.write(data)

            if not old_obj.name:
                new_obj.name = new_obj.id

            self.session_new.add(new_obj)
