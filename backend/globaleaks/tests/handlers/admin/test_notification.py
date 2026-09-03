from twisted.internet.defer import inlineCallbacks

from globaleaks.handlers import admin
from globaleaks.models.config import ConfigFactory
from globaleaks.orm import transact
from globaleaks.rest import errors
from globaleaks.tests import helpers

# special guest:

stuff = "³²¼½¬¼³²"


@transact
def get_val(session, tid, var_name):
    return ConfigFactory(session, tid).get_val(var_name)


class TestNotificationInstance(helpers.TestHandlerWithPopulatedDB):
    _handler = admin.notification.NotificationInstance

    @inlineCallbacks
    def put(self, **changes):
        handler = self.request(role='admin')
        notif_desc = yield handler.get()
        notif_desc.update(changes)

        handler = self.request(notif_desc, role='admin')
        response = yield handler.put()
        return response

    @inlineCallbacks
    def test_get(self):
        handler = self.request(role='admin')
        response = yield handler.get()
        self.assertEqual(response['smtp_server'], 'mail.globaleaks.org')

    @inlineCallbacks
    def test_get_never_reads_the_password_back(self):
        handler = self.request(role='admin')
        response = yield handler.get()
        self.assertEqual(response['smtp_password'], '')
        self.assertTrue(response['smtp_password_set'])

    @inlineCallbacks
    def test_put(self):
        response = yield self.put(smtp_server=stuff, smtp_password='widdlyscuds')
        self.assertEqual(response['smtp_server'], stuff)
        self.assertEqual(response['smtp_password'], '')
        self.assertEqual((yield get_val(1, 'smtp_password')), 'widdlyscuds')

    @inlineCallbacks
    def test_put_with_no_password_keeps_the_one_held(self):
        yield self.put(smtp_password='widdlyscuds')
        yield self.put(smtp_server=stuff)
        self.assertEqual((yield get_val(1, 'smtp_password')), 'widdlyscuds')

    @inlineCallbacks
    def test_put_with_no_authentication_drops_the_password(self):
        response = yield self.put(smtp_authentication=False, smtp_password='widdlyscuds')
        self.assertFalse(response['smtp_password_set'])
        self.assertEqual((yield get_val(1, 'smtp_password')), '')

    @inlineCallbacks
    def test_put_with_authentication_and_no_password_at_all_is_refused(self):
        yield self.put(smtp_authentication=False)

        yield self.assertFailure(self.put(smtp_authentication=True), errors.InputValidationError)

        response = yield self.put(smtp_authentication=True, smtp_password='widdlyscuds')
        self.assertTrue(response['smtp_password_set'])
