from twisted.internet.defer import inlineCallbacks

from globaleaks import models
from globaleaks.handlers import auth
from globaleaks.handlers.user import UserInstance
from globaleaks.models.config import ConfigFactory
from globaleaks.handlers.whistleblower.wbtip import WBTipInstance
from globaleaks.orm import transact
from globaleaks.rest import errors
from globaleaks.sessions import Sessions
from globaleaks.state import State
from globaleaks.tests import helpers


@transact
def count_audit_entries(session, type):
    return session.query(models.AuditLog).filter(models.AuditLog.type == type).count()


@transact
def add_profile_role(session, username, role):
    user = session.query(models.User).filter(models.User.tid == 1, models.User.username == username).one()
    session.add(models.UserProfileRole({'profile_id': user.profile_id, 'role': role}))


@transact
def get_idp_id(session, username):
    return session.query(models.User).filter(models.User.tid == 1, models.User.username == username).one().idp_id


@transact
def set_idp_id(session, username, idp_id, enabled=True):
    user = session.query(models.User).filter(models.User.tid == 1, models.User.username == username).one()
    user.idp_id = idp_id
    user.enabled = enabled


@transact
def set_config_variable(session, var_name, value):
    ConfigFactory(session, 1).set_val(var_name, value)


@transact
def get_user_desc(session, username):
    user = session.query(models.User).filter(models.User.tid == 1, models.User.username == username).one()

    return {
        'id': user.id,
        'hash': user.hash,
        'role': user.role,
        'idp_id': user.idp_id,
        'mail_address': user.mail_address,
        'password_change_needed': user.password_change_needed
    }


class TestAuthTypeHandler(helpers.TestHandlerWithPopulatedDB):
    _handler = auth.AuthTypeHandler

    # since all logins happen in the same way,
    # the following tests are performed on the recipient user.

    @inlineCallbacks
    def test_whistleblower_request(self):
        handler = self.request({
            'username': '',
        })

        response = yield handler.post()
        self.assertTrue('type' in response)
        self.assertEqual(response['type'], 'key')
        self.assertTrue('salt' in response)
        self.assertEqual(response['salt'], helpers.VALID_SALT)

    @inlineCallbacks
    def test_receiver_request(self):
        handler = self.request({
            'username': 'receiver1',
        })

        response = yield handler.post()
        self.assertTrue('type' in response)
        self.assertEqual(response['type'], 'key')
        self.assertTrue('salt' in response)
        self.assertEqual(response['salt'], helpers.VALID_SALT)


class TestAuthTypeHandlerWithServersideHashing(helpers.TestHandlerWithPopulatedDB):
    _handler = auth.AuthTypeHandler
    clientside_hashing = False

    # since all logins for roles admin, receiver and custodian happen
    # in the same way, the following tests are performed on the recipient user.

    @inlineCallbacks
    def test_whistleblower_request(self):
        handler = self.request({
            'username': '',
        })

        response = yield handler.post()
        self.assertTrue('type' in response)
        self.assertEqual(response['type'], 'key')
        self.assertTrue('salt' in response)
        self.assertEqual(response['salt'], helpers.VALID_SALT)

    @inlineCallbacks
    def test_receiver_request(self):
        handler = self.request({
            'username': 'receiver1',
        })

        response = yield handler.post()
        self.assertTrue('type' in response)
        self.assertEqual(response['type'], 'password')


@transact
def user_bound_to(session, idp_id):
    user = session.query(models.User).filter(models.User.tid == 1, models.User.idp_id == idp_id).one_or_none()
    if user is None:
        return None

    return {'username': user.username, 'name': user.name, 'mail_address': user.mail_address,
            'role': user.role, 'hash': user.hash}


