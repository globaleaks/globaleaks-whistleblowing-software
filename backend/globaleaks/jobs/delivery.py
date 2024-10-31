# -*- coding: utf-8 -*-
import os

from twisted.internet import abstract
from twisted.internet.defer import inlineCallbacks

from globaleaks import models
from globaleaks.jobs.job import LoopingJob
from globaleaks.orm import transact
from globaleaks.settings import Settings
from globaleaks.utils.crypto import GCE
from globaleaks.utils.log import log
from globaleaks.utils.pgp import PGPContext


__all__ = ['Delivery']


@transact
def file_delivery(session):
    """
    This function roll over the InternalFile uploaded, extract a path, id and
    receivers associated, one entry for each combination. representing the
    WhistleblowerFile that need to be created.
    """
    receiverfiles_maps = {}
    whistleblowerfiles_maps = {}

    for ifile, itip in session.query(models.InternalFile, models.InternalTip) \
                              .filter(models.InternalFile.new.is_(True),
                                      models.InternalTip.id == models.InternalFile.internaltip_id) \
                              .order_by(models.InternalFile.creation_date) \
                              .limit(20):
        ifile.new = False
        src = ifile.id

        for rtip, user in session.query(models.ReceiverTip, models.User) \
                                 .filter(models.ReceiverTip.internaltip_id == ifile.internaltip_id,
                                         models.User.id == models.ReceiverTip.receiver_id):
            receiverfile = models.WhistleblowerFile()
            receiverfile.internalfile_id = ifile.id
            receiverfile.receivertip_id = rtip.id

            # https://github.com/globaleaks/globaleaks-whistleblowing-software/issues/444
            # avoid to mark the receiverfile as new if it is part of a submission
            # this way we avoid to send unuseful messages
            receiverfile.new = not ifile.creation_date == itip.creation_date

            session.add(receiverfile)

            if ifile.id not in receiverfiles_maps:
                receiverfiles_maps[ifile.id] = {
                    'key': itip.crypto_tip_pub_key,
                    'src': src,
                    'wbfiles': []
                }

            receiverfiles_maps[ifile.id]['wbfiles'].append({
                'dst': os.path.abspath(os.path.join(Settings.attachments_path, receiverfile.internalfile_id)),
                'pgp_key_public': user.pgp_key_public
            })

    for rfile, itip in session.query(models.ReceiverFile, models.InternalTip)\
                               .filter(models.ReceiverFile.new.is_(True),
                                       models.ReceiverFile.internaltip_id == models.InternalTip.id) \
                               .order_by(models.ReceiverFile.creation_date) \
                               .limit(20):
        rfile.new = False
        src = rfile.id

        whistleblowerfiles_maps[rfile.id] = {
            'key': itip.crypto_tip_pub_key,
            'src': src,
            'dst': os.path.abspath(os.path.join(Settings.attachments_path, rfile.id)),
        }

        rfile.new = False

    return receiverfiles_maps, whistleblowerfiles_maps


def write_plaintext_file(sf, dest_path):
    try:
        with sf.open('rb') as encrypted_file, open(dest_path, "a+b") as plaintext_file:
            chunk = encrypted_file.read(abstract.FileDescriptor.bufferSize)
            while chunk:
                plaintext_file.write(chunk)
                chunk = encrypted_file.read(abstract.FileDescriptor.bufferSize)

    except Exception as excep:
        log.err("Unable to create plaintext file %s: %s", dest_path, excep)


def write_encrypted_file(key, sf, dest_path):
    try:
        with sf.open('rb') as encrypted_file, \
             GCE.streaming_encryption_open('ENCRYPT', key, dest_path) as seo:
            chunk = encrypted_file.read(abstract.FileDescriptor.bufferSize)
            while chunk:
                seo.encrypt_chunk(chunk, 0)
                chunk = encrypted_file.read(abstract.FileDescriptor.bufferSize)

            seo.encrypt_chunk(b'', 1)
    except Exception as excep:
        log.err("Unable to create plaintext file %s: %s", dest_path, excep)


def process_receiverfiles(state, files_maps):
    """
    Function that process uploaded receiverfiles

    :param state: A reference to the application state
    :param files_maps: descriptors of whistleblower files to be processed
    """
    for a, m in files_maps.items():
        sf = state.get_tmp_file_by_name(m['src'])

        for rcounter, rf in enumerate(m['wbfiles']):
            try:
                if m['key']:
                    write_encrypted_file(m['key'], sf, rf['dst'])
                elif rf['pgp_key_public']:
                    with sf.open('rb') as encrypted_file:
                        PGPContext(rf['pgp_key_public']).encrypt_file(encrypted_file, rf['dst'])
                else:
                    write_plaintext_file(sf, rf['dst'])
            except:
                pass


def process_whistleblowerfiles(state, files_maps):
    """
    Function that process uploaded whistleblowerfiles

    :param state: A reference to the application state
    :param files_maps: descriptors of whistleblower files to be processed
    """
    for _, m in files_maps.items():
        try:
            sf = state.get_tmp_file_by_name(m['src'])

            if m['key']:
                write_encrypted_file(m['key'], sf, m['dst'])
            else:
                write_plaintext_file(sf, m['dst'])
        except:
            pass


class Delivery(LoopingJob):
    interval = 5
    monitor_interval = 180

    @inlineCallbacks
    def operation(self):
        """
        This function creates receiver files
        """
        receiverfiles_maps, whistleblowerfiles_maps = yield file_delivery()

        process_receiverfiles(self.state, receiverfiles_maps)
        process_whistleblowerfiles(self.state, whistleblowerfiles_maps)
