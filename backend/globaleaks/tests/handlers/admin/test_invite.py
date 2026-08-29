from twisted.internet.defer import inlineCallbacks, maybeDeferred

from globaleaks import models
from globaleaks.handlers.admin import invite
from globaleaks.orm import transact
from globaleaks.rest import errors
from globaleaks.tests import helpers


@transact
def tenant_of(session, invite_id):
    """
    Return the site the invitation has been issued for
    """
    subscriber = session.query(models.Subscriber) \
                        .filter(models.Subscriber.id == invite_id).one()

    return session.query(models.Tenant) \
                  .filter(models.Tenant.id == subscriber.tid).one().active


INVITE = {
    'organization_name': 'Invited Organization',
    'email': 'invited@example.org',
    'mail_template': ''
}


class TestInvitesCollection(helpers.TestHandlerWithPopulatedDB):
    """
    An invitation to accredit an organization is issued by the administrators
    """
    _handler = invite.InvitesCollection

    @inlineCallbacks
    def test_post(self):
        handler = self.request(INVITE, role='admin')
        response = yield handler.post()

        self.assertEqual(response['organization_name'], 'Invited Organization')
        self.assertEqual(response['organization_email'], 'invited@example.org')
        self.assertEqual(response['status'], 'invited')

        # the site the organization will hold exists already, and is inactive
        # until somebody authorizes the registration
        self.assertFalse((yield tenant_of(response['id'])))

    @inlineCallbacks
    def test_post_hands_the_token_over_only_once(self):
        # The invitation is a link, and the link is the token: the database
        # keeps its hash, so whoever reads the invitations afterwards cannot
        # recover the link and enter the registration in place of the invited.
        handler = self.request(INVITE, role='admin')
        created = yield handler.post()

        self.assertTrue(created['token'])

        listed = yield self.request(role='admin').get()

        self.assertEqual([entry['token'] for entry in listed], [''])

    @inlineCallbacks
    def test_get(self):
        yield self.request(INVITE, role='admin').post()

        response = yield self.request(role='admin').get()

        self.assertEqual(len(response), 1)
        self.assertEqual(response[0]['organization_name'], 'Invited Organization')
        self.assertEqual(response[0]['status'], 'invited')


class TestAdminInviteInstance(helpers.TestHandlerWithPopulatedDB):
    """
    An invitation is withdrawn while nobody has answered it, and is authorized
    """
    _handler = invite.AdminInviteInstance

    @inlineCallbacks
    def setUp(self):
        yield helpers.TestHandlerWithPopulatedDB.setUp(self)

        collection = self.request(INVITE, role='admin',
                                  handler_cls=invite.InvitesCollection)

        self.invite = yield collection.post()

    @inlineCallbacks
    def test_delete(self):
        yield self.request(role='admin').delete(self.invite['id'])

        listed = yield self.request(role='admin',
                                    handler_cls=invite.InvitesCollection).get()

        self.assertEqual(listed, [])

    @inlineCallbacks
    def test_delete_of_an_invitation_that_does_not_exist_is_refused(self):
        handler = self.request(role='admin')

        yield self.assertFailure(maybeDeferred(handler.delete, 'x' * 36),
                                 errors.ForbiddenOperation)

    @inlineCallbacks
    def test_an_invitation_nobody_answered_is_neither_authorized_nor_denied(self):
        # There is nothing to decide upon until the invited organization has
        # registered: the decision is taken on what it declared of itself.
        for action in ['accept', 'deny']:
            handler = self.request({'action': action}, role='admin')

            yield self.assertFailure(maybeDeferred(handler.put, self.invite['id']),
                                     errors.ForbiddenOperation)

    @inlineCallbacks
    def test_put_with_an_action_the_platform_does_not_know_is_refused(self):
        handler = self.request({'action': 'whatever'}, role='admin')

        yield self.assertFailure(maybeDeferred(handler.put, self.invite['id']),
                                 errors.InputValidationError)


class TestInviteInstance(helpers.TestHandlerWithPopulatedDB):
    """
    The invited organization reaches its own invitation by the token it was
    """
    _handler = invite.InviteInstance

    @inlineCallbacks
    def setUp(self):
        yield helpers.TestHandlerWithPopulatedDB.setUp(self)

        collection = self.request(INVITE, role='admin',
                                  handler_cls=invite.InvitesCollection)

        self.invite = yield collection.post()

    @inlineCallbacks
    def test_get(self):
        handler = self.request()
        response = yield handler.get(self.invite['token'])

        self.assertEqual(response['organization_name'], 'Invited Organization')
        self.assertEqual(response['organization_email'], 'invited@example.org')

        # what is served is the invitation, never the token that opens it
        self.assertNotIn('token', response)

    @inlineCallbacks
    def test_get_with_a_token_that_opens_nothing_is_refused(self):
        handler = self.request()

        yield self.assertFailure(maybeDeferred(handler.get, 'a' * 64),
                                 errors.ForbiddenOperation)
