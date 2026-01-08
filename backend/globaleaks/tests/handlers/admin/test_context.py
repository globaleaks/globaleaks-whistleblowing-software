from twisted.internet.defer import inlineCallbacks

from globaleaks.handlers.admin import context
from globaleaks.models import Context, ReceiverContext
from globaleaks.orm import transact
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
    def test_delete_soft_deletes_context(self):
        """
        Test that deleting a context marks it as deleted (soft delete)
        instead of physically removing it
        """
        # Create a context
        context_data = yield context.create_context(1, self.state.user_session, helpers.get_dummy_context(), 'en')

        # Delete the context using the delete_context function directly
        yield context.delete_context(1, self.state.user_session, context_data['id'])

        # Verify the context is soft deleted
        @transact
        def check_context_status(session):
            ctx = session.query(Context).filter(Context.id == context_data['id']).one_or_none()
            if ctx is None:
                return None
            return ctx.status

        status = yield check_context_status()
        # Context should be marked as deleted
        self.assertEqual(status, 'deleted')

    @inlineCallbacks
    def test_delete_removes_receiver_associations(self):
        """
        Test that deleting a context removes receiver associations
        """
        # Create a context
        context_data = yield context.create_context(1, self.state.user_session, helpers.get_dummy_context(), 'en')

        # Delete the context using the delete_context function directly
        yield context.delete_context(1, self.state.user_session, context_data['id'])

        # Verify receiver associations are removed
        @transact
        def check_receiver_associations(session):
            return session.query(ReceiverContext).filter(
                ReceiverContext.context_id == context_data['id']
            ).count()

        count = yield check_receiver_associations()
        self.assertEqual(count, 0)

    @inlineCallbacks
    def test_deleted_contexts_not_in_list(self):
        """
        Test that deleted contexts are not returned in the list
        """
        # Get initial count
        initial_list = yield context.get_contexts(1, 'en')
        initial_count = len(initial_list)

        # Create a context
        context_data = yield context.create_context(1, self.state.user_session, helpers.get_dummy_context(), 'en')

        # Verify it's in the list
        list_after_create = yield context.get_contexts(1, 'en')
        self.assertEqual(len(list_after_create), initial_count + 1)

        # Delete the context
        yield context.delete_context(1, self.state.user_session, context_data['id'])

        # Verify it's not in the list anymore
        list_after_delete = yield context.get_contexts(1, 'en')
        self.assertEqual(len(list_after_delete), initial_count)
