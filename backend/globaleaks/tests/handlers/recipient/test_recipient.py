from twisted.internet.defer import inlineCallbacks

from globaleaks import models
from globaleaks.handlers import recipient
from globaleaks.rest import errors
from globaleaks.tests import helpers


class TestTipsCollection(helpers.TestHandlerWithPopulatedDB):
    _handler = recipient.TipsCollection

    @inlineCallbacks
    def setUp(self):
        yield helpers.TestHandlerWithPopulatedDB.setUp(self)
        yield self.perform_full_submission_actions()

    @inlineCallbacks
    def test_get(self):
        handler = self.request(user_id=self.dummyReceiver_1['id'], role='receiver')
        rtips = yield handler.get()
        for idx in range(len(rtips)):
            self.assertEqual(rtips[idx]['file_count'], 2)
            self.assertEqual(rtips[idx]['comment_count'], 2)
            self.assertEqual(rtips[idx]['receiver_count'], 2)
