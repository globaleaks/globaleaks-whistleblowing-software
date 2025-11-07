import os

from twisted.internet import abstract
from twisted.internet.defer import inlineCallbacks

from globaleaks import models
from globaleaks.jobs.job import LoopingJob
from globaleaks.orm import transact
from globaleaks.settings import Settings
from globaleaks.utils.crypto import GCE
from globaleaks.utils.log import log


__all__ = ['Delivery']


@transact
def file_delivery(session):
    """
    This function roll over the InternalFile uploaded, extract a path, id and
    receivers associated, one entry for each combination. representing the
    WhistleblowerFile that need to be created.
    """
    files_map = {}

    # Fetch the InternalFiles and their related InternalTips
    ifile_tip_pairs = session.query(models.InternalFile, models.InternalTip) \
                             .filter(models.InternalFile.new.is_(True),
                                     models.InternalTip.id == models.InternalFile.internaltip_id) \
                             .order_by(models.InternalFile.creation_date) \
                             .limit(20) \
                             .all()

    # Extract InternalFile IDs for batch query
    itip_ids = {ifile.id: ifile.internaltip_id for ifile, _ in ifile_tip_pairs}

    # Fetch all ReceiverTips and Users in one query
    receiver_map = {}
    if itip_ids:
        receivers = session.query(models.ReceiverTip.id, models.ReceiverTip.internaltip_id) \
                           .filter(models.ReceiverTip.internaltip_id.in_(itip_ids.values())) \
                           .all()

        for rtip_id, internaltip_id in receivers:
            receiver_map.setdefault(internaltip_id, []).append(rtip_id)

    # Process the files and create WhistleblowerFile records
    for ifile, itip in ifile_tip_pairs:
        ifile.new = False  # Mark as processed

        # Store metadata
        files_map[ifile.id] = {
            'key': itip.crypto_tip_pub_key,
            'src': ifile.id,
            'dst': os.path.abspath(os.path.join(Settings.attachments_path, ifile.id)),
        }

        # Retrieve all receivers for this file
        for rtip_id in receiver_map.get(ifile.internaltip_id, []):
            whistleblowerfile = models.WhistleblowerFile()
            whistleblowerfile.internalfile_id = ifile.id
            whistleblowerfile.receivertip_id = rtip_id

            # https://github.com/globaleaks/globaleaks-whistleblowing-software/issues/444
            # avoid to mark the receiverfile as new if it is part of a submission
            # this way we avoid to send unuseful messages
            whistleblowerfile.new = not ifile.creation_date == itip.creation_date

            session.add(whistleblowerfile)

    for rfile, itip in session.query(models.ReceiverFile, models.InternalTip)\
                               .filter(models.ReceiverFile.new.is_(True),
                                       models.ReceiverFile.internaltip_id == models.InternalTip.id) \
                               .order_by(models.ReceiverFile.creation_date) \
                               .limit(20):
        rfile.new = False

        files_map[rfile.id] = {
            'key': itip.crypto_tip_pub_key,
            'src': rfile.id,
            'dst': os.path.abspath(os.path.join(Settings.attachments_path, rfile.id)),
        }

    return files_map


def write_plaintext_file(sf, dest_path):
    try:
        with sf.open('r') as encrypted_file, open(dest_path, "a+b") as plaintext_file:
            chunk = encrypted_file.read(abstract.FileDescriptor.bufferSize)
            while chunk:
                plaintext_file.write(chunk)
                chunk = encrypted_file.read(abstract.FileDescriptor.bufferSize)

    except Exception as excep:
        log.err("Unable to create plaintext file %s: %s", dest_path, excep)


def write_encrypted_file(key, sf, dest_path):
    try:
        with sf.open('r') as encrypted_file, \
             GCE.streaming_encryption_open('ENCRYPT', key, dest_path) as seo:
            chunk = encrypted_file.read(abstract.FileDescriptor.bufferSize)
            while chunk:
                seo.encrypt_chunk(chunk, 0)
                chunk = encrypted_file.read(abstract.FileDescriptor.bufferSize)

            seo.encrypt_chunk(b'', 1)
    except Exception as excep:
        log.err("Unable to create plaintext file %s: %s", dest_path, excep)


class Delivery(LoopingJob):
    interval = 5
    monitor_interval = 180

    @inlineCallbacks
    def operation(self):
        """
        This function creates receiver files
        """
        files_map = yield file_delivery()

        for _, file in files_map.items():
            try:
                sf = self.state.get_tmp_file_by_name(file['src'])

                if file['key']:
                    write_encrypted_file(file['key'], sf, file['dst'])
                else:
                    write_plaintext_file(sf, file['dst'])
            except:
                pass
