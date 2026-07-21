import json

from twisted.internet.defer import inlineCallbacks, succeed
from twisted.trial import unittest

from unittest.mock import patch

from globaleaks.utils import oauth2

TOKEN_ENDPOINT = 'https://login.example.org/token'


class FakeResponse:
    def __init__(self, code):
        self.code = code


class FakeAgent:
    """A minimal agent recording how many requests it received."""
    def __init__(self, code=200):
        self.code = code
        self.calls = 0

    def request(self, method, url, headers, producer):
        self.calls += 1
        self.method = method
        self.url = url
        return succeed(FakeResponse(self.code))


def token_body(**kwargs):
    payload = {'access_token': 'a-token', 'expires_in': 3600}
    payload.update(kwargs)
    return json.dumps(payload).encode()


class TestOAuth2(unittest.TestCase):
    def setUp(self):
        oauth2._token_cache.clear()

    @inlineCallbacks
    def test_get_access_token(self):
        agent = FakeAgent()
        with patch.object(oauth2, 'readBody', side_effect=lambda r: succeed(token_body())):
            token = yield oauth2.get_access_token(agent, TOKEN_ENDPOINT, 'id', 'secret', 'scope')

        self.assertEqual(token, 'a-token')
        self.assertEqual(agent.calls, 1)
        self.assertEqual(agent.method, b'POST')

    @inlineCallbacks
    def test_token_is_cached(self):
        agent = FakeAgent()
        with patch.object(oauth2, 'readBody', side_effect=lambda r: succeed(token_body())):
            yield oauth2.get_access_token(agent, TOKEN_ENDPOINT, 'id', 'secret', 'scope')
            token = yield oauth2.get_access_token(agent, TOKEN_ENDPOINT, 'id', 'secret', 'scope')

        self.assertEqual(token, 'a-token')
        self.assertEqual(agent.calls, 1)

    @inlineCallbacks
    def test_invalidate_token_forces_a_new_request(self):
        agent = FakeAgent()
        with patch.object(oauth2, 'readBody', side_effect=lambda r: succeed(token_body())):
            yield oauth2.get_access_token(agent, TOKEN_ENDPOINT, 'id', 'secret', 'scope')
            oauth2.invalidate_token(TOKEN_ENDPOINT, 'id', 'scope')
            yield oauth2.get_access_token(agent, TOKEN_ENDPOINT, 'id', 'secret', 'scope')

        self.assertEqual(agent.calls, 2)

    @inlineCallbacks
    def test_http_error_raises(self):
        agent = FakeAgent(code=400)
        with patch.object(oauth2, 'readBody', side_effect=lambda r: succeed(b'{}')):
            yield self.assertFailure(
                oauth2.get_access_token(agent, TOKEN_ENDPOINT, 'id', 'secret', 'scope'),
                oauth2.OAuth2Error)

    @inlineCallbacks
    def test_missing_access_token_raises(self):
        agent = FakeAgent()
        body = json.dumps({'token_type': 'Bearer'}).encode()
        with patch.object(oauth2, 'readBody', side_effect=lambda r: succeed(body)):
            yield self.assertFailure(
                oauth2.get_access_token(agent, TOKEN_ENDPOINT, 'id', 'secret', 'scope'),
                oauth2.OAuth2Error)
