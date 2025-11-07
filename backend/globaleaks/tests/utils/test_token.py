from twisted.internet.defer import inlineCallbacks

from globaleaks.tests import helpers


class TestToken(helpers.TestGL):
    @inlineCallbacks
    def setUp(self):
        yield helpers.TestGL.setUp(self)

        self.state.tokens.clear()

    def test_tokens_garbage_collected(self):
        self.assertTrue(len(self.state.tokens) == 0)

        for _ in range(100):
            self.state.tokens.new(1)

        self.assertTrue(len(self.state.tokens) == 100)

        self.test_reactor.advance(self.state.tokens.timeout + 1)

        self.assertTrue(len(self.state.tokens) == 0)
