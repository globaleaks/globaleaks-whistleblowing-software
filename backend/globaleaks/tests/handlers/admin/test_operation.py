
from globaleaks import models
from globaleaks.handlers.admin.operation import AdminOperationHandler
from globaleaks.handlers.base import BaseHandler
from globaleaks.jobs import delivery
from globaleaks.models.config import db_get_config_variable, db_set_config_variable, ConfigFactory
from globaleaks.orm import transact, tw
from globaleaks.rest import errors
from globaleaks.tests import helpers

from twisted.internet import defer


@transact
def set_backup_config(session, tid, values):
    config = ConfigFactory(session, tid)
    for var_name, value in values.items():
        config.set_val(var_name, value)


@transact
def set_idp_id(session, user_id, idp_id):
    session.query(models.User).filter(models.User.id == user_id).one().idp_id = idp_id


@transact
def get_idp_id(session, user_id):
    return session.query(models.User).filter(models.User.id == user_id).one().idp_id


@transact
def get_backup_config(session, tid):
    config = ConfigFactory(session, tid)
    return {var_name: config.get_val(var_name)
            for var_name in ('backup_enabled', 'backup_time', 'backup_period', 'backup_retention')}


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

    def test_put_on_secondary_tenant_is_forbidden(self):
        # Resetting the submissions is restricted to root tenant administrators
        # (or root administrators acting through a management session).
        data_request = {
            'operation': 'reset_submissions',
            'args': {}
        }

        handler = self.request(data_request, role='admin', tid=2)

        self.assertRaises(errors.ForbiddenOperation, handler.put)

    def test_put_on_secondary_tenant_with_management_session(self):
        # A root administrator operating on a secondary tenant through a
        # management session is allowed to reset its submissions.
        data_request = {
            'operation': 'reset_submissions',
            'args': {}
        }

        handler = self.request(data_request, role='admin', tid=2,
                               properties={'management_session': True})

        return handler.put()


