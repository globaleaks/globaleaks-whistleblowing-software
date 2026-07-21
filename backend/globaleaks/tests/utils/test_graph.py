from twisted.internet.defer import inlineCallbacks, succeed
from twisted.trial import unittest

from unittest.mock import patch

from globaleaks.utils import graph


class FakeResponse:
    def __init__(self, code):
        self.code = code


class FakeAgent:
    """A minimal agent recording the request it received."""
    def __init__(self, code=202):
        self.code = code
        self.calls = 0

    def request(self, method, url, headers, producer):
        self.calls += 1
        self.method = method
        self.url = url
        self.headers = headers
        self.producer = producer
        return succeed(FakeResponse(self.code))


class TestGraph(unittest.TestCase):
    @inlineCallbacks
    def test_send_mail_posts_to_graph(self):
        """Test that send_mail submits the message to the Graph sendMail endpoint."""
        agent = FakeAgent()
        with patch.object(graph, 'readBody', side_effect=lambda r: succeed(b'')):
            result = yield graph.send_mail(agent, 'the-token', 'Sender', 'sender@example.com', 'to@example.com', 'Subject', 'Body')

        self.assertTrue(result)
        self.assertEqual(agent.calls, 1)
        self.assertEqual(agent.method, b'POST')
        self.assertEqual(agent.url, b'https://graph.microsoft.com/v1.0/users/sender%40example.com/sendMail')
        self.assertEqual(agent.headers.getRawHeaders(b'Authorization'), [b'Bearer the-token'])
        self.assertEqual(agent.headers.getRawHeaders(b'Content-Type'), [b'text/plain'])

    @inlineCallbacks
    def test_non_accepted_status_raises(self):
        """Test that a non-202 response is reported as a GraphError."""
        agent = FakeAgent(code=500)
        with patch.object(graph, 'readBody', side_effect=lambda r: succeed(b'')):
            yield self.assertFailure(
                graph.send_mail(agent, 'the-token', 'Sender', 'sender@example.com', 'to@example.com', 'Subject', 'Body'),
                graph.GraphError)
