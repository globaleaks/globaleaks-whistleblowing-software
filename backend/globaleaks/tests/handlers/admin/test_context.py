from twisted.internet.defer import inlineCallbacks

from globaleaks import models
from globaleaks.handlers.admin import context
from globaleaks.models import Context
from globaleaks.orm import transact
from globaleaks.rest import errors
from globaleaks.tests import helpers


@transact
def get_context_by_id(session, context_id):
    ctx = session.query(models.Context).filter(models.Context.id == context_id).first()
    if ctx:
        return {'id': ctx.id, 'deleted': ctx.deleted}
    return None


@transact
def get_receiver_context_count(session, context_id):
    return session.query(models.ReceiverContext).filter(
        models.ReceiverContext.context_id == context_id
    ).count()


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


class TestContextStats(helpers.TestHandlerWithPopulatedDB):
    _handler = context.ContextStats

    @inlineCallbacks
    def test_get(self):
        """Test retrieving context stats"""
        handler = self.request(role='admin')
        response = yield handler.get(self.dummyContext['id'])

        self.assertIn('open_reports', response)
        self.assertIn('total_reports', response)
        self.assertIn('last_update', response)
        self.assertIsInstance(response['open_reports'], int)
        self.assertIsInstance(response['total_reports'], int)
        self.assertGreaterEqual(response['total_reports'], response['open_reports'])


class TestContextDeletion(helpers.TestHandlerWithPopulatedDB):
    _handler = context.ContextInstance

    @inlineCallbacks
    def test_delete_with_valid_stats(self):
        """Test deletion succeeds when expected stats match current stats"""
        # Get current stats
        stats = yield context.get_context_stats(1, self.dummyContext['id'])

        # Create handler with expected stats as query params
        handler = self.request({}, role='admin')
        handler.request.args[b'expected_open'] = [str(stats['open_reports']).encode()]
        handler.request.args[b'expected_total'] = [str(stats['total_reports']).encode()]

        yield handler.delete(self.dummyContext['id'])

    @inlineCallbacks
    def test_delete_with_mismatched_stats(self):
        """Test deletion fails when expected stats don't match current stats"""
        # Create handler with wrong expected stats
        handler = self.request({}, role='admin')
        handler.request.args[b'expected_open'] = [b'999']
        handler.request.args[b'expected_total'] = [b'999']

        yield self.assertFailure(handler.delete(self.dummyContext['id']), errors.ContextStatsChanged)

    @inlineCallbacks
    def test_soft_delete_marks_context_as_deleted(self):
        """Test that soft delete marks context as deleted instead of removing it"""
        # Get initial stats
        stats = yield context.get_context_stats(1, self.dummyContext['id'])

        # Perform deletion with correct stats
        handler = self.request({}, role='admin')
        handler.request.args[b'expected_open'] = [str(stats['open_reports']).encode()]
        handler.request.args[b'expected_total'] = [str(stats['total_reports']).encode()]

        yield handler.delete(self.dummyContext['id'])

        # Verify context still exists in DB but is marked as deleted
        ctx = yield get_context_by_id(self.dummyContext['id'])
        self.assertIsNotNone(ctx)
        self.assertTrue(ctx['deleted'])

    @inlineCallbacks
    def test_soft_delete_removes_receiver_associations(self):
        """Test that soft delete removes ReceiverContext associations"""
        # Get initial receiver count for the context
        initial_count = yield get_receiver_context_count(self.dummyContext['id'])
        self.assertGreater(initial_count, 0, "Context should have receivers before deletion")

        # Get stats and perform deletion
        stats = yield context.get_context_stats(1, self.dummyContext['id'])

        handler = self.request({}, role='admin')
        handler.request.args[b'expected_open'] = [str(stats['open_reports']).encode()]
        handler.request.args[b'expected_total'] = [str(stats['total_reports']).encode()]

        yield handler.delete(self.dummyContext['id'])

        # Verify ReceiverContext associations are removed
        final_count = yield get_receiver_context_count(self.dummyContext['id'])
        self.assertEqual(final_count, 0, "All receiver associations should be removed after deletion")

    @inlineCallbacks
    def test_deleted_context_not_returned_in_list(self):
        """Test that deleted contexts are not returned in the contexts list"""
        # Get initial context count using ContextsCollection handler
        list_handler = self.request(role='admin', handler_cls=context.ContextsCollection)
        initial_contexts = yield list_handler.get()
        initial_count = len([c for c in initial_contexts if c['id'] == self.dummyContext['id']])
        self.assertEqual(initial_count, 1, "Context should be in list before deletion")

        # Delete the context
        stats = yield context.get_context_stats(1, self.dummyContext['id'])
        delete_handler = self.request({}, role='admin')
        delete_handler.request.args[b'expected_open'] = [str(stats['open_reports']).encode()]
        delete_handler.request.args[b'expected_total'] = [str(stats['total_reports']).encode()]
        yield delete_handler.delete(self.dummyContext['id'])

        # Verify context is not in list after deletion
        list_handler = self.request(role='admin', handler_cls=context.ContextsCollection)
        final_contexts = yield list_handler.get()
        final_count = len([c for c in final_contexts if c['id'] == self.dummyContext['id']])
        self.assertEqual(final_count, 0, "Deleted context should not be in list")


class TestContextStatsWithSubmissions(helpers.TestHandlerWithPopulatedDB):
    """Test context stats when there are actual submissions"""
    _handler = context.ContextStats

    @inlineCallbacks
    def setUp(self):
        yield helpers.TestHandlerWithPopulatedDB.setUp(self)
        yield self.perform_full_submission_actions()

    @inlineCallbacks
    def test_get_stats_with_submissions(self):
        """Test that stats correctly count submissions in the context"""
        handler = self.request(role='admin')
        response = yield handler.get(self.dummyContext['id'])

        # With populated submissions, we should have reports
        self.assertIn('open_reports', response)
        self.assertIn('total_reports', response)
        self.assertIn('last_update', response)
        self.assertGreater(response['total_reports'], 0, "Should have submissions after populate")
        # last_update should be set when there are reports
        if response['total_reports'] > 0:
            self.assertIsNotNone(response['last_update'])
