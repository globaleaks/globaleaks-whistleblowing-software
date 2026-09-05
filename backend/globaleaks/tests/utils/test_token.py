from twisted.internet.defer import inlineCallbacks

from globaleaks.rest import errors
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

    def test_a_token_is_served_with_its_id_and_salt(self):
        token = self.state.tokens.new(1)

        serialized = token.serialize()

        self.assertEqual(serialized['id'], token.id.decode())
        self.assertEqual(serialized['salt'], token.salt.decode())
        self.assertEqual(serialized['creation_date'], token.creation_date)
        self.assertIsNone(token.session)

    def test_a_token_remembers_the_session_it_is_issued_to(self):
        token = self.state.tokens.new(1, session='session')

        self.assertEqual(token.session, 'session')
        self.assertIs(self.state.tokens.get(token.id), token)

    def test_an_unknown_token_is_refused(self):
        self.assertRaises(errors.InvalidPoW, self.state.tokens.get, b'unknown')
        self.assertRaises(errors.InvalidPoW, self.state.tokens.validate, b'unknown:1')
        self.assertRaises(errors.InvalidPoW, self.state.tokens.validate, b'malformed')

    def test_a_solved_token_is_consumed(self):
        answer = helpers.get_token()

        token = self.state.tokens.validate(answer)

        self.assertEqual(token.id, helpers.TOKEN)
        self.assertEqual(len(self.state.tokens), 0)
        self.assertRaises(errors.InvalidPoW, self.state.tokens.validate, answer)

    def test_a_wrong_answer_is_refused_and_consumes_the_token(self):
        helpers.get_token()

        self.assertRaises(errors.InvalidPoW, self.state.tokens.validate, helpers.TOKEN + b':1')
        self.assertEqual(len(self.state.tokens), 0)
