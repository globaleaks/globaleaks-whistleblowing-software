from twisted.internet.defer import inlineCallbacks

from globaleaks import db, models
from globaleaks.handlers import exchange
from globaleaks.handlers.admin import exchange as admin_exchange
from globaleaks.handlers.admin.questionnaire import db_get_questionnaire
from globaleaks.handlers.admin.user import create_user
from globaleaks.handlers.recipient import rtip
from globaleaks.models.config import ConfigFactory
from globaleaks.orm import transact
from globaleaks.rest import errors
from globaleaks.tests import helpers


@transact
def uuid_of(session, tid):
    return ConfigFactory(session, tid).get_val('uuid')


@transact
def give_dummy_keys(session, user_id):
    user = session.get(models.User, user_id)
    user.salt = helpers.VALID_SALT
    user.hash = helpers.VALID_HASH
    user.crypto_prv_key = helpers.USER_PRV_KEY_ENC
    user.crypto_pub_key = helpers.USER_PUB_KEY
    user.crypto_bkp_key = helpers.USER_BKP_KEY
    user.crypto_rec_key = helpers.USER_REC_KEY


@transact
def take_part(session, channel_id, receiver_id):
    session.add(models.ReceiverContext({'context_id': channel_id, 'receiver_id': receiver_id}))


@transact
def questionnaire_of(session, tid):
    questionnaire = models.Questionnaire()
    questionnaire.tid = tid
    questionnaire.name = f'questionnaire of {tid}'
    session.add(questionnaire)
    session.flush()

    return questionnaire.id


@transact
def sides_of(session, itip_id):
    """
    Return the site a report belongs to, its type and the sites and users that hold it
    """
    itip = session.get(models.InternalTip, itip_id)
    holders = session.query(models.User.tid, models.User.id) \
                     .filter(models.User.id == models.ReceiverTip.receiver_id,
                             models.ReceiverTip.internaltip_id == itip_id).all()

    return itip.tid, itip.type, {tid for tid, _ in holders}, {user_id for _, user_id in holders}


@transact
def receipt_of(session, itip_id):
    itip = session.get(models.InternalTip, itip_id)
    handed = session.query(models.InternalTipData) \
                    .filter(models.InternalTipData.internaltip_id == itip_id,
                            models.InternalTipData.key == 'receipt').count()

    return itip.receipt_change_needed, handed


class ExchangeTest(helpers.TestHandlerWithPopulatedDB):
    """
    Two sites: the first one holds the reports, the second one takes part in the exchanges
    """
    exchange_type = 'communication'

    @inlineCallbacks
    def setUp(self):
        yield helpers.TestHandlerWithPopulatedDB.setUp(self)
        yield self.perform_full_submission_actions()

        self.destination = yield create_user(2, None, self.get_dummy_receiver('destination'), 'en')
        yield give_dummy_keys(self.destination['id'])

        source = yield uuid_of(1)
        target = yield uuid_of(2)
        collection = self.request({
            'type': self.exchange_type,
            'source': source,
            'target': target,
            'channel': '',
            'channel_name': 'Exchange channel',
            'questionnaire': '',
            'request_questionnaire': ''
        }, role='admin', handler_cls=admin_exchange.ExchangeCollection)
        self.exchange = yield collection.post()

        yield take_part(self.exchange['channel'], self.destination['id'])
        yield db.refresh_tenant_cache()

    @transact
    def answers_for(self, session, tid, questionnaire_id):
        answers = {}
        questionnaire = db_get_questionnaire(session, tid, questionnaire_id, 'en')
        for step in questionnaire['steps']:
            for field in step['children']:
                self.fill_random_field_recursively(answers, field)

        return answers

    def as_destination(self, body='', handler_cls=None):
        return self.request(body, tid=2, user_id=self.destination['id'], role='receiver',
                            handler_cls=handler_cls)

    @inlineCallbacks
    def read(self, itip_id, tid=1, user_id=None):
        handler = self.request(tid=tid, user_id=user_id, role='receiver',
                               handler_cls=rtip.RTipInstance)
        return (yield handler.get(itip_id))

    @inlineCallbacks
    def comment(self, itip_id, visibility, tid=1, user_id=None):
        handler = self.request({'content': f'a word from side {tid}', 'visibility': visibility},
                               tid=tid, user_id=user_id, role='receiver',
                               handler_cls=rtip.RTipCommentCollection)
        return (yield handler.post(itip_id))


