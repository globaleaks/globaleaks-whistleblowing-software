from twisted.internet.defer import inlineCallbacks

from globaleaks import db, models
from globaleaks.handlers import admin
from globaleaks.handlers.admin import tenant
from globaleaks.models.config import DEFAULT_PROFILE_ID, ConfigFactory, db_get_config_variable, db_get_held_keys, \
    db_set_config_variable
from globaleaks.models.config_desc import ConfigL10NFilters
from globaleaks.orm import transact, tw
from globaleaks.rest import errors
from globaleaks.tests import helpers

# special guest:

stuff = "³²¼½¬¼³²"


@transact
def get_val(session, tid, var_name):
    return ConfigFactory(session, tid).get_val(var_name)


@transact
def held_keys(session, tid):
    return db_get_held_keys(session, tid)


@transact
def logged(session, tid, log_type):
    return session.query(models.AuditLog).filter(models.AuditLog.tid == tid,
                                                 models.AuditLog.type == log_type).count()


class TestNotificationSettingsInstance(helpers.TestHandlerWithPopulatedDB):
    _handler = admin.notification.NotificationSettingsInstance

    @inlineCallbacks
    def test_get(self):
        handler = self.request(role='admin')
        response = yield handler.get()
        self.assertEqual(set(response), {'enable_admin_notification_emails',
                                         'enable_analyst_notification_emails',
                                         'enable_custodian_notification_emails',
                                         'enable_receiver_notification_emails',
                                         'tip_expiration_threshold'})

    @inlineCallbacks
    def test_put(self):
        handler = self.request(role='admin')
        desc = yield handler.get()

        desc['tip_expiration_threshold'] = 3
        desc['enable_admin_notification_emails'] = False

        handler = self.request(desc, role='admin')
        response = yield handler.put()
        self.assertEqual(response['tip_expiration_threshold'], 3)
        self.assertFalse(response['enable_admin_notification_emails'])
        self.assertEqual((yield logged(1, 'update_notification_settings')), 1)


class TestNotificationTemplatesInstance(helpers.TestHandlerWithPopulatedDB):
    _handler = admin.notification.NotificationTemplatesInstance

    @inlineCallbacks
    def test_get(self):
        handler = self.request(role='admin')
        response = yield handler.get()
        self.assertEqual(response['templates'], ConfigL10NFilters['notification'])
        self.assertEqual(set(response) - {'templates'}, set(ConfigL10NFilters['notification']))

    @inlineCallbacks
    def test_put(self):
        handler = self.request(role='admin')
        desc = yield handler.get()

        desc['tip_mail_title'] = stuff

        handler = self.request(desc, role='admin')
        response = yield handler.put()
        self.assertEqual(response['tip_mail_title'], stuff)
        self.assertEqual((yield logged(1, 'update_notification_templates')), 1)


