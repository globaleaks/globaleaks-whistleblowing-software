from unittest.mock import patch

from twisted.internet.defer import inlineCallbacks, succeed, fail

from globaleaks.tests import helpers


class TestStateSendmail(helpers.TestGL):
    @inlineCallbacks
    def setUp(self):
        yield helpers.TestGL.setUp(self)
        self.state.settings.disable_notifications = False

    def tearDown(self):
        self.state.settings.disable_notifications = True
        helpers.TestGL.tearDown(self)

    def configure_modern_auth(self, auth_type, prefix='smtp',
                              endpoint='https://login.example.com/token',
                              scope='scope'):
        """Set the modern authentication settings on the given SMTP profile."""
        notification = self.state.tenants[1].cache.notification
        if prefix == 'smtp2':
            notification.smtp2_enabled = True
        setattr(notification, prefix + '_authentication_type', auth_type)
        setattr(notification, prefix + '_oauth2_token_endpoint', endpoint)
        setattr(notification, prefix + '_oauth2_client_id', 'client-id')
        setattr(notification, prefix + '_oauth2_client_secret', 'client-secret')
        setattr(notification, prefix + '_oauth2_scope', scope)

    @inlineCallbacks
    def test_sendmail_basic_does_not_fetch_token(self):
        """Basic authentication does not acquire an OAuth2 token."""
        with patch('globaleaks.state.get_access_token') as mock_token, \
             patch('globaleaks.state.sendmail', return_value=succeed(True)) as mock_sendmail:
            result = yield self.state.sendmail(1, 'to@example.com', 'subject', 'body')

        self.assertTrue(result)
        self.assertEqual(mock_token.call_count, 0)
        self.assertIsNone(mock_sendmail.call_args.kwargs['oauth2_token'])

    @inlineCallbacks
    def test_sendmail_oauth2_fetches_and_forwards_token(self):
        """OAuth2 authentication acquires a token and forwards it to sendmail."""
        self.configure_modern_auth('oauth2')

        with patch('globaleaks.state.get_access_token', return_value=succeed('the-token')) as mock_token, \
             patch('globaleaks.state.sendmail', return_value=succeed(True)) as mock_sendmail:
            result = yield self.state.sendmail(1, 'to@example.com', 'subject', 'body')

        self.assertTrue(result)
        self.assertEqual(mock_token.call_count, 1)
        self.assertEqual(mock_token.call_args[0][1], 'https://login.example.com/token')
        self.assertEqual(mock_sendmail.call_args.kwargs['oauth2_token'], 'the-token')

    @inlineCallbacks
    def test_sendmail_oauth2_token_failure_returns_false(self):
        """A failure to obtain a token aborts the send and reports failure."""
        self.configure_modern_auth('oauth2')

        with patch('globaleaks.state.get_access_token', return_value=fail(Exception("boom"))), \
             patch('globaleaks.state.sendmail', return_value=succeed(True)) as mock_sendmail:
            result = yield self.state.sendmail(1, 'to@example.com', 'subject', 'body')

        self.assertFalse(result)
        self.assertEqual(mock_sendmail.call_count, 0)
    @inlineCallbacks
    def test_sendmail_smtp2_oauth2_uses_secondary_profile(self):
        """The secondary SMTP profile resolves its own OAuth2 settings."""
        self.configure_modern_auth('oauth2', prefix='smtp2',
                                   endpoint='https://login.example.com/token2')

        with patch('globaleaks.state.get_access_token', return_value=succeed('the-token-2')) as mock_token, \
             patch('globaleaks.state.sendmail', return_value=succeed(True)) as mock_sendmail:
            result = yield self.state.sendmail(1, 'to@example.com', 'subject', 'body', use_smtp2=True)

        self.assertTrue(result)
        self.assertEqual(mock_token.call_count, 1)
        self.assertEqual(mock_token.call_args[0][1], 'https://login.example.com/token2')
        self.assertEqual(mock_sendmail.call_args.kwargs['oauth2_token'], 'the-token-2')