# Handlers dealing with tip interface for whistleblowers (wbtip)
from io import BytesIO
import json
import mimetypes
import os

from nacl.encoding import Base64Encoder
from globaleaks.utils.securetempfile import SecureTemporaryFile
from globaleaks.utils.zipstream import ZipStream
from twisted.internet.threads import deferToThread
from twisted.internet.defer import inlineCallbacks, returnValue

from globaleaks import models
from globaleaks.handlers.admin.auditlog import serialize_log
from globaleaks.handlers.admin.node import db_admin_serialize_node
from globaleaks.handlers.admin.notification import db_get_notification
from globaleaks.handlers.base import BaseHandler
from globaleaks.handlers.whistleblower.submission import decrypt_tip, \
    db_set_internaltip_answers, db_get_questionnaire, \
    db_archive_questionnaire_schema, db_set_internaltip_data, \
    extract_statistical_data
from globaleaks.handlers.user import serialize_user
from globaleaks.models import serializers
from globaleaks.orm import db_get, transact
from globaleaks.rest import errors, requests
from globaleaks.state import State
from globaleaks.utils.antivirus import enqueue_antivirus_scan, enqueue_tip_files_for_rescan, get_av_result, prepare_file_download, serialize_files_metadata_csv
from globaleaks.utils.crypto import GCE, sha256, sha512
from globaleaks.utils.fs import directory_traversal_check
from globaleaks.utils.log import log
from globaleaks.utils.templating import Templating, mail_uses_smtp2
from globaleaks.utils.utility import datetime_now, datetime_null
from globaleaks.models.config import db_get_config_variable

@transact
def get_report_audit_log(session, tid, user_id):
    _ = db_get(session, models.InternalTip, models.InternalTip.id == user_id)

    logs = session.query(models.AuditLog) \
                  .filter(models.AuditLog.tid == tid,
                          models.AuditLog.object_id == user_id) \
                  .order_by(models.AuditLog.date.desc())

    return [serialize_log(log) for log in logs]


def db_notify_report_update(session, user, rtip, itip):
    """
    :param session: An ORM session
    :param user: An user ORM object
    :param rtip: A rtip ORM object
    :param itip: A itip ORM object
    """
    data = {
      'type': 'tip_update',
      'user': serialize_user(session, user, user.language),
      'node': db_admin_serialize_node(session, user.tid, user.language),
      'tip': serializers.serialize_rtip(session, itip, rtip, user.language),
    }

    data['notification'] = db_get_notification(session, user.tid, user.language)

    subject, body = Templating().get_mail_subject_and_body(data)

    session.add(models.Mail({
        'address': data['user']['mail_address'],
        'subject': subject,
        'body': body,
        'tid': user.tid,
        'secondary_smtp': mail_uses_smtp2(data['notification'], data['type'])
    }))


def db_notify_recipients_of_tip_update(session, itip_id):
    for user, rtip, itip in session.query(models.User, models.ReceiverTip, models.InternalTip) \
                                   .filter(models.User.id == models.ReceiverTip.receiver_id,
                                           models.ReceiverTip.internaltip_id == models.InternalTip.id,
                                           models.ReceiverTip.last_access > models.ReceiverTip.last_notification,
                                           models.InternalTip.id == itip_id):
        db_notify_report_update(session, user, rtip, itip)


def db_get_wbtip(session, itip_id, language):
    itip = db_get(session, models.InternalTip, models.InternalTip.id == itip_id)

    itip.last_access = datetime_now()

    return serializers.serialize_wbtip(session, itip, language), Base64Encoder.decode(itip.crypto_tip_prv_key)


@transact
def get_wbtip(session, itip_id, language):
    return db_get_wbtip(session, itip_id, language)


