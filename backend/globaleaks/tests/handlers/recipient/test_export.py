import io
import zipfile

from globaleaks import models
from globaleaks.handlers.recipient import export
from globaleaks.jobs.delivery import Delivery
from globaleaks.orm import transact
from globaleaks.tests import helpers
from twisted.internet.defer import inlineCallbacks, returnValue


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
