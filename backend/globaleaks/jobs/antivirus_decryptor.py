from globaleaks.jobs.job import LoopingJob
from globaleaks.settings import Settings
from globaleaks.utils.crypto import GCE
from globaleaks.state import State
from globaleaks.utils.antivirus import FileAnalysis, SizedReader
from globaleaks.models.enums import EnumStateFile
from globaleaks.models.config import db_get_config_variable
from globaleaks import models
from globaleaks.orm import transact
from twisted.internet.defer import inlineCallbacks
from datetime import datetime, timezone
import os

BUFFER_SIZE = 8192

def verdict_to_state(result):
    # A file the scanner has not judged stays pending: only a verdict it did
    # give is a verdict, and anything else is the absence of one.
    if result == 'safe':
        return EnumStateFile.verified.name

    if result == 'unsafe':
        return EnumStateFile.infected.name

    return EnumStateFile.pending.name


def open_decrypted(path, key):
    """
    Open a file stored encrypted, to read its content in the clear a chunk at a time
    instead of holding it whole in memory

    :param path: The path of the file
    :param key: The private key of the report
    :return: A reader of the content, or None if the file is empty
    """
    sfo = GCE.streaming_encryption_open('DECRYPT', key, path)
    first = sfo.read(BUFFER_SIZE)
    if not first:
        sfo.close()
        return None

    return SizedReader(sfo, first)


@transact
def update_verification_status(session, file_id, result):
    # File ids are globally unique upload filenames, so resolve the record by
    # id across both file tables instead of guessing the type from the name.
    file_obj = session.query(models.InternalFile).filter_by(id=file_id).first() or \
               session.query(models.ReceiverFile).filter_by(id=file_id).first()
    if file_obj:
        tid = session.query(models.InternalTip.tid).filter_by(id=file_obj.internaltip_id).scalar()
        if tid is None or not db_get_config_variable(session, tid, 'antivirus_enabled'):
            result = None

        state = verdict_to_state(result)

        file_obj.state = state
        file_obj.verification_date = None if state == EnumStateFile.pending.name \
                                     else datetime.now(timezone.utc)

class AntivirusDecryptor(LoopingJob):
    interval = 3
    scanner_factory = FileAnalysis

    @inlineCallbacks
    def operation(self):
        if not State.antivirus_files:
            return

        name, tip_prv_key = State.antivirus_files.pop(0)
        State.antivirus_file_ids.discard(name)
        if not tip_prv_key:
            return

        encrypted_path = os.path.join(Settings.attachments_path, name)
        if not os.path.exists(encrypted_path):
            return

        content = open_decrypted(encrypted_path, tip_prv_key)
        if content is None:
            return

        try:
            scanner = self.scanner_factory()
            result = yield scanner.scan_file(content)
        finally:
            content.close()

        update_verification_status(name, result)
        yield None
