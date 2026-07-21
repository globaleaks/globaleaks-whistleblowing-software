from email import message_from_bytes
from twisted.internet.defer import Deferred, fail, succeed
from twisted.test.proto_helpers import MemoryReactorClock
from twisted.trial import unittest
from twisted.mail.smtp import ESMTPSenderFactory
from unittest.mock import patch

from globaleaks.utils.mail import (
    MIME_mail_build,
    sendmail,
    XOAuth2Authenticator,
    XOAuth2ESMTPSender,
)


class TestMailUtils(unittest.TestCase):
    def test_mime_mail_build(self):
        """Test that MIME_mail_build constructs a valid email."""
        mail = MIME_mail_build("Sender", "sender@example.com", "Receiver", "receiver@example.com", "Test Subject", "Test Body")
        mail_content = message_from_bytes(mail.getvalue())

        self.assertEqual(mail_content["From"], "=?utf-8?q?Sender?= <sender@example.com>")
        self.assertEqual(mail_content["To"], "=?utf-8?q?Receiver?= <receiver@example.com>")
        self.assertEqual(mail_content["Subject"], "=?utf-8?q?Test_Subject?=")
        self.assertEqual(mail_content.get_payload()[0].get_payload(decode=True).decode(), "Test Body")

    def test_mime_mail_build_non_ascii(self):
        """Test that MIME_mail_build correctly encodes non-ASCII characters."""
        mail = MIME_mail_build("Sènder", "sender@example.com", "Réceiver", "receiver@example.com", "Tëst Subject", "Bødÿ")
        mail_content = message_from_bytes(mail.getvalue())

        self.assertIn("=?utf-8?", mail_content["From"])
        self.assertIn("=?utf-8?", mail_content["To"])
        self.assertIn("=?utf-8?", mail_content["Subject"])
        self.assertEqual(mail_content.get_payload()[0].get_payload(decode=True).decode(), "Bødÿ")

    @patch("globaleaks.utils.mail.reactor", new_callable=lambda: MemoryReactorClock())
    @patch("globaleaks.utils.mail.TCP4ClientEndpoint.connect", return_value=succeed(None))
    @patch("globaleaks.utils.mail.ESMTPSenderFactory")
    def test_sendmail_success(self, mock_factory, mock_connect, mock_reactor):
        """Test that sendmail initiates an SMTP connection correctly and handles success."""

        mock_factory.return_value = ESMTPSenderFactory(
            username="user".encode(),
            password="pass".encode(),
            fromEmail="sender@example.com",
            toEmail=["receiver@example.com"],  # Should be a list
            file=MIME_mail_build("Sender", "sender@example.com", "Receiver", "receiver@example.com", "Test Subject", "Test Body"),
            deferred=Deferred()
        )

        d = sendmail(tid=1,
                     smtp_host="smtp.example.com",
                     smtp_port=587,
                     security="TLS",
                     authentication=True,
                     username="user",
                     password="pass",
                     from_name="Sender",
                     from_address="sender@example.com",
                     to_address="receiver@example.com",
                     subject="Test Subject",
                     body="Test Body",
                     anonymize=False)

        self.assertIsInstance(d, Deferred)
        self.assertEqual(mock_connect.call_count, 1)

    @patch("globaleaks.utils.mail.reactor", new_callable=lambda: MemoryReactorClock())
    @patch("globaleaks.utils.mail.TCP4ClientEndpoint.connect", side_effect=lambda *args, **kwargs: fail(Exception("Connection Failed")))
    def test_sendmail_failure(self, mock_connect, mock_reactor):
        """Test that sendmail handles failures correctly."""

        d = sendmail(tid=1,
                     smtp_host="smtp.example.com",
                     smtp_port=587,
                     security="TLS",
                     authentication=True,
                     username="user",
                     password="pass",
                     from_name="Sender",
                     from_address="sender@example.com",
                     to_address="receiver@example.com",
                     subject="Test Subject",
                     body="Test Body",
                     anonymize=False)

        def callback(result):
            self.assertFalse(result)

        d.addCallback(callback)
        self.assertEqual(mock_connect.call_count, 1)

    @patch("globaleaks.utils.mail.reactor", new_callable=lambda: MemoryReactorClock())
    @patch("globaleaks.utils.mail.TCP4ClientEndpoint.connect", return_value=succeed(None))
    @patch("globaleaks.utils.mail.tls.TLSMemoryBIOFactory")
    def test_sendmail_ssl_security(self, mock_tls, mock_connect, mock_reactor):
        """Test sendmail with SSL security option."""
        d = sendmail(tid=1,
                     smtp_host="smtp.example.com",
                     smtp_port=465,
                     security="SSL",
                     authentication=True,
                     username="user",
                     password="pass",
                     from_name="Sender",
                     from_address="sender@example.com",
                     to_address="receiver@example.com",
                     subject="Test Subject",
                     body="Test Body",
                     anonymize=False)

        self.assertIsInstance(d, Deferred)
        self.assertEqual(mock_tls.call_count, 1)

    @patch("globaleaks.utils.mail.reactor", new_callable=lambda: MemoryReactorClock())
    @patch("globaleaks.utils.mail.SOCKS5ClientEndpoint.connect", return_value=succeed(None))
    def test_sendmail_anonymized(self, mock_socks_connect, mock_reactor):
        """Test sendmail with anonymized SOCKS5 proxy connection."""
        d = sendmail(tid="test_tid",
                     smtp_host="smtp.example.com",
                     smtp_port=587,
                     security="TLS",
                     authentication=True,
                     username="user",
                     password="pass",
                     from_name="Sender",
                     from_address="sender@example.com",
                     to_address="receiver@example.com",
                     subject="Test Subject",
                     body="Test Body",
                     anonymize=True)

        self.assertIsInstance(d, Deferred)
        self.assertEqual(mock_socks_connect.call_count, 1)

    def test_xoauth2_authenticator_name(self):
        """Test that the XOAUTH2 authenticator advertises the XOAUTH2 mechanism."""
        auth = XOAuth2Authenticator(b"user@example.com")
        self.assertEqual(auth.getName(), b"XOAUTH2")

    def test_xoauth2_authenticator_challenge_response(self):
        """Test that the XOAUTH2 authenticator builds the SASL bearer string."""
        auth = XOAuth2Authenticator(b"user@example.com")
        response = auth.challengeResponse(b"the-token")
        self.assertEqual(response, b"user=user@example.com\x01auth=Bearer the-token\x01\x01")

    def test_xoauth2_sender_registers_only_xoauth2(self):
        """Test that the XOAUTH2 sender offers no password-based mechanism."""
        sender = XOAuth2ESMTPSender(b"user@example.com", b"the-token", None, b"localhost")
        names = [a.getName() for a in sender.authenticators]
        self.assertEqual(names, [b"XOAUTH2"])

    @patch("globaleaks.utils.mail.reactor", new_callable=lambda: MemoryReactorClock())
    @patch("globaleaks.utils.mail.TCP4ClientEndpoint.connect", return_value=succeed(None))
    @patch("globaleaks.utils.mail.XOAuth2ESMTPSenderFactory")
    def test_sendmail_oauth2(self, mock_factory, mock_connect, mock_reactor):
        """Test that sendmail uses the XOAUTH2 factory when given a token."""
        d = sendmail(tid=1,
                     smtp_host="smtp.example.com",
                     smtp_port=587,
                     security="TLS",
                     authentication=True,
                     username="user@example.com",
                     password="",
                     from_name="Sender",
                     from_address="sender@example.com",
                     to_address="receiver@example.com",
                     subject="Test Subject",
                     body="Test Body",
                     anonymize=False,
                     oauth2_token="the-token")

        self.assertIsInstance(d, Deferred)
        self.assertEqual(mock_factory.call_count, 1)
        args, kwargs = mock_factory.call_args
        self.assertEqual(args[0], b"user@example.com")
        self.assertEqual(args[1], b"the-token")
        self.assertEqual(mock_connect.call_count, 1)

    @patch("globaleaks.utils.mail.TCP4ClientEndpoint.connect", side_effect=Exception("Unexpected error"))
    def test_sendmail_unexpected_exception(self, mock_connect):
        """Test sendmail handling of unexpected exceptions."""
        d = sendmail(tid=1,
                     smtp_host="smtp.example.com",
                     smtp_port=587,
                     security="TLS",
                     authentication=True,
                     username="user",
                     password="pass",
                     from_name="Sender",
                     from_address="sender@example.com",
                     to_address="receiver@example.com",
                     subject="Test Subject",
                     body="Test Body",
                     anonymize=False)

        def callback(result):
            self.assertFalse(result)

        d.addCallback(callback)
        self.assertEqual(mock_connect.call_count, 1)
