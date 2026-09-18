from twisted.internet import reactor
from twisted.internet.error import AlreadyCalled, AlreadyCancelled


class TempDict(dict):
    reactor = reactor
    reset_timeout_on_access = True

    def __init__(self, timeout=300, max_size=0):
        self.timeout = timeout
        self.max_size = max_size
        dict.__init__(self)

    def __setitem__(self, key, value):
        # When a maximum size is configured, evict the oldest entry before
        # inserting a new one so that neither the store nor the reactor's
        # delayed-call queue can grow without bound. Eviction is routed through
        # __delitem__ so the evicted entry's expiration timer is cancelled
        # rather than leaked. dict preserves insertion order, so the first key
        # returned by the iterator is the oldest.
        if self.max_size and key not in self and len(self) >= self.max_size:
            self.__delitem__(next(iter(self)))

        value.expireCall = self.reactor.callLater(self.timeout, self.__delitem__, key)
        return dict.__setitem__(self, key, value)

    def __delitem__(self, key):
        value = self.pop(key, None)

        if value:
            try:
                value.expireCall.cancel()  # pylint: disable=no-member
            except (AlreadyCalled, AlreadyCancelled):
                # The only exceptions DelayedCall.cancel() can raise (per Twisted docs).
                pass

            if hasattr(value, 'expireCallback') and value.expireCallback:
                value.expireCallback()

    def reset_timeout(self, value):
        if value and value.expireCall is not None:
            try:
                value.expireCall.reset(self.timeout)
            except (AlreadyCalled, AlreadyCancelled):
                # Same as DelayedCall.cancel(): these are the only documented raises.
                pass

    def get(self, key):
        value = dict.get(self, key)

        if self.reset_timeout_on_access:
            self.reset_timeout(value)

        return value
