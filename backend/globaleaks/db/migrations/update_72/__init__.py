"""
Migration 71 -> 72: retain identity access for existing recipient profiles.
"""
from globaleaks.db.migrations.update import MigrationBase


class MigrationScript(MigrationBase):
    def epilogue(self):
        role = self.model_to['UserProfileRole']
        permission = self.model_to['UserProfilePermission']
        profile_ids = {profile_id for profile_id, in self.session_new.query(role.profile_id)
                                                                  .filter(role.role.in_(['receiver', 'transmitter']))}
        for profile_id in profile_ids:
            for key in ['can_view_whistleblower_identity', 'can_request_whistleblower_identity']:
                self.add_entry('UserProfilePermission', permission({'profile_id': profile_id, 'permission': key}))
