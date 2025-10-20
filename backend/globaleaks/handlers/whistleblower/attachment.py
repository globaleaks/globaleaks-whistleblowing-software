# Handler dealing with submissions file uploads and subsequent submissions attachments
from nacl.encoding import Base64Encoder

from globaleaks.state import State
from globaleaks import models
from globaleaks.handlers.base import BaseHandler
from globaleaks.models import serializers
from globaleaks.orm import transact, db_log
from globaleaks.utils.crypto import GCE
from globaleaks.utils.utility import datetime_now


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
    now = datetime_now()

    itip = session.query(models.InternalTip) \
                  .filter(models.InternalTip.id == internaltip_id,
                          models.InternalTip.status != 'closed',
                          models.InternalTip.tid.in_({tid, State.tenants[tid].cache.ptid})).one()

    itip.update_date = now
    itip.last_access = now

    # Store file type and name before encryption for audit log
    file_type_for_log = uploaded_file['type']
    filename_for_log = uploaded_file['name']

    if itip.crypto_tip_pub_key:
        for k in ['name', 'type', 'size']:
            uploaded_file[k] = Base64Encoder.encode(GCE.asymmetric_encrypt(itip.crypto_tip_pub_key, str(uploaded_file[k])))

    new_file = models.InternalFile()
    new_file.id = uploaded_file['filename']
    new_file.name = uploaded_file['name']
    new_file.content_type = uploaded_file['type']
    new_file.size = uploaded_file['size']
    new_file.reference_id = uploaded_file['reference_id']
    new_file.internaltip_id = internaltip_id

    if uploaded_file['submission']:
        new_file.creation_date = itip.creation_date

    session.add(new_file)

    # Log whistleblower file upload
    log_data = {
        'file_type': file_type_for_log,
        'filename': filename_for_log
    }

    db_log(session, tid=tid, type='upload_file', user_id=itip.operator_id, object_id=itip.id, data=log_data)

    return serializers.serialize_ifile(session, new_file)


class SubmissionAttachment(BaseHandler):
    """
    Whistleblower interface to upload a new file for a non-finalized submission
    """
    check_roles = 'whistleblower'
    upload_handler = True

    def post(self):
        self.uploaded_file['submission'] = True
        self.session.files.append(self.uploaded_file)


class PostSubmissionAttachment(SubmissionAttachment):
    """
    Whistleblower interface to upload a new file for an existing submission
    """
    check_roles = 'whistleblower'
    upload_handler = True

    def post(self):
        self.uploaded_file['submission'] = False

        return register_ifile_on_db(self.request.tid, self.session.user_id, self.uploaded_file)