@transact
def create_comment(session, tid, user_id, content):
    itip = db_get(session,
                  models.InternalTip,
                  (models.InternalTip.id == user_id,
                   models.InternalTip.tid.in_({tid, State.tenants[tid].cache.ptid})))

    itip.update_date = itip.last_access = datetime_now()

    _content = content
    hash_sha256 = sha256(content)
    hash_sha512 = sha512(content)
    _hash_sha256 = hash_sha256.decode()
    _hash_sha512 = hash_sha512.decode()
    if itip.crypto_tip_pub_key:
        _content = Base64Encoder.encode(GCE.asymmetric_encrypt(itip.crypto_tip_pub_key, content)).decode()
        _hash_sha256 = Base64Encoder.encode(GCE.asymmetric_encrypt(itip.crypto_tip_pub_key, hash_sha256)).decode()
        _hash_sha512 = Base64Encoder.encode(GCE.asymmetric_encrypt(itip.crypto_tip_pub_key, hash_sha512)).decode()

    comment = models.Comment()
    comment.internaltip_id = itip.id
    comment.content = _content
    comment.hash_sha256 = _hash_sha256
    comment.hash_sha512 = _hash_sha512
    session.add(comment)
    session.flush()

    ret = serializers.serialize_comment(session, comment)
    ret['content'] = content
    ret['hash_sha256'] = hash_sha256
    ret['hash_sha512'] = hash_sha512

    return ret


@transact
def update_identity_information(session, tid, user_id, identity_field_id, wbi, language):
    itip = db_get(session,
                  models.InternalTip,
                  (models.InternalTip.id == user_id,
                   models.InternalTip.status != 'closed',
                   models.InternalTip.tid == tid))

    if itip.crypto_tip_pub_key:
        wbi = Base64Encoder.encode(GCE.asymmetric_encrypt(itip.crypto_tip_pub_key, json.dumps(wbi).encode())).decode()

    db_set_internaltip_data(session, itip.id, 'whistleblower_identity', wbi)

    now = datetime_now()
    itip.update_date = now
    itip.last_access = now

    db_notify_recipients_of_tip_update(session, itip.id)


@transact
def store_additional_questionnaire_answers(session, tid, user_id, answers, language):
    itip, context = session.query(models.InternalTip, models.Context) \
                           .filter(models.InternalTip.id == user_id,
                                   models.InternalTip.status != 'closed',
                                   models.InternalTip.tid == tid,
                                   models.Context.id == models.InternalTip.context_id).one()

    if not context.additional_questionnaire_id:
        return

    for _, field_items in answers.items():
            for item in field_items:
                if 'value' in item and item['value']:
                    val_str = str(item['value'])
                    item['hash_sha256'] = sha256(val_str).decode()
                    item['hash_sha512'] = sha512(val_str).decode()

    steps = db_get_questionnaire(session, tid, context.additional_questionnaire_id, None)['steps']
    questionnaire_hash = db_archive_questionnaire_schema(session, steps)

    stat_data = extract_statistical_data(session, tid, answers)

    if itip.crypto_tip_pub_key:
        if stat_data:
            crypto_stat_pub_key = db_get(session, models.Config.value, (models.Config.tid == tid, models.Config.var_name == 'crypto_stat_pub_key'))[0]
            stat_data = Base64Encoder.encode(GCE.asymmetric_encrypt(crypto_stat_pub_key, json.dumps(stat_data, cls=JSONEncoder).encode())).decode()

        answers = Base64Encoder.encode(GCE.asymmetric_encrypt(itip.crypto_tip_pub_key, json.dumps(answers).encode())).decode()

    db_set_internaltip_answers(session, itip.id, questionnaire_hash, answers, stat_data)

    db_notify_recipients_of_tip_update(session, itip.id)


@transact
def change_receipt(session, itip_id, cc, receipt, receipt_change_needed):
    """
    Transaction for updating old receipt to a new one
    """
    itip = session.query(models.InternalTip) \
                  .filter(models.InternalTip.id == itip_id).one_or_none()
    if itip is None:
        return

    tid = itip.tid

    # update receipt
    wb_key, itip.receipt_hash = GCE.calculate_key_and_hash(receipt, State.tenants[tid].cache.receipt_salt)
    itip.receipt_change_needed = receipt_change_needed

    if cc is None:
        return

    # update private keys
    itip.crypto_prv_key = Base64Encoder.encode(GCE.symmetric_encrypt(wb_key, cc))


