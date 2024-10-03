# -*- coding: utf-8 -*-
from twisted.internet import reactor


class TempDict(dict):
    reactor = reactor
    reset_timeout_on_access = True

    def __init__(self, timeout=300):
        self.timeout = timeout
        dict.__init__(self)

    def __setitem__(self, key, value):
        value.expireCall = self.reactor.callLater(self.timeout, self.__delitem__, key)
        return dict.__setitem__(self, key, value)

    def __delitem__(self, key):
        value = self.pop(key, None)

        if value:
            try:
                value.expireCall.cancel()  # pylint: disable=no-member
            except:
                pass

            if hasattr(value, 'expireCallback') and value.expireCallback:
                value.expireCallback()

    def reset_timeout(self, value):
        if value and value.expireCall is not None:
            try:
                value.expireCall.reset(self.timeout)
            except:
                pass

    def get(self, key):
        value = dict.get(self, key)

        if self.reset_timeout_on_access:
            self.reset_timeout(value)

        return value
