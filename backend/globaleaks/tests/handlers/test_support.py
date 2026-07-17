from twisted.internet.defer import inlineCallbacks

from globaleaks import models
from globaleaks.handlers import support
from globaleaks.handlers.admin import support as admin_support
from globaleaks.orm import transact
from globaleaks.tests import helpers


class TestSupportHandler(helpers.TestHandlerWithPopulatedDB):
    _handler = support.SupportHandler

    @transact
    def _get_mail_bodies(self, session):
        return [m.body for m in session.query(models.Mail)]

    @transact
    def _get_first_message(self, session):
        support_request = session.query(models.SupportRequest).first()
        message = session.query(models.SupportMessage).first()
        return {
            'request_id': support_request.id,
            'author_id': support_request.author_id,
            'crypto_pub_key': support_request.crypto_pub_key,
            'crypto_author_prv_key': support_request.crypto_author_prv_key,
            'mail_address': support_request.mail_address,
            'status': support_request.status,
            'content': message.content,
        }

    @inlineCallbacks
    def test_post_anonymous_is_encrypted(self):
        text = 'The email is to ask support for a sensitive matter'
        mail = 'giovanni.pellerano@globaleaks.org'
        request = {'mail_address': mail, 'text': text}

        yield self.test_model_count(models.SupportRequest, 0)
        yield self.test_model_count(models.SupportMessage, 0)
        yield self.test_model_count(models.Mail, 0)

        handler = self.request(request)
        yield handler.post()
        self.assertEqual(handler.request.code, 200)

        yield self.test_model_count(models.SupportRequest, 1)
        yield self.test_model_count(models.SupportMessage, 1)

        # a content-free notification is queued for the tenant administrators
        yield self.test_model_count(models.Mail, 1)

        row = yield self._get_first_message()

        # the request is anonymous: no author is bound to it
        self.assertIsNone(row['author_id'])

        # a per-thread keypair has been generated
        self.assertNotEqual(row['crypto_pub_key'], '')

        # message content and the requester e-mail are sealed at rest
        self.assertNotEqual(row['content'], text)
        self.assertNotIn(text, row['content'])
        self.assertNotEqual(row['mail_address'], mail)
        self.assertNotEqual(row['mail_address'], '')

    @inlineCallbacks
    def test_post_authenticated_binds_author(self):
        text = 'Authenticated support request'
        request = {'mail_address': '', 'text': text}

        handler = self.request(request, role='receiver')
        yield handler.post()
        self.assertEqual(handler.request.code, 200)

        row = yield self._get_first_message()

        # the authenticated requester is bound and can read replies later (v2)
        self.assertEqual(row['author_id'], self.dummyReceiver_1['id'])
        self.assertNotEqual(row['crypto_author_prv_key'], '')
        self.assertNotEqual(row['content'], text)

    @inlineCallbacks
    def test_notification_is_content_free(self):
        text = 'super-secret-support-string'
        request = {'mail_address': 'a@b.com', 'text': text}

        handler = self.request(request)
        yield handler.post()

        bodies = yield self._get_mail_bodies()
        self.assertEqual(len(bodies), 1)
        # the request content never travels by e-mail
        self.assertNotIn(text, bodies[0])
        self.assertNotIn('a@b.com', bodies[0])
