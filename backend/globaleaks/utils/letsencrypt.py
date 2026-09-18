import josepy
import re

from datetime import datetime
from acme import challenges, client, crypto_util, messages, errors

from globaleaks.utils.log import log


class ChallTok:
    def __init__(self, tok):
        self.tok = tok


def select_http01_chall(orderr):
    """Extract authorization resource from within order resource."""
    # Authorization Resource: authz.
    # This object holds the offered challenges by the server and their status.
    authz_list = orderr.authorizations

    for authz in authz_list:
        # Choosing challenge.
        # authz.body.challenges is a set of ChallengeBody objects.
        for i in authz.body.challenges:
            # Find the supported challenge.
            if isinstance(i.chall, challenges.HTTP01):
                return i

    raise RuntimeError('HTTP-01 challenge was not offered by the CA server.')


def split_certificate_chain(full_chain_pem):
    """
    Parse and split a certificate chain

    :param full_chain_pem: the PEM chain of certificates
    :return: the list of certificates contained in the PEM chain
    """
    certificates = re.findall('-----BEGIN CERTIFICATE-----.*?-----END CERTIFICATE-----', full_chain_pem, re.DOTALL)
    return certificates[0], ''.join(certificates[1:])


def convert_asn1_date(asn1_bytes):
    """
    Print a date in asn1 format

    :param asn1_bytes: the daate to be printed
    :return:
    """
    return datetime.strptime(asn1_bytes.decode(), '%Y%m%d%H%M%SZ')


def create_v2_client(directory_url, accnt_key):
    """Creates an ACME v2 Client for making requests to Let's Encrypt with"""

    accnt_key = josepy.JWKRSA(key=accnt_key)
    net = client.ClientNetwork(accnt_key, user_agent="GlobaLeaks Let's Encrypt Client")
    directory = messages.Directory.from_json(net.get(directory_url).json())

    return client.ClientV2(directory, net)


def get_boulder_tos(directory_url, accnt_key):
    """Returns the TOS for Let's Encrypt from Boulder"""
    return create_v2_client(directory_url, accnt_key).directory.meta.terms_of_service


def request_new_certificate(hostname, accnt_key, key, tmp_chall_dict, directory_url):
    """Runs the entire process of ACME registration and certificate request"""

    client = create_v2_client(directory_url, accnt_key)

    new_reg = messages.NewRegistration.from_data(
      terms_of_service_agreed=True
    )

    try:
        client.net.account = client.new_account(new_reg)

    except errors.ConflictError as error:
        existing_reg = messages.RegistrationResource(body=new_reg, uri=error.location)
        existing_reg = client.query_registration(existing_reg)
        client.update_registration(existing_reg)

    # Handle compatibility with up to date python-acme/python-cryptography
    # included since debian trixie
    if isinstance(key, str):
        key = key.encode('utf-8')

    csr = crypto_util.make_csr(key, [hostname], False)
    order = client.new_order(csr)

    log.info('Created a new order for the issuance of a certificate for %s', hostname)

    challb = select_http01_chall(order)

    _, chall_tok = challb.response_and_validation(client.net.key)
    v = challb.chall.encode("token")
    log.info('Exposing challenge on %s', v)
    tmp_chall_dict[v] = ChallTok(chall_tok)

    cr = client.answer_challenge(challb, challb.response(client.net.key))
    log.debug('Acme CA responded to challenge request with: %s', cr)

    order = client.poll_and_finalize(order)

    return split_certificate_chain(order.fullchain_pem)
