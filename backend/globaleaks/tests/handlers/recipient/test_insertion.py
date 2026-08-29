from twisted.internet.defer import inlineCallbacks

from globaleaks import models
from globaleaks.handlers.recipient import insertion
from globaleaks.orm import transact
from globaleaks.rest import errors
from globaleaks.tests import helpers
from globaleaks.utils.crypto import Base64Encoder, GCE, sha256


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
    of the report encrypted with it
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

        self.operator = FakeUserSession(self.dummyReceiver_1['id'])

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
        self.assertIn(self.dummyContext['id'], offered)

        # a channel of the exchanges receives what the other sites file and is
        # not one a report is entered on
        self.assertNotIn(exchange_channel, offered)

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
        self.assertEqual(report['type'], 'submission')
        self.assertEqual(report['context_id'], self.dummyContext['id'])

        # the recipient that entered it is the operator of what it entered,
        # and the report reaches the recipients of the channel
        self.assertEqual(report['operator_id'], self.dummyReceiver_1['id'])
        self.assertIn(self.dummyReceiver_1['id'], report['receivers'])

    @inlineCallbacks
    def test_a_channel_of_the_exchanges_is_not_entered_on(self):
        exchange_channel = yield declare_exchange_channel(1)

        yield self.assertFailure(self.enter(exchange_channel),
                                 errors.InputValidationError)

    @inlineCallbacks
    def test_the_access_code_composed_opens_what_a_channel_providing_it_enters(self):
        yield set_access_code_policy(self.dummyContext['id'], True)

        result = yield self.enter(self.dummyContext['id'])
        self.assertTrue(result['provide_access_code'])

        receipt_hash, _ = yield keys_of(result['id'])

        # the report is keyed by the code the recipient composed: it is what
        # is handed over and what opens the report afterwards
        self.assertEqual(receipt_hash, sha256(ACCESS_CODE_KEY).decode())

    @inlineCallbacks
    def test_the_access_code_composed_is_discarded_where_a_channel_does_not_provide_it(self):
        yield set_access_code_policy(self.dummyContext['id'], False)

        result = yield self.enter(self.dummyContext['id'])
        self.assertFalse(result['provide_access_code'])

        receipt_hash, crypto_prv_key = yield keys_of(result['id'])

        # the report is keyed by a code the server drew and handed to no one:
        # the one the client composed neither opens the report nor decrypts
        # the key of it
        self.assertNotEqual(receipt_hash, sha256(ACCESS_CODE_KEY).decode())
        self.assertRaises(Exception, GCE.symmetric_decrypt, ACCESS_CODE_KEY,
                          Base64Encoder.decode(crypto_prv_key))
