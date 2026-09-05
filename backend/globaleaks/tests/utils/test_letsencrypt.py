import copy
import os
import re

from unittest.mock import MagicMock, patch

import josepy
from acme import challenges, errors
from cryptography.hazmat.primitives import serialization
from OpenSSL import crypto
from twisted.trial.unittest import TestCase

from globaleaks.tests import helpers
from globaleaks.utils import letsencrypt

DIRECTORY_URL = 'https://acme.invalid/directory'

DIRECTORY = {
    'newAccount': 'https://acme.invalid/new-account',
    'newOrder': 'https://acme.invalid/new-order',
    'meta': {
        'termsOfService': 'https://acme.invalid/terms'
    }
}

TOKEN = b'a token the CA hands out for the challenge'


def certificates_in(pem):
    return re.findall('-----BEGIN CERTIFICATE-----.*?-----END CERTIFICATE-----', pem, re.DOTALL)


class TestRunAcmeReg(TestCase):
    def test_format_asn1_date(self):
        s = b'20170827153000Z'

        d = letsencrypt.convert_asn1_date(s)

        self.assertEqual(d.year, 2017)
        self.assertEqual(d.month, 8)
        self.assertEqual(d.day, 27)

    def test_format_as1_date_from_certs(self):
        test_cases = [
            {'path': 'valid/cert.pem',
             'year': 2027,
             'month': 2,
             'day': 25,
             },
            {'path': 'invalid/expired_cert.pem',
             'year': 2017,
             'month': 2,
             'day': 4,
             },
            {'path': 'invalid/glbc_le_stage_cert.pem',
             'year': 2017,
             'month': 8,
             'day': 22,
             },
        ]

        for tc in test_cases:
            path = os.path.join(helpers.DATA_DIR, 'https', tc['path'])
            with open(path) as f:
                cert = crypto.load_certificate(crypto.FILETYPE_PEM, f.read())

            s = cert.get_notAfter()
            date = letsencrypt.convert_asn1_date(s)
            self.assertEqual(date.year, tc['year'])
            self.assertEqual(date.month, tc['month'])
            self.assertEqual(date.day, tc['day'])


class TestCertificateChain(TestCase):
    """
    What the CA hands back is one PEM: the certificate of the site first, its
    issuers after it. The two are told apart because the site is served its own
    certificate and the chain of its issuers separately.
    """
    def test_the_chain_is_split_into_the_certificate_and_its_issuers(self):
        cert, chain = letsencrypt.split_certificate_chain(helpers.HTTPS_DATA['cert'] +
                                                          helpers.HTTPS_DATA['chain'])

        self.assertEqual(cert, certificates_in(helpers.HTTPS_DATA['cert'])[0])
        self.assertEqual(chain, ''.join(certificates_in(helpers.HTTPS_DATA['chain'])))

    def test_a_lone_certificate_has_no_issuers(self):
        cert, chain = letsencrypt.split_certificate_chain(helpers.HTTPS_DATA['cert'])

        self.assertEqual(cert, certificates_in(helpers.HTTPS_DATA['cert'])[0])
        self.assertEqual(chain, '')


class TestChallengeSelection(TestCase):
    """
    The site can only prove its name over HTTP: among the challenges the CA
    offers, the HTTP-01 one is the only one that can be answered, and an order
    that does not offer it cannot be fulfilled at all.
    """
    def order_offering(self, *challs):
        offered = []
        for chall in challs:
            challb = MagicMock()
            challb.chall = chall
            offered.append(challb)

        authz = MagicMock()
        authz.body.challenges = offered

        order = MagicMock()
        order.authorizations = [authz]

        return order, offered

    def test_the_http01_challenge_is_picked_among_the_offered_ones(self):
        order, offered = self.order_offering(challenges.DNS01(token=TOKEN),
                                             challenges.HTTP01(token=TOKEN))

        self.assertIs(letsencrypt.select_http01_chall(order), offered[1])

    def test_an_order_offering_no_http01_challenge_cannot_be_fulfilled(self):
        order, _ = self.order_offering(challenges.DNS01(token=TOKEN))

        with self.assertRaisesRegex(Exception, 'HTTP-01'):
            letsencrypt.select_http01_chall(order)

    def test_the_answer_to_a_challenge_is_kept_as_given(self):
        self.assertEqual(letsencrypt.ChallTok('the answer').tok, 'the answer')


