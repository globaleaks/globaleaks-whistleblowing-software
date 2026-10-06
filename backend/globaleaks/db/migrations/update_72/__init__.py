"""Migration 71 -> 72: move flat filesystem storage into tenant directories."""
import os

from globaleaks.db.migrations.update import MigrationBase
from globaleaks.settings import Settings
from globaleaks.utils.fs import directory_traversal_check, get_storage_path


def move_storage_file(tid, kind, file_id):
    """
    Move a tracked file into its tenant directory

    :param tid: The tenant ID
    :param kind: The storage directory
    :param file_id: The file ID
    """
    destination = get_storage_path(tid, kind, file_id, create=True)
    source_root = Settings.files_path if kind == 'files' else Settings.attachments_path
    source = os.path.join(source_root, file_id)
    directory_traversal_check(source_root, source)

    if os.path.islink(source) or os.path.islink(destination):
        raise RuntimeError('Refusing to migrate a storage symlink: %s' % file_id)
    if os.path.lexists(destination):
        if not os.path.isfile(destination) or os.path.lexists(source):
            raise RuntimeError('Tenant storage destination already exists: %s' % destination)
        return
    if not os.path.lexists(source):
        return
    if not os.path.isfile(source):
        raise RuntimeError('Storage source is not a regular file: %s' % source)

    os.rename(source, destination)


class MigrationScript(MigrationBase):
    def epilogue(self):
        tenant_model = self.model_to['Tenant']
        file_model = self.model_to['File']
        internal_tip_model = self.model_to['InternalTip']
        internal_file_model = self.model_to['InternalFile']
        receiver_file_model = self.model_to['ReceiverFile']
        whistleblower_file_model = self.model_to['WhistleblowerFile']

        for tid, in self.session_new.query(tenant_model.id):
            for kind in ('files', 'attachments', 'log'):
                get_storage_path(tid, kind, create=True)

        files = self.session_new.query(file_model.tid, file_model.id)
        ifiles = self.session_new.query(internal_tip_model.tid, internal_file_model.id) \
                                .filter(internal_file_model.internaltip_id == internal_tip_model.id)
        rfiles = self.session_new.query(internal_tip_model.tid, receiver_file_model.id) \
                                .filter(receiver_file_model.internaltip_id == internal_tip_model.id)
        wbfiles = self.session_new.query(internal_tip_model.tid, whistleblower_file_model.id) \
                                 .filter(whistleblower_file_model.internalfile_id == internal_file_model.id,
                                         internal_file_model.internaltip_id == internal_tip_model.id)

        for kind, query in (('files', files), ('attachments', ifiles),
                            ('attachments', rfiles), ('attachments', wbfiles)):
            for tid, file_id in query.yield_per(1000):
                move_storage_file(tid, kind, file_id)
