
from twisted.internet.defer import inlineCallbacks

from globaleaks.handlers.admin import context
from globaleaks.handlers.base import BaseHandler
from globaleaks.models import Context
from globaleaks.orm import transact
from globaleaks.rest import errors
from globaleaks.tests import helpers


class TestContextsCollection(helpers.TestCollectionHandler):
    _handler = context.ContextsCollection
    _test_desc = {
        'model': Context,
        'create': context.create_context,
        'data': {
            'tip_timetolive': 100
        }
    }


class TestContextInstance(helpers.TestInstanceHandler):
    _handler = context.ContextInstance
    _test_desc = {
        'model': Context,
        'create': context.create_context,
        'data': {
            'tip_timetolive': 100
        }
    }

    @inlineCallbacks
    def test_delete_requires_confirmation(self):
        self.patch(BaseHandler, 'check_confirmation', BaseHandler.real_check_confirmation)

        data = self.get_dummy_request()
        data = yield self._test_desc['create'](1, self.session, data, 'en')

        handler = self.request(data, role='admin')

        self.assertRaises(errors.InvalidAuthentication, handler.delete, data['id'])

    @inlineCallbacks
    def test_delete_with_confirmation(self):
        self.patch(BaseHandler, 'check_confirmation', BaseHandler.real_check_confirmation)

        confirmation = helpers.VALID_CONFIRMATION

        data = self.get_dummy_request()
        data = yield self._test_desc['create'](1, self.session, data, 'en')

        handler = self.request(data, role='admin', headers={'x-confirmation': confirmation})

        yield handler.delete(data['id'])


@transact
def declare_channel(session, tid, name='Exchange channel'):
    """
    Declare on a site a channel the exchanges run through
    """
    channel = Context()
    channel.tid = tid
    channel.exchange = True
    channel.name = {'en': name}
    session.add(channel)
    session.flush()

    return channel.id


@transact
def channel_of(session, context_id):
    channel = session.query(Context) \
                     .filter(Context.id == context_id) \
                     .one_or_none()

    if channel is None:
        return None

    return {'name': channel.name.get('en', ''), 'exchange': channel.exchange}


def channel_request(name):
    request = Context().dict('en')
    request['name'] = name
    request['questionnaire_id'] = 'default'

    return request


class TestExchangeChannelConfiguration(helpers.TestGLWithPopulatedDB):
    """
    A channel of the exchanges belongs to the exchanges that run through it:
    it is configured by the administrators of the platform, that established
    them, and the administrators of the site holding it read it where it lives
    but do not write it.
    """
    @inlineCallbacks
    def setUp(self):
        yield helpers.TestGLWithPopulatedDB.setUp(self)

        self.channel_id = yield declare_channel(1)

    @inlineCallbacks
    def test_the_administrators_of_the_site_do_not_write_it(self):
        yield self.assertFailure(context.update_context(1, self.channel_id,
                                                        channel_request('Renamed'), 'en'),
                                 errors.ForbiddenOperation)

        self.assertEqual((yield channel_of(self.channel_id))['name'], 'Exchange channel')

    @inlineCallbacks
    def test_the_administrators_of_the_platform_configure_it(self):
        yield context.update_context(1, self.channel_id,
                                     channel_request('Renamed'), 'en', True)

        self.assertEqual((yield channel_of(self.channel_id))['name'], 'Renamed')

    @inlineCallbacks
    def test_the_administrators_of_the_site_do_not_drop_it(self):
        yield self.assertFailure(context.delete_context(1, self.channel_id),
                                 errors.ForbiddenOperation)

        self.assertIsNotNone((yield channel_of(self.channel_id)))

        yield context.delete_context(1, self.channel_id, True)

        self.assertIsNone((yield channel_of(self.channel_id)))

    @inlineCallbacks
    def test_a_channel_is_never_declared_among_the_channels_of_a_site(self):
        # a channel of the exchanges is born of the exchange that runs through
        # it: no request declares one, and none stops being one
        request = channel_request('Ordinary')
        request['exchange'] = True
        created = yield context.create_context(1, None, request, 'en')

        self.assertFalse(created['exchange'])
        self.assertFalse((yield channel_of(created['id']))['exchange'])

        request = channel_request('Ordinary')
        request['exchange'] = True
        yield context.update_context(1, created['id'], request, 'en')

        self.assertFalse((yield channel_of(created['id']))['exchange'])
