from globaleaks.jobs.job import LoopingJob
from globaleaks.settings import Settings
from globaleaks.utils.crypto import GCE
from globaleaks.state import State
from globaleaks.utils.antivirus import FileAnalysis
from globaleaks.models.enums import EnumStateFile
from globaleaks.models.config import db_get_config_variable
from globaleaks import models
from globaleaks.orm import transact
from twisted.internet.defer import inlineCallbacks
from io import BytesIO
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


def decrypt_file(path, key):
    sfo = GCE.streaming_encryption_open('DECRYPT', key, path)
    decrypted_buffer = BytesIO()
    while True:
        chunk = sfo.read(BUFFER_SIZE)
        if not chunk:
            break
        decrypted_buffer.write(chunk)

    return decrypted_buffer.getvalue()


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

        decrypted_content = decrypt_file(encrypted_path, tip_prv_key)
        if not decrypted_content:
            return

        scanner = self.scanner_factory()
        result = yield scanner.scan_file(decrypted_content)

        update_verification_status(name, result)
        yield None
