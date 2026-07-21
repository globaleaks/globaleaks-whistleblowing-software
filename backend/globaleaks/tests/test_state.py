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

    @inlineCallbacks
    def test_sendmail_basic_does_not_fetch_token(self):
        """Basic authentication does not acquire an OAuth2 token."""
        with patch('globaleaks.state.get_access_token') as mock_token, \
             patch('globaleaks.state.sendmail', return_value=succeed(True)) as mock_sendmail:
            result = yield self.state.sendmail(1, 'to@example.com', 'subject', 'body')

        self.assertTrue(result)
        self.assertEqual(mock_token.call_count, 0)
        _, kwargs = mock_sendmail.call_args
        self.assertIsNone(kwargs['oauth2_token'])

    @inlineCallbacks
    def test_sendmail_oauth2_fetches_and_forwards_token(self):
        """OAuth2 authentication acquires a token and forwards it to sendmail."""
        notification = self.state.tenants[1].cache.notification
        notification.smtp_authentication_type = 'oauth2'
        notification.smtp_oauth2_token_endpoint = 'https://login.example.com/token'
        notification.smtp_oauth2_client_id = 'client-id'
        notification.smtp_oauth2_client_secret = 'client-secret'
        notification.smtp_oauth2_scope = 'https://outlook.office365.com/.default'

        with patch('globaleaks.state.get_access_token', return_value=succeed('the-token')) as mock_token, \
             patch('globaleaks.state.sendmail', return_value=succeed(True)) as mock_sendmail:
            result = yield self.state.sendmail(1, 'to@example.com', 'subject', 'body')

        self.assertTrue(result)
        self.assertEqual(mock_token.call_count, 1)
        token_args = mock_token.call_args[0]
        self.assertEqual(token_args[1], 'https://login.example.com/token')
        self.assertEqual(token_args[2], 'client-id')
        _, kwargs = mock_sendmail.call_args
        self.assertEqual(kwargs['oauth2_token'], 'the-token')

    @inlineCallbacks
    def test_sendmail_oauth2_token_failure_returns_false(self):
        """A failure to obtain a token aborts the send and reports failure."""
        notification = self.state.tenants[1].cache.notification
        notification.smtp_authentication_type = 'oauth2'
        notification.smtp_oauth2_token_endpoint = 'https://login.example.com/token'
        notification.smtp_oauth2_client_id = 'client-id'
        notification.smtp_oauth2_client_secret = 'client-secret'
        notification.smtp_oauth2_scope = 'scope'

        with patch('globaleaks.state.get_access_token', return_value=fail(Exception("boom"))), \
             patch('globaleaks.state.sendmail', return_value=succeed(True)) as mock_sendmail:
            result = yield self.state.sendmail(1, 'to@example.com', 'subject', 'body')

        self.assertFalse(result)
        self.assertEqual(mock_sendmail.call_count, 0)

    @inlineCallbacks
    def test_sendmail_graph_uses_graph_transport(self):
        """Graph authentication delivers through the Graph transport, not SMTP."""
        notification = self.state.tenants[1].cache.notification
        notification.smtp_authentication_type = 'graph'
        notification.smtp_oauth2_token_endpoint = 'https://login.example.com/token'
        notification.smtp_oauth2_client_id = 'client-id'
        notification.smtp_oauth2_client_secret = 'client-secret'
        notification.smtp_oauth2_scope = 'https://graph.microsoft.com/.default'

        with patch('globaleaks.state.get_access_token', return_value=succeed('the-token')) as mock_token, \
             patch('globaleaks.state.graph_send_mail', return_value=succeed(True)) as mock_graph, \
             patch('globaleaks.state.sendmail', return_value=succeed(True)) as mock_sendmail:
            result = yield self.state.sendmail(1, 'to@example.com', 'subject', 'body')

        self.assertTrue(result)
        self.assertEqual(mock_token.call_count, 1)
        self.assertEqual(mock_graph.call_count, 1)
        self.assertEqual(mock_graph.call_args[0][1], 'the-token')
        self.assertEqual(mock_sendmail.call_count, 0)

    @inlineCallbacks
    def test_sendmail_smtp2_oauth2_uses_secondary_profile(self):
        """The secondary SMTP profile resolves its own OAuth2 settings."""
        notification = self.state.tenants[1].cache.notification
        notification.smtp2_enabled = True
        notification.smtp2_authentication_type = 'oauth2'
        notification.smtp2_oauth2_token_endpoint = 'https://login.example.com/token2'
        notification.smtp2_oauth2_client_id = 'client-id-2'
        notification.smtp2_oauth2_client_secret = 'client-secret-2'
        notification.smtp2_oauth2_scope = 'https://outlook.office365.com/.default'

        with patch('globaleaks.state.get_access_token', return_value=succeed('the-token-2')) as mock_token, \
             patch('globaleaks.state.sendmail', return_value=succeed(True)) as mock_sendmail:
            result = yield self.state.sendmail(1, 'to@example.com', 'subject', 'body', use_smtp2=True)

        self.assertTrue(result)
        self.assertEqual(mock_token.call_count, 1)
        self.assertEqual(mock_token.call_args[0][1], 'https://login.example.com/token2')
        _, kwargs = mock_sendmail.call_args
        self.assertEqual(kwargs['oauth2_token'], 'the-token-2')

    @inlineCallbacks
    def test_sendmail_graph_send_failure_returns_false(self):
        """A Graph delivery failure is reported without falling back to SMTP."""
        notification = self.state.tenants[1].cache.notification
        notification.smtp_authentication_type = 'graph'
        notification.smtp_oauth2_token_endpoint = 'https://login.example.com/token'
        notification.smtp_oauth2_client_id = 'client-id'
        notification.smtp_oauth2_client_secret = 'client-secret'
        notification.smtp_oauth2_scope = 'https://graph.microsoft.com/.default'

        with patch('globaleaks.state.get_access_token', return_value=succeed('the-token')), \
             patch('globaleaks.state.graph_send_mail', return_value=fail(Exception("boom"))), \
             patch('globaleaks.state.sendmail', return_value=succeed(True)) as mock_sendmail:
            result = yield self.state.sendmail(1, 'to@example.com', 'subject', 'body')

        self.assertFalse(result)
        self.assertEqual(mock_sendmail.call_count, 0)
