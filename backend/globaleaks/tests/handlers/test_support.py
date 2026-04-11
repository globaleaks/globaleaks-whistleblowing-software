from globaleaks import models
from globaleaks.handlers import support
from globaleaks.tests import helpers
from twisted.internet.defer import inlineCallbacks


class TestSupportHandler(helpers.TestHandlerWithPopulatedDB):
    _handler = support.SupportHandler

    def test_generate_support_email(self):
        mail_address = "user.name@example.com"
        hostname = "globaleaks.org"
        request_text = "Visit http://example.com and contact user.name@example.com"

        result = support.generate_support_email(mail_address, hostname, request_text)

        expected = (
            "From: user[.]name[@]example[.]com\n\n"
            "Site: globaleaks.org\n\n"
            "Request:\nVisit http[://]example[.]com and contact user[.]name[@]example[.]com"
        )

        self.assertEqual(result, expected)

    @inlineCallbacks
    def test_post(self):
        request = {
            'mail_address': 'giovanni.pellerano@globaleaks.org',
            'text': 'The email is to ask support for...'
        }

        yield self.test_model_count(models.Mail, 0)
        handler = self.request(request)
        yield handler.post()
        self.assertEqual(handler.request.code, 200)
        yield self.test_model_count(models.Mail, 1)
