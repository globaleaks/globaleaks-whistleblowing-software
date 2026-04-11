from twisted.trial import unittest
from globaleaks.utils import defang

# Test cases: (input_text, expected_output)
texts = [
    # Basic https URL
    ("https://google.com", "https[://]google[.]com"),

    # FTP URL with single slash
    ("ftp:/server.com", "ftp[:/]server[.]com"),

    # Email
    ("user@example.com", "user[@]example[.]com"),

    # Already defanged URL
    ("https[://]already[.]defanged.com", "https[://]already[.]defanged[.]com"),

    # Text with multiple URLs
    ("Check https://site.com and ftp:/files.net", "Check https[://]site[.]com and ftp[:/]files[.]net"),

    # Text with invisible characters
    ("hidden\u200bchar\u200chere", "hiddencharhere"),

    # Text with existing defanged sequences
    ("avoid [://] double [.] defang", "avoid [://] double [.] defang"),

    # Colon-heavy text
    ("time: 12:30", "time[:] 12[:]30"),

    # Complex mix
    ("ftp:/user@domain.com:21/path", "ftp[:/]user[@]domain[.]com[:]21/path"),
]

class TestDefang(unittest.TestCase):
    def test_defang(self):
        for text, expected in texts:
            with self.subTest(text=text):
                # Test defang correctness
                self.assertEqual(defang.defang(text), expected)

                # Test idempotence
                self.assertEqual(defang.defang(expected), expected)
