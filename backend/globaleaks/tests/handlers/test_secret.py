import base64
import os

from nacl.encoding import Base64Encoder
from nacl.pwhash import argon2id
from nacl.secret import SecretBox
from twisted.internet.defer import inlineCallbacks

from globaleaks import models
from globaleaks.db.migrations.recover_receipts import db_mark_invalidated_receipts
from globaleaks.handlers import auth, secret
from globaleaks.handlers.auth import receipt_hash_2023
from globaleaks.models.config import ConfigFactory
from globaleaks.orm import transact
from globaleaks.rest import errors
from globaleaks.sessions import Sessions
from globaleaks.state import State
from globaleaks.tests import helpers
from globaleaks.utils.crypto import GCE
from globaleaks.utils.utility import datetime_now

SECRET = 'the secret of the platform used until 2023'
RECEIPT = '1234567812345678'
LEGACY_RECEIPT = '8765432187654321'


def derive_key_5_0(password, salt):
    # The key derivation of 5.0, with which the secret encrypted the private keys
    return argon2id.kdf(32, password.encode(), base64.b64decode(salt)[0:16],
                        opslimit=GCE.options['OPSLIMIT'] + 1,
                        memlimit=1 << GCE.options['MEMLIMIT'])


@transact
def import_reports(session):
    # The reports of a site as 5.0 left them: one imported from the platform
    # used until 2023, one hashed by the server, none derived by the client
    salt = ConfigFactory(session, 1).get_val('receipt_salt')
    prv_key, pub_key = GCE.generate_keypair()

    itips = session.query(models.InternalTip).filter(models.InternalTip.tid == 1).all()

    imported, legacy = itips[0], itips[1]

    imported.receipt_hash = receipt_hash_2023(RECEIPT, salt)
    imported.crypto_pub_key = pub_key
    imported.crypto_prv_key = Base64Encoder.encode(SecretBox(derive_key_5_0(SECRET, salt)).encrypt(prv_key))

    legacy.receipt_hash = GCE.calculate_key_and_hash(LEGACY_RECEIPT, salt)[1]
    legacy.crypto_pub_key = ''

    for itip in itips[2:]:
        itip.receipt_hash = os.urandom(64).hex()

    return imported.id, legacy.id, prv_key


@transact
def get_report(session, itip_id):
    itip = session.query(models.InternalTip).filter(models.InternalTip.id == itip_id).one()
    return itip.receipt_hash, itip.crypto_prv_key


@transact
def mark_invalidated_receipts(session):
    # The update of a site that ran 5.0.98 after holding the reports of 5.0
    entry = models.AuditLog()
    entry.tid, entry.type, entry.user_id = 1, 'version_update', 'system'
    entry.date, entry.data = datetime_now(), {'from': '5.0.10', 'to': '5.0.98'}
    session.add(entry)
    session.flush()

    db_mark_invalidated_receipts(session, '5.0.98')


class TestSecret(helpers.TestHandlerWithPopulatedDB):
    _handler = secret.Secret

    @inlineCallbacks
    def setUp(self):
        yield helpers.TestHandlerWithPopulatedDB.setUp(self)
        self.addCleanup(setattr, State, 'secret_key', None)

        salt = GCE.generate_salt()
        with open(os.path.join(State.settings.working_path, 'secret_key_hash.txt'), 'w') as f:
            f.write(GCE.argon2id(SECRET, salt) + ':' + salt)

        yield self.perform_full_submission_actions()
        self.itip_id, self.legacy_id, self.prv_key = yield import_reports()

    def load_secret(self, value):
        return self.request('secret=' + value, handler_cls=secret.Secret).post()

    def login(self, receipt):
        handler = self.request({'receipt': receipt}, handler_cls=auth.ReceiptAuthHandler)
        handler.request.client_using_tor = True
        return handler.post()

    @inlineCallbacks
    def test_a_wrong_secret_is_not_loaded(self):
        yield self.load_secret('wrong')
        self.assertFalse(State.secret_key)

    @inlineCallbacks
    def test_an_imported_report_is_not_reached_without_the_secret(self):
        yield self.assertFailure(self.login(RECEIPT), errors.InvalidAuthentication)

    @inlineCallbacks
    def test_an_imported_report_is_reached_with_the_secret_and_moves_to_the_receipt(self):
        yield self.load_secret(SECRET)
        self.assertTrue(State.secret_key)

        response = yield self.login(RECEIPT)
        self.assertEqual(Sessions.get(response['id']).cc, self.prv_key)

        receipt_hash, crypto_prv_key = yield get_report(self.itip_id)
        salt = State.tenants[1].cache.receipt_salt
        key, hash = GCE.calculate_key_and_hash(RECEIPT, salt)
        self.assertEqual(receipt_hash, hash)
        self.assertEqual(GCE.symmetric_decrypt(key, Base64Encoder.decode(crypto_prv_key)), self.prv_key)

        # From now on the receipt alone reaches it
        State.secret_key = None
        response = yield self.login(RECEIPT)
        self.assertEqual(Sessions.get(response['id']).cc, self.prv_key)

    @inlineCallbacks
    def test_the_update_keeps_the_receipts_of_a_site_holding_imported_reports(self):
        before = [(yield get_report(self.itip_id)), (yield get_report(self.legacy_id))]
        yield mark_invalidated_receipts()
        after = [(yield get_report(self.itip_id)), (yield get_report(self.legacy_id))]
        self.assertEqual(before, after)

        response = yield self.login(LEGACY_RECEIPT)
        self.assertTrue('id' in response)
