import json

from sqlalchemy.orm.exc import NoResultFound

from globaleaks.handlers import public
from globaleaks.handlers.admin.context import create_context
from globaleaks.models.config import ConfigFactory
from globaleaks.orm import tw
from globaleaks.rest import requests
from globaleaks.tests import helpers
from twisted.internet.defer import inlineCallbacks


class HiddenContextMixin:
    @inlineCallbacks
    def create_hidden_context(self):
        request = dict(self.dummyContext)
        request.pop('id', None)
        request['receivers'] = [self.dummyReceiver_1['id']]
        request['hidden'] = True
        context = yield create_context(1, None, request, 'en')
        return context


class TestPublicResource(HiddenContextMixin, helpers.TestHandlerWithPopulatedDB):
    _handler = public.PublicResource

    @inlineCallbacks
    def test_get(self):
        handler = self.request()
        response = yield handler.get()

        self._handler.validate_request(json.dumps(response, default=str), requests.PublicResourcesDesc)

    @inlineCallbacks
    def test_disabled_onion_service_is_not_advertised(self):
        def update_and_serialize(session, enabled):
            node = ConfigFactory(session, 1)
            node.set_val('onionservice_enable', enabled)
            return public.db_serialize_node(session, 1, 'en')

        original = yield tw(public.db_serialize_node, 1, 'en')
        response = yield tw(update_and_serialize, False)
        self.assertEqual(response['onionservice'], '')
        response = yield tw(update_and_serialize, True)
        self.assertEqual(response['onionservice'], original['onionservice'])

    @inlineCallbacks
    def test_hidden_context_is_not_publicly_listed(self):
        context = yield self.create_hidden_context()

        handler = self.request()
        response = yield handler.get()

        context_ids = [c['id'] for c in response['contexts']]
        self.assertNotIn(context['id'], context_ids)

        # the questionnaire referenced only by the hidden context must not leak
        questionnaire_ids = [q['id'] for q in response['questionnaires']]
        if context['questionnaire_id'] not in [c['questionnaire_id'] for c in response['contexts']]:
            self.assertNotIn(context['questionnaire_id'], questionnaire_ids)


class TestContextInstance(HiddenContextMixin, helpers.TestHandlerWithPopulatedDB):
    _handler = public.ContextInstance

    @inlineCallbacks
    def test_get_hidden_context_by_id(self):
        context = yield self.create_hidden_context()

        handler = self.request()
        response = yield handler.get(context['id'])

        self.assertEqual(response['context']['id'], context['id'])
        self.assertTrue(response['context']['hidden'])

        questionnaire_ids = [q['id'] for q in response['questionnaires']]
        self.assertIn(context['questionnaire_id'], questionnaire_ids)

    @inlineCallbacks
    def test_get_missing_context_raises(self):
        handler = self.request()
        yield self.assertFailure(handler.get('aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa'),
                                 NoResultFound)
