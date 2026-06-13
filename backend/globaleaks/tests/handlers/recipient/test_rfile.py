from twisted.internet.defer import inlineCallbacks

from globaleaks import models
from globaleaks.handlers.recipient import rtip
from globaleaks.handlers.whistleblower import wbtip
from globaleaks.jobs.delivery import Delivery
from globaleaks.orm import transact
from globaleaks.rest import errors
from globaleaks.tests import helpers

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
    user = session.query(models.User).get(user_id)
    user.can_mask_information = value
    user.can_redact_information = value


class TestWBFileWorkFlow(helpers.TestHandlerWithPopulatedDB):
    _handler = None

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
        self._handler = wbtip.ReceiverFileDownload
        wbtips_desc = yield self.get_wbtips()
        for wbtip_desc in wbtips_desc:
            rfiles_desc = yield self.get_rfiles(wbtip_desc['id'])
            for rfile_desc in rfiles_desc:
                handler = self.request(role='whistleblower', user_id=wbtip_desc['id'])
                yield handler.get(rfile_desc['id'])
                self.assertEqual(handler.request.getResponseBody(), file_content)

        # A recipient masks every recipient file.
        rtips_desc = yield self.get_rtips()
        for rtip_desc in rtips_desc:
            for rfile_desc in rtip_desc['rfiles']:
                yield mask_receiverfile(rtip_desc['id'], rfile_desc['id'])

        # The whistleblower can no longer download the masked files.
        self._handler = wbtip.ReceiverFileDownload
        wbtips_desc = yield self.get_wbtips()
        for wbtip_desc in wbtips_desc:
            rfiles_desc = yield self.get_rfiles(wbtip_desc['id'])
            for rfile_desc in rfiles_desc:
                handler = self.request(role='whistleblower', user_id=wbtip_desc['id'])
                yield self.assertFailure(handler.get(rfile_desc['id']), errors.ForbiddenOperation)

        # A recipient entitled to mask/redact keeps access to the masked file
        # (the populated recipient holds both permissions).
        self._handler = rtip.ReceiverFileDownload
        rtips_desc = yield self.get_rtips()
        for rtip_desc in rtips_desc:
            for rfile_desc in rtip_desc['rfiles']:
                handler = self.request(role='receiver', user_id=rtip_desc['receiver_id'])
                yield handler.get(rfile_desc['id'])
                self.assertTrue(handler.request.getResponseBody())

        # A recipient without the permission cannot download the masked file.
        rtips_desc = yield self.get_rtips()
        for rtip_desc in rtips_desc:
            yield set_redaction_privileges(rtip_desc['receiver_id'], False)
            for rfile_desc in rtip_desc['rfiles']:
                handler = self.request(role='receiver', user_id=rtip_desc['receiver_id'])
                yield self.assertFailure(handler.get(rfile_desc['id']), errors.ForbiddenOperation)

    @inlineCallbacks
    def test_personal_rfile_not_accessible_to_other_recipients(self):
        yield self.perform_full_submission_actions()

        # Receiver1 uploads a recipient file marked personal on a shared report.
        self._handler = rtip.ReceiverFileUpload
        rtips_desc = yield self.get_rtips()
        rtip_desc = rtips_desc[0]
        attachment = self.get_dummy_attachment(content=file_content)
        attachment['visibility'] = b'personal'
        handler = self.request(role='receiver', user_id=self.dummyReceiver_1['id'], attachment=attachment)
        yield handler.post(rtip_desc['id'])

        rtips_desc = yield self.get_rtips()
        rfile_id = rtips_desc[0]['rfiles'][0]['id']

        # The author can download their own personal file.
        self._handler = rtip.ReceiverFileDownload
        handler = self.request(role='receiver', user_id=self.dummyReceiver_1['id'])
        yield handler.get(rfile_id)
        self.assertTrue(handler.request.getResponseBody())

        # Another recipient on the same report cannot, even knowing its UUID.
        handler = self.request(role='receiver', user_id=self.dummyReceiver_2['id'])
        yield self.assertFailure(handler.get(rfile_id), errors.ResourceNotFound)