class TestAuthentication(helpers.TestHandlerWithPopulatedDB):
    _handler = auth.AuthenticationHandler

    # since all logins for roles admin, receiver and custodian happen
    # in the same way, the following tests are performed on the admin user.

    @inlineCallbacks
    def test_successful_login(self):
        handler = self.request({
            'tid': 1,
            'username': 'admin',
            'password': helpers.VALID_KEY,
            'authcode': '',
        })
        response = yield handler.post()
        self.assertTrue('id' in response)

    @inlineCallbacks
    def test_successful_multitenant_login_switch(self):
        handler = self.request({
            'tid': 1,
            'username': 'admin',
            'password': helpers.VALID_KEY,
            'authcode': ''
        })

        response = yield handler.post()

        auth_switch_handler = self.request({},
                                           headers={'x-session': response['id']},
                                           handler_cls=auth.TenantAuthSwitchHandler)

        response = yield auth_switch_handler.get(2)
        self.assertTrue('redirect' in response)

    @inlineCallbacks
    def test_the_switch_names_a_site_whose_cache_is_not_loaded_yet(self):
        handler = self.request({
            'tid': 1,
            'username': 'admin',
            'password': helpers.VALID_KEY,
            'authcode': ''
        })

        response = yield handler.post()

        # The answer to the creation of a site returns before the reload of the
        # state: until then the site is in the database and not in the cache,
        # and the address handed back would name no site at all
        del State.tenants[2]

        auth_switch_handler = self.request({},
                                           headers={'x-session': response['id']},
                                           handler_cls=auth.TenantAuthSwitchHandler)

        response = yield auth_switch_handler.get(2)

        self.assertTrue(State.tenants[2].cache.uuid)
        self.assertIn(f'/t/{State.tenants[2].cache.uuid}/', response['redirect'])


    @inlineCallbacks
    def test_accept_login_in_https(self):
        handler = self.request({
            'tid': 1,
            'username': 'admin',
            'password': helpers.VALID_KEY,
            'authcode': ''
        })
        State.tenants[1].cache['https_admin'] = True
        response = yield handler.post()
        self.assertTrue('id' in response)

    @inlineCallbacks
    def test_deny_login_in_https(self):
        handler = self.request({
            'tid': 1,
            'username': 'admin',
            'password': helpers.VALID_KEY,
            'authcode': ''
        })
        State.tenants[1].cache['https_admin'] = False
        yield self.assertFailure(handler.post(), errors.InvalidAuthentication)

    @inlineCallbacks
    def test_invalid_login_wrong_password(self):
        handler = self.request({
            'tid': 1,
            'username': 'admin',
            'password': 'INVALIDPASSWORD',
            'authcode': '',
        })

        yield self.assertFailure(handler.post(), errors.InvalidAuthentication)

    @inlineCallbacks
    def test_invalid_login_is_recorded_in_the_audit_log(self):
        # db_login_failure logs and then raises; the raise reaches the @transact
        # wrapper, so the entry must survive the resulting rollback.
        handler = self.request({
            'tid': 1,
            'username': 'admin',
            'password': 'INVALIDPASSWORD',
            'authcode': '',
        })

        yield self.assertFailure(handler.post(), errors.InvalidAuthentication)

        self.assertEqual((yield count_audit_entries('login_failure')), 1)

    @inlineCallbacks
    def test_invalid_login_of_unexistent_user_is_recorded_in_the_audit_log(self):
        handler = self.request({
            'tid': 1,
            'username': 'unexistent',
            'password': 'INVALIDPASSWORD',
            'authcode': '',
        })

        yield self.assertFailure(handler.post(), errors.InvalidAuthentication)

        self.assertEqual((yield count_audit_entries('login_failure')), 1)

    @inlineCallbacks
    def test_single_session_per_user(self):
        handler = self.request({
            'tid': 1,
            'username': 'admin',
            'password': helpers.VALID_KEY,
            'authcode': '',
        })

        r1 = yield handler.post()

        handler = self.request({
            'tid': 1,
            'username': 'admin',
            'password': helpers.VALID_KEY,
            'authcode': '',
        })

        r2 = yield handler.post()

        self.assertTrue(Sessions.get(r1['id']) is None)
        self.assertTrue(Sessions.get(r2['id']) is not None)

    @inlineCallbacks
    def test_session_is_revoked(self):
        auth_handler = self.request({
            'tid': 1,
            'username': 'receiver1',
            'password': helpers.VALID_KEY,
            'authcode': '',
        })

        r1 = yield auth_handler.post()

        user_handler = self.request({}, headers={'x-session': r1['id']},
                                        handler_cls=UserInstance)

        # The first_session is valid and the request should work
        yield user_handler.get()

        # The second authentication invalidates the first session
        auth_handler = self.request({
            'tid': 1,
            'username': 'receiver1',
            'password': helpers.VALID_KEY,
            'authcode': '',
        })

        r2 = yield auth_handler.post()

        user_handler = self.request({}, headers={'x-session': r1['id']},
                                        handler_cls=UserInstance)

        # The first_session should now deny access to authenticated resources
        yield self.assertRaises(errors.NotAuthenticated, user_handler.get)

        # The second_session should have no problems.
        user_handler = self.request({}, headers={'x-session': r2['id']},
                                        handler_cls=UserInstance)

        yield user_handler.get()

    @inlineCallbacks
    def test_login_reject_on_ip_filtering(self):
        State.tenants[1].cache['ip_filter_admin_enable'] = True
        State.tenants[1].cache['ip_filter_admin'] = '192.168.2.0/24'

        handler = self.request({
            'tid': 1,
            'username': 'admin',
            'password': helpers.VALID_KEY,
            'authcode': ''
        }, client_addr=b'192.168.1.1')
        yield self.assertFailure(handler.post(), errors.InvalidAuthentication)

    @inlineCallbacks
    def test_login_success_on_ip_filtering(self):
        State.tenants[1].cache['ip_filter_admin_enable'] = True
        State.tenants[1].cache['ip_filter_admin'] = '192.168.2.0/24'

        handler = self.request({
            'tid': 1,
            'username': 'admin',
            'password': helpers.VALID_KEY,
            'authcode': ''
        }, client_addr=b'192.168.2.1')
        response = yield handler.post()
        self.assertTrue('id' in response)


