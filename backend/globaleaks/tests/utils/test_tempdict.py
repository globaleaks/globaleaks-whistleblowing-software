from globaleaks.tests import helpers
from globaleaks.utils.tempdict import TempDict


class TestObject(object):
    callbacks_count = 0

    def __init__(self, obj_id):
        self.id = obj_id

    def expireCallback(self):
        TestObject.callbacks_count += 1


class TestTempDict(helpers.TestGL):
    def test_timeout(self):
        timeout = 1337

        xxx = TempDict(timeout=timeout)

        for x in range(1, timeout + 1):
            xxx[x] = TestObject(x)
            self.assertEqual(len(xxx), x)
            self.test_reactor.advance(1)

        for x in range(1, timeout + 1):
            self.assertEqual(len(xxx), timeout - x)
            self.test_reactor.advance(1)

        self.assertEqual(len(xxx), 0)

        self.assertEqual(TestObject.callbacks_count, timeout)

    def test_max_size(self):
        max_size = 10

        xxx = TempDict(timeout=1337, max_size=max_size)

        # A bare value (no expireCallback) keeps eviction from touching the
        # shared TestObject counter; timer cancellation is asserted via the
        # reactor below instead.
        class Value:
            pass

        # Insert well beyond the cap; the store must never exceed max_size.
        for x in range(1, 3 * max_size + 1):
            xxx[x] = Value()
            self.assertLessEqual(len(xxx), max_size)

        self.assertEqual(len(xxx), max_size)

        # The most recent max_size entries are retained; the oldest are evicted.
        self.assertEqual(sorted(xxx.keys()),
                         list(range(2 * max_size + 1, 3 * max_size + 1)))

        # Evicted entries' expiration timers are cancelled rather than leaked:
        # the reactor holds exactly one pending delayed call per live entry.
        self.assertEqual(len(self.test_reactor.getDelayedCalls()), max_size)
