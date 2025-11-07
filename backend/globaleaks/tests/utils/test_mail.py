from email import message_from_bytes
from twisted.internet.defer import Deferred, fail, succeed
from twisted.trial import unittest
from twisted.mail.smtp import ESMTPSenderFactory
from unittest.mock import patch

from globaleaks.utils.mail import MIME_mail_build, sendmail


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

    @patch("globaleaks.utils.mail.TCP4ClientEndpoint.connect", return_value=succeed(None))
    @patch("globaleaks.utils.mail.ESMTPSenderFactory")
    def test_sendmail_success(self, mock_factory, mock_connect):
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

    @patch("globaleaks.utils.mail.TCP4ClientEndpoint.connect", side_effect=lambda *args, **kwargs: fail(Exception("Connection Failed")))
    def test_sendmail_failure(self, mock_connect):
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

    @patch("globaleaks.utils.mail.TCP4ClientEndpoint.connect", return_value=succeed(None))
    @patch("globaleaks.utils.mail.tls.TLSMemoryBIOFactory")
    def test_sendmail_ssl_security(self, mock_tls, mock_connect):
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

    @patch("globaleaks.utils.mail.SOCKS5ClientEndpoint.connect", return_value=succeed(None))
    def test_sendmail_anonymized(self, mock_socks_connect):
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