class TestAuthenticationWithServersideHashing(helpers.TestHandlerWithPopulatedDB):
    _handler = auth.AuthenticationHandler
    clientside_hashing = False

    @inlineCallbacks
    def test_successful_login(self):
        handler = self.request({
            'tid': 1,
            'username': 'admin',
            'password': helpers.VALID_PASSWORD,
            'authcode': '',
        })
        response = yield handler.post()
        self.assertTrue('id' in response)


class TestAuthenticationWithIdp(helpers.TestHandlerWithPopulatedDB):
    _handler = auth.AuthenticationHandler

    def login_request(self, username, subject):
        handler = self.request({
            'tid': 1,
            'username': username,
            'password': helpers.VALID_KEY,
            'authcode': ''
        })

        handler.request.oidc_token = {'sub': subject} if subject else ''

        return handler

    @inlineCallbacks
    def setUp(self):
        yield helpers.TestHandlerWithPopulatedDB.setUp(self)

        State.tenants[1].cache.idp = True

    @inlineCallbacks
    def test_login_without_a_token_is_refused(self):
        handler = self.login_request('admin', '')

        yield self.assertFailure(handler.post(), errors.InvalidAuthentication)

    @inlineCallbacks
    def test_login_without_a_subject_is_refused(self):
        handler = self.login_request('admin', 'subject')
        handler.request.oidc_token = {'name': 'no subject'}

        yield self.assertFailure(handler.post(), errors.InvalidAuthentication)

    @inlineCallbacks
    def test_login_binds_the_identity_to_the_account(self):
        response = yield self.login_request('admin', 'subject-1').post()

        self.assertIn('id', response)
        self.assertEqual((yield get_idp_id('admin')), 'subject-1')
        self.assertEqual((yield count_audit_entries('idp_identity_binding')), 1)

    @inlineCallbacks
    def test_a_bound_account_is_entered_by_its_identity_alone(self):
        yield set_idp_id('admin', 'subject-1')

        response = yield self.login_request('admin', 'subject-1').post()
        self.assertIn('id', response)

        handler = self.login_request('admin', 'subject-2')
        yield self.assertFailure(handler.post(), errors.InvalidAuthentication)
        self.assertEqual((yield get_idp_id('admin')), 'subject-1')

    @inlineCallbacks
    def test_a_bound_identity_resolves_its_account_whatever_the_username(self):
        yield set_idp_id('admin', 'subject-1')

        response = yield self.login_request(self.dummy_receiver_1['username'], 'subject-1').post()

        self.assertEqual(response['username'], 'admin')
        self.assertEqual((yield get_idp_id(self.dummy_receiver_1['username'])), '')

    @inlineCallbacks
    def test_a_wrong_password_binds_nothing(self):
        handler = self.request({'tid': 1, 'username': 'admin', 'password': 'wrong', 'authcode': ''})
        handler.request.oidc_token = {'sub': 'subject-1'}

        yield self.assertFailure(handler.post(), errors.InvalidAuthentication)
        self.assertEqual((yield get_idp_id('admin')), '')


