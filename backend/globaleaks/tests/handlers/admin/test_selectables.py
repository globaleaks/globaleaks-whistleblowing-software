from twisted.internet.defer import inlineCallbacks

from globaleaks import models
from globaleaks.handlers.admin import notification, selectables, user
from globaleaks.rest import errors
from globaleaks.tests import helpers


class TestSelectablesCollection(helpers.TestHandlerWithPopulatedDB):
    _handler = selectables.SelectablesCollection

    @inlineCallbacks
    def test_get(self):
        handler = self.request({}, role='admin')
        response = yield handler.get()

        self.assertEqual(sorted(response.keys()), ['contexts', 'questionnaires', 'users'])
        self.assertTrue(len(response['users']) > 0)

        # An option carries what names it and what the pages choose it by, and
        # nothing of the account it stands for
        for entry in response['users']:
            self.assertEqual(sorted(entry.keys()),
                             ['encryption', 'escrow', 'id', 'name', 'role'])

        for group in ['contexts', 'questionnaires']:
            for entry in response[group]:
                self.assertEqual(sorted(entry.keys()), ['id', 'name'])

    @inlineCallbacks
    def test_get_is_served_to_an_administrator_scoped_out_of_every_area(self):
        # Choosing a recipient for a channel is not managing the users: the
        # options are served whatever the areas the administrator manages
        handler = self.request({},
                               role='admin',
                               permissions={permission: False for permission in models.admin_permissions})

        response = yield handler.get()

        self.assertTrue(len(response['users']) > 0)


class TestUsersReadIsGated(helpers.TestHandlerWithPopulatedDB):
    _handler = user.UsersCollection

    def test_get_without_the_permission_is_refused(self):
        # The area is gated on every operation: what it holds - the addresses,
        # the key material and the state of the accounts - is not read by an
        # administrator scoped out of it
        handler = self.request({}, role='admin', permissions={'can_manage_users': False})

        return self.assertRaises(errors.ForbiddenOperation, handler.get)


class TestNotificationReadIsGated(helpers.TestHandlerWithPopulatedDB):
    _handler = notification.NotificationInstance

    def test_get_without_the_permission_is_refused(self):
        # The notification settings carry the credentials of the mail server
        handler = self.request({}, role='admin', permissions={'can_manage_notifications': False})

        return self.assertRaises(errors.ForbiddenOperation, handler.get)
