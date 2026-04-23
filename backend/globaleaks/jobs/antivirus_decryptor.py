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

@transact
def update_verification_status(session, file_id, result, file_type):
    model = models.InternalFile if file_type == 'internal' else models.ReceiverFile
    file_obj = session.query(model).filter_by(id=file_id).first()
    if file_obj:
        tid = session.query(models.InternalTip.tid).filter_by(id=file_obj.internaltip_id).scalar()
        if tid is None or not db_get_config_variable(session, tid, 'antivirus_enabled'):
            result = None

        if result == 'safe':
            file_obj.verification_date = datetime.now(timezone.utc)
            file_obj.state = EnumStateFile.verified.name
        elif result == 'unsafe':
            file_obj.verification_date = datetime.now(timezone.utc)
            file_obj.state = EnumStateFile.infected.name
        else:
            file_obj.verification_date = None
            file_obj.state = EnumStateFile.pending.name

class AntivirusDecryptor(LoopingJob):
    interval = 3

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

        sfo = GCE.streaming_encryption_open('DECRYPT', tip_prv_key, encrypted_path)
        decrypted_buffer = BytesIO()
        while True:
            chunk = sfo.read(BUFFER_SIZE)
            if not chunk:
                break
            decrypted_buffer.write(chunk)

        decrypted_content = decrypted_buffer.getvalue()
        if not decrypted_content:
            return

        scanner = FileAnalysis()
        result = yield scanner.scan_file(decrypted_content)

        file_type = 'internal' if name.startswith('i') else 'receiver'
        update_verification_status(name, result, file_type)
        yield None
