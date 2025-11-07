import time

from twisted.trial import unittest

from globaleaks.utils.crypto import sha256
from globaleaks.utils.ratelimit import TokenBucket, RateLimit, TOKENSTATE_STRUCT

class TokenBucketTests(unittest.TestCase):
    def test_allow_initial_and_refill(self):
        bucket = TokenBucket(limit=5, refill_interval=1, initial_burst=2)
        now = time.monotonic()

        # Pack initial state: tokens=2 (float), last_checked=now (double), rate_limit_count=0 (uint)
        state = TOKENSTATE_STRUCT.pack(2.0, now, 0)

        # Unpack, update, repack for each call
        tokens, last_checked, rate_limit_count = TOKENSTATE_STRUCT.unpack(state)
        state = bucket.update(tokens, last_checked, rate_limit_count)
        _, _, rate_limit_count = TOKENSTATE_STRUCT.unpack(state)
        self.assertEqual(rate_limit_count, 0)

        tokens, last_checked, rate_limit_count = TOKENSTATE_STRUCT.unpack(state)
        state = bucket.update(tokens, last_checked, rate_limit_count)
        _, _, rate_limit_count = TOKENSTATE_STRUCT.unpack(state)
        self.assertEqual(rate_limit_count, 0)

        tokens, last_checked, rate_limit_count = TOKENSTATE_STRUCT.unpack(state)
        state = bucket.update(tokens, last_checked, rate_limit_count)
        _, _, rate_limit_count = TOKENSTATE_STRUCT.unpack(state)
        self.assertEqual(rate_limit_count, 1)

        # Simulate 1 second elapsed by adjusting last_checked backward
        tokens, last_checked, rate_limit_count = TOKENSTATE_STRUCT.unpack(state)
        last_checked -= 1
        state = TOKENSTATE_STRUCT.pack(tokens, last_checked, rate_limit_count)

        tokens, last_checked, rate_limit_count = TOKENSTATE_STRUCT.unpack(state)
        state = bucket.update(tokens, last_checked, rate_limit_count)
        _, _, rate_limit_count = TOKENSTATE_STRUCT.unpack(state)
        self.assertEqual(rate_limit_count, 0)

    def test_tokens_do_not_exceed_capacity(self):
        bucket = TokenBucket(limit=10, refill_interval=1, initial_burst=5)
        now = time.monotonic()

        # tokens=5, last_checked=now-1, rate_limit_count=0
        state = TOKENSTATE_STRUCT.pack(5.0, now - 1, 0)

        tokens, last_checked, rate_limit_count = TOKENSTATE_STRUCT.unpack(state)
        updated = bucket.update(tokens, last_checked, rate_limit_count)

        tokens, _, rate_limit_count = TOKENSTATE_STRUCT.unpack(updated)

        self.assertLessEqual(tokens, bucket.capacity)
        self.assertEqual(rate_limit_count, 0)


class RateLimitTests(unittest.TestCase):
    def test_check_resets_and_increments(self):
        rate_limit = RateLimit(1_000_000)
        key = b'testkey'
        limit = 2
        refill_interval = 1

        hashed_key = sha256(rate_limit.seed + key)[:16]

        # First two checks: rate_limit_count == 0 (allowed)
        self.assertEqual(rate_limit.check(key, limit, refill_interval), 0)
        self.assertEqual(rate_limit.check(key, limit, refill_interval), 0)

        # Force state to zero tokens manually:
        now = time.monotonic()
        zero_tokens_state = TOKENSTATE_STRUCT.pack(0.0, now, 0)
        rate_limit[hashed_key] = zero_tokens_state

        # Subsequent checks increment rate_limit_count
        self.assertEqual(rate_limit.check(key, limit, refill_interval), 1)
        self.assertEqual(rate_limit.check(key, limit, refill_interval), 2)
