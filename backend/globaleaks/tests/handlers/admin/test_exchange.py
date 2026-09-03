from twisted.internet.defer import inlineCallbacks, maybeDeferred

from globaleaks import models
from globaleaks.handlers.admin import exchange
from globaleaks.models.config import ConfigFactory
from globaleaks.orm import transact
from globaleaks.rest import errors
from globaleaks.tests import helpers


@transact
def uuid_of(session, tid):
    return ConfigFactory(session, tid).get_val('uuid')


@transact
def channel_of(session, channel_id):
    channel = session.query(models.Context) \
                     .filter(models.Context.id == channel_id).one()

    return channel.tid, channel.exchange


@transact
def questionnaire_of(session, tid):
    questionnaire = models.Questionnaire()
    questionnaire.tid = tid
    questionnaire.name = f'questionnaire of {tid}'
    session.add(questionnaire)
    session.flush()

    return questionnaire.id


class TestExchangeCollection(helpers.TestHandlerWithPopulatedDB):
    """
    The exchanges established between the sites of the platform are configured
    """
    _handler = exchange.ExchangeCollection

    @inlineCallbacks
    def setUp(self):
        yield helpers.TestHandlerWithPopulatedDB.setUp(self)

        self.source = yield uuid_of(2)
        self.target = yield uuid_of(3)

    def desc(self, **kwargs):
        request = {
            'type': 'transmission',
            'source': self.source,
            'target': self.target,
            'channel': '',
            'channel_name': 'Exchange channel',
            'questionnaire': '',
            'request_questionnaire': ''
        }
        request.update(kwargs)

        return request

    @inlineCallbacks
    def establish(self, **kwargs):
        handler = self.request(self.desc(**kwargs), role='admin')

        return (yield handler.post())

    @inlineCallbacks
    def test_post(self):
        response = yield self.establish()

        self.assertEqual(response['type'], 'transmission')
        self.assertEqual(response['source'], self.source)
        self.assertEqual(response['target'], self.target)

        # the channel named on the exchange is declared on the destination,
        # and is a channel the exchanges run through
        tid, is_exchange = yield channel_of(response['channel'])
        self.assertEqual(tid, 3)
        self.assertTrue(is_exchange)

    @inlineCallbacks
    def test_get(self):
        established = yield self.establish()

        handler = self.request(role='admin')
        response = yield handler.get()

        self.assertEqual([entry['id'] for entry in response], [established['id']])

    @inlineCallbacks
    def test_post_with_an_unknown_type_is_refused(self):
        handler = self.request(self.desc(type='invalid'), role='admin')

        yield self.assertFailure(handler.post(), errors.InputValidationError)

    @inlineCallbacks
    def test_post_relating_a_site_to_itself_is_refused(self):
        handler = self.request(self.desc(target=self.source), role='admin')

        yield self.assertFailure(handler.post(), errors.InputValidationError)

    @inlineCallbacks
    def test_post_running_through_no_channel_is_refused(self):
        handler = self.request(self.desc(channel_name=''), role='admin')

        yield self.assertFailure(handler.post(), errors.InputValidationError)


class TestExchangeInstance(helpers.TestHandlerWithPopulatedDB):
    """
    What the platform decides of an exchange - the questionnaire composing what
    """
    _handler = exchange.ExchangeInstance

    @inlineCallbacks
    def setUp(self):
        yield helpers.TestHandlerWithPopulatedDB.setUp(self)

        source = yield uuid_of(2)
        target = yield uuid_of(3)

        collection = self.request({
            'type': 'transmission',
            'source': source,
            'target': target,
            'channel': '',
            'channel_name': 'Exchange channel',
            'questionnaire': '',
            'request_questionnaire': ''
        }, role='admin', handler_cls=exchange.ExchangeCollection)

        self.exchange = yield collection.post()

    @inlineCallbacks
    def test_put(self):
        # a transmission files on the destination, that owns what it receives:
        # the questionnaire composing the report is one of the destination
        questionnaire = yield questionnaire_of(3)

        handler = self.request({
            'questionnaire': questionnaire,
            'request_questionnaire': questionnaire
        }, role='admin')

        response = yield handler.put(self.exchange['id'])

        self.assertEqual(response['questionnaire'], questionnaire)
        self.assertEqual(response['request_questionnaire'], questionnaire)

    @inlineCallbacks
    def test_put_discards_a_questionnaire_of_another_site(self):
        # the questionnaire shapes what lives on the side owning the reports:
        # one belonging to another site names nothing
        questionnaire = yield questionnaire_of(2)

        handler = self.request({
            'questionnaire': questionnaire,
            'request_questionnaire': ''
        }, role='admin')

        response = yield handler.put(self.exchange['id'])

        self.assertEqual(response['questionnaire'], '')

    @inlineCallbacks
    def test_delete(self):
        handler = self.request(role='admin')

        yield handler.delete(self.exchange['id'])

        collection = self.request(role='admin', handler_cls=exchange.ExchangeCollection)
        self.assertEqual((yield collection.get()), [])

    @inlineCallbacks
    def test_operations_require_the_permission_over_the_sites(self):
        handler = self.request(role='admin',
                               permissions={'can_manage_sites': False})

        # the decorator refuses before the handler is entered: the call is
        # wrapped so that the refusal reaches the assertion as a failure
        yield self.assertFailure(maybeDeferred(handler.delete, self.exchange['id']),
                                 errors.ForbiddenOperation)
