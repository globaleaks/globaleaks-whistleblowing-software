from twisted.internet.defer import inlineCallbacks

from globaleaks import models
from globaleaks.handlers.recipient import rtip
from globaleaks.handlers.whistleblower import wbtip
from globaleaks.jobs.delivery import Delivery
from globaleaks.models.config import db_set_config_variable
from globaleaks.orm import transact
from globaleaks.rest import errors
from globaleaks.tests import helpers
from globaleaks.utils.utility import datetime_now
import io
import zipfile

file_content = b'Hello World'


@transact
def mask_receiverfile(session, itip_id, rfile_id):
    redaction = models.Redaction()
    redaction.reference_id = rfile_id
    redaction.entry = '0'
    redaction.internaltip_id = itip_id
    redaction.temporary_redaction = [{'start': '-inf', 'end': 'inf'}]
    redaction.permanent_redaction = []
    session.add(redaction)


@transact
def set_redaction_privileges(session, user_id, value):
    user = session.get(models.User, user_id)
    user.can_mask_information = value
    user.can_redact_information = value

    # The permissions are read from the profile of the user
    for permission in ('can_mask_information', 'can_redact_information'):
        row = session.query(models.UserProfilePermission) \
                     .filter(models.UserProfilePermission.profile_id == user.profile_id,
                             models.UserProfilePermission.permission == permission).one_or_none()
        if value and row is None:
            session.add(models.UserProfilePermission({'profile_id': user.profile_id,
                                                      'permission': permission}))
        elif not value and row is not None:
            session.delete(row)


class TestWBFileWorkFlow(helpers.TestHandlerWithPopulatedDB):
    _handler = None

    @staticmethod
    def downloaded_content(body):
        """
        Return the file a download carries, taken out of the archive when it is one

        :param body: The body of the response to the download
        """
        if not body.startswith(b'PK\x03\x04'):
            return body

        z = zipfile.ZipFile(io.BytesIO(body))

        for info in z.infolist():
            # The archive carries the file beside the entries the
            # application adds to describe it.
            if info.filename.upper() not in ('README.TXT', 'METADATA.CSV'):
                return z.read(info)

        return z.read(z.infolist()[0]) if z.infolist() else None

    @inlineCallbacks
    def check_wb_downloads(self, expected_content):
        """
        Check what the whistleblower gets when downloading every recipient file

        :param expected_content: The content every download carries, None when
                                 the files are masked and no download is allowed
        """
        self._handler = wbtip.ReceiverFileDownload
        wbtips_desc = yield self.get_wbtips()
        for wbtip_desc in wbtips_desc:
            rfiles_desc = yield self.get_rfiles(wbtip_desc['id'])
            for rfile_desc in rfiles_desc:
                handler = self.request(role='whistleblower', user_id=wbtip_desc['id'])
                if expected_content is None:
                    yield self.assertFailure(handler.get(rfile_desc['id']), errors.ForbiddenOperation)
                else:
                    yield handler.get(rfile_desc['id'])
                    self.assertEqual(self.downloaded_content(handler.request.getResponseBody()), expected_content)

    @inlineCallbacks
    def check_recipient_downloads(self, entitled):
        """
        Check what a recipient gets when downloading every masked recipient file

        :param entitled: Whether the recipient holds the redaction privileges;
                         when it does not they are revoked before downloading
        """
        self._handler = rtip.ReceiverFileDownload
        rtips_desc = yield self.get_rtips()
        for rtip_desc in rtips_desc:
            if not entitled:
                yield set_redaction_privileges(rtip_desc['receiver_id'], False)

            for rfile_desc in rtip_desc['rfiles']:
                handler = self.request(role='receiver', user_id=rtip_desc['receiver_id'])
                if entitled:
                    yield handler.get(rfile_desc['id'])
                    self.assertTrue(handler.request.getResponseBody())
                else:
                    yield self.assertFailure(handler.get(rfile_desc['id']), errors.ForbiddenOperation)

    @inlineCallbacks
    def test_get(self):
        yield self.perform_full_submission_actions()

        self._handler = rtip.ReceiverFileUpload
        rtips_desc = yield self.get_rtips()
        for rtip_desc in rtips_desc:
            attachment = self.get_dummy_attachment(content=file_content)
            handler = self.request(role='receiver', user_id=rtip_desc['receiver_id'], attachment=attachment)
            yield handler.post(rtip_desc['id'])

        yield Delivery().run()

        # The whistleblower can download recipient files until they are masked.
        yield self.check_wb_downloads(file_content)

        # A recipient masks every recipient file.
        rtips_desc = yield self.get_rtips()
        for rtip_desc in rtips_desc:
            for rfile_desc in rtip_desc['rfiles']:
                yield mask_receiverfile(rtip_desc['id'], rfile_desc['id'])

        # The whistleblower can no longer download the masked files.
        yield self.check_wb_downloads(None)

        # A recipient entitled to mask/redact keeps access to the masked file
        # (the populated recipient holds both permissions).
        yield self.check_recipient_downloads(True)

        # A recipient without the permission cannot download the masked file.
        yield self.check_recipient_downloads(False)

    @inlineCallbacks
    def test_personal_rfile_not_accessible_to_other_recipients(self):
        yield self.perform_full_submission_actions()

        # Receiver1 uploads a recipient file marked personal on a shared report.
        self._handler = rtip.ReceiverFileUpload
        rtips_desc = yield self.get_rtips()
        rtip_desc = rtips_desc[0]
        attachment = self.get_dummy_attachment(content=file_content)
        attachment['visibility'] = b'personal'
        handler = self.request(role='receiver', user_id=self.dummy_receiver_1['id'], attachment=attachment)
        yield handler.post(rtip_desc['id'])

        # The upload only registers the file: the delivery job is what writes
        # it to the attachments, after the scan.
        yield Delivery().run()

        rtips_desc = yield self.get_rtips()
        rfile_id = rtips_desc[0]['rfiles'][0]['id']

        # The author can download their own personal file.
        self._handler = rtip.ReceiverFileDownload
        handler = self.request(role='receiver', user_id=self.dummy_receiver_1['id'])
        yield handler.get(rfile_id)
        self.assertTrue(handler.request.getResponseBody())

        # Another recipient on the same report cannot, even knowing its UUID.
        handler = self.request(role='receiver', user_id=self.dummy_receiver_2['id'])
        yield self.assertFailure(handler.get(rfile_id), errors.ResourceNotFound)


