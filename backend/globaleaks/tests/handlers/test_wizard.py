import copy

from twisted.internet.defer import inlineCallbacks

from globaleaks import models
from globaleaks.handlers import wizard
from globaleaks.rest import errors
from globaleaks.tests import helpers


class TestWizard(helpers.TestHandler):
    _handler = wizard.Wizard

    @inlineCallbacks
    def test_post_config1(self):
        yield self.test_model_count(models.User, 0)

        handler = self.request(self.dummy_wizard)
        yield handler.post()

        yield self.test_model_count(models.User, 2)

        # should fail if the wizard has been already completed
        yield self.assertFailure(handler.post(), errors.ForbiddenOperation)

    @inlineCallbacks
    def test_post_config2(self):
        dummy_wizard_config = copy.deepcopy(self.dummy_wizard)
        dummy_wizard_config['skip_recipient_account_creation'] = True

        yield self.test_model_count(models.User, 0)

        handler = self.request(dummy_wizard_config)
        yield handler.post()

        yield self.test_model_count(models.User, 1)

        # should fail if the wizard has been already completed
        yield self.assertFailure(handler.post(), errors.ForbiddenOperation)

    @inlineCallbacks
    def test_post_config3(self):
        dummy_wizard_config = copy.deepcopy(self.dummy_wizard)
        dummy_wizard_config['admin_escrow'] = False

        yield self.test_model_count(models.User, 0)

        handler = self.request(dummy_wizard_config)
        yield handler.post()

        yield self.test_model_count(models.User, 2)

        # should fail if the wizard has been already completed
        yield self.assertFailure(handler.post(), errors.ForbiddenOperation)
