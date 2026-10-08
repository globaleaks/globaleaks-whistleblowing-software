import os

from OpenSSL import SSL
from twisted.trial import unittest

from globaleaks.tests import helpers
from globaleaks.utils import tls
from globaleaks.utils.sni import SNIMap


class Connection:
    """
    The side of a TLS connection the map looks at: the name it asks for, and the
    context it is moved to
    """
    def __init__(self, servername):
        self.servername = servername
        self.context = None

    def get_servername(self):
        return self.servername

    def get_context(self):
        return self.context

    def set_context(self, context):
        self.context = context


def site(hostname):
    return {
        'ssl_key': helpers.HTTPS_DATA['key'],
        'ssl_cert': helpers.HTTPS_DATA['cert'],
        'ssl_intermediate': helpers.HTTPS_DATA['chain'],
        'hostname': hostname
    }


class TestSNIMap(unittest.TestCase):
    """
    A connection is served the certificate of the site whose name it asks for;
    a certificate given in files is served instead on every connection, whatever
    the name and whatever the sites carry.
    """
    def setUp(self):
        self.snimap = SNIMap()
        self.snimap.load(1, site('www.globaleaks.org'))
        self.snimap.load(2, site('other.globaleaks.org'))

        self.path = self.mktemp()
        os.makedirs(self.path)

        # the files of a Kubernetes TLS secret: the certificate followed by its chain
        self.cert = self.write('tls.crt', helpers.HTTPS_DATA['cert'] + helpers.HTTPS_DATA['chain'])
        self.key = self.write('tls.key', helpers.HTTPS_DATA['key'])

    def write(self, name, content):
        path = os.path.join(self.path, name)

        with open(path, 'wb' if isinstance(content, bytes) else 'w') as f:
            f.write(content)

        return path

    def served(self, servername):
        connection = Connection(servername)
        self.snimap.select_context(connection)
        return connection.context

    def test_a_site_is_served_its_own_certificate(self):
        self.assertIs(self.served(b'other.globaleaks.org'),
                      self.snimap.contexts_by_hostname['other.globaleaks.org'].getContext())

    def test_a_connection_naming_no_site_is_served_the_root_site(self):
        self.assertIs(self.served(None), self.snimap.default_context)
        self.assertIs(self.served(b'unknown.org'), self.snimap.default_context)

    def test_the_certificate_in_files_is_served_whatever_the_name(self):
        self.snimap.load_files(self.cert, self.key)

        for servername in [b'www.globaleaks.org', b'other.globaleaks.org', b'unknown.org', None]:
            self.assertIs(self.served(servername), self.snimap.fixed_context)

        self.assertIs(self.snimap.default_context, self.snimap.fixed_context)

    def test_files_unchanged_keep_the_context_in_use(self):
        self.assertIsNotNone(self.snimap.load_files(self.cert, self.key))
        context = self.snimap.fixed_context

        self.assertIsNone(self.snimap.load_files(self.cert, self.key))

        # the same context keeps the TLS sessions it opened
        self.assertIs(self.snimap.fixed_context, context)

    def test_renewed_files_replace_the_context_in_use(self):
        self.snimap.load_files(self.cert, self.key)
        context = self.snimap.fixed_context

        key, cert = tls.gen_selfsigned_certificate('globaleaks.whistleblowing.svc')
        self.write('tls.crt', cert)
        self.write('tls.key', key)

        served = self.snimap.load_files(self.cert, self.key)

        self.assertEqual(served.get_subject().CN, 'globaleaks.whistleblowing.svc')
        self.assertIsNot(self.snimap.fixed_context, context)
        self.assertIs(self.served(b'www.globaleaks.org'), self.snimap.fixed_context)

    def test_the_root_site_does_not_take_the_place_of_the_certificate_in_files(self):
        self.snimap.load_files(self.cert, self.key)

        self.snimap.unload(1)
        self.assertIs(self.snimap.default_context, self.snimap.fixed_context)

        self.snimap.load(1, site('www.globaleaks.org'))
        self.assertIs(self.snimap.default_context, self.snimap.fixed_context)

    def test_a_read_that_fails_keeps_the_certificate_in_use(self):
        self.snimap.load_files(self.cert, self.key)
        context = self.snimap.fixed_context

        self.assertRaises(FileNotFoundError,
                          self.snimap.load_files, os.path.join(self.path, 'missing'), self.key)

        self.assertIs(self.snimap.fixed_context, context)

    def test_a_key_that_does_not_match_the_certificate_is_refused(self):
        key = self.write('other.key', tls.gen_ecc_key())

        self.assertRaises(SSL.Error, self.snimap.load_files, self.cert, key)

        self.assertIsNone(self.snimap.fixed_context)

    def test_a_file_holding_no_certificate_is_refused(self):
        cert = self.write('empty.crt', 'not a certificate')

        self.assertRaises(tls.ValidationException, self.snimap.load_files, cert, self.key)

        self.assertIsNone(self.snimap.fixed_context)
