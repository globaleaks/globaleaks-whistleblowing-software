from twisted.trial import unittest
from globaleaks.rest.cache import Cache

class TestCache(unittest.TestCase):
    def setUp(self):
        Cache.invalidate() # Ensure cache is empty before each test

    def test_set_and_get_cache(self):
        Cache.set(1, b"/test", "en", b"application/json", "cached_response")
        result = Cache.get(1, b"/test", "en")
        self.assertEqual(result, (b"application/json", "cached_response"))

    def test_get_nonexistent_cache(self):
        result = Cache.get(1, b"/nonexistent", "en")
        self.assertIsNone(result)

    def test_cache_invalidates_specific_tid(self):
        Cache.set(1, b"/test", "en", b"application/json", "cached_response")
        Cache.set(2, b"/test", "en", b"application/json", "cached_response2")

        Cache.invalidate(2)
        self.assertIsNone(Cache.get(2, b"/test", "en"))
        self.assertIsNotNone(Cache.get(1, b"/test", "en"))

    def test_cache_invalidates_all(self):
        Cache.set(1, b"/test", "en", b"application/json", "cached_response")
        Cache.set(2, b"/test", "en", b"application/json", "cached_response2")

        Cache.invalidate(1)
        self.assertIsNone(Cache.get(1, b"/test", "en"))
        self.assertIsNone(Cache.get(2, b"/test", "en"))
