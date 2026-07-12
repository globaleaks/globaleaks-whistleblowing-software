from globaleaks.models.enums import EnumStateFile, EnumVisibility
from globaleaks.db.migrations.update import MigrationBase
from globaleaks.models import Model
from globaleaks.models.properties import *
from globaleaks.utils.utility import datetime_now, datetime_null


class Comment_v_71(Model):
    __tablename__ = 'comment'

    id = Column(UnicodeText(36), primary_key=True, default=uuid4)
    creation_date = Column(DateTime, default=datetime_now, nullable=False)
    internaltip_id = Column(UnicodeText(36), nullable=False, index=True)
    author_id = Column(UnicodeText(36))
    content = Column(UnicodeText, nullable=False)
    visibility = Column(Enum(EnumVisibility), default='public', nullable=False)
    new = Column(Boolean, default=True, nullable=False)


class InternalFile_v_71(Model):
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


class ReceiverFile_v_71(Model):
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


class MigrationScript(MigrationBase):
    def migrate_Comment(self):
        old_comments = self.session_old.query(self.model_from['Comment']).all()
        new_comments = []

        for old_obj in old_comments:
            new_comment = self.model_to['Comment']()

            for key in new_comment.__mapper__.column_attrs.keys():
                if hasattr(old_obj, key):
                    setattr(new_comment, key, getattr(old_obj, key))

            new_comment.hash_sha256 = ''
            new_comment.hash_sha512 = ''

            new_comments.append(new_comment)

        self.session_new.add_all(new_comments)

    def migrate_InternalFile(self):
        old_rows = self.session_old.query(self.model_from['InternalFile']).all()

        for old in old_rows:
            new = self.model_to['InternalFile']()

            for col in new.__mapper__.column_attrs.keys():
                if hasattr(old, col):
                    setattr(new, col, getattr(old, col))

            new.hash_sha256 = ''
            new.hash_sha512 = ''

            self.session_new.add(new)

    def migrate_ReceiverFile(self):
        old_rows = self.session_old.query(self.model_from['ReceiverFile']).all()

        for old in old_rows:
            new = self.model_to['ReceiverFile']()

            for col in new.__mapper__.column_attrs.keys():
                if hasattr(old, col):
                    setattr(new, col, getattr(old, col))

            new.hash_sha256 = ''
            new.hash_sha512 = ''

            self.session_new.add(new)