class TestAuthTypeHandlerWithIdpProvisioning(helpers.TestHandlerWithPopulatedDB):
    _handler = auth.AuthTypeHandler

    @inlineCallbacks
    def setUp(self):
        yield helpers.TestHandlerWithPopulatedDB.setUp(self)

        State.tenants[1].cache.idp = True
        State.tenants[1].cache.idp_provisioning = True

        yield set_config_variable('default_user_profile', 'recipient')

    def authtype_request(self, claims):
        handler = self.request({'username': ''})
        handler.request.oidc_token = claims
        return handler

    @inlineCallbacks
    def test_an_unknown_identity_naming_a_free_username_is_provisioned(self):
        response = yield self.authtype_request({'sub': 'subject-1', 'preferred_username': 'newcomer'}).post()

        self.assertEqual(response, {'type': 'provisioning'})

    @inlineCallbacks
    def test_an_unknown_identity_naming_a_taken_username_binds_through_the_credentials(self):
        response = yield self.authtype_request({'sub': 'subject-1', 'preferred_username': 'admin'}).post()

        self.assertEqual(response, {'type': 'binding'})

    @inlineCallbacks
    def test_an_unknown_identity_binds_where_nothing_is_provisioned(self):
        State.tenants[1].cache.idp_provisioning = False

        response = yield self.authtype_request({'sub': 'subject-1', 'preferred_username': 'newcomer'}).post()

        self.assertEqual(response, {'type': 'binding'})

    @inlineCallbacks
    def test_a_bound_identity_is_asked_the_password_of_its_account(self):
        yield set_idp_id('admin', 'subject-1')

        response = yield self.authtype_request({'sub': 'subject-1'}).post()

        self.assertEqual(response['type'], 'key')
        self.assertEqual(response['username'], 'admin')

    @inlineCallbacks
    def test_a_provisioned_account_without_a_password_resumes_the_provisioning(self):
        claims = {'sub': 'subject-1', 'preferred_username': 'newcomer'}

        login = self.request({'tid': 1, 'username': '', 'password': '', 'authcode': ''},
                             handler_cls=auth.AuthenticationHandler)
        login.request.oidc_token = claims
        yield login.post()

        response = yield self.authtype_request(claims).post()

        self.assertEqual(response, {'type': 'provisioning'})


