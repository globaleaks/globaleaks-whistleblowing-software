from globaleaks import models
from globaleaks.handlers.admin.operation import AdminOperationHandler
from globaleaks.jobs import delivery
from globaleaks.rest import errors
from globaleaks.tests import helpers

from twisted.internet import defer


class TestAdminPasswordReset(helpers.TestHandlerWithPopulatedDB):
    _handler = AdminOperationHandler

class TestAdminResetSubmissions(helpers.TestHandlerWithPopulatedDB):
    _handler = AdminOperationHandler

    @defer.inlineCallbacks
    def setUp(self):
        yield helpers.TestHandlerWithPopulatedDB.setUp(self)
        yield self.perform_full_submission_actions()
        yield delivery.Delivery().run()

    @defer.inlineCallbacks
    def test_put(self):
        yield self.test_model_count(models.InternalTip, 2)
        yield self.test_model_count(models.ReceiverTip, 4)
        yield self.test_model_count(models.InternalFile, 4)
        yield self.test_model_count(models.WhistleblowerFile, 8)
        yield self.test_model_count(models.Comment, 4)
        yield self.test_model_count(models.Mail, 0)

        data_request = {
            'operation': 'reset_submissions',
            'args': {}
        }

        handler = self.request(data_request, role='admin')

        yield handler.put()

        yield self.test_model_count(models.InternalTip, 0)
        yield self.test_model_count(models.ReceiverTip, 0)
        yield self.test_model_count(models.InternalFile, 0)
        yield self.test_model_count(models.WhistleblowerFile, 0)
        yield self.test_model_count(models.Comment, 0)
        yield self.test_model_count(models.Mail, 0)


class TestAdminOperations(helpers.TestHandlerWithPopulatedDB):
    _handler = AdminOperationHandler

    def _test_operation_handler(self, operation, args={}, tid=1):
        data_request = {
            'operation': operation,
            'args': args
        }

        handler = self.request(data_request, role='admin', tid=tid)

        return handler.put()

    def test_admin_set_hostname(self):
        return self._test_operation_handler('set_hostname',
                                           {'value': 'www.nsa.gov'})

    def test_admin_set_hostname_invalid_because_used(self):
        return self.assertFailure(self._test_operation_handler('set_hostname',
                                                               {'value': 'www.gov.il'}),
                                  errors.InputValidationError),

    def test_admin_set_hostname_invalid_because_onion(self):
        return self.assertFailure(self._test_operation_handler('set_hostname',
                                                               {'value': 'vlltmarak3cn67bu32gq356azn2gkjl5seytdhotpa5uhofejlbeemqd.onion'}),
                                  errors.InputValidationError)

    def test_admin_set_hostname_invalid_because_localhost(self):
        return self.assertFailure(self._test_operation_handler('set_hostname',
                                                               {'value': 'localhost'}),
                                  errors.InputValidationError)

    def test_admin_test_mail(self):
        return self._test_operation_handler('test_mail')

    @defer.inlineCallbacks
    def test_admin_set_user_password(self):
        yield self.test_model_count(models.Mail, 0)

        yield self._test_operation_handler('set_user_password',
                                           {'user_id': self.dummyReceiver_1['id'],
                                            'password': helpers.VALID_KEY})

        yield self.test_model_count(models.Mail, 1)

    def test_admin_disable_2fa(self):
        return self._test_operation_handler('disable_2fa',
                                           {'value': self.dummyReceiver_1['id']})

    def test_admin_send_password_reset_email(self):
        return self._test_operation_handler('send_password_reset_email',
                                           {'value': self.dummyReceiver_1['id']})

    def test_admin_reset_smtp_settings(self):
        return self._test_operation_handler('reset_smtp_settings')

    def test_admin_enable_encryption(self):
        return self._test_operation_handler('enable_encryption')

    @defer.inlineCallbacks
    def test_admin_toggle_escrow(self):
        # double toggle is needed to test disabling and enabling
        yield self._test_operation_handler('toggle_escrow')
        yield self._test_operation_handler('toggle_escrow')

    @defer.inlineCallbacks
    def test_admin_toggle_escrow_on_secondary_tenant(self):
        # double toggle is needed to test disabling and enabling
        yield self._test_operation_handler('toggle_escrow', tid=2)
        yield self._test_operation_handler('toggle_escrow', tid=2)

    @defer.inlineCallbacks
    def test_admin_toggle_user_escrow_on_a_user(self):
        # double toggle is needed to test disabling and enabling
        yield self._test_operation_handler('toggle_user_escrow', {'value': self.dummyReceiver_1['id']})
        yield self._test_operation_handler('toggle_user_escrow', {'value': self.dummyReceiver_1['id']})

    def test_admin_toggle_user_escrow_prevents_auto_revocation(self):
        return self.assertFailure(self._test_operation_handler('toggle_user_escrow',
                                                               {'value': self.dummyAdmin['id']}),
                                  errors.InputValidationError)

    def test_admin_reset_templates(self):
        return self._test_operation_handler('reset_templates')

    def test_admin_reset_onion_private_key(self):
        return self._test_operation_handler('reset_onion_private_key')

    def test_admin_enable_user_permission_file_upload(self):
        return self._test_operation_handler('enable_user_permission_file_upload')
