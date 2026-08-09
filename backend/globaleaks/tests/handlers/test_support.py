from nacl.encoding import Base64Encoder
from twisted.internet.defer import inlineCallbacks

from globaleaks import models
from globaleaks.handlers import support
from globaleaks.handlers.admin.tenant import create_and_initialize
from globaleaks.handlers.admin.user import create_user, db_update_user
from globaleaks.orm import transact, tw
from globaleaks.rest import errors
from globaleaks.sessions import Session
from globaleaks.tests import helpers
from globaleaks.utils.crypto import GCE


class TestSupport(helpers.TestHandlerWithPopulatedDB):
    """
    The support keys implement the same hierarchy of the escrow keys:

      root support key --wraps--> secondary tenant support key --wraps--> thread key

    Every administrator holds the support key of its own tenant, sealed to its
    own key; the administrators of the root tenant reach the key of any
    secondary tenant by descending the hierarchy.
    """
    _handler = support.SupportHandler

    # the archived database fixture does not carry the support schema yet
    initialize_test_database_using_archived_db = False

    @inlineCallbacks
    def setUp(self):
        # The test suite mocks key generation with a single fixed keypair:
        # the hierarchy is only meaningful when every key is distinct.
        setattr(GCE, 'generate_keypair', helpers.GCE_orig_generate_keypair)

        yield helpers.TestHandlerWithPopulatedDB.setUp(self)

        self.root_admin = yield self.get_administrator(1)
        self.tenant_admin = yield self.get_administrator(2)

    def tearDown(self):
        setattr(GCE, 'generate_keypair', helpers.mock_GCE_generate_keypair)

        return helpers.TestHandlerWithPopulatedDB.tearDown(self)

    #
    # Helpers
    #

    @staticmethod
    def user_cc(user):
        """
        Return the private key of a user created with the test password
        """
        return GCE.symmetric_decrypt(helpers.USER_KEY, Base64Encoder.decode(user.crypto_prv_key))

    @transact
    def get_administrator(self, session, tid):
        """
        Return an administrator of the tenant along with its own private key
        """
        user = session.query(models.User) \
                      .filter(models.User.tid == tid,
                              models.User.role == 'admin') \
                      .first()

        return {'id': user.id, 'cc': self.user_cc(user)}

    @transact
    def drop_user_keypair(self, session, user_id):
        """
        Bring the account back to the state of one that has not completed its
        access yet: it holds no key of its own
        """
        user = session.query(models.User).filter(models.User.id == user_id).one()
        user.crypto_pub_key = ''
        user.crypto_prv_key = ''

    @transact
    def bind_idp_identity(self, session, user_id, subject):
        """
        Bind an identity of the identity provider to the account, as the login
        does once the account has authenticated with its own credentials
        """
        user = session.query(models.User).filter(models.User.id == user_id).one()
        user.idp_id = subject

    @transact
    def get_support_public_key(self, session, tid):
        return support.get_support_config(session, tid, 'crypto_support_pub_key')

    @transact
    def get_user_support_key(self, session, tid, user_id):
        """
        Return the support key held by the user, unwrapped with its own key
        """
        user = session.query(models.User).filter(models.User.id == user_id).one()

        return support.decrypt_private_key(self.user_cc(user),
                                           user.crypto_support_prv_key,
                                           support.get_support_config(session, tid, 'crypto_support_pub_key'))

    @transact
    def get_users_holding_key(self, session, tid):
        """
        Return the users whose stored support key opens the key of the tenant
        """
        support_public_key = support.get_support_config(session, tid, 'crypto_support_pub_key')

        ret = []
        for user in session.query(models.User).filter(models.User.crypto_support_prv_key != ''):
            if support.decrypt_private_key(self.user_cc(user), user.crypto_support_prv_key, support_public_key) is not None:
                ret.append((user.tid, user.role))

        return sorted(ret)

    @transact
    def get_tenant_wrapped_key(self, session, tid, root_support_private_key):
        """
        Unwrap the tenant support key stored in the tenant configuration
        """
        return support.decrypt_private_key(root_support_private_key,
                                           support.get_support_config(session, tid, 'crypto_support_prv_key'),
                                           support.get_support_config(session, tid, 'crypto_support_pub_key'))

    @transact
    def get_storage(self, session, support_request_id):
        support_request = session.query(models.SupportRequest) \
                                 .filter(models.SupportRequest.id == support_request_id).one()

        message = session.query(models.SupportMessage) \
                         .filter(models.SupportMessage.support_request_id == support_request.id).one()

        return {
            'crypto_prv_key': support_request.crypto_prv_key,
            'root_crypto_prv_key': support_request.root_crypto_prv_key,
            'crypto_author_prv_key': support_request.crypto_author_prv_key,
            'mail_address': support_request.mail_address,
            'content': message.content,
            'mails': [mail.body for mail in session.query(models.Mail)]
        }

    def admin_session(self, tid=1, admin=None):
        """
        Session of an administrator of the tenant tid
        """
        admin = admin if admin is not None else self.root_admin

        return Session(tid, admin['id'], tid, 'admin', 'admin', admin['cc'])

    def root_management_session(self, tid):
        """
        Session of a root administrator managing the secondary tenant tid
        """
        return Session(tid, self.root_admin['id'], 1, 'admin', 'admin', self.root_admin['cc'])

    def new_user_desc(self, role, username):
        desc = self.get_dummy_user(role, username)
        desc.pop('id')
        return desc

    #
    # 1. The support key of a tenant is granted to the administrator created by the wizard
    #
    @inlineCallbacks
    def test_wizard_administrator_holds_the_tenant_support_key(self):
        support_public_key = yield self.get_support_public_key(2)
        support_private_key = yield self.get_user_support_key(2, self.tenant_admin['id'])

        self.assertTrue(support_public_key)
        self.assertIsNotNone(support_private_key)
        self.assertTrue(support.private_key_matches_public(support_private_key, support_public_key))

    #
    # 2. The support key is handed over to every administrator created afterwards
    #
    @inlineCallbacks
    def test_support_key_is_granted_to_every_new_administrator(self):
        root_support_private_key = yield self.get_user_support_key(1, self.root_admin['id'])

        new_admin = yield create_user(1, self.admin_session(), self.new_user_desc('admin', 'admin2'), 'en')
        new_receiver = yield create_user(1, self.admin_session(), self.new_user_desc('receiver', 'receiver3'), 'en')

        admin_key = yield self.get_user_support_key(1, new_admin['id'])
        receiver_key = yield self.get_user_support_key(1, new_receiver['id'])

        self.assertEqual(admin_key, root_support_private_key)
        self.assertIsNone(receiver_key)

    #
    # 3. The key of a secondary tenant is created with the tenant and wrapped to the root key
    #
    @inlineCallbacks
    def test_secondary_tenant_key_is_wrapped_to_the_root_key(self):
        root_support_private_key = yield self.get_user_support_key(1, self.root_admin['id'])

        tenant = yield create_and_initialize({'name': 'tenant-4', 'active': True, 'subdomain': 'tenant4', 'profile': 'default'})

        support_public_key = yield self.get_support_public_key(tenant['id'])
        support_private_key = yield self.get_tenant_wrapped_key(tenant['id'], root_support_private_key)

        self.assertTrue(support_public_key)
        self.assertIsNotNone(support_private_key)
        self.assertTrue(support.private_key_matches_public(support_private_key, support_public_key))

    #
    # 4. A root administrator reads the requests of every tenant
    #
    @inlineCallbacks
    def test_root_administrator_reads_the_requests_of_every_tenant(self):
        yield support.create_support_request(1, None, 'root@example.org', 'Root request')
        yield support.create_support_request(2, None, 'tenant2@example.org', 'Tenant 2 request')
        yield support.create_support_request(3, None, 'tenant3@example.org', 'Tenant 3 request')

        support_requests = yield support.get_admin_support_requests(1, self.admin_session())

        self.assertEqual(len(support_requests), 3)
        self.assertTrue(all(support_request['key_available'] for support_request in support_requests))
        self.assertEqual(sorted(support_request['messages'][0]['content'] for support_request in support_requests),
                         ['Root request', 'Tenant 2 request', 'Tenant 3 request'])

    #
    # 5. The key of a secondary tenant is granted to its administrators, whoever creates them
    #
    @inlineCallbacks
    def test_secondary_tenant_key_is_granted_to_its_administrators(self):
        support_private_key = yield self.get_user_support_key(2, self.tenant_admin['id'])

        created_by_root = yield create_user(2, self.root_management_session(2), self.new_user_desc('admin', 'admin4'), 'en')
        created_by_tenant = yield create_user(2, self.admin_session(2, self.tenant_admin), self.new_user_desc('admin', 'admin5'), 'en')

        key_created_by_root = yield self.get_user_support_key(2, created_by_root['id'])
        key_created_by_tenant = yield self.get_user_support_key(2, created_by_tenant['id'])

        self.assertEqual(key_created_by_root, support_private_key)
        self.assertEqual(key_created_by_tenant, support_private_key)

    #
    # 6. The key of a secondary tenant is never handed over to the users of the root tenant
    #
    @inlineCallbacks
    def test_secondary_tenant_key_is_never_granted_to_root_tenant_users(self):
        yield create_user(2, self.root_management_session(2), self.new_user_desc('admin', 'admin6'), 'en')
        yield create_user(1, self.admin_session(), self.new_user_desc('admin', 'admin7'), 'en')

        holders = yield self.get_users_holding_key(2)

        self.assertTrue(holders)
        self.assertEqual([tid for tid, _ in holders], [2] * len(holders))

    #
    # 7. The key of a secondary tenant is held by the administrators of that tenant only
    #
    @inlineCallbacks
    def test_secondary_tenant_key_is_held_by_its_administrators_only(self):
        demoted = yield create_user(2, self.admin_session(2, self.tenant_admin), self.new_user_desc('admin', 'admin8'), 'en')

        holders = yield self.get_users_holding_key(2)
        self.assertEqual(sorted(holders), [(2, 'admin'), (2, 'admin')])

        request = dict(demoted)
        request['role'] = 'receiver'
        request['roles'] = ['receiver']
        request['pgp_key_remove'] = False
        yield tw(db_update_user, 2, self.admin_session(2, self.tenant_admin), demoted['id'], request, 'en')

        holders = yield self.get_users_holding_key(2)
        self.assertEqual(holders, [(2, 'admin')])

    #
    # 8. The key of a secondary tenant opens the requests of that tenant only
    #
    @inlineCallbacks
    def test_secondary_tenant_administrator_reads_its_own_requests_only(self):
        yield support.create_support_request(1, None, 'root@example.org', 'Root request')
        other, _ = yield support.create_support_request(3, None, 'tenant3@example.org', 'Tenant 3 request')
        yield support.create_support_request(2, None, 'tenant2@example.org', 'Tenant 2 request')

        tenant_session = self.admin_session(2, self.tenant_admin)

        support_requests = yield support.get_admin_support_requests(2, tenant_session)
        self.assertEqual([support_request['tid'] for support_request in support_requests], [2])
        self.assertEqual(support_requests[0]['messages'][0]['content'], 'Tenant 2 request')

        yield self.assertFailure(support.get_admin_support_requests(2, tenant_session, tenant_id=1),
                                 errors.ForbiddenOperation)

        yield self.assertFailure(support.update_support_request_status(2, tenant_session, other['id'], 'opened'),
                                 errors.ResourceNotFound)

    #
    # The request and its messages are stored encrypted and the notification is content free
    #
    @inlineCallbacks
    def test_anonymous_request_is_stored_encrypted(self):
        handler = self.request({'mail_address': 'user@example.org', 'text': 'Anonymous request'})
        created = yield handler.post()

        storage = yield self.get_storage(created['id'])

        self.assertEqual(created['status'], 'new')
        self.assertTrue(storage['crypto_prv_key'])
        self.assertTrue(storage['root_crypto_prv_key'])
        self.assertEqual(storage['crypto_author_prv_key'], '')
        self.assertNotIn('user@example.org', storage['mail_address'])
        self.assertNotIn('Anonymous request', storage['content'])
        self.assertTrue(storage['mails'])
        self.assertTrue(all('Anonymous request' not in body for body in storage['mails']))

        support_requests = yield support.get_admin_support_requests(1, self.admin_session())
        self.assertEqual(support_requests[0]['mail_address'], 'user@example.org')
        self.assertEqual(support_requests[0]['messages'][0]['content'], 'Anonymous request')

    #
    # The length of a message is bounded so that the public endpoint cannot
    # be used to fill the database
    #
    @inlineCallbacks
    def test_post_rejects_a_message_too_long(self):
        request = {
            'mail_address': 'user@example.org',
            'text': 'x' * (support.MAX_SUPPORT_MESSAGE_LENGTH + 1)
        }

        handler = self.request(request)
        yield self.assertFailure(handler.post(), errors.InputValidationError)

    #
    # An authenticated requester and the administrators share the thread
    #
    @inlineCallbacks
    def test_authenticated_support_conversation(self):
        user_session = Session(1, self.dummyReceiver_1['id'], 1, 'receiver1', 'receiver', helpers.USER_PRV_KEY)

        created, _ = yield support.create_support_request(1, user_session, '', 'User message')
        yield support.create_admin_support_message(1, self.admin_session(), created['id'], 'Admin reply')
        yield support.create_user_support_message(1, user_session, created['id'], 'User follow-up')

        support_requests = yield support.get_user_support_requests(1, user_session)

        self.assertEqual([message['content'] for message in support_requests[0]['messages']],
                         ['User message', 'Admin reply', 'User follow-up'])
        self.assertEqual(support_requests[0]['author_username'], 'receiver1')

    #
    # An account that has authenticated on the identity provider and has still
    # to set its password holds a session that identifies it but no key on the
    # account itself: it is exactly the step from which support is asked, and
    # its request is recorded as its own all the same
    #
    @inlineCallbacks
    def test_request_of_an_account_still_completing_its_access(self):
        user_id = self.dummyReceiver_1['id']
        yield self.drop_user_keypair(user_id)

        # the session is keyed on the keypair the account adopts when it sets
        # its password, as the login via the identity provider issues it
        session_private_key, _ = GCE.generate_keypair()
        user_session = Session(1, user_id, 1, 'receiver1', 'receiver', session_private_key)

        yield support.create_support_request(1, user_session, '', 'I lost my password')

        support_requests = yield support.get_admin_support_requests(1, self.admin_session())

        self.assertEqual(support_requests[0]['author_username'], 'receiver1')
        self.assertEqual([message['content'] for message in support_requests[0]['messages']],
                         ['I lost my password'])

        # and the thread is readable by its author as soon as the access is complete
        support_requests = yield support.get_user_support_requests(1, user_session)

        self.assertTrue(support_requests[0]['key_available'])

    #
    # An user that has authenticated on the identity provider and is being
    # asked for the password that decrypts its keys holds no session, but the
    # identity it presents is bound to its account and identifies it
    #
    @inlineCallbacks
    def test_request_of_an_identity_bound_to_an_account(self):
        user_id = self.dummyReceiver_1['id']
        yield self.bind_idp_identity(user_id, 'idp-subject-receiver1')

        handler = self.request({'text': 'I lost my password'})
        handler.request.oidc_token = {'sub': 'idp-subject-receiver1'}
        yield handler.post()

        support_requests = yield support.get_admin_support_requests(1, self.admin_session())

        self.assertEqual(support_requests[0]['author_username'], 'receiver1')
        self.assertEqual([message['content'] for message in support_requests[0]['messages']],
                         ['I lost my password'])

        # and the account reads it back once it has completed its login
        user_session = Session(1, user_id, 1, 'receiver1', 'receiver', helpers.USER_PRV_KEY)
        support_requests = yield support.get_user_support_requests(1, user_session)

        self.assertTrue(support_requests[0]['key_available'])

    #
    # An identity bound to no account identifies no requester
    #
    @inlineCallbacks
    def test_request_of_an_identity_bound_to_no_account(self):
        handler = self.request({'text': 'Who am I'})
        handler.request.oidc_token = {'sub': 'unknown-subject'}

        yield self.assertFailure(handler.post(), errors.ForbiddenOperation)

    #
    # Requests are numbered progressively within the tenant they belong to
    #
    @inlineCallbacks
    def test_requests_are_numbered_progressively_by_tenant(self):
        yield support.create_support_request(1, None, 'root@example.org', 'Root request 1')
        yield support.create_support_request(2, None, 'tenant2@example.org', 'Tenant 2 request 1')
        yield support.create_support_request(1, None, 'root@example.org', 'Root request 2')
        yield support.create_support_request(2, None, 'tenant2@example.org', 'Tenant 2 request 2')

        support_requests = yield support.get_admin_support_requests(1, self.admin_session())

        self.assertEqual(sorted((support_request['tid'], support_request['progressive'])
                                for support_request in support_requests),
                         [(1, 1), (1, 2), (2, 1), (2, 2)])
        self.assertTrue(all(support_request['tenant_name'] for support_request in support_requests))
