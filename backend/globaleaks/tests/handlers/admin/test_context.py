
from twisted.internet.defer import inlineCallbacks

from globaleaks.handlers.admin import context
from globaleaks.handlers.base import BaseHandler
from globaleaks import models
from globaleaks.models import Context
from globaleaks.models.config import ConfigFactory, DEFAULT_PROFILE_ID
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


@transact
def derive(session, tid, profile):
    ConfigFactory(session, tid).set_val('profile', profile)


@transact
def questionnaire_of(session, tid):
    questionnaire = models.Questionnaire()
    questionnaire.tid = tid
    questionnaire.name = f'questionnaire of {tid}'
    session.add(questionnaire)
    session.flush()

    return questionnaire.id


class TestContextQuestionnaires(helpers.TestGLWithPopulatedDB):
    """
    A site composes its own channels with its questionnaires, those of the profile it derives from
    and those of the root site, and with no other
    """
    def context_request(self, questionnaire_id):
        request = Context().dict('en')
        request['name'] = 'Channel'
        request['questionnaire_id'] = questionnaire_id

        return request

    @inlineCallbacks
    def test_a_channel_asks_the_questionnaires_of_the_profile_or_of_the_root(self):
        yield derive(3, 'default')

        for tid in (DEFAULT_PROFILE_ID, 1):
            questionnaire = yield questionnaire_of(tid)

            created = yield context.create_context(3, None, self.context_request(questionnaire), 'en')

            self.assertEqual(created['questionnaire_id'], questionnaire)

    @inlineCallbacks
    def test_a_channel_does_not_ask_the_questionnaires_of_another_site(self):
        questionnaire = yield questionnaire_of(2)

        yield self.assertFailure(context.create_context(3, None, self.context_request(questionnaire), 'en'),
                                 errors.InputValidationError)
