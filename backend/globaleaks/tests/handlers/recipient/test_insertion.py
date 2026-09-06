from twisted.internet.defer import inlineCallbacks

from globaleaks import models
from globaleaks.handlers.recipient import insertion
from globaleaks.orm import transact
from globaleaks.tests import helpers
from globaleaks.utils.crypto import Base64Encoder


# The key the client derives from the digits it composes: what reaches the
# platform is the key and never the digits
ACCESS_CODE_KEY = b'k' * 32


class FakeUserSession:
    def __init__(self, user_id):
        self.user_id = user_id
        # the attachments of what is entered are held on the session of the
        # recipient entering it
        self.files = []


@transact
def declare_exchange_channel(session, tid, name='Exchange channel'):
    """
    Declare on a site a channel the exchanges run through
    """
    channel = models.Context()
    channel.tid = tid
    channel.exchange = True
    channel.name = {'en': name}
    session.add(channel)
    session.flush()

    return channel.id


@transact
def set_access_code_policy(session, channel_id, provided):
    """
    Declare whether a channel provides the access code of what is entered on it
    """
    session.query(models.Context) \
           .filter(models.Context.id == channel_id) \
           .one().provide_access_code = provided


@transact
def keys_of(session, itip_id):
    """
    Return what a report is keyed by: the hash of its access code and the key
    """
    itip = session.query(models.InternalTip) \
                  .filter(models.InternalTip.id == itip_id) \
                  .one()

    return itip.receipt_hash, itip.crypto_prv_key


@transact
def report_of(session, itip_id):
    itip = session.query(models.InternalTip) \
                  .filter(models.InternalTip.id == itip_id) \
                  .one_or_none()

    if itip is None:
        return None

    receivers = [r[0] for r in session.query(models.ReceiverTip.receiver_id)
                                      .filter(models.ReceiverTip.internaltip_id == itip.id)]

    return {'tid': itip.tid, 'type': itip.type, 'context_id': itip.context_id,
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

        self.operator = FakeUserSession(self.dummy_receiver_1['id'])

    def options(self, channel_id=''):
        return insertion.get_insertion_options(1, self.operator, channel_id, 'en')

    def enter(self, channel_id, answers=None):
        receipt = Base64Encoder.encode(ACCESS_CODE_KEY).decode()

        return insertion.create_inserted_report(
            1, self.operator,
            {'context_id': channel_id, 'answers': answers or {},
             'receipt': receipt}, 'en')

    @inlineCallbacks
    def test_the_channels_of_the_site_are_the_ones_offered(self):
        exchange_channel = yield declare_exchange_channel(1)

        options = yield self.options()

        offered = [channel['id'] for channel in options['channels']]
        self.assertIn(self.dummy_context['id'], offered)

        # a channel of the exchanges receives what the other sites file and is
        # not one a report is entered on
        self.assertNotIn(exchange_channel, offered)

    @inlineCallbacks
    def test_the_channel_chosen_composes_the_report(self):
        options = yield self.options(self.dummy_context['id'])

        self.assertEqual(options['channel_id'], self.dummy_context['id'])
        self.assertTrue(len(options['questionnaire']['steps']) > 0)

    @inlineCallbacks
    def test_the_report_entered_is_a_report_of_the_site(self):
        result = yield self.enter(self.dummy_context['id'])

        report = yield report_of(result['id'])
        self.assertEqual(report['tid'], 1)
        self.assertEqual(report['type'], 'submission')
        self.assertEqual(report['context_id'], self.dummy_context['id'])

        # the recipient that entered it is the operator of what it entered,
        # and the report reaches the recipients of the channel
        self.assertEqual(report['operator_id'], self.dummy_receiver_1['id'])
        self.assertIn(self.dummy_receiver_1['id'], report['receivers'])
