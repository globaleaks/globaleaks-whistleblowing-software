import io
import zipfile

from globaleaks import models
from globaleaks.handlers.recipient import export, rtip
from globaleaks.jobs.delivery import Delivery
from globaleaks.orm import transact
from globaleaks.tests import helpers
from twisted.internet.defer import DeferredList, inlineCallbacks, returnValue


@transact
def mask_internalfile(session, itip_id, ifile_id):
    redaction = models.Redaction()
    redaction.reference_id = ifile_id
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


class TestExportHandler(helpers.TestHandlerWithPopulatedDB):
    _handler = export.ExportHandler
    # Disable PGP wrapping so the exported ZIP body can be inspected directly.
    pgp_configuration = 'NONE'

    # All of the setup here is used by the templating that goes into the data.txt file.
    @inlineCallbacks
    def setUp(self):
        yield helpers.TestHandlerWithPopulatedDB.setUp(self)

        yield self.perform_full_submission_actions()

        # creates the receiver files
        yield Delivery().run()

    @inlineCallbacks
    def export_zip_names(self, itip_id, receiver_id):
        handler = self.request({}, role='receiver')
        handler.session.user_id = receiver_id

        yield handler.get(itip_id)

        body = handler.request.getResponseBody()
        self.assertNotEqual(body, b'')

        with zipfile.ZipFile(io.BytesIO(body)) as zf:
            returnValue(zf.namelist())

    @inlineCallbacks
    def test_export(self):
        rtips_desc = yield self.get_rtips()

        handler = self.request({}, role='receiver')
        handler.session.user_id = rtips_desc[0]['receiver_id']

        yield handler.get(rtips_desc[0]['id'])
        self.assertNotEqual(handler.request.getResponseBody(), b'')

    @inlineCallbacks
    def test_concurrent_exports_same_user_serialized_and_cleaned_up(self):
        # Two concurrent exports from the same user must both succeed (queued,
        # not rejected) and the per-user lock must be dropped afterwards so the
        # download_locks mapping does not accumulate entries over time.
        rtips_desc = yield self.get_rtips()
        itip_id = rtips_desc[0]['id']
        receiver_id = rtips_desc[0]['receiver_id']

        self.assertEqual(self.state.download_locks, {})

        h1 = self.request({}, role='receiver')
        h1.session.user_id = receiver_id

        h2 = self.request({}, role='receiver')
        h2.session.user_id = receiver_id

        # Fire both before awaiting either, so they contend for the lock.
        d1 = h1.get(itip_id)
        d2 = h2.get(itip_id)

        # While both are in flight at most one lock exists for the user.
        self.assertEqual(list(self.state.download_locks), [receiver_id])

        yield DeferredList([d1, d2])

        self.assertNotEqual(h1.request.getResponseBody(), b'')
        self.assertNotEqual(h2.request.getResponseBody(), b'')

        # The lock is released and removed once the user's exports complete.
        self.assertEqual(self.state.download_locks, {})

    @inlineCallbacks
    def test_export_never_includes_masked_wbfiles(self):
        # Regression test: a fully masked whistleblower file must never be
        # exported, regardless of the recipient's masking/redaction privileges.
        rtips_desc = yield self.get_rtips()
        itip_id = rtips_desc[0]['id']

        ifile_ids = yield self.get_ifiles_by_wbtip_id(itip_id)
        self.assertTrue(len(ifile_ids) > 0)

        # The privileged receiver fully masks every whistleblower file.
        for ifile_id in ifile_ids:
            yield mask_internalfile(itip_id, ifile_id)

        # The privileged receiver must not receive the masked files on export.
        names = yield self.export_zip_names(itip_id, self.dummyReceiver_1['id'])
        self.assertFalse(any(n.startswith('files/') for n in names))

        # The unprivileged receiver must not receive them either.
        yield set_redaction_privileges(self.dummyReceiver_2['id'], False)

        names = yield self.export_zip_names(itip_id, self.dummyReceiver_2['id'])
        self.assertFalse(any(n.startswith('files/') for n in names))

    @inlineCallbacks
    def test_export_never_includes_masked_rfiles(self):
        # A masked recipient file is listed in the report but its content must
        # never be exported.
        rtips_desc = yield self.get_rtips()
        itip_id = rtips_desc[0]['id']
        receiver_id = rtips_desc[0]['receiver_id']

        # The recipient attaches a public file to the report.
        self._handler = rtip.ReceiverFileUpload
        attachment = self.get_dummy_attachment()
        handler = self.request(role='receiver', user_id=receiver_id, attachment=attachment)
        yield handler.post(itip_id)
        self._handler = export.ExportHandler

        rtips_desc = yield self.get_rtips()
        rfiles = rtips_desc[0]['rfiles']
        self.assertTrue(len(rfiles) > 0)

        # Before masking the file is part of the export.
        names = yield self.export_zip_names(itip_id, receiver_id)
        self.assertTrue(any(n.startswith('files_attached_from_recipients/') for n in names))

        # Once masked the file content must not be exported anymore.
        for rfile in rfiles:
            yield mask_internalfile(itip_id, rfile['id'])

        names = yield self.export_zip_names(itip_id, receiver_id)
        self.assertFalse(any(n.startswith('files_attached_from_recipients/') for n in names))


class TestExportHandlerPGP(helpers.TestHandlerWithPopulatedDB):
    _handler = export.ExportHandler
    # Keep PGP wrapping enabled (the default) to exercise the export path that
    # assembles the full archive off the reactor and then PGP-encrypts it.
    pgp_configuration = 'ALL'

    @inlineCallbacks
    def setUp(self):
        yield helpers.TestHandlerWithPopulatedDB.setUp(self)

        yield self.perform_full_submission_actions()

        yield Delivery().run()

    @inlineCallbacks
    def test_export_pgp(self):
        rtips_desc = yield self.get_rtips()

        handler = self.request({}, role='receiver')
        handler.session.user_id = rtips_desc[0]['receiver_id']

        yield handler.get(rtips_desc[0]['id'])

        # The body is the PGP-wrapped archive (not a plain ZIP) and the download
        # is advertised with the .pgp extension.
        self.assertNotEqual(handler.request.getResponseBody(), b'')

        content_disposition = handler.request.responseHeaders.getRawHeaders(b'content-disposition')[0]
        self.assertIn(b'.zip.pgp', content_disposition)
