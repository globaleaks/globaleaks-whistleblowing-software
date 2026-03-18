import re
import uuid
from datetime import datetime
from twisted.trial import unittest

from globaleaks.utils import defang


class TestUtility(unittest.TestCase):
    def test_defang_invisible_chars(self):
        text = "http://exam\u200bple.com/path\u200cto/file.html\nuser.name@exam\u200bple.com"
        expected = "[http://]example[.]com/pathto/file[.]html\nuser[.]name[@]example[.]com"
        self.assertEqual(defang.defang_text(text), expected)


    def test_defang_uris_strict(self):
        text = "Visit http://example.com/path.to/file.html and https://sub.domain.com"
        expected = "Visit [http://]example[.]com/path[.]to/file[.]html and [https://]sub[.]domain[.]com"
        self.assertEqual(defang.defang_uris(text), expected)


    def test_defang_emails_strict(self):
        text = "Contact me at user.name@example.com"
        expected = "Contact me at user[.]name[@]example[.]com"
        self.assertEqual(defang.defang_emails(text), expected)


    def test_defang_text_combined(self):
        text = """
        Hello, visit http://example.com/path.to/file.html
        and contact user.name@example.com
        """
        expected = """
        Hello, visit [http://]example[.]com/path[.]to/file[.]html
        and contact user[.]name[@]example[.]com
        """
        self.assertEqual(defang.defang_text(text), expected)


    def test_defang_text_mixed_evasion(self):
        text = "Link: http://example.com/path(1).html?x=1.2\u200b and mail: test.user+spam@example.co.uk"
        expected = "Link: [http://]example[.]com/path(1)[.]html?x=1[.]2 and mail: test[.]user+spam[@]example[.]co[.]uk"
        self.assertEqual(defang.defang_text(text), expected)


    def test_defang_text_no_links_or_emails(self):
        text = "This is a safe text with no links or emails."
        self.assertEqual(defang.defang_text(text), text)

    def test_defang_idempotent(self):
       text = "Visit http://exámple.com and email user.name@exámple.com"

       first_pass = defang.defang_text(text)
       second_pass = defang.defang_text(first_pass)

       self.assertEqual(first_pass, second_pass)