class Operations(BaseHandler):
    """
    This interface expose some utility methods for the Whistleblower Tip.
    """
    check_roles = "whistleblower"

    def put(self):
        request = self.validate_request(self.request.content.read(), requests.OpsDesc)
        if request["operation"] != "change_receipt":
            raise errors.InputValidationError("Invalid command")

        return change_receipt(self.session.user_id, self.session.cc,
                              self.session.properties["new_receipt"],
                              "operator_session" in self.session.properties)


class WBTipInstance(BaseHandler):
    """
    This interface expose the Whistleblower Tip.
    """
    check_roles = 'whistleblower'

    @inlineCallbacks
    def get(self):
        tip, crypto_tip_prv_key = yield get_wbtip(self.session.user_id, self.request.language)

        if State.tenants[self.request.tid].cache.antivirus_enabled and crypto_tip_prv_key:
            enqueue_tip_files_for_rescan(tip, GCE.asymmetric_decrypt(self.session.cc, crypto_tip_prv_key))

        tip = yield serializers.process_logs(tip, tip['id'])

        if crypto_tip_prv_key:
            tip = yield deferToThread(decrypt_tip, self.session.cc, crypto_tip_prv_key, tip)

        returnValue(tip)


class WBTipCommentCollection(BaseHandler):
    """
    This interface expose the Whistleblower Tip Comments
    """
    check_roles = 'whistleblower'

    def post(self):
        request = self.validate_request(self.request.content.read(), requests.CommentDesc)
        return create_comment(self.request.tid, self.session.user_id, request['content'])


class WhistleblowerFileDownload(BaseHandler):
    """
    This handler exposes wbfiles for download.
    """
    check_roles = 'whistleblower'
    handler_exec_time_threshold = 3600

    @transact
    def download_wbfile(self, session, tid, user_id, file_id):
        ifile, itip = db_get(session,
                             (models.InternalFile,
                              models.InternalTip),
                             (models.InternalFile.id == file_id,
                              models.InternalFile.internaltip_id == models.InternalTip.id,
                              models.InternalTip.id == user_id))
        log.debug("Download of file %s by whistleblower %s" % (ifile.id, user_id))
        antivirus_enabled = db_get_config_variable(session, tid, 'antivirus_enabled')
        recheck_needed = prepare_file_download(ifile, antivirus_enabled)

        return ifile.name, ifile.id, itip.crypto_tip_prv_key, ifile.state, antivirus_enabled, recheck_needed, ifile.size

    @inlineCallbacks
    def get(self, wbfile_id):
        name, ifile_id, tip_prv_key, state, antivirus_enabled, recheck_needed, size = yield self.download_wbfile(
            self.request.tid, self.session.user_id, wbfile_id)

        if recheck_needed and tip_prv_key:
            _tip_prv_key = GCE.asymmetric_decrypt(self.session.cc, Base64Encoder.decode(tip_prv_key))
            enqueue_antivirus_scan(ifile_id, _tip_prv_key)

        file_path = os.path.join(self.state.settings.attachments_path, ifile_id)
        directory_traversal_check(self.state.settings.attachments_path, file_path)
        self.check_file_presence(file_path)

        files = []

        if tip_prv_key:
            tip_prv_key = GCE.asymmetric_decrypt(self.session.cc, Base64Encoder.decode(tip_prv_key))
            name = GCE.asymmetric_decrypt(tip_prv_key, Base64Encoder.decode(name.encode())).decode()
            files.append({'key': tip_prv_key, 'path': file_path, 'name': name})
        else:
            files.append({'path': file_path, 'name': name})

        mimetype, _ = mimetypes.guess_type(name)
        mimetype = mimetype or 'application/octet-stream'
        if tip_prv_key and size:
            size = int(GCE.asymmetric_decrypt(tip_prv_key, Base64Encoder.decode(str(size).encode())).decode())

        metadata = serialize_files_metadata_csv([{'name': name, 'type': mimetype,
                                                  'size': size, 'av_result': get_av_result(state)}])
        files.append({'fo': BytesIO(metadata), 'name': 'metadata.csv'})

        zipstream = ZipStream(files)
        stf = SecureTemporaryFile(self.state.settings.tmp_path)

        with stf.open('w') as f:
            for x in zipstream:
                f.write(x)

        zip_name = os.path.splitext(name)[0] + '.zip'
        with stf.open('r') as f:
            yield self.write_file_as_download(zip_name, f)