class TestReceiverFileDownloadAntivirus(helpers.TestHandlerWithPopulatedDB):
    _handler = rtip.ReceiverFileDownload

    @transact
    def set_antivirus_enabled(self, session, enabled):
        db_set_config_variable(session, 1, 'antivirus_enabled', enabled)

    @transact
    def set_rfile_antivirus_state(self, session, file_id, state):
        db_set_config_variable(session, 1, 'antivirus_enabled', True)
        rfile = session.query(models.ReceiverFile).filter_by(id=file_id).one()
        rfile.state = state
        rfile.verification_date = datetime_now()

    @inlineCallbacks
    def create_receiver_file(self):
        yield self.perform_full_submission_actions()

        rtip_desc = (yield self.get_rtips())[0]
        attachment = self.get_dummy_attachment(content=file_content)
        handler = self.request(role='receiver',
                               user_id=rtip_desc['receiver_id'],
                               attachment=attachment,
                               handler_cls=rtip.ReceiverFileUpload)
        yield handler.post(rtip_desc['id'])
        yield Delivery().run()

        rtip_desc = (yield self.get_rtips())[0]
        return rtip_desc['receiver_id'], rtip_desc['rfiles'][0]['id']


class TestWhistleblowerReceiverFileDownloadAntivirus(helpers.TestHandlerWithPopulatedDB):
    _handler = wbtip.ReceiverFileDownload

    @transact
    def set_rfile_antivirus_state(self, session, file_id, state):
        db_set_config_variable(session, 1, 'antivirus_enabled', True)
        rfile = session.query(models.ReceiverFile).filter_by(id=file_id).one()
        rfile.state = state
        rfile.verification_date = datetime_now()

    @inlineCallbacks
    def create_receiver_file(self):
        yield self.perform_full_submission_actions()

        rtip_desc = (yield self.get_rtips())[0]
        attachment = self.get_dummy_attachment(content=file_content)
        handler = self.request(role='receiver',
                               user_id=rtip_desc['receiver_id'],
                               attachment=attachment,
                               handler_cls=rtip.ReceiverFileUpload)
        yield handler.post(rtip_desc['id'])
        yield Delivery().run()

        rfile_id = (yield self.get_rfiles(rtip_desc['id']))[0]['id']
        return rtip_desc['id'], rfile_id
