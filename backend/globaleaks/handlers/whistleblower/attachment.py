# Handler dealing with submissions file uploads and subsequent submissions attachments

from nacl.encoding import Base64Encoder
from twisted.internet.defer import inlineCallbacks

from globaleaks import models
from globaleaks.handlers.base import BaseHandler
from globaleaks.models import serializers
from globaleaks.orm import db_log, transact
from globaleaks.rest import errors
from globaleaks.utils.crypto import GCE
from globaleaks.transactions import db_check_disk_space_limit
from globaleaks.utils.fs import srm
from globaleaks.utils.utility import datetime_now


@transact
def check_disk_space_limit(session, tid, size):
    db_check_disk_space_limit(session, tid, size)


@transact
def register_ifile_on_db(session, tid, internaltip_id, uploaded_file):
    """
    Register a file on the database

    :param session: An ORM session
    :param tid: A tenant id
    :param internaltip_id: A id of the submission on which attaching the file
    :param uploaded_file: A file to be attached
    :return: A descriptor of the file
    """
    db_check_disk_space_limit(session, tid, int(uploaded_file['size']))

    now = datetime_now()

    itip = session.query(models.InternalTip) \
                  .filter(models.InternalTip.id == internaltip_id,
                          models.InternalTip.status != 'closed',
                          models.InternalTip.tid == tid).one()

    itip.update_date = now
    itip.last_access = now

    if itip.crypto_tip_pub_key:
        for k in ['name', 'type', 'size', 'hash_sha256', 'hash_sha512']:
            uploaded_file[k] = Base64Encoder.encode(GCE.asymmetric_encrypt(itip.crypto_tip_pub_key, str(uploaded_file[k])))

    new_file = models.InternalFile()
    new_file.id = uploaded_file['filename']
    new_file.name = uploaded_file['name']
    new_file.content_type = uploaded_file['type']
    new_file.size = uploaded_file['size']
    new_file.reference_id = uploaded_file['reference_id']
    new_file.internaltip_id = internaltip_id
    new_file.hash_sha256 = uploaded_file['hash_sha256']
    new_file.hash_sha512 = uploaded_file['hash_sha512']

    if uploaded_file['submission']:
        new_file.creation_date = itip.creation_date

    session.add(new_file)

    db_log(session, tid=tid, type='whistleblower_upload_file', user_id=internaltip_id, object_id=new_file.id, data={'internaltip_id': internaltip_id})

    return serializers.serialize_ifile(session, new_file)


class SubmissionAttachment(BaseHandler):
    """
    Whistleblower interface to upload a new file for a non-finalized submission
    """
    check_roles = 'whistleblower'
    upload_handler = True

    def discard_upload(self):
        self.state.TempUploadFiles.pop(self.uploaded_file['id'], None)
        try:
            srm(self.uploaded_file['body'].filepath)
        except OSError:
            pass

    @inlineCallbacks
    def post(self):
        size = sum(int(f['size']) for f in self.session.files) + int(self.uploaded_file['size'])

        try:
            yield check_disk_space_limit(self.request.tid, size)
        except errors.TenantLimitExceeded:
            self.discard_upload()
            raise

        self.uploaded_file['submission'] = True
        self.session.files.append(self.uploaded_file)


class PostSubmissionAttachment(SubmissionAttachment):
    """
    Whistleblower interface to upload a new file for an existing submission
    """
    check_roles = 'whistleblower'
    upload_handler = True

    @inlineCallbacks
    def post(self):
        self.uploaded_file['submission'] = False

        try:
            return (yield register_ifile_on_db(self.request.tid, self.session.user_id, self.uploaded_file))
        except errors.TenantLimitExceeded:
            self.discard_upload()
            raise
