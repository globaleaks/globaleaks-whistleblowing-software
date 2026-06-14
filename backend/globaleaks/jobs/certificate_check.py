import random
import time

from datetime import datetime, timedelta

from twisted.internet.defer import inlineCallbacks

from OpenSSL.crypto import load_certificate, FILETYPE_PEM

from globaleaks.handlers.admin.https import db_acme_cert_request, db_load_tls_config
from globaleaks.handlers.admin.node import db_admin_serialize_node
from globaleaks.handlers.admin.notification import db_get_notification
from globaleaks.handlers.admin.user import db_get_users
from globaleaks.jobs.job import DailyJob
from globaleaks.orm import transact
from globaleaks.utils import letsencrypt
from globaleaks.utils.log import log
from globaleaks.utils.utility import deferred_sleep


class CertificateCheck(DailyJob):
    interval = 24 * 3600

    # Notify about failing HTTPS renewal starting from a week before
    # expiration. This setting is choosen as the half of the
    # letsencrypt renewal threshold. This particular choice is intended
    # to limit the number of email sent enabling up 7 days of failing
    # retries without sending emails.

    notify_expr_within = 7
    acme_try_renewal = 14

    @transact
    def certificate_mail_creation(self, session, mail_type, tid, expiration_date):
        notif = self.state.tenants[tid].cache.notification
        if notif and not notif.enable_admin_notification_emails:
            return

        for user_desc in db_get_users(session, tid, 'admin'):
            if not user_desc['notification']:
                continue

            lang = user_desc['language']

            template_vars = {
                'type': mail_type,
                'node': db_admin_serialize_node(session, tid, lang),
                'notification': db_get_notification(session, tid, lang),
                'expiration_date': expiration_date,
                'user': user_desc,
            }

            self.state.format_and_send_mail(session, tid, user_desc['mail_address'], template_vars)

    @transact
    def renew_certificate(self, session, tid):
        try:
            db_acme_cert_request(session, tid)
        except Exception as e:
            log.err('Automatic HTTPS renewal failed (%s)', e, tid=tid)
            return False

        return db_load_tls_config(session, tid)

    @inlineCallbacks
    def operation(self):
        # Randomize the execution of certificates checks and renewals
        # https://letsencrypt.org/docs/faq/#why-should-my-let-s-encrypt-acme-client-run-at-a-random-time
        yield deferred_sleep(random.randint(1, 3) * 3600 + random.randint(900, 2700))  # noqa: S311 - non-crypto renewal-time randomization per Let's Encrypt guidance

        # Update start time in relation to delayed daily random start
        self.start_time = int(time.time() * 1000)

        now = datetime.now()

        for tid in self.state.tenants.keys():
            if not self.state.tenants[tid].cache['https_enabled']:
                continue

            cert = load_certificate(FILETYPE_PEM, self.state.tenants[tid].cache['https_cert'])
            expiration_date = letsencrypt.convert_asn1_date(cert.get_notAfter())
            if self.state.tenants[tid].cache['acme'] and now > expiration_date - timedelta(self.acme_try_renewal):
                tls_config = yield self.renew_certificate(tid)

                if tls_config:
                    self.state.snimap.unload(tid)
                    self.state.snimap.load(tid, tls_config)
                else:
                    # Send an email to the admin cause this requires user intervention
                    if now > expiration_date - timedelta(self.notify_expr_within) and \
                        not self.state.tenants[tid].cache.notification.enable_notification_emails_admin:
                        yield self.certificate_mail_creation('https_certificate_renewal_failure', tid, expiration_date)

            # Regular certificates expiration checks
            elif now > expiration_date - timedelta(self.notify_expr_within):
                log.info('The HTTPS Certificate is expiring on %s', expiration_date, tid=tid)
                if not self.state.tenants[tid].cache.notification.enable_notification_emails_admin:
                    yield self.certificate_mail_creation('https_certificate_expiration', tid, expiration_date)

            yield deferred_sleep(15)
