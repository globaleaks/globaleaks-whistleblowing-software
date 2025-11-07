
from globaleaks.handlers.recipient import export
from globaleaks.jobs.delivery import Delivery
from globaleaks.tests import helpers
from twisted.internet.defer import inlineCallbacks


class TestExportHandler(helpers.TestHandlerWithPopulatedDB):
    _handler = export.ExportHandler

    # All of the setup here is used by the templating that goes into the data.txt file.
    @inlineCallbacks
    def setUp(self):
        yield helpers.TestHandlerWithPopulatedDB.setUp(self)

        yield self.perform_full_submission_actions()

        # creates the receiver files
        yield Delivery().run()

    @inlineCallbacks
    def test_export(self):
        rtips_desc = yield self.get_rtips()

        handler = self.request({}, role='receiver')
        handler.session.user_id = rtips_desc[0]['receiver_id']

        yield handler.get(rtips_desc[0]['id'])
        self.assertNotEqual(handler.request.getResponseBody(), b'')
