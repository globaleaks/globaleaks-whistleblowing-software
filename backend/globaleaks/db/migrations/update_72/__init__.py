# -*- coding: UTF-8 -*-
"""
Migration 71 -> 72: the primary color of the sites.

The palette of the interface is computed from the variable primary_color, that
a site neither holding nor inheriting a value of its own resolves to the
default #0978CF, the color of the official GlobaLeaks palette. No row is
written: a row on a site would make it hold the color in place of inheriting
the one of its profile.
"""
from globaleaks.db.migrations.update import MigrationBase


class MigrationScript(MigrationBase):
    pass
