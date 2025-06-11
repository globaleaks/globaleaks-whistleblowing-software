import io
import os
import time
from datetime import datetime
from globaleaks import models
from globaleaks.settings import Settings
from globaleaks.utils.crypto import GCE
from globaleaks.utils.antivirus import FileAnalysis
from globaleaks.models.enums import EnumStateFile
from globaleaks.jobs.job import LoopingJob
from twisted.internet.defer import inlineCallbacks
from globaleaks.orm import transact

BUFFER_SIZE = 8192

@transact
def file_delivery(session):
    files_map = {}
    ifile_tip_pairs = session.query(models.InternalFile, models.InternalTip) \
        .filter(models.InternalFile.new.is_(True),
                models.InternalTip.id == models.InternalFile.internaltip_id) \
        .order_by(models.InternalFile.creation_date) \
        .limit(20) \
        .all()

    itip_ids = {ifile.id: ifile.internaltip_id for ifile, _ in ifile_tip_pairs}

    receiver_map = {}
    if itip_ids:
        receivers = session.query(models.ReceiverTip.id, models.ReceiverTip.internaltip_id) \
            .filter(models.ReceiverTip.internaltip_id.in_(itip_ids.values())) \
            .all()

        for rtip_id, internaltip_id in receivers:
            receiver_map.setdefault(internaltip_id, []).append(rtip_id)

    for ifile, itip in ifile_tip_pairs:
        ifile.new = False
        files_map[ifile.id] = {
            'key': itip.crypto_tip_pub_key,
            'src': ifile.id,
            'dst': os.path.abspath(os.path.join(Settings.attachments_path, ifile.id)),
            'scan': True,
            'type': 'internal'
        }

        for rtip_id in receiver_map.get(ifile.internaltip_id, []):
            wbf = models.WhistleblowerFile()
            wbf.internalfile_id = ifile.id
            wbf.receivertip_id = rtip_id
            wbf.new = not ifile.creation_date == itip.creation_date
            session.add(wbf)

    rfile_tip_pairs = session.query(models.ReceiverFile, models.InternalTip) \
        .filter(models.ReceiverFile.new.is_(True),
                models.ReceiverFile.internaltip_id == models.InternalTip.id) \
        .order_by(models.ReceiverFile.creation_date) \
        .limit(20) \
        .all()

    for rfile, itip in rfile_tip_pairs:
        rfile.new = False
        files_map[rfile.id] = {
            'key': itip.crypto_tip_pub_key,
            'src': rfile.id,
            'dst': os.path.abspath(os.path.join(Settings.attachments_path, rfile.id)),
            'scan': True,
            'type': 'receiver'
        }

    return files_map

@transact
def save_antivirus_status(session, file_id, result, file_type='internal'):
    model = models.InternalFile if file_type == 'internal' else models.ReceiverFile
    file_obj = session.query(model).filter_by(id=file_id).first()
    if file_obj is None:
        return

    file_obj.verification_date = datetime.utcnow()
    if result == 'unsafe':
        file_obj.state = EnumStateFile.infected.value
    else:
        file_obj.state = EnumStateFile.verified.value

def write_encrypted_file(key, sf, dest_path):
    try:
        with GCE.streaming_encryption_open('ENCRYPT', key, dest_path) as seo:
            chunk = sf.read(BUFFER_SIZE)
            while chunk:
                seo.encrypt_chunk(chunk, 0)
                chunk = sf.read(BUFFER_SIZE)
            seo.encrypt_chunk(b'', 1)
    except Exception as ex:
        raise

def write_plaintext_file(sf, dest_path):
    with open(dest_path, 'wb') as f:
        chunk = sf.read(BUFFER_SIZE)
        while chunk:
            f.write(chunk)
            chunk = sf.read(BUFFER_SIZE)

class Delivery(LoopingJob):
    interval = 5
    monitor_interval = 180

    @inlineCallbacks
    def operation(self):
        files_map = yield file_delivery()
        scanner = FileAnalysis()

        for file_id, file in files_map.items():
            sf = self._get_source_file(file['src'])
            if sf is None:
                continue

            manual = isinstance(sf, io.BufferedReader)
            if not manual:
                sf = sf.open('r')

            if file['scan']:
                result = yield self._scan(sf, file_id, file.get('type', 'internal'), scanner)
                if result == 'unsafe':
                    sf.close()
                    continue
            else:
                save_antivirus_status(file_id, 'safe', file.get('type', 'internal'))

            sf.seek(0)
            (write_encrypted_file if file['key'] else write_plaintext_file)(file['key'] if file['key'] else sf, sf, file['dst'])
            sf.close()
            tmp_path = os.path.join(Settings.tmp_path, file_id)
            os.remove(tmp_path)

    def _get_source_file(self, filename):
        sf = self.state.get_tmp_file_by_name(filename)
        if sf is None:
            time.sleep(1)
            sf = self.state.get_tmp_file_by_name(filename)
        if sf is None:
            path = os.path.join(Settings.tmp_path, filename)
            return open(path, "rb") if os.path.exists(path) else None
        return sf

    @inlineCallbacks
    def _scan(self, sf, file_id, file_type, scanner):
        sf.seek(0)
        result = yield scanner.scan_file(sf.read())
        save_antivirus_status(file_id, result, file_type)
        return result