class TestAuthenticationWithIdpProvisioning(helpers.TestHandlerWithPopulatedDB):
    _handler = auth.AuthenticationHandler

    @inlineCallbacks
    def setUp(self):
        yield helpers.TestHandlerWithPopulatedDB.setUp(self)

        State.tenants[1].cache.idp = True
        State.tenants[1].cache.idp_provisioning = True

        yield set_config_variable('default_user_profile', 'recipient')

    def login_request(self, username, password, claims):
        handler = self.request({
            'tid': 1,
            'username': username,
            'password': password,
            'authcode': ''
        })

        handler.request.oidc_token = claims

        return handler

    @inlineCallbacks
    def test_an_unknown_identity_is_provisioned_an_account(self):
        claims = {'sub': 'subject-1', 'preferred_username': 'newcomer',
                  'email': 'newcomer@example.org', 'name': 'New Comer'}

        response = yield self.login_request('', '', claims).post()

        self.assertIn('id', response)
        user = yield user_bound_to('subject-1')
        self.assertEqual((user['username'], user['name'], user['mail_address'], user['role'], user['hash']),
                         ('newcomer', 'New Comer', 'newcomer@example.org', 'receiver', ''))
        self.assertEqual((yield count_audit_entries('idp_user_provisioning')), 1)

    @inlineCallbacks
    def test_the_username_falls_back_on_the_email_and_then_on_the_subject(self):
        yield self.login_request('', '', {'sub': 'subject-1', 'email': 'by-mail@example.org'}).post()
        yield self.login_request('', '', {'sub': 'subject-2'}).post()

        self.assertEqual((yield user_bound_to('subject-1'))['username'], 'by-mail@example.org')
        self.assertEqual((yield user_bound_to('subject-2'))['username'], 'subject-2')

    @inlineCallbacks
    def test_a_provisioned_account_is_entered_again_by_its_identity(self):
        claims = {'sub': 'subject-1', 'preferred_username': 'newcomer'}

        yield self.login_request('', '', claims).post()
        response = yield self.login_request('', '', claims).post()

        self.assertIn('id', response)
        self.assertEqual((yield count_audit_entries('idp_user_provisioning')), 1)

    @inlineCallbacks
    def test_an_identity_naming_a_taken_username_is_refused(self):
        handler = self.login_request('', '', {'sub': 'subject-1', 'preferred_username': 'admin'})

        yield self.assertFailure(handler.post(), errors.InvalidAuthentication)
        self.assertIsNone((yield user_bound_to('subject-1')))

    @inlineCallbacks
    def test_an_account_holding_a_password_is_not_entered_by_the_identity_alone(self):
        yield set_idp_id('admin', 'subject-1')

        handler = self.login_request('', '', {'sub': 'subject-1'})

        yield self.assertFailure(handler.post(), errors.InvalidAuthentication)

    @inlineCallbacks
    def test_nothing_is_provisioned_where_the_provisioning_is_off(self):
        State.tenants[1].cache.idp_provisioning = False

        handler = self.login_request('', '', {'sub': 'subject-1', 'preferred_username': 'newcomer'})

        yield self.assertFailure(handler.post(), errors.InvalidAuthentication)
        self.assertIsNone((yield user_bound_to('subject-1')))

    @inlineCallbacks
    def test_nothing_is_provisioned_where_the_site_creates_no_user_by_default(self):
        yield set_config_variable('default_user_profile', 'none')

        handler = self.login_request('', '', {'sub': 'subject-1', 'preferred_username': 'newcomer'})

        yield self.assertFailure(handler.post(), errors.InvalidAuthentication)

    @inlineCallbacks
    def test_a_token_without_a_subject_provisions_nothing(self):
        handler = self.login_request('', '', {'preferred_username': 'newcomer'})

        yield self.assertFailure(handler.post(), errors.InvalidAuthentication)


