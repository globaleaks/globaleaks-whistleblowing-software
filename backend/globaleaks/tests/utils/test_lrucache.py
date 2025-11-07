from twisted.trial import unittest

from globaleaks.utils.lrucache import LRUCache

class TestLRUCache(unittest.TestCase):
    def test_insert_and_retrieve(self):
        cache = LRUCache(max_size=3)
        cache['a'] = 1
        cache['b'] = 2
        cache['c'] = 3
        self.assertEqual(cache['a'], 1)
        self.assertEqual(cache['b'], 2)
        self.assertEqual(cache['c'], 3)

    def test_lru_eviction(self):
        cache = LRUCache(max_size=3)
        cache['a'] = 1
        cache['b'] = 2
        cache['c'] = 3
        # Access 'a' and 'b' so 'c' is least recently used
        _ = cache['a']
        _ = cache['b']
        # Insert new item, should evict 'c'
        cache['d'] = 4
        self.assertNotIn('c', cache)
        self.assertIn('a', cache)
        self.assertIn('b', cache)
        self.assertIn('d', cache)

    def test_update_moves_to_end(self):
        cache = LRUCache(max_size=3)
        cache['a'] = 1
        cache['b'] = 2
        cache['c'] = 3
        # Update 'a' should move it to the end (most recently used)
        cache['a'] = 10
        # Insert new item, should evict 'b' as it is least recently used now
        cache['d'] = 4
        self.assertNotIn('b', cache)
        self.assertIn('a', cache)
        self.assertIn('c', cache)
        self.assertIn('d', cache)
        self.assertEqual(cache['a'], 10)

    def test_access_non_existent_key_raises(self):
        cache = LRUCache(max_size=2)
        cache['a'] = 1
        with self.assertRaises(KeyError):
            _ = cache['nonexistent']

