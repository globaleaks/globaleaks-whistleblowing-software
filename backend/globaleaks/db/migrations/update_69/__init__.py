# -*- coding: UTF-8
from globaleaks.db.migrations.update import MigrationBase
from globaleaks.models import Model, EnumVisibility
from globaleaks.models.properties import Boolean, Column, DateTime, Enum, Integer, JSON, UnicodeText
from globaleaks.utils.utility import datetime_now, datetime_null
from uuid import uuid4


class Comment_v_68(Model):
    __tablename__ = 'comment'

    id = Column(UnicodeText(36), primary_key=True, default=uuid4)
    creation_date = Column(DateTime, default=datetime_now, nullable=False)
    internaltip_id = Column(UnicodeText(36), nullable=False, index=True)
    author_id = Column(UnicodeText(36))
    content = Column(UnicodeText, nullable=False)
    visibility = Column(Enum(EnumVisibility), default='public', nullable=False)
    new = Column(Boolean, default=True, nullable=False)


class InternalFile_v_68(Model):
    __tablename__ = 'internalfile'

    id = Column(UnicodeText(36), primary_key=True, default=uuid4)
    creation_date = Column(DateTime, default=datetime_now, nullable=False)
    internaltip_id = Column(UnicodeText(36), nullable=False, index=True)
    name = Column(UnicodeText, nullable=False)
    content_type = Column(JSON, default='', nullable=False)
    size = Column(JSON, default='', nullable=False)
    new = Column(Boolean, default=True, nullable=False)
    reference_id = Column(UnicodeText(36), default='', nullable=False)


class ReceiverFile_v_68(Model):
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
    """
    Evidence hashing.

    Comment, InternalFile and ReceiverFile carry the sha256 and the sha512 of
    the evidence they refer to, so that it can be attested afterwards. The
    columns are added empty on the records that predate the feature: the
    original content is not rehashed here, because a hash computed now would
    attest the state of the archive at migration time rather than the state at
    the time the evidence was received, which is what the feature is for.
    """