class TestReceiptAuth(helpers.TestHandlerWithPopulatedDB):
    _handler = auth.ReceiptAuthHandler

    @inlineCallbacks
    def test_invalid_whistleblower_login(self):
        handler = self.request({
            'receipt': 'INVALIDRECEIPT'
        })
        yield self.assertFailure(handler.post(), errors.InvalidAuthentication)

    @inlineCallbacks
    def test_successful_whistleblower_login(self):
        yield self.perform_full_submission_actions()
        handler = self.request({
            'receipt': self.dummy_submission['receipt']
        })
        handler.request.client_using_tor = True
        response = yield handler.post()
        self.assertTrue('id' in response)

    @inlineCallbacks
    def test_accept_whistleblower_login_in_https(self):
        yield self.perform_full_submission_actions()
        handler = self.request({'receipt': self.dummy_submission['receipt']})
        State.tenants[1].cache['https_whistleblower'] = True
        response = yield handler.post()
        self.assertTrue('id' in response)

    @inlineCallbacks
    def test_deny_whistleblower_login_in_https(self):
        yield self.perform_full_submission_actions()
        handler = self.request({'receipt': self.dummy_submission['receipt']})
        State.tenants[1].cache['https_whistleblower'] = False
        yield self.assertFailure(handler.post(), errors.InvalidAuthentication)

    @inlineCallbacks
    def test_single_session_per_whistleblower(self):
        """
        Asserts that the first_id is dropped from Sessions and requests
        using that session id are rejected
        """
        yield self.perform_full_submission_actions()

        handler = self.request({
            'receipt': self.dummy_submission['receipt']
        })

        handler.request.client_using_tor = True
        response = yield handler.post()
        first_id = response['id']

        wbtip_handler = self.request(headers={'x-session': first_id},
                                     handler_cls=WBTipInstance)
        yield wbtip_handler.get()

        handler = self.request({
            'receipt': self.dummy_submission['receipt']
        })

        response = yield handler.post()
        second_id = response['id']

        wbtip_handler = self.request(headers={'x-session': first_id},
                                     handler_cls=WBTipInstance)
        yield self.assertRaises(errors.NotAuthenticated, wbtip_handler.get)

        self.assertTrue(Sessions.get(first_id) is None)

        valid_session = Sessions.get(second_id)
        self.assertTrue(valid_session is not None)

        self.assertEqual(valid_session.role, 'whistleblower')

        wbtip_handler = self.request(headers={'x-session': second_id},
                                     handler_cls=WBTipInstance)
        yield wbtip_handler.get()


    @inlineCallbacks
    def test_empty_receipt_login_replaces_presented_session(self):
        """
        Asserts that a whistleblower session used to request a new
        submission session is consumed instead of accumulating
        """
        handler = self.request({'receipt': ''})
        handler.request.client_using_tor = True
        response = yield handler.post()
        first_id = response['id']

        handler = self.request({'receipt': ''}, headers={'x-session': first_id})
        handler.request.client_using_tor = True
        response = yield handler.post()
        second_id = response['id']

        self.assertNotEqual(first_id, second_id)
        self.assertTrue(Sessions.get(first_id) is None)
        self.assertTrue(Sessions.get(second_id) is not None)


class TestSessionHandler(helpers.TestHandlerWithPopulatedDB):
    @inlineCallbacks
    def test_successful_admin_session_setup_renewal_and_logout(self):
        # since all logins for roles admin, receiver and custodian happen
        # in the same way, the following tests are performed on the admin user.
        self._handler = auth.AuthenticationHandler

        # Login
        handler = self.request({
            'tid': 1,
            'username': 'admin',
            'password': helpers.VALID_KEY,
            'authcode': ''
        })

        response = yield handler.post()
        self.assertTrue(handler.session is None)
        self.assertTrue('id' in response)

        self._handler = auth.SessionHandler

        session_id = response['id']
        session = Sessions.get(session_id)
        session.token.id = helpers.TOKEN
        session.token.salt = helpers.TOKEN_SALT

        # Wrong Session Renewal
        handler = self.request({'token': 'wrong_token:666'}, headers={'x-session': session_id})
        response = yield handler.post()
        self.assertEqual(response['token']['id'], helpers.TOKEN.decode())

        # Correct Session Renewal
        handler = self.request({'token': helpers.TOKEN_ANSWER.decode()}, headers={'x-session': session_id})
        response = yield handler.post()
        self.assertNotEqual(response['token']['id'], helpers.TOKEN.decode())

        # Logout
        handler = self.request({}, headers={'x-session': session_id})
        yield handler.delete()

        yield handler.delete()

    @inlineCallbacks
    def test_successful_whistleblower_logout(self):
        self._handler = auth.ReceiptAuthHandler

        yield self.perform_full_submission_actions()

        handler = self.request({
            'receipt': self.dummy_submission['receipt']
        })

        handler.request.client_using_tor = True

        response = yield handler.post()
        self.assertTrue(handler.session is None)
        self.assertTrue('id' in response)

        self._handler = auth.SessionHandler

        # Logout
        handler = self.request({}, headers={'x-session': response['id']})
        yield handler.delete()


