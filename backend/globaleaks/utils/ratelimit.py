import time
import struct

from globaleaks.utils.crypto import sha256
from globaleaks.utils.lrucache import LRUCache
from globaleaks.utils.utility import uuid4

# Struct format: 2 doubles (tokens, last_checked), 1 unsigned int (rate_limit_count)
TOKENSTATE_STRUCT = struct.Struct('ddI')

class TokenBucket:
    __slots__ = ('refill_interval', 'refill_rate', 'capacity')

    def __init__(self, limit: int, refill_interval: int, initial_burst: int = 20):
        self.refill_interval = refill_interval
        self.refill_rate = limit / refill_interval
        self.capacity = initial_burst

    def update(self, tokens: float, last_checked: float, rate_limit_count: int) -> bytes:
        now = time.monotonic()
        elapsed = now - last_checked
        tokens = min(self.capacity, tokens + elapsed * self.refill_rate)

        if tokens >= 1:
            tokens -= 1
            rate_limit_count = 0
        else:
            rate_limit_count += 1

        # Pack updated state into bytes
        return TOKENSTATE_STRUCT.pack(tokens, now, rate_limit_count)


class RateLimit(LRUCache):
    seed = uuid4().encode()

    def check(self, key: bytes, limit: int, refill_interval: int) -> int:
        hashed_key = sha256(self.seed + key)[:16]  # 16 bytes hash key

        if hashed_key not in self:
            now = time.monotonic()
            packed = TOKENSTATE_STRUCT.pack(float(limit), now, 0)
            self[hashed_key] = packed

        packed = self[hashed_key]
        tokens, last_checked, rate_limit_count = TOKENSTATE_STRUCT.unpack(packed)

        bucket = TokenBucket(limit, refill_interval)
        new_packed = bucket.update(tokens, last_checked, rate_limit_count)
        self[hashed_key] = new_packed

        _, _, new_rate_limit_count = TOKENSTATE_STRUCT.unpack(new_packed)
        return new_rate_limit_count
