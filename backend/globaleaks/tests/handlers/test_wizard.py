import copy

from twisted.internet.defer import inlineCallbacks

from globaleaks import models
from globaleaks.handlers import wizard
from globaleaks.models.config import ConfigFactory
from globaleaks.orm import transact
from globaleaks.rest import errors
from globaleaks.tests import helpers


class TestWizard(helpers.TestHandler):
    _handler = wizard.Wizard

    @transact
    def _support_key_state(self, session):
        pub = ConfigFactory(session, 1).get_val('crypto_support_pub_key')
        admin = session.query(models.User).filter(models.User.tid == 1,
                                                  models.User.role == 'admin').first()
        return pub, (admin.crypto_support_prv_key if admin else '')

    @inlineCallbacks
    def test_wizard_creates_support_key(self):
        handler = self.request(self.dummyWizard)
        yield handler.post()

        pub, admin_prv = yield self._support_key_state()
        # the tenant support keypair is created at wizard time and its private
        # key is sealed to the first administrator
        self.assertNotEqual(pub, '')
        self.assertNotEqual(admin_prv, '')

    @inlineCallbacks
    def test_post_config1(self):
        yield self.test_model_count(models.User, 0)

        handler = self.request(self.dummyWizard)
        yield handler.post()

        yield self.test_model_count(models.User, 2)

        # should fail if the wizard has been already completed
        yield self.assertFailure(handler.post(), errors.ForbiddenOperation)

    @inlineCallbacks
    def test_post_config2(self):
        dummyWizardConfig = copy.deepcopy(self.dummyWizard)
        dummyWizardConfig['skip_recipient_account_creation'] = True

        yield self.test_model_count(models.User, 0)

        handler = self.request(dummyWizardConfig)
        yield handler.post()

        yield self.test_model_count(models.User, 1)

        # should fail if the wizard has been already completed
        yield self.assertFailure(handler.post(), errors.ForbiddenOperation)

    @inlineCallbacks
    def test_post_config3(self):
        dummyWizardConfig = copy.deepcopy(self.dummyWizard)
        dummyWizardConfig['admin_escrow'] = False

        yield self.test_model_count(models.User, 0)

        handler = self.request(dummyWizardConfig)
        yield handler.post()

        yield self.test_model_count(models.User, 2)

        # should fail if the wizard has been already completed
        yield self.assertFailure(handler.post(), errors.ForbiddenOperation)
