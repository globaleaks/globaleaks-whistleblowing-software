# Implement anomalies check
from twisted.internet.defer import inlineCallbacks

from globaleaks.handlers.admin.node import db_admin_serialize_node
from globaleaks.handlers.admin.notification import db_get_notification
from globaleaks.handlers.admin.user import db_get_users
from globaleaks.jobs.job import LoopingJob
from globaleaks.orm import transact
from globaleaks.rest.cache import Cache
from globaleaks.state import State
from globaleaks.transactions import db_schedule_email
from globaleaks.utils.fs import get_disk_space
from globaleaks.utils.log import log
from globaleaks.utils.templating import Templating


@transact
def generate_admin_alert_mail(session, tid, alert):
    for user_desc in db_get_users(session, tid, 'admin'):
        user_language = user_desc['language']

        data = {
            'type': 'admin_anomaly',
            'node': db_admin_serialize_node(session, tid, user_language),
            'notification': db_get_notification(session, tid, user_language),
            'alert': alert,
            'user': user_desc,
        }

        subject, body = Templating().get_mail_subject_and_body(data)

        db_schedule_email(session, tid, user_desc['mail_address'], subject, body)


@inlineCallbacks
def check_disk_space(free_workdir_bytes, total_workdir_bytes):
    free_disk_megabytes = free_workdir_bytes / (1024 * 1024)
    free_disk_percentage = free_workdir_bytes / (total_workdir_bytes / 100)

    accept_submissions = True
    alarm_level_disk = 0

    # list of bad conditions ordered starting from the worst case scenario
    if free_disk_megabytes <= State.tenants[1].cache.threshold_free_disk_megabytes_high or \
           free_disk_percentage <= State.tenants[1].cache.threshold_free_disk_percentage_high:
       alarm_level_disk = 1 # HIGH
       accept_submissions = False
    elif free_disk_megabytes <= State.tenants[1].cache.threshold_free_disk_megabytes_low or \
             free_disk_percentage <= State.tenants[1].cache.threshold_free_disk_percentage_low:
       alarm_level_disk = 2 # LOW

    if State.accept_submissions != accept_submissions:
        if accept_submissions:
             log.debug("Disabling submissions due to reduced space availability")
        else:
             log.debug("Re-enabling submission after resolved space limit")

        State.accept_submissions = accept_submissions

        # Must invalidate the cache here becuase accept_subs served in /public has changed
        Cache.invalidate()

        alert = {
            'alarm_level_disk': alarm_level_disk,
            'measured_freespace': free_workdir_bytes,
            'measured_totalspace': total_workdir_bytes,
        }

        yield generate_admin_alert_mail(1, alert)


class Anomalies(LoopingJob):
    """
    This job checks for anomalies and take care of saving them on the db.
    """
    interval = 60

    @inlineCallbacks
    def operation(self):
        free_workdir_bytes, total_workdir_bytes = get_disk_space(State.settings.working_path)
        yield check_disk_space(free_workdir_bytes, total_workdir_bytes)