class TestCommunication(ExchangeTest):
    """
    A communication carries a report of the first site to the recipients of the second one
    """
    _handler = exchange.RTipCommunication

    @inlineCallbacks
    def setUp(self):
        yield ExchangeTest.setUp(self)

        rtips = yield self.get_rtips()
        self.origin_id = rtips[0]['id']

    def as_communicator(self, body='', can_communicate=True):
        return self.request(body, role='receiver', permissions={'can_send_communications': can_communicate})

    @inlineCallbacks
    def communicate(self):
        options = yield self.as_communicator().get(self.origin_id)
        answers = yield self.answers_for(1, options['questionnaire']['id'])

        return (yield self.as_communicator({
            'target_tid': 2,
            'exchange_id': self.exchange['id'],
            'answers': answers
        }).post(self.origin_id))

    @inlineCallbacks
    def test_the_report_stays_on_the_origin_and_is_held_by_both_sides(self):
        filed = yield self.communicate()

        self.assertEqual(filed['type'], 'exchange')
        self.assertTrue(filed['accessible'])

        tid, type, sites, holders = yield sides_of(filed['id'])
        self.assertEqual((tid, type, sites), (1, 'exchange', {1, 2}))
        self.assertEqual(holders, {self.dummyReceiver_1['id'],
                                   self.dummyReceiver_2['id'],
                                   self.destination['id']})

    @inlineCallbacks
    def test_the_origin_owns_the_report_and_the_destination_reads_it(self):
        filed = yield self.communicate()

        origin = yield self.read(filed['id'])
        destination = yield self.read(filed['id'], tid=2, user_id=self.destination['id'])

        self.assertTrue(origin['owned'])
        self.assertFalse(destination['owned'])
        self.assertEqual(origin['exchange']['type'], 'communication')
        # the destination walks back to no origin: it holds none
        self.assertEqual(origin['exchange']['internaltip_id'], self.origin_id)
        self.assertEqual(destination['exchange']['internaltip_id'], '')

    @inlineCallbacks
    def test_the_public_space_is_shared_and_the_internal_one_stays_with_its_side(self):
        filed = yield self.communicate()

        yield self.comment(filed['id'], 'public', tid=2, user_id=self.destination['id'])
        yield self.comment(filed['id'], 'internal', tid=2, user_id=self.destination['id'])
        yield self.comment(filed['id'], 'internal')

        origin = yield self.read(filed['id'])
        destination = yield self.read(filed['id'], tid=2, user_id=self.destination['id'])

        # the comments written, apart from what the log of the report adds among them
        def written(report):
            return [c for c in report['comments'] if 'type' not in c]

        self.assertEqual(sorted(c['visibility'] for c in written(origin)), ['internal', 'public'])
        self.assertEqual(sorted(c['visibility'] for c in written(destination)), ['internal', 'public'])
        self.assertNotEqual([c['id'] for c in written(origin) if c['visibility'] == 'internal'],
                            [c['id'] for c in written(destination) if c['visibility'] == 'internal'])

    @inlineCallbacks
    def test_the_read_receipt_is_the_access_of_the_other_side(self):
        filed = yield self.communicate()

        written = yield self.comment(filed['id'], 'public')
        origin = yield self.read(filed['id'])
        # the destination has not opened the report since the comment was written
        self.assertLess(origin['counterpart_last_access'], written['creation_date'])

        yield self.read(filed['id'], tid=2, user_id=self.destination['id'])
        origin = yield self.read(filed['id'])
        self.assertGreater(origin['counterpart_last_access'], written['creation_date'])

    @inlineCallbacks
    def test_the_spaces_are_public_internal_and_personal(self):
        filed = yield self.communicate()

        handler = self.request({'content': 'x', 'visibility': 'exchange'}, role='receiver',
                               handler_cls=rtip.RTipCommentCollection)
        yield self.assertFailure(handler.post(filed['id']), errors.InputValidationError)

    @inlineCallbacks
    def test_communicating_is_a_permission_of_the_recipient(self):
        options = yield self.as_communicator(can_communicate=False).get(self.origin_id)
        self.assertFalse(options['available'])

        handler = self.as_communicator({'target_tid': 2, 'exchange_id': self.exchange['id'], 'answers': {}},
                                       can_communicate=False)
        yield self.assertFailure(handler.post(self.origin_id), errors.ForbiddenOperation)

    @inlineCallbacks
    def test_the_origin_lists_what_it_communicated(self):
        filed = yield self.communicate()

        origin = yield self.read(self.origin_id)
        self.assertEqual([entry['id'] for entry in origin['exchanges']], [filed['id']])
        self.assertTrue(origin['exchanges'][0]['accessible'])