class TestTokenAuth(helpers.TestHandlerWithPopulatedDB):
    _handler = auth.TokenAuthHandler

    # since all logins for roles admin, receiver and custodian happen
    # in the same way, the following tests are performed on the recipient user.

    @inlineCallbacks
    def setUp(self):
        yield helpers.TestHandlerWithPopulatedDB.setUp(self)
        session = Sessions.new(1, self.dummy_receiver_1['id'], 1, self.dummy_receiver_1['username'], 'receiver')
        session.properties['authtoken'] = True
        self.authtoken = session.id

    @inlineCallbacks
    def test_successful_login(self):
        handler = self.request({
            'authtoken': self.authtoken,
        })

        response = yield handler.post()
        self.assertTrue('id' in response)

        # The redirect login is single-use: the adopted session becomes a primary
        # session that can no longer be adopted through tokenauth.
        adopted = Sessions.get(response['id'])
        self.assertFalse(adopted.properties.get('authtoken'))

    @inlineCallbacks
    def test_rejects_non_authtoken_session(self):
        # A primary session id (not issued for the redirect login flow) must not
        # be adoptable through tokenauth: this prevents a captured session id from
        # being bound to a client-supplied key without proof of possession.
        session = Sessions.new(1, self.dummy_receiver_1['id'], 1, self.dummy_receiver_1['username'], 'receiver')

        handler = self.request({'authtoken': session.id})
        yield self.assertFailure(handler.post(), errors.InvalidAuthentication)

        # The presented session must remain intact: not rotated, its DPoP binding
        # unchanged.
        self.assertIsNotNone(Sessions.get(session.id))

    @inlineCallbacks
    def test_session_use_enforces_tenant_connection_policy(self):
        # Every authenticated request must honour the session-owning tenant's
        # connection policy, not only the login/redemption step.
        session = Sessions.new(1, self.dummy_receiver_1['id'], 1, self.dummy_receiver_1['username'], 'receiver')

        State.tenants[1].cache['https_receiver'] = True
        user_handler = self.request({}, headers={'x-session': session.id},
                                        handler_cls=UserInstance)
        yield user_handler.get()

        State.tenants[1].cache['https_receiver'] = False
        user_handler = self.request({}, headers={'x-session': session.id},
                                        handler_cls=UserInstance)
        yield self.assertRaises(errors.InvalidAuthentication, user_handler.get)


    @inlineCallbacks
    def test_redemption_enforces_session_tenant_connection_policy(self):
        # A session bound to tenant 2 must be validated against tenant 2's
        # connection policy even when redeemed through a more permissive tenant.
        session = Sessions.new(2, self.dummy_receiver_1['id'], 2, self.dummy_receiver_1['username'], 'receiver')
        session.properties['authtoken'] = True

        State.tenants[1].cache['https_receiver'] = True
        State.tenants[2].cache['https_receiver'] = False

        handler = self.request({
            'authtoken': session.id,
        })

        yield self.assertFailure(handler.post(), errors.InvalidAuthentication)