class TestAcmeClient(TestCase):
    """
    The client speaks to the CA it is pointed at, on behalf of the account
    whose key it holds: the directory of the CA says where the orders are to be
    placed and what terms are being agreed to.
    """
    def setUp(self):
        self.account_key = serialization.load_pem_private_key(helpers.HTTPS_DATA['key'].encode(), None)

        self.net = MagicMock()
        self.net.get.return_value.json.return_value = copy.deepcopy(DIRECTORY)

    def test_the_client_is_built_on_the_directory_of_the_ca(self):
        with patch.object(letsencrypt.client, 'ClientNetwork', return_value=self.net) as network:
            acme_client = letsencrypt.create_v2_client(DIRECTORY_URL, self.account_key)

        self.net.get.assert_called_once_with(DIRECTORY_URL)
        self.assertIs(acme_client.net, self.net)
        self.assertEqual(acme_client.directory['newOrder'], DIRECTORY['newOrder'])
        # the account is identified by its key, presented in the JOSE form
        self.assertIsInstance(network.call_args[0][0], josepy.JWKRSA)

    def test_the_terms_of_service_are_read_from_the_directory(self):
        with patch.object(letsencrypt.client, 'ClientNetwork', return_value=self.net):
            terms = letsencrypt.get_boulder_tos(DIRECTORY_URL, self.account_key)

        self.assertEqual(terms, DIRECTORY['meta']['termsOfService'])


class TestCertificateRequest(TestCase):
    """
    Getting a certificate is a sequence with the CA: an account, an order, a
    challenge answered over HTTP and, at the end of it, the certificate issued
    against a request signed by the key of the site.
    """
    def setUp(self):
        self.acme_client = MagicMock()

        self.challb = MagicMock()
        self.challb.chall = challenges.HTTP01(token=TOKEN)
        self.challb.response_and_validation.return_value = (MagicMock(), 'the validation of the challenge')

        authz = MagicMock()
        authz.body.challenges = [self.challb]

        self.order = MagicMock()
        self.order.authorizations = [authz]
        self.order.fullchain_pem = helpers.HTTPS_DATA['cert'] + helpers.HTTPS_DATA['chain']

        self.acme_client.new_order.return_value = self.order
        self.acme_client.poll_and_finalize.return_value = self.order

        self.exposed = {}

    def request(self, key=helpers.HTTPS_DATA['key']):
        with patch.object(letsencrypt, 'create_v2_client', return_value=self.acme_client) as create:
            result = letsencrypt.request_new_certificate('www.globaleaks.org', 'the account key',
                                                         key, self.exposed, DIRECTORY_URL)

        create.assert_called_once_with(DIRECTORY_URL, 'the account key')

        return result

    def test_the_certificate_issued_is_returned_with_its_chain(self):
        cert, chain = self.request()

        self.assertEqual(cert, certificates_in(helpers.HTTPS_DATA['cert'])[0])
        self.assertEqual(chain, ''.join(certificates_in(helpers.HTTPS_DATA['chain'])))

        self.acme_client.new_account.assert_called_once()
        self.acme_client.poll_and_finalize.assert_called_once_with(self.order)

    def test_the_order_is_placed_with_a_request_signed_by_the_key_of_the_site(self):
        cases = [("a key given as text", helpers.HTTPS_DATA['key']),
                 ("a key given as bytes", helpers.HTTPS_DATA['key'].encode())]

        for reason, key in cases:
            self.acme_client.new_order.reset_mock()

            self.request(key)

            csr = self.acme_client.new_order.call_args[0][0]
            self.assertIn(b'-----BEGIN CERTIFICATE REQUEST-----', csr,
                          f"{reason} does not produce a signing request")

    def test_the_challenge_is_exposed_under_its_token_and_answered(self):
        self.request()

        token = self.challb.chall.encode('token')
        self.assertIsInstance(self.exposed[token], letsencrypt.ChallTok)
        self.assertEqual(self.exposed[token].tok, 'the validation of the challenge')

        self.acme_client.answer_challenge.assert_called_once_with(self.challb,
                                                                  self.challb.response.return_value)

    def test_an_account_already_registered_with_the_ca_is_reused(self):
        self.acme_client.new_account.side_effect = errors.ConflictError('https://acme.invalid/account/1')

        self.request()

        existing = self.acme_client.query_registration.call_args[0][0]
        self.assertEqual(existing.uri, 'https://acme.invalid/account/1')
        self.acme_client.update_registration.assert_called_once_with(
            self.acme_client.query_registration.return_value)