class TestRequestAndTransmission(ExchangeTest):
    """
    A transmission is asked for, decided by the destination and then filed on it
    """
    _handler = exchange.Transmissions
    exchange_type = 'transmission'

    @inlineCallbacks
    def setUp(self):
        yield ExchangeTest.setUp(self)

        self.transmitter = yield create_user(1, None, self.get_dummy_user('transmitter', 'transmitter'), 'en')
        yield give_dummy_keys(self.transmitter['id'])

        questionnaire = yield questionnaire_of(2)
        handler = self.request({
            'questionnaire': questionnaire,
            'request_questionnaire': questionnaire
        }, role='admin', handler_cls=admin_exchange.ExchangeInstance)
        yield handler.put(self.exchange['id'])

    def as_transmitter(self, body='', handler_cls=None):
        return self.request(body, user_id=self.transmitter['id'], role='transmitter',
                            handler_cls=handler_cls)

    def options(self):
        return self.as_transmitter(handler_cls=exchange.TransmissionOptions).get()

    @inlineCallbacks
    def file(self):
        options = yield self.options()

        filed = yield self.as_transmitter({
            'target_tid': 2,
            'exchange_id': self.exchange['id'],
            'answers': {}
        }).post()

        return options['stage'], filed

    @inlineCallbacks
    def decide(self, request_id, allow):
        handler = self.as_destination({'operation': 'set',
                                       'args': {'key': 'allow_transmission', 'value': allow}},
                                      handler_cls=rtip.RTipInstance)
        yield handler.put(request_id)

    @inlineCallbacks
    def test_the_transmitter_is_offered_the_destination_and_what_to_compose(self):
        options = yield self.options()

        self.assertEqual([target['id'] for target in options['targets']], [2])
        self.assertEqual([option['id'] for option in options['targets'][0]['options']], [self.exchange['id']])
        self.assertEqual((options['target_tid'], options['exchange_id'], options['stage']),
                         (2, self.exchange['id'], 'request'))
        self.assertIsNotNone(options['questionnaire'])

    @inlineCallbacks
    def test_the_request_is_followed_by_who_presented_it_and_decided_by_the_destination(self):
        stage, request = yield self.file()

        self.assertEqual((stage, request['type']), ('request', 'request'))
        self.assertTrue(request['accessible'])

        tid, type, sites, holders = yield sides_of(request['id'])
        self.assertEqual((tid, type, sites), (2, 'request', {1, 2}))
        self.assertEqual(holders, {self.transmitter['id'], self.destination['id']})

        # the recipient that composed the request never decides it
        handler = self.request({'operation': 'set',
                                'args': {'key': 'allow_transmission', 'value': True}},
                               user_id=self.transmitter['id'], role='transmitter',
                               handler_cls=rtip.RTipInstance)
        yield self.assertFailure(handler.put(request['id']), errors.ForbiddenOperation)

        yield self.decide(request['id'], True)
        decided = yield self.read(request['id'], tid=2, user_id=self.destination['id'])
        self.assertTrue(decided['allow_transmission'])

    @inlineCallbacks
    def test_the_read_receipt_on_a_request_is_the_access_of_the_other_site(self):
        _, request = yield self.file()

        written = yield self.comment(request['id'], 'public', user_id=self.transmitter['id'])
        seen = yield self.read(request['id'], user_id=self.transmitter['id'])
        self.assertLess(seen['counterpart_last_access'], written['creation_date'])

        yield self.read(request['id'], tid=2, user_id=self.destination['id'])
        seen = yield self.read(request['id'], user_id=self.transmitter['id'])
        self.assertGreater(seen['counterpart_last_access'], written['creation_date'])

    @inlineCallbacks
    def test_what_is_filed_upon_the_request_is_handed_over(self):
        _, request = yield self.file()
        yield self.decide(request['id'], True)

        stage, filed = yield self.file()

        self.assertEqual((stage, filed['type']), ('report', 'exchange'))
        self.assertFalse(filed['accessible'])

        # the destination holds it alone: the whistleblower reaches it with the receipt handed over
        tid, type, sites, holders = yield sides_of(filed['id'])
        self.assertEqual((tid, type, sites, holders), (2, 'exchange', {2}, {self.destination['id']}))

        change_needed, handed = yield receipt_of(filed['id'])
        self.assertTrue(change_needed)
        self.assertEqual(handed, 0)
        _, handed = yield receipt_of(request['id'])
        self.assertEqual(handed, 1)

        # the sender keeps the trace of both, and opens the request only
        transmissions = yield self.as_transmitter().get()
        self.assertEqual({entry['id']: bool(entry['rtip_id']) for entry in transmissions},
                         {request['id']: True, filed['id']: False})

    @inlineCallbacks
    def test_nothing_is_composed_while_a_request_waits_to_be_decided(self):
        yield self.file()

        options = yield self.options()
        self.assertEqual(options['targets'], [])

        handler = self.as_transmitter({'target_tid': 2, 'exchange_id': self.exchange['id'], 'answers': {}})
        yield self.assertFailure(handler.post(), errors.InputValidationError, errors.ForbiddenOperation)

    @inlineCallbacks
    def test_a_denied_request_grants_nothing(self):
        _, request = yield self.file()
        yield self.decide(request['id'], False)

        stage, _ = yield self.file()
        self.assertEqual(stage, 'request')


class TestTransferredAnswers(helpers.TestGL):
    """
    What is composed for another site never carries the identity of the whistleblower
    """
    def test_the_whistleblower_identity_is_dropped_wherever_it_is_nested(self):
        schema = [{'children': [{'id': 'name', 'template_id': ''},
                                {'id': 'group', 'template_id': '',
                                 'children': [{'id': 'identity', 'template_id': 'whistleblower_identity'}]}]},
                  {'children': [{'id': 'identity-2', 'template_id': 'whistleblower_identity'}]}]
        answers = {'name': 'kept', 'identity': 'dropped', 'identity-2': 'dropped', 'other': 'kept'}

        sanitized = exchange.sanitize_transmission_answers(schema, answers)

        self.assertEqual(sanitized, {'name': 'kept', 'identity': '', 'identity-2': '', 'other': 'kept'})
        # the answers composed are left as they were
        self.assertEqual(answers['identity'], 'dropped')
