# -*- coding: utf-8 -*-
# Implements periodic checks in order to verify pgp key status and other consistencies:

from datetime import timedelta

from globaleaks import models
from globaleaks.handlers.admin.node import db_admin_serialize_node
from globaleaks.handlers.admin.notification import db_get_notification
from globaleaks.handlers.admin.user import db_get_users
from globaleaks.handlers.user import user_serialize_user
from globaleaks.jobs.job import DailyJob
from globaleaks.orm import transact
from globaleaks.transactions import db_schedule_email
from globaleaks.utils.log import log
from globaleaks.utils.templating import Templating
from globaleaks.utils.utility import datetime_now, datetime_null

__all__ = ['PGPCheck']


def db_get_expired_or_expiring_pgp_users(session, tids_list):
    threshold = datetime_now() + timedelta(15)

    return session.query(models.User).filter(models.User.pgp_key_public != '',
                                             models.User.pgp_key_expiration != datetime_null(),
                                             models.User.pgp_key_expiration < threshold,
                                             models.User.tid.in_(tids_list))


class PGPCheck(DailyJob):
    monitor_interval = 5 * 60

    def prepare_admin_pgp_alerts(self, session, tid, expired_or_expiring):
        for user_desc in db_get_users(session, tid, 'admin'):
            user_language = user_desc['language']

            data = {
                'type': 'admin_pgp_alert',
                'node': db_admin_serialize_node(session, tid, user_language),
                'notification': db_get_notification(session, tid, user_language),
                'users': expired_or_expiring,
                'user': user_desc,
            }

            subject, body = Templating().get_mail_subject_and_body(data)

            db_schedule_email(session, tid, data['user']['mail_address'], subject, body)

    def prepare_user_pgp_alerts(self, session, tid, user_desc):
        user_language = user_desc['language']

        data = {
            'type': 'pgp_alert',
            'node': db_admin_serialize_node(session, tid, user_language),
            'notification': db_get_notification(session, tid, user_language),
            'user': user_desc
        }

        subject, body = Templating().get_mail_subject_and_body(data)

        db_schedule_email(session, tid, user_desc['mail_address'], subject, body)

    @transact
    def perform_pgp_validation_checks(self, session):
        tenant_expiry_map = {1: []}

        for user in db_get_expired_or_expiring_pgp_users(session, self.state.tenants.keys()):
            user_desc = user_serialize_user(session, user, user.language)
            tenant_expiry_map.setdefault(user.tid, []).append(user_desc)

            log.info('Removing expired PGP key of: %s', user.username, tid=user.tid)
            if user.pgp_key_expiration < datetime_now():
                user.pgp_key_public = ''
                user.pgp_key_fingerprint = ''
                user.pgp_key_expiration = datetime_null()

        for tid, expired_or_expiring in tenant_expiry_map.items():
            for user_desc in expired_or_expiring:
                self.prepare_user_pgp_alerts(session, tid, user_desc)

            if self.state.tenants[tid].cache.notification.enable_notification_emails_admin:
                continue

            if expired_or_expiring:
                self.prepare_admin_pgp_alerts(session, tid, expired_or_expiring)

    def operation(self):
        return self.perform_pgp_validation_checks()
