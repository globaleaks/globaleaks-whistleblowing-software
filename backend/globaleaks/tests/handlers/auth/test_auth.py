from twisted.internet.defer import inlineCallbacks

from globaleaks.handlers import auth
from globaleaks.handlers.user import UserInstance
from globaleaks.handlers.whistleblower.wbtip import WBTipInstance
from globaleaks.rest import errors
from globaleaks.sessions import Sessions
from globaleaks.state import State
from globaleaks.tests import helpers


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

    #@inlineCallbacks
    #def test_successful_role_switch(self):
    #    handler = self.request({
    #        'tid': 1,
    #        'username': 'admin',
    #        'password': helpers.VALID_KEY,
    #        'authcode': ''
    #    })
    #
    #    response = yield handler.post()
    #
    #    role_switch_handler = self.request({},
    #                                       headers={'x-session': response['id']},
    #                                       handler_cls=auth.RoleAuthSwitchHandler)
    #
    #    response = yield role_switch_handler.get('custodian')
    #    self.assertTrue('redirect' in response)

    @inlineCallbacks
    def test_unsuccessful_role_switch(self):
        handler = self.request({
            'tid': 1,
            'username': 'admin',
            'password': helpers.VALID_KEY,
            'authcode': ''
        })

        response = yield handler.post()

        role_switch_handler = self.request({},
                                           headers={'x-session': response['id']},
                                           handler_cls=auth.RoleAuthSwitchHandler)

        yield self.assertFailure(role_switch_handler.get('receiver'), errors.InvalidAuthentication)

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
        yield self.assertFailure(handler.post(), errors.TorNetworkRequired)

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
        yield self.assertFailure(handler.post(), errors.AccessLocationInvalid)

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
            'receipt': self.dummySubmission['receipt']
        })
        handler.request.client_using_tor = True
        response = yield handler.post()
        self.assertTrue('id' in response)

    @inlineCallbacks
    def test_accept_whistleblower_login_in_https(self):
        yield self.perform_full_submission_actions()
        handler = self.request({'receipt': self.dummySubmission['receipt']})
        State.tenants[1].cache['https_whistleblower'] = True
        response = yield handler.post()
        self.assertTrue('id' in response)

    @inlineCallbacks
    def test_deny_whistleblower_login_in_https(self):
        yield self.perform_full_submission_actions()
        handler = self.request({'receipt': self.dummySubmission['receipt']})
        State.tenants[1].cache['https_whistleblower'] = False
        yield self.assertFailure(handler.post(), errors.TorNetworkRequired)

    @inlineCallbacks
    def test_single_session_per_whistleblower(self):
        """
        Asserts that the first_id is dropped from Sessions and requests
        using that session id are rejected
        """
        yield self.perform_full_submission_actions()

        handler = self.request({
            'receipt': self.dummySubmission['receipt']
        })

        handler.request.client_using_tor = True
        response = yield handler.post()
        first_id = response['id']

        wbtip_handler = self.request(headers={'x-session': first_id},
                                     handler_cls=WBTipInstance)
        yield wbtip_handler.get()

        handler = self.request({
            'receipt': self.dummySubmission['receipt']
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

        self.assertEqual(handler.request.responseHeaders.hasHeader("Clear-Site-Data"), True)
        self.assertEqual(handler.request.responseHeaders.getRawHeaders("Clear-Site-Data")[0], '"*"')

    @inlineCallbacks
    def test_successful_whistleblower_logout(self):
        self._handler = auth.ReceiptAuthHandler

        yield self.perform_full_submission_actions()

        handler = self.request({
            'receipt': self.dummySubmission['receipt']
        })

        handler.request.client_using_tor = True

        response = yield handler.post()
        self.assertTrue(handler.session is None)
        self.assertTrue('id' in response)

        self._handler = auth.SessionHandler

        # Logout
        handler = self.request({}, headers={'x-session': response['id']})
        yield handler.delete()

        self.assertEqual(handler.request.responseHeaders.hasHeader("Clear-Site-Data"), True)
        self.assertEqual(handler.request.responseHeaders.getRawHeaders("Clear-Site-Data")[0], '"*"')


class TestTokenAuth(helpers.TestHandlerWithPopulatedDB):
    _handler = auth.TokenAuthHandler

    # since all logins for roles admin, receiver and custodian happen
    # in the same way, the following tests are performed on the recipient user.

    @inlineCallbacks
    def setUp(self):
        yield helpers.TestHandlerWithPopulatedDB.setUp(self)
        session = Sessions.new(1, self.dummyReceiver_1['id'], 1, 'receiver')
        self.authtoken = session.id

    @inlineCallbacks
    def test_successful_login(self):
        handler = self.request({
            'authtoken': self.authtoken,
        })

        response = yield handler.post()
        self.assertTrue('id' in response)