class TestSMTPInstance(helpers.TestHandlerWithPopulatedDB):
    _handler = admin.notification.SMTPInstance

    @inlineCallbacks
    def test_get_never_reads_the_password_back(self):
        for name in ['smtp1', 'smtp2']:
            handler = self.request(role='admin')
            response = yield handler.get(name)
            self.assertEqual(response['server'], 'mail.globaleaks.org')
            self.assertNotIn('password', response)
            self.assertTrue(response['password_set'])

        # the main server is on by default, the secondary one off
        handler = self.request(role='admin')
        response = yield handler.get('smtp1')
        self.assertTrue(response['enabled'])
        self.assertNotIn('template_types', response)

        handler = self.request(role='admin')
        response = yield handler.get('smtp2')
        self.assertFalse(response['enabled'])
        self.assertEqual(response['template_types'], [])

    @inlineCallbacks
    def test_the_main_server_is_turned_off_and_a_reset_leaves_it_off(self):
        response = yield self.put_smtp1(enabled=False)
        self.assertFalse(response['enabled'])
        self.assertFalse((yield get_val(1, 'smtp_enabled')))

        handler = self.request(role='admin')
        response = yield handler.delete('smtp1')
        self.assertFalse(response['enabled'])

    @inlineCallbacks
    def test_put_writes_its_own_server_alone(self):
        handler = self.request(role='admin')
        desc = yield handler.get('smtp1')

        desc['server'] = stuff
        desc['password'] = 'widdlyscuds'

        handler = self.request(desc, role='admin')
        response = yield handler.put('smtp1')
        self.assertEqual(response['server'], stuff)
        self.assertNotIn('password', response)
        self.assertEqual((yield get_val(1, 'smtp_password')), 'widdlyscuds')
        self.assertEqual((yield get_val(1, 'smtp2_server')), 'mail.globaleaks.org')
        self.assertEqual((yield logged(1, 'update_smtp1')), 1)

    @inlineCallbacks
    def test_put_with_no_password_keeps_the_one_held(self):
        yield self.test_put_writes_its_own_server_alone()

        handler = self.request(role='admin')
        desc = yield handler.get('smtp1')
        desc['password'] = ''

        handler = self.request(desc, role='admin')
        yield handler.put('smtp1')
        self.assertEqual((yield get_val(1, 'smtp_password')), 'widdlyscuds')

    @inlineCallbacks
    def put_smtp1(self, tid=1, **changes):
        handler = self.request(role='admin', tid=tid)
        desc = yield handler.get('smtp1')
        desc['password'] = ''
        desc.update(changes)

        handler = self.request(desc, role='admin', tid=tid)
        response = yield handler.put('smtp1')
        return response

    @inlineCallbacks
    def test_put_with_no_authentication_drops_the_password(self):
        yield self.put_smtp1(password='widdlyscuds')
        yield self.put_smtp1(authentication=False, password='widdlyscuds')

        # what a site does not hold of its own it reads from its profile, or from the defaults of
        # the application when it names none
        self.assertNotIn('smtp_password', (yield held_keys(1)))
        self.assertEqual((yield get_val(1, 'smtp_password')), 'globaleaks')

    @inlineCallbacks
    def test_put_with_authentication_and_no_password_at_all_is_refused(self):
        # only the default profile, which inherits from nobody, can be left without a password
        response = yield self.put_smtp1(tid=DEFAULT_PROFILE_ID, authentication=False)
        self.assertFalse(response['password_set'])

        yield self.assertFailure(self.put_smtp1(tid=DEFAULT_PROFILE_ID, authentication=True),
                                 errors.InputValidationError)

        response = yield self.put_smtp1(tid=DEFAULT_PROFILE_ID, authentication=True, password='widdlyscuds')
        self.assertTrue(response['password_set'])

    @inlineCallbacks
    def test_put_of_the_secondary_server(self):
        handler = self.request(role='admin')
        desc = yield handler.get('smtp2')

        desc['enabled'] = True
        desc['template_types'] = ['tip', 'tip_update']
        desc['server'] = stuff
        desc['password'] = ''

        handler = self.request(desc, role='admin')
        response = yield handler.put('smtp2')
        self.assertTrue(response['enabled'])
        self.assertEqual(response['template_types'], ['tip', 'tip_update'])
        self.assertEqual((yield get_val(1, 'smtp2_server')), stuff)
        self.assertEqual((yield get_val(1, 'smtp_server')), 'mail.globaleaks.org')
        self.assertEqual((yield logged(1, 'update_smtp2')), 1)

    @inlineCallbacks
    def test_delete_brings_the_server_back_to_the_defaults(self):
        yield self.test_put_of_the_secondary_server()

        handler = self.request(role='admin')
        response = yield handler.delete('smtp2')
        self.assertEqual(response['server'], 'mail.globaleaks.org')
        self.assertEqual((yield get_val(1, 'smtp2_password')), 'globaleaks')
        self.assertEqual((yield logged(1, 'reset_smtp2')), 1)

        # whether the server is in use, and for which notifications, is not a part of the server
        self.assertTrue(response['enabled'])
        self.assertEqual(response['template_types'], ['tip', 'tip_update'])


class TestSMTPOfASiteNamingAProfile(helpers.TestHandlerWithPopulatedDB):
    """
    A site naming a profile writes only what the profile leaves free
    """
    _handler = admin.notification.SMTPInstance

    @inlineCallbacks
    def setUp(self):
        yield helpers.TestHandlerWithPopulatedDB.setUp(self)

        profile = yield tenant.create({'name': 'A profile',
                                       'active': True,
                                       'subdomain': '',
                                       'profile': 'default'}, is_profile=True)

        yield self.name_the_profile(2, profile['id'])

        # the handler reads the tenant from the cache, and the profile has just been created
        yield db.refresh_tenant_cache()

    @transact
    def name_the_profile(self, session, tid, pid):
        db_set_config_variable(session, tid, 'profile', db_get_config_variable(session, pid, 'uuid'))

    @inlineCallbacks
    def test_the_server_the_profile_holds_is_not_written(self):
        handler = self.request(role='admin', tid=2)
        desc = yield handler.get('smtp1')

        desc['server'] = stuff
        desc['password'] = 'widdlyscuds'

        handler = self.request(desc, role='admin', tid=2)
        response = yield handler.put('smtp1')
        self.assertEqual(response['server'], 'mail.globaleaks.org')
        self.assertEqual((yield get_val(2, 'smtp_password')), 'globaleaks')


class TestNotificationOfTheMails(helpers.TestHandlerWithPopulatedDB):
    @inlineCallbacks
    def test_the_mails_are_composed_without_the_passwords(self):
        notification = yield tw(admin.notification.db_get_notification, 1, 'en')
        self.assertNotIn('smtp_password', notification)
        self.assertNotIn('smtp2_password', notification)
        self.assertIn('smtp2_template_types', notification)
        self.assertIn('tip_mail_title', notification)
