from twisted.internet.defer import inlineCallbacks
from globaleaks.handlers import custodian
from globaleaks.handlers.recipient import rtip
from globaleaks.sessions import Sessions
from globaleaks.tests import helpers


class TestIdentityAccessRequestInstance(helpers.TestHandlerWithPopulatedDB):
    _handler = custodian.IdentityAccessRequestInstance

    @inlineCallbacks
    def setUp(self):
        yield helpers.TestHandlerWithPopulatedDB.setUp(self)
        yield self.perform_full_submission_actions()

        dummyRTips = yield self.get_rtips()
        self.iars = []

        for rtip_desc in dummyRTips:
            user_session = Sessions.new(1,
                                        rtip_desc['receiver_id'],
                                        1,
                                        'recipient',
                                        helpers.USER_PRV_KEY,
                                        '')

            iar = yield rtip.create_identityaccessrequest(1,
                                                          user_session,
                                                          rtip_desc['id'],
                                                          {'request_motivation': 'request motivation'})
            self.iars.append(iar['id'])

    @inlineCallbacks
    def test_put_identityaccessrequest_response(self):
        reply = {
          'reply':  'authorized',
          'reply_motivation': 'oh yeah!'
        }

        handler = self.request(reply, user_id=self.dummyCustodian['id'], role='custodian')

        yield handler.put(self.iars[0])


class TestIdentityAccessRequestsCollection(helpers.TestHandlerWithPopulatedDB):
    _handler = custodian.IdentityAccessRequestsCollection

    @inlineCallbacks
    def setUp(self):
        yield helpers.TestHandlerWithPopulatedDB.setUp(self)
        yield self.perform_full_submission_actions()

    def test_get(self):
        handler = self.request(user_id=self.dummyCustodian['id'], role='custodian')
        return handler.get()
