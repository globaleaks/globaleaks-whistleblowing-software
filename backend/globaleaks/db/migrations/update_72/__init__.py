"""
Migration 71 -> 72: configure supplementary recipients on channels.
"""
from globaleaks.db.migrations.update import MigrationBase
from globaleaks.models import Model
from globaleaks.models.properties import Column, UnicodeText, Integer, Boolean, JSON, uuid4


class Context_v_71(Model):
    __tablename__ = 'context'

    id = Column(UnicodeText(36), primary_key=True, default=uuid4)
    tid = Column(Integer, default=1, nullable=False)
    show_steps_navigation_interface = Column(Boolean, default=True, nullable=False)
    allow_recipients_selection = Column(Boolean, default=False, nullable=False)
    maximum_selectable_receivers = Column(Integer, default=0, nullable=False)
    select_all_receivers = Column(Boolean, default=True, nullable=False)
    tip_timetolive = Column(Integer, default=90, nullable=False)
    tip_reminder = Column(Integer, default=0, nullable=False)
    name = Column(JSON, default=dict, nullable=False)
    description = Column(JSON, default=dict, nullable=False)
    show_receivers_in_alphabetical_order = Column(Boolean, default=True, nullable=False)
    score_threshold_high = Column(Integer, default=0, nullable=False)
    score_threshold_medium = Column(Integer, default=0, nullable=False)
    questionnaire_id = Column(UnicodeText(36), default='default', nullable=False, index=True)
    additional_questionnaire_id = Column(UnicodeText(36), default='', nullable=False, index=True)
    slug = Column(UnicodeText(100), default='', nullable=False)
    hidden = Column(Boolean, default=False, nullable=False)
    order = Column(Integer, default=0, nullable=False)
    internally_available = Column(Boolean, default=False, nullable=False)
    provide_access_code = Column(Boolean, default=False, nullable=False)
    template_id = Column(UnicodeText(36), default='', nullable=False)
    exchange = Column(Boolean, default=False, nullable=False)



class MigrationScript(MigrationBase):
    pass
