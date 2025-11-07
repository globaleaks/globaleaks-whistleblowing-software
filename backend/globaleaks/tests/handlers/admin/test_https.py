from OpenSSL import crypto, SSL
from twisted.internet.defer import inlineCallbacks

from globaleaks.handlers.admin import https
from globaleaks.models import config
from globaleaks.orm import tw
from globaleaks.rest import errors
from globaleaks.state import State
from globaleaks.tests import helpers
from globaleaks.utils.letsencrypt import ChallTok


@inlineCallbacks
def set_init_params():
    hostname = '127.0.0.1:9999'
    yield tw(config.db_set_config_variable, 1, 'hostname', hostname)
    State.tenants[1].cache.hostname = hostname


class TestFileHandler(helpers.TestHandler):
    _handler = https.FileHandler

    @inlineCallbacks
    def setUp(self):
        yield super(TestFileHandler, self).setUp()
        yield set_init_params()

    @inlineCallbacks
    def get_and_check(self, name, is_set):
        handler = self.request(role='admin', handler_cls=https.ConfigHandler)
        response = yield handler.get()
        self.assertEqual(response['files'][name]['set'], is_set)

    @inlineCallbacks
    def test_key_file_upload_invalid_key(self):
        n = 'key'

        yield self.get_and_check(n, False)

        # Try to upload an invalid key
        bad_key = 'donk donk donk donk donk donk'
        handler = self.request({'name': 'key', 'content': bad_key}, role='admin')
        yield self.assertFailure(handler.post(n), errors.InputValidationError)

    @inlineCallbacks
    def test_key_file_upload_valid_key(self):
        n = 'key'

        yield self.get_and_check(n, False)

        # Upload a valid key
        good_key = helpers.HTTPS_DATA['key']
        handler = self.request({'name': 'key', 'content': good_key}, role='admin')

        yield handler.post(n)

        yield self.get_and_check(n, True)

    @inlineCallbacks
    def test_key_generate_and_delete(self):
        n = 'key'

        yield self.get_and_check(n, False)

        handler = self.request({'name': 'key'}, role='admin')

        # Test key generation
        yield handler.put(n)

        yield self.get_and_check(n, True)

        # Try delete actions
        yield handler.delete(n)

        yield self.get_and_check(n, False)

    @inlineCallbacks
    def test_cert_file(self):
        n = 'cert'

        yield self.get_and_check(n, False)

        # Upload a valid key
        handler = self.request({'name': 'key', 'content': helpers.HTTPS_DATA['key']}, role='admin')
        yield handler.post('key')

        # Test bad cert
        body = {'name': 'cert', 'content': 'bonk bonk bonk'}
        handler = self.request(body, role='admin')
        yield self.assertFailure(handler.post(n), errors.InputValidationError)

        # Upload a valid cert
        body = {'name': 'cert', 'content': helpers.HTTPS_DATA[n]}
        handler = self.request(body, role='admin')
        yield handler.post(n)

        yield self.get_and_check(n, True)

        handler = self.request(role='admin')

        # Finally delete the cert
        yield handler.delete(n)
        yield self.get_and_check(n, False)

    @inlineCallbacks
    def test_chain_file(self):
        n = 'chain'

        yield self.get_and_check(n, False)

        # Upload a valid key
        handler = self.request({'name': 'key', 'content': helpers.HTTPS_DATA['key']}, role='admin')
        yield handler.post('key')

        # Upload a valid chain
        handler = self.request({'name': 'cert', 'content': helpers.HTTPS_DATA['cert']}, role='admin')
        yield handler.post('cert')

        State.tenants[1].cache.hostname = '127.0.0.1'

        body = {'name': 'chain', 'content': helpers.HTTPS_DATA[n]}
        handler = self.request(body, role='admin')

        yield handler.post(n)
        yield self.get_and_check(n, True)

        handler = self.request(role='admin')

        yield handler.delete(n)
        yield self.get_and_check(n, False)


class TestConfigHandler(helpers.TestHandler):
    _handler = https.ConfigHandler

    @inlineCallbacks
    def test_all_methods(self):
        handler = self.request(role='admin')

        yield set_init_params()

        # Verify HTTPS is initially disabled
        response = yield handler.get()
        self.assertFalse(response['enabled'])

        # Simulate configuration
        yield tw(https.db_load_https_key, 1, helpers.HTTPS_DATA['key'])
        yield tw(https.db_load_https_cert, 1, helpers.HTTPS_DATA['cert'])
        yield tw(https.db_load_https_chain, 1, helpers.HTTPS_DATA['chain'])

        # Enable HTTPS
        yield handler.post()
        response = yield handler.get()
        self.assertTrue(response['enabled'])

        # Disable HTTPS
        yield handler.put()
        response = yield handler.get()
        self.assertFalse(response['enabled'])

        self.test_reactor.pump([50])

        yield handler.delete()

        response = yield handler.get()
        self.assertFalse(response['enabled'])
        self.test_reactor.pump([50])


class TestCSRHandler(helpers.TestHandler):
    _handler = https.CSRHandler

    @inlineCallbacks
    def test_post(self):
        yield set_init_params()
        yield tw(https.db_load_https_key, 1, helpers.HTTPS_DATA['key'])
        State.tenants[1].cache.hostname = 'notreal.ns.com'

        body = {
            'country': 'it',
            'province': 'regione',
            'city': 'citta',
            'company': 'azienda',
            'department': 'reparto',
            'email': 'indrizzio@email',
        }

        handler = self.request(body, role='admin')
        response = yield handler.post()

        pem_csr = crypto.load_certificate_request(SSL.FILETYPE_PEM, response)

        comps = pem_csr.get_subject().get_components()
        self.assertIn((b'CN', b'notreal.ns.com'), comps)
        self.assertIn((b'C', b'IT'), comps)
        self.assertIn((b'L', b'citta'), comps)


class TestAcmeChallengeHandler(helpers.TestHandler):
    _handler = https.AcmeChallengeHandler

    @inlineCallbacks
    def test_get(self):
        # tmp_chall_dict pollutes scope
        tok = 'yT-RDI9dU7dJPxaTYOgY_YnYYByT4CVAVCC7W3zUDIw'
        v = '{}.5vh2ZRCJGmNUKEEBn-SN6esbMnSl1w8ZT0LDUwexTAM'.format(tok)
        ct = ChallTok(v)

        State.tenants[1].acme_tmp_chall_dict[tok] = ct

        handler = self.request()
        resp = yield handler.get(tok)

        self.assertEqual(resp, v)
