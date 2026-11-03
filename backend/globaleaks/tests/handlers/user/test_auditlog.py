from twisted.internet.defer import inlineCallbacks

# The helpers load the handlers in the order the API does: the package of the
# user handlers, imported first, would close a cycle through the admin ones
from globaleaks.tests import helpers

from globaleaks.handlers import user
from globaleaks.orm import db_log, tw
from globaleaks.rest import errors


class TestUserAuditLog(helpers.TestHandlerWithPopulatedDB):
    _handler = user.auditlog.UserAuditLog

    @inlineCallbacks
    def setUp(self):
        yield helpers.TestHandlerWithPopulatedDB.setUp(self)

        me = self.dummy_receiver_1['id']
        other = self.dummy_receiver_2['id']
        admin = self.dummy_admin['id']

        # What the user did, what was done on the account by an administrator
        # and by the system, what was attempted on it, and what pertains to
        # somebody else
        for entry in [
            {'type': 'access_report', 'user_id': me, 'object_id': 'itip'},
            {'type': 'login_failure', 'user_id': me},
            {'type': 'change_password', 'user_id': admin, 'object_id': me},
            {'type': 'disable_2fa', 'user_id': 'system', 'object_id': me},
            {'type': 'reset_idp_binding', 'tid': 2, 'user_id': admin, 'object_id': me},
            {'type': 'delete_user', 'user_id': admin, 'object_id': other},
            {'type': 'login', 'user_id': other},
            {'type': 'update_node', 'user_id': admin}
        ]:
            yield tw(db_log, **{'tid': 1, **entry})

    @inlineCallbacks
    def test_get_returns_what_pertains_to_the_account(self):
        me = self.dummy_receiver_1['id']

        handler = self.request(user_id=me, role='receiver')
        response = yield handler.get()

        types = sorted(entry['type'] for entry in response)
        self.assertEqual(types, ['access_report', 'change_password', 'disable_2fa',
                                 'login_failure', 'reset_idp_binding'])

        for entry in response:
            self.assertTrue(me in (entry['user_id'], entry['object_id']))

        # Who acted is named by the entry itself
        usernames = {entry['type']: entry['username'] for entry in response}
        self.assertEqual(usernames['change_password'], self.dummy_admin['username'])
        self.assertEqual(usernames['access_report'], self.dummy_receiver_1['username'])
        self.assertEqual(usernames['disable_2fa'], 'system')

        # Most recent first
        dates = [entry['date'] for entry in response]
        self.assertEqual(dates, sorted(dates, reverse=True))

    @inlineCallbacks
    def test_get_is_scoped_to_the_user_in_session(self):
        handler = self.request(user_id=self.dummy_admin['id'], role='admin')
        response = yield handler.get()

        self.assertFalse([entry for entry in response if entry['type'] in ['access_report', 'login_failure']])
        self.assertTrue({'change_password', 'delete_user', 'update_node'} <= {entry['type'] for entry in response})

    def test_get_without_a_user_session_is_refused(self):
        handler = self.request({}, role='whistleblower')

        return self.assertRaises(errors.NotAuthenticated, handler.get)
