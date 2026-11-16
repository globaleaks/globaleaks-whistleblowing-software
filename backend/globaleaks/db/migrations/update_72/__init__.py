"""
Migration 71 -> 72: add the recipient trigger mode, defaulting to replacement.
"""
from globaleaks.db.migrations.update import MigrationBase
from globaleaks.models import Model
from globaleaks.models.enums import EnumFieldOptionScoreType
from globaleaks.models.properties import Column, Integer, UnicodeText, JSON, Enum, Boolean
from globaleaks.utils.utility import uuid4


class FieldOption_v_71(Model):
    __tablename__ = 'fieldoption'

    id = Column(UnicodeText(36), primary_key=True, default=uuid4)
    field_id = Column(UnicodeText(36), nullable=False, index=True)
    order = Column(Integer, default=0, nullable=False)
    label = Column(JSON, default=dict, nullable=False)
    hint1 = Column(JSON, default=dict, nullable=False)
    hint2 = Column(JSON, default=dict, nullable=False)
    score_points = Column(Integer, default=0, nullable=False)
    score_type = Column(Enum(EnumFieldOptionScoreType), default='addition', nullable=False)
    block_submission = Column(Boolean, default=False, nullable=False)
    trigger_receiver = Column(JSON, default=list, nullable=False)


class MigrationScript(MigrationBase):
    pass
