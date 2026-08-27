from twisted.internet.defer import inlineCallbacks

from globaleaks import models
from globaleaks.handlers.recipient import insertion
from globaleaks.orm import transact
from globaleaks.rest import errors
from globaleaks.tests import helpers
from globaleaks.utils.crypto import Base64Encoder


class FakeUserSession:
    def __init__(self, user_id):
        self.user_id = user_id
        # the attachments of what is entered are held on the session of the
        # recipient entering it
        self.files = []


@transact
def report_of(session, itip_id):
    itip = session.query(models.InternalTip) \
                  .filter(models.InternalTip.id == itip_id) \
                  .one_or_none()

    if itip is None:
        return None

    receivers = [r[0] for r in session.query(models.ReceiverTip.receiver_id)
                                      .filter(models.ReceiverTip.internaltip_id == itip.id)]

    return {'tid': itip.tid, 'context_id': itip.context_id,
            'operator_id': itip.operator_id, 'receivers': receivers}


class TestInsertedReport(helpers.TestGLWithPopulatedDB):
    """
    A recipient enters on its own site a report of the site: it is filed on
    one of the channels the site holds for the reporting people and reaches
    the recipients of it.
    """
    @inlineCallbacks
    def setUp(self):
        yield helpers.TestGLWithPopulatedDB.setUp(self)

        self.operator = FakeUserSession(self.dummyReceiver_1['id'])

    def options(self, channel_id=''):
        return insertion.get_insertion_options(1, self.operator, channel_id, 'en')

    def enter(self, channel_id, answers=None):
        # The receipt is the key the client derives from the digits it hands
        # over: what reaches the platform is the key and never the digits
        receipt = Base64Encoder.encode(b'k' * 32).decode()

        return insertion.create_inserted_report(
            1, self.operator,
            {'context_id': channel_id, 'answers': answers or {},
             'receipt': receipt}, 'en')

    @inlineCallbacks
    def test_the_channels_of_the_site_are_the_ones_offered(self):
        options = yield self.options()

        offered = [channel['id'] for channel in options['channels']]
        self.assertIn(self.dummyContext['id'], offered)

    @inlineCallbacks
    def test_the_channel_chosen_composes_the_report(self):
        options = yield self.options(self.dummyContext['id'])

        self.assertEqual(options['channel_id'], self.dummyContext['id'])
        self.assertTrue(len(options['questionnaire']['steps']) > 0)

    @inlineCallbacks
    def test_the_report_entered_is_a_report_of_the_site(self):
        result = yield self.enter(self.dummyContext['id'])

        report = yield report_of(result['id'])
        self.assertEqual(report['tid'], 1)
        self.assertEqual(report['context_id'], self.dummyContext['id'])

        # the recipient that entered it is the operator of what it entered,
        # and the report reaches the recipients of the channel
        self.assertEqual(report['operator_id'], self.dummyReceiver_1['id'])
        self.assertIn(self.dummyReceiver_1['id'], report['receivers'])

    @inlineCallbacks
    def test_a_channel_of_another_site_is_not_entered_on(self):
        yield self.assertFailure(self.enter(helpers.uuid4()),
                                 errors.InputValidationError)
