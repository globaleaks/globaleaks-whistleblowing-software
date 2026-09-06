
from twisted.internet.defer import inlineCallbacks

from globaleaks.handlers.admin import context
from globaleaks.handlers.base import BaseHandler
from globaleaks.models import Context, ContextAdditionalQuestionnaire
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
    """
    @inlineCallbacks
    def setUp(self):
        yield helpers.TestGLWithPopulatedDB.setUp(self)

        self.channel_id = yield declare_channel(1)


@transact
def named_additional_questionnaires(session, context_id):
    return sorted(q[0] for q in session.query(ContextAdditionalQuestionnaire.questionnaire_id)
                                       .filter(ContextAdditionalQuestionnaire.context_id == context_id))


@transact
def derive_context(session, tid, template_id):
    """
    Derive on a tenant the channel a channel of its profile is the template of
    """
    template = session.query(Context).filter(Context.id == template_id).one()

    return context.db_derive_context(session, tid, template).id


class TestContextAdditionalQuestionnaires(helpers.TestGLWithPopulatedDB):
    """
    A channel names the additional questionnaires it can ask of its reports and
    """
    def context_request(self, additional, automatic=''):
        request = Context().dict('en')
        request['name'] = 'Channel'
        request['questionnaire_id'] = 'default'
        request['additional_questionnaires'] = additional
        request['additional_questionnaire_id'] = automatic

        return request

    @inlineCallbacks
    def test_the_set_and_its_election_travel_with_the_channel(self):
        request = self.context_request([self.dummy_questionnaire['id']], self.dummy_questionnaire['id'])

        created = yield context.create_context(1, None, request, 'en')

        self.assertEqual(created['additional_questionnaires'], [self.dummy_questionnaire['id']])
        self.assertEqual(created['additional_questionnaire_id'], self.dummy_questionnaire['id'])

        read = yield context.get_context(1, created['id'], 'en')
        self.assertEqual(read['additional_questionnaires'], [self.dummy_questionnaire['id']])

    @inlineCallbacks
    def test_a_channel_names_questionnaires_without_electing_any(self):
        request = self.context_request([self.dummy_questionnaire['id'], 'default'])

        created = yield context.create_context(1, None, request, 'en')

        self.assertEqual(sorted(created['additional_questionnaires']),
                         sorted([self.dummy_questionnaire['id'], 'default']))
        self.assertEqual(created['additional_questionnaire_id'], '')

    @inlineCallbacks
    def test_the_election_is_one_of_the_set(self):
        request = self.context_request([], self.dummy_questionnaire['id'])

        yield self.assertFailure(context.create_context(1, None, request, 'en'),
                                 errors.InputValidationError)

    @inlineCallbacks
    def test_the_election_is_cleared_keeping_the_set(self):
        request = self.context_request([self.dummy_questionnaire['id']], self.dummy_questionnaire['id'])
        created = yield context.create_context(1, None, request, 'en')

        request = self.context_request([self.dummy_questionnaire['id']])
        request['id'] = created['id']

        updated = yield context.update_context(1, created['id'], request, 'en')

        self.assertEqual(updated['additional_questionnaires'], [self.dummy_questionnaire['id']])
        self.assertEqual(updated['additional_questionnaire_id'], '')

    @inlineCallbacks
    def test_the_set_is_rewritten_by_what_the_channel_is_updated_with(self):
        request = self.context_request([self.dummy_questionnaire['id'], 'default'], 'default')
        created = yield context.create_context(1, None, request, 'en')

        request = self.context_request(['default'], 'default')
        request['id'] = created['id']

        yield context.update_context(1, created['id'], request, 'en')

        named = yield named_additional_questionnaires(created['id'])
        self.assertEqual(named, ['default'])

    @inlineCallbacks
    def test_a_derived_channel_inherits_the_set(self):
        """
        The set lives in a table of its own and is not a column of the channel:
        """
        request = self.context_request([self.dummy_questionnaire['id'], 'default'], 'default')
        template = yield context.create_context(1, None, request, 'en')

        derived_id = yield derive_context(1, template['id'])

        named = yield named_additional_questionnaires(derived_id)
        self.assertEqual(named, sorted([self.dummy_questionnaire['id'], 'default']))

        derived = yield context.get_context(1, derived_id, 'en')
        self.assertEqual(derived['additional_questionnaire_id'], 'default')