class TestAdminOperations(helpers.TestHandlerWithPopulatedDB):
    _handler = AdminOperationHandler

    def _test_operation_handler(self, operation, args=None, tid=1, properties=None, headers=None):
        data_request = {
            'operation': operation,
            'args': args if args is not None else {}
        }

        handler = self.request(data_request, role='admin', tid=tid, properties=properties, headers=headers)

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

    @defer.inlineCallbacks
    def test_admin_set_hostname_valid_subdomain_of_root_tenant_hostname(self):
        yield self._test_operation_handler('set_hostname',
                                           {'value': 'sub.www.state.gov'},
                                           tid=2,
                                           properties={'management_session': True})

        value = yield tw(db_get_config_variable, 2, 'hostname')
        self.assertEqual(value, 'sub.www.state.gov')

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
        # Setting a user's password is a sensitive operation that requires the
        # operator to confirm with their own credential (password or 2FA).
        self.patch(BaseHandler, 'check_confirmation', BaseHandler.real_check_confirmation)

        confirmation = helpers.VALID_CONFIRMATION

        return self._test_operation_handler('set_user_password',
                                           {'user_id': self.dummyReceiver_1['id'],
                                            'password': helpers.VALID_KEY},
                                           headers={'x-confirmation': confirmation})

    def test_admin_set_user_password_requires_confirmation(self):
        # Without a valid confirmation of the operator's credential the
        # operation must be rejected.
        self.patch(BaseHandler, 'check_confirmation', BaseHandler.real_check_confirmation)

        self.assertRaises(errors.InvalidAuthentication,
                          self._test_operation_handler,
                          'set_user_password',
                          {'user_id': self.dummyReceiver_1['id'],
                           'password': helpers.VALID_KEY})

    def test_admin_disable_2fa(self):
        return self._test_operation_handler('disable_2fa',
                                           {'value': self.dummyReceiver_1['id']})

    def test_admin_send_password_reset_email(self):
        # Issuing a password reset link is a sensitive operation that requires
        # the operator to confirm with their own credential (password or 2FA).
        self.patch(BaseHandler, 'check_confirmation', BaseHandler.real_check_confirmation)

        confirmation = helpers.VALID_CONFIRMATION

        return self._test_operation_handler('send_password_reset_email',
                                           {'value': self.dummyReceiver_1['id']},
                                           headers={'x-confirmation': confirmation})

    def test_admin_send_password_reset_email_requires_confirmation(self):
        # Without a valid confirmation of the operator's credential the
        # operation must be rejected.
        self.patch(BaseHandler, 'check_confirmation', BaseHandler.real_check_confirmation)

        self.assertRaises(errors.InvalidAuthentication,
                          self._test_operation_handler,
                          'send_password_reset_email',
                          {'value': self.dummyReceiver_1['id']})

    def test_admin_send_password_reset_email_skips_confirmation_in_management_session(self):
        # A root administrator operating on a secondary tenant through a
        # management session is exempted from step-up confirmation when issuing
        # a password reset link: the operation succeeds without any
        # x-confirmation header.
        self.patch(BaseHandler, 'check_confirmation', BaseHandler.real_check_confirmation)

        return self._test_operation_handler('send_password_reset_email',
                                           {'value': self.dummyReceiver_1['id']},
                                           tid=2,
                                           properties={'management_session': True})

    @defer.inlineCallbacks
    def test_admin_reset_idp_binding(self):
        yield set_idp_id(self.dummyReceiver_1['id'], 'subject1')

        yield self._test_operation_handler('reset_idp_binding',
                                           {'value': self.dummyReceiver_1['id']})

        # The account is bound again on its next authentication
        idp_id = yield get_idp_id(self.dummyReceiver_1['id'])
        self.assertEqual(idp_id, '')

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

    @defer.inlineCallbacks
    def test_admin_reset_backups(self):
        yield set_backup_config(1, {
            'backup_enabled': True,
            'backup_time': '10:00',
            'backup_period': 12,
            'backup_retention': 30
        })

        yield self._test_operation_handler('reset_backups')

        config = yield get_backup_config(1)
        self.assertEqual(config, {
            'backup_enabled': False,
            'backup_time': '02:00',
            'backup_period': 24,
            'backup_retention': 7
        })

    def test_admin_reset_backups_forbidden_on_secondary_tenant(self):
        return self.assertFailure(self._test_operation_handler('reset_backups', tid=2),
                                  errors.ForbiddenOperation)


class TestAdminProtectedUsers(helpers.TestHandlerWithPopulatedDB):
    # A freshly initialized database is required so that the protected_users
    # config row (added after the archived test database was generated) is
    # present and can be set.
    initialize_test_database_using_archived_db = False

    _handler = AdminOperationHandler

    def _test_operation_handler(self, operation, args=None):
        data_request = {
            'operation': operation,
            'args': args if args is not None else {}
        }

        handler = self.request(data_request, role='admin')

        return handler.put()

    @defer.inlineCallbacks
    def test_set_user_password_forbidden_for_protected_user(self):
        # Setting the password of a protected user must be forbidden
        yield tw(db_set_config_variable, 1, 'protected_users', [self.dummyReceiver_1['id']])

        yield self.assertFailure(self._test_operation_handler('set_user_password',
                                                             {'user_id': self.dummyReceiver_1['id'],
                                                              'password': helpers.VALID_KEY}),
                                 errors.ForbiddenOperation)

    @defer.inlineCallbacks
    def test_send_password_reset_email_forbidden_for_protected_user(self):
        # Issuing a password reset link to a protected user must be forbidden
        yield tw(db_set_config_variable, 1, 'protected_users', [self.dummyReceiver_1['id']])

        yield self.assertFailure(self._test_operation_handler('send_password_reset_email',
                                                             {'value': self.dummyReceiver_1['id']}),
                                 errors.ForbiddenOperation)