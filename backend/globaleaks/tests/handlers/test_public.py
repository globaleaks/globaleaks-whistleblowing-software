import json

from sqlalchemy.orm.exc import NoResultFound

from globaleaks import models
from globaleaks.handlers import public
from globaleaks.handlers.admin.context import create_context
from globaleaks.orm import transact
from globaleaks.rest import requests
from globaleaks.tests import helpers
from twisted.internet.defer import inlineCallbacks


@transact
def set_closure_questionnaire(session, context_id):
    """
    Configure on a context a closure questionnaire not referenced anywhere
    else, returning its id
    """
    questionnaire = models.Questionnaire()
    questionnaire.tid = 1
    questionnaire.name = 'Closure'
    session.add(questionnaire)
    session.flush()

    session.query(models.Context) \
           .filter(models.Context.id == context_id) \
           .one().closure_questionnaire_id = questionnaire.id

    return questionnaire.id


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

    @inlineCallbacks
    def test_closure_questionnaire_is_not_publicly_published(self):
        """
        The closure questionnaire belongs to the management of the reports:
        neither its schema nor its designation are part of the public data.
        """
        questionnaire_id = yield set_closure_questionnaire(self.dummyContext['id'])

        handler = self.request()
        response = yield handler.get()

        self.assertNotIn(questionnaire_id, [q['id'] for q in response['questionnaires']])

        for context in response['contexts']:
            self.assertNotIn('closure_questionnaire_id', context)


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
    def test_closure_questionnaire_is_not_bundled_with_the_context(self):
        questionnaire_id = yield set_closure_questionnaire(self.dummyContext['id'])

        handler = self.request()
        response = yield handler.get(self.dummyContext['id'])

        self.assertNotIn('closure_questionnaire_id', response['context'])
        self.assertNotIn(questionnaire_id, [q['id'] for q in response['questionnaires']])

    @inlineCallbacks
    def test_get_missing_context_raises(self):
        handler = self.request()
        yield self.assertFailure(handler.get('aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa'),
                                 NoResultFound)
