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

    def _test_operation_handler(self, operation, args=None, tid=1, properties=None):
        data_request = {
            'operation': operation,
            'args': args if args is not None else {}
        }

        handler = self.request(data_request, role='admin', tid=tid, properties=properties)

        return handler.put()

    def test_admin_set_hostname(self):
        return self._test_operation_handler('set_hostname',
                                           {'value': 'www.nsa.gov'})

    def test_admin_set_hostname_invalid_because_used(self):
        return self.assertFailure(self._test_operation_handler('set_hostname',
                                                               {'value': 'www.gov.il'}),
                                  errors.InputValidationError),

    def test_admin_set_hostname_invalid_because_subdomain_of_other_tenant(self):
        # The hostname derived from the subdomain of tenant 2 is reserved
        return self.assertFailure(self._test_operation_handler('set_hostname',
                                                               {'value': 'tenant-2.example.org'}),
                                  errors.InputValidationError)

    def test_admin_set_hostname_invalid_because_ending_with_root_tenant_hostname(self):
        # The root tenant hostname is a forbidden ending for secondary tenants
        return self.assertFailure(self._test_operation_handler('set_hostname',
                                                               {'value': 'sub.www.state.gov'},
                                                               tid=2,
                                                               properties={'management_session': True}),
                                  errors.InputValidationError)

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

    def test_admin_set_user_password(self):
        return self._test_operation_handler('set_user_password',
                                           {'user_id': self.dummyReceiver_1['id'],
                                            'password': helpers.VALID_KEY})

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
