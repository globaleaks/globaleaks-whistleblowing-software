from globaleaks import models
from globaleaks.handlers import support
from globaleaks.models.config import ConfigFactory
from globaleaks.orm import transact
from globaleaks.sessions import Session
from globaleaks.tests import helpers
from twisted.internet.defer import inlineCallbacks


class TestSupportHandler(helpers.TestHandlerWithPopulatedDB):
    _handler = support.SupportHandler

    def admin_session(self):
        return Session(1, self.dummyAdmin['id'], 1, self.dummyAdmin['username'], 'admin', helpers.USER_PRV_KEY)

    def user_session(self):
        return Session(1, self.dummyReceiver_1['id'], 1, self.dummyReceiver_1['username'], 'receiver', helpers.USER_PRV_KEY)

    @transact
    def get_tenant_admin(self, session, tid):
        user = session.query(models.User).filter(models.User.tid == tid, models.User.role == 'admin').one()
        return {'id': user.id, 'username': user.username}

    @transact
    def get_key_state(self, session):
        root_admin = session.query(models.User).filter(models.User.tid == 1, models.User.id == self.dummyAdmin['id']).one()
        tenant_admin = session.query(models.User).filter(models.User.tid == 2, models.User.role == 'admin').one()
        return {
            'root_public': ConfigFactory(session, 1).get_val('crypto_support_pub_key'),
            'root_admin_private': root_admin.crypto_support_prv_key,
            'tenant_public': ConfigFactory(session, 2).get_val('crypto_support_pub_key'),
            'tenant_root_private': ConfigFactory(session, 2).get_val('crypto_support_prv_key'),
            'tenant_admin_private': tenant_admin.crypto_support_prv_key
        }

    @transact
    def get_storage(self, session, support_request_id):
        request = session.query(models.SupportRequest).filter(models.SupportRequest.id == support_request_id).one()

        message = session.query(models.SupportMessage) \
                         .filter(models.SupportMessage.support_request_id == request.id) \
                         .order_by(models.SupportMessage.creation_date.asc()) \
                         .first()

        mails = session.query(models.Mail).all()
        return {
            'request': {
                'author_id': request.author_id,
                'crypto_pub_key': request.crypto_pub_key,
                'crypto_prv_key': request.crypto_prv_key,
                'root_crypto_prv_key': request.root_crypto_prv_key,
                'crypto_author_prv_key': request.crypto_author_prv_key,
                'mail_address': request.mail_address
            },
            'message': {'content': message.content},
            'mails': [{'body': mail.body} for mail in mails]
        }

    @inlineCallbacks
    def test_support_keys_are_initialized(self):
        keys = yield self.get_key_state()

        self.assertTrue(keys['root_public'])
        self.assertTrue(keys['root_admin_private'])
        self.assertTrue(keys['tenant_public'])
        self.assertTrue(keys['tenant_root_private'])
        self.assertTrue(keys['tenant_admin_private'])

    @inlineCallbacks
    def test_create_encrypted_support_request(self):
        mail_address = 'user@example.org'
        content = 'Encrypted support request'
        handler = self.request({'mail_address': mail_address, 'text': content})
        created = yield handler.post()
        storage = yield self.get_storage(created['id'])

        self.assertEqual(created['status'], 'new')
        self.assertTrue(storage['request']['crypto_pub_key'])
        self.assertTrue(storage['request']['crypto_prv_key'])
        self.assertTrue(storage['request']['root_crypto_prv_key'])
        self.assertEqual(storage['request']['crypto_author_prv_key'], '')
        self.assertNotIn(mail_address, storage['request']['mail_address'])
        self.assertNotIn(content, storage['message']['content'])
        self.assertEqual(len(storage['mails']), 1)
        self.assertNotIn(content, storage['mails'][0]['body'])

        requests = yield support.get_admin_support_requests(1, self.admin_session())
        self.assertEqual(requests[0]['mail_address'], mail_address)
        self.assertEqual(requests[0]['messages'][0]['content'], content)

    @inlineCallbacks
    def test_authenticated_support_conversation(self):
        user_session = self.user_session()
        admin_session = self.admin_session()
        created = yield support.create_support_request(1, user_session, '', 'User message')
        storage = yield self.get_storage(created['id'])

        self.assertEqual(storage['request']['author_id'], self.dummyReceiver_1['id'])
        self.assertTrue(storage['request']['crypto_author_prv_key'])

        reply, notification = yield support.create_admin_support_message(1, admin_session, created['id'], 'Admin reply')
        self.assertEqual(reply['content'], 'Admin reply')
        self.assertTrue(notification['content_free'])

        message = yield support.create_user_support_message(1, user_session, created['id'], 'User follow-up')
        self.assertEqual(message['content'], 'User follow-up')

        requests = yield support.get_user_support_requests(1, user_session)
        self.assertEqual([message['content'] for message in requests[0]['messages']], ['User message', 'Admin reply', 'User follow-up'])

    @inlineCallbacks
    def test_tenant_and_root_admin_access(self):
        tenant_admin = yield self.get_tenant_admin(2)
        tenant_session = Session(2, tenant_admin['id'], 2, tenant_admin['username'], 'admin', helpers.USER_PRV_KEY)
        root_session = self.admin_session()
        created = yield support.create_support_request(2, None, 'tenant@example.org', 'Tenant request')

        tenant_requests = yield support.get_admin_support_requests(2, tenant_session)
        self.assertEqual(len(tenant_requests), 1)
        self.assertEqual(tenant_requests[0]['messages'][0]['content'], 'Tenant request')

        root_requests = yield support.get_admin_support_requests(1, root_session, tenant_id=2)
        self.assertEqual(len(root_requests), 1)
        self.assertEqual(root_requests[0]['tid'], 2)
        self.assertEqual(root_requests[0]['messages'][0]['content'], 'Tenant request')

        reply, _ = yield support.create_admin_support_message(1, root_session, created['id'], 'Root reply')
        self.assertEqual(reply['content'], 'Root reply')
