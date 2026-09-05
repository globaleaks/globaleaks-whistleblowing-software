from datetime import datetime, timedelta
from unittest.mock import patch

from OpenSSL.crypto import FILETYPE_PEM, load_certificate
from twisted.internet.defer import inlineCallbacks, succeed

from globaleaks import models
from globaleaks.db import refresh_tenant_cache
from globaleaks.handlers.admin import https
from globaleaks.jobs import certificate_check
from globaleaks.jobs.certificate_check import CertificateCheck
from globaleaks.models.config import ConfigFactory
from globaleaks.orm import transact
from globaleaks.tests import helpers
from globaleaks.utils import letsencrypt

EXPIRATION = letsencrypt.convert_asn1_date(
    load_certificate(FILETYPE_PEM, helpers.HTTPS_DATA['cert']).get_notAfter())


def days_before_expiration(days):
    """
    A clock stopped the given number of days before the certificate expires
    """
    moment = EXPIRATION - timedelta(days=days)

    class Now(datetime):
        @classmethod
        def now(cls, tz=None):
            return moment

    return Now


class TestCertificateCheck(helpers.TestGLWithPopulatedDB):
    """
    The certificate of a site is watched: one issued by the ACME CA is renewed
    on its own two weeks before it expires, and one that cannot be renewed has
    the administrators of the site warned in its last week of validity.
    """
    @inlineCallbacks
    def setUp(self):
        yield super().setUp()

        yield self.configure_https(acme=False)

        # the map of the served configurations is global to the process: what a
        # test before has left in it would answer for this one
        self.state.snimap.configs_by_tid.clear()

        self.job = CertificateCheck()

    @transact
    def db_configure_https(self, session, acme):
        config = ConfigFactory(session, 1)
        config.set_val('https_enabled', True)
        config.set_val('https_key', helpers.HTTPS_DATA['key'])
        config.set_val('https_cert', helpers.HTTPS_DATA['cert'])
        config.set_val('https_chain', helpers.HTTPS_DATA['chain'])
        config.set_val('acme', acme)

    @inlineCallbacks
    def configure_https(self, acme):
        yield self.db_configure_https(acme)
        yield refresh_tenant_cache()

    @inlineCallbacks
    def check(self, days):
        with patch.object(certificate_check, 'deferred_sleep', lambda _: succeed(None)), \
             patch.object(certificate_check, 'datetime', days_before_expiration(days)):
            yield self.job.operation()

    @inlineCallbacks
    def renewal(self, days, outcome):
        with patch.object(https.letsencrypt, 'request_new_certificate', **outcome) as request:
            yield self.check(days)

        return request

    @inlineCallbacks
    def test_a_certificate_far_from_its_expiration_raises_no_alarm(self):
        yield self.check(30)

        yield self.test_model_count(models.Mail, 0)

    @inlineCallbacks
    def test_the_admins_are_warned_in_the_last_week_of_validity(self):
        yield self.check(3)

        yield self.test_model_count(models.Mail, 1)

    @transact
    def admins_opt_out_of_notifications(self, session):
        session.query(models.User).filter(models.User.tid == 1, models.User.role == 'admin') \
                                  .update({'notification': False})

    @inlineCallbacks
    def test_only_the_admins_who_asked_for_notifications_are_warned(self):
        yield self.admins_opt_out_of_notifications()

        yield self.check(3)

        yield self.test_model_count(models.Mail, 0)

    @inlineCallbacks
    def test_the_warning_is_withheld_when_admin_notifications_are_off(self):
        self.state.tenants[1].cache.notification.enable_admin_notification_emails = False

        yield self.check(3)

        yield self.test_model_count(models.Mail, 0)

    @inlineCallbacks
    def test_a_site_without_https_is_not_checked(self):
        self.state.tenants[1].cache.https_enabled = False
        # were it looked at, this would not even parse
        self.state.tenants[1].cache.https_cert = 'not a certificate'

        yield self.check(3)

        yield self.test_model_count(models.Mail, 0)

    @inlineCallbacks
    def test_an_acme_certificate_is_renewed_two_weeks_before_its_expiration(self):
        yield self.configure_https(acme=True)

        request = yield self.renewal(10, {'return_value': (helpers.HTTPS_DATA['cert'],
                                                           helpers.HTTPS_DATA['chain'])})

        request.assert_called_once()
        self.assertEqual(request.call_args[0][0], self.state.tenants[1].cache.hostname)
        # the site is served with what the CA issued, without a restart
        self.assertEqual(self.state.snimap.configs_by_tid[1]['ssl_cert'],
                         helpers.HTTPS_DATA['cert'])
        yield self.test_model_count(models.Mail, 0)

    @inlineCallbacks
    def test_an_acme_certificate_not_yet_due_is_left_as_it_is(self):
        yield self.configure_https(acme=True)

        request = yield self.renewal(20, {'return_value': None})

        request.assert_not_called()
        yield self.test_model_count(models.Mail, 0)

    @inlineCallbacks
    def test_a_failed_renewal_is_retried_in_silence_until_the_last_week(self):
        yield self.configure_https(acme=True)

        request = yield self.renewal(10, {'side_effect': Exception('the CA is unreachable')})

        request.assert_called_once()
        self.assertNotIn(1, self.state.snimap.configs_by_tid)
        yield self.test_model_count(models.Mail, 0)

    @inlineCallbacks
    def test_a_renewal_still_failing_in_the_last_week_is_reported_to_the_admins(self):
        yield self.configure_https(acme=True)

        yield self.renewal(3, {'side_effect': Exception('the CA is unreachable')})

        yield self.test_model_count(models.Mail, 1)

    @inlineCallbacks
    def test_a_renewal_that_fails_yields_no_configuration(self):
        yield self.configure_https(acme=True)

        with patch.object(https.letsencrypt, 'request_new_certificate',
                          side_effect=Exception('the CA is unreachable')):
            tls_config = yield self.job.renew_certificate(1)

        self.assertFalse(tls_config)