class ReceiverFileDownload(BaseHandler):
    check_roles = 'whistleblower'
    handler_exec_time_threshold = 3600

    @transact
    def download_rfile(self, session, tid, file_id):
        rfile, wbtip = db_get(session,
                               (models.ReceiverFile, models.InternalTip),
                               (models.ReceiverFile.id == file_id,
                                models.ReceiverFile.internaltip_id == models.InternalTip.id,
                                models.InternalTip.id == self.session.user_id))

        if not wbtip:
            raise errors.ResourceNotFound

        if rfile.access_date == datetime_null():
            rfile.access_date = datetime_now()

        antivirus_enabled = db_get_config_variable(session, tid, 'antivirus_enabled')
        recheck_needed = prepare_file_download(rfile, antivirus_enabled)

        log.debug("Download of file %s by whistleblower %s",
                  rfile.id, self.session.user_id)

        return (rfile.name, rfile.id, Base64Encoder.decode(wbtip.crypto_tip_prv_key), '',
                rfile.state, recheck_needed, rfile.size)

    @inlineCallbacks
    def get(self, rfile_id):
        (name, filelocation, tip_prv_key, pgp_key,
         state, recheck_needed, size) = yield self.download_rfile(self.request.tid, rfile_id)

        if recheck_needed and tip_prv_key:
            _tip_prv_key = GCE.asymmetric_decrypt(self.session.cc, tip_prv_key)
            enqueue_antivirus_scan(filelocation, _tip_prv_key)

        file_path = os.path.join(self.state.settings.attachments_path, filelocation)
        directory_traversal_check(self.state.settings.attachments_path, file_path)

        files = []
        if tip_prv_key:
            tip_prv_key = GCE.asymmetric_decrypt(self.session.cc, tip_prv_key)
            name = GCE.asymmetric_decrypt(tip_prv_key, Base64Encoder.decode(name.encode())).decode()
            files.append({'key': tip_prv_key, 'path': file_path, 'name': name})
        else:
            files.append({'path': file_path, 'name': name})

        mimetype, _ = mimetypes.guess_type(name)
        mimetype = mimetype or 'application/octet-stream'
        if tip_prv_key and size:
            size = int(GCE.asymmetric_decrypt(tip_prv_key, Base64Encoder.decode(str(size).encode())).decode())

        metadata = serialize_files_metadata_csv([{'name': name, 'type': mimetype,
                                                  'size': size, 'av_result': get_av_result(state)}])
        files.append({'fo': BytesIO(metadata), 'name': 'metadata.csv'})

        zipstream = ZipStream(files)
        stf = SecureTemporaryFile(self.state.settings.tmp_path)

        with stf.open('w') as f:
            for x in zipstream:
                f.write(x)

        with stf.open('r') as f:
            yield self.write_file_as_download(name + '.zip', f, pgp_key)


class WBTipIdentityHandler(BaseHandler):
    """
    This is the interface that securely allows the whistleblower to provide his identity
    """
    check_roles = 'whistleblower'

    def post(self):
        request = self.validate_request(self.request.content.read(), requests.WhisleblowerIdentityAnswers)

        return update_identity_information(self.request.tid,
                                           self.session.user_id,
                                           request['identity_field_id'],
                                           request['identity_field_answers'],
                                           self.request.language)


class WBTipAdditionalQuestionnaire(BaseHandler):
    """
    This is the interface that securely allows the whistleblower to fill the additional questionnaire
    """
    check_roles = 'whistleblower'

    def post(self):
        request = self.validate_request(self.request.content.read(), requests.AdditionalQuestionnaireAnswers)
        return store_additional_questionnaire_answers(self.request.tid,
                                                      self.session.user_id,
                                                      request['answers'],
                                                      self.request.language)

class ReportAuditLog(BaseHandler):
    """
    Handler that provide access to the report audit log
    """
    check_roles = 'whistleblower'

    def get(self, tip_id):
        return get_report_audit_log(self.session.tid, self.session.user_id)
