# -*- coding: UTF-8 -*-
"""
Migration script for database version 72.

This migration adds a 'deleted' column to the Context table to support
soft deletion of channels, preserving reports while marking channels as deleted.
"""
from globaleaks.db.migrations.update import MigrationBase
from globaleaks.models import Model
from globaleaks.models.properties import *
from globaleaks.utils.utility import datetime_now


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
    additional_questionnaire_id = Column(UnicodeText(36), index=True)
    hidden = Column(Boolean, default=False, nullable=False)
    order = Column(Integer, default=0, nullable=False)


class MigrationScript(MigrationBase):
    """
    Migration script that adds the 'deleted' column to Context table.
    """

    def migrate_Context(self):
        """
        Migrate Context table, adding the 'deleted' field set to False for all existing contexts.
        """
        old_contexts = self.session_old.query(self.model_from['Context']).all()

        for old_obj in old_contexts:
            new_context = self.model_to['Context']()

            for key in new_context.__mapper__.column_attrs.keys():
                if hasattr(old_obj, key):
                    setattr(new_context, key, getattr(old_obj, key))

            # Set deleted to False for existing contexts
            new_context.deleted = False

            self.session_new.add(new_context)

