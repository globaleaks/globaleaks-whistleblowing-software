# -*- coding: utf-8 -*-
#
# Implement anomalies check
from twisted.internet.defer import inlineCallbacks

from globaleaks.handlers.admin.node import db_admin_serialize_node
from globaleaks.handlers.admin.notification import db_get_notification
from globaleaks.handlers.admin.user import db_get_users
from globaleaks.orm import transact
from globaleaks.rest.cache import Cache
from globaleaks.state import State
from globaleaks.transactions import db_schedule_email
from globaleaks.utils.fs import get_disk_space
from globaleaks.utils.log import log
from globaleaks.utils.templating import Templating
from globaleaks.utils.utility import datetime_now, datetime_null, is_expired

ANOMALY_MAP = {
    'completed_submissions': 20,
    'failed_logins': 5,
    'successful_logins': 20
}


def get_disk_anomaly_conditions(free_workdir_bytes, total_workdir_bytes):
    free_disk_megabytes = free_workdir_bytes / (1024 * 1024)
    free_disk_percentage = free_workdir_bytes / (total_workdir_bytes / 100)

    def info_msg_0():
        return "free_disk_megabytes <= %d or free_disk_percentage <= %d" % \
               (State.tenants[1].cache.threshold_free_disk_megabytes_high,
                State.tenants[1].cache.threshold_free_disk_percentage_high)

    def info_msg_1():
        return "free_disk_megabytes <= %d or free_disk_percentage <= %d" % \
               (State.tenants[1].cache.threshold_free_disk_megabytes_low,
                State.tenants[1].cache.threshold_free_disk_percentage_low)

    # list of bad conditions ordered starting from the worst case scenario
    return [
        {
            'condition': free_disk_megabytes <= State.tenants[1].cache.threshold_free_disk_megabytes_high or
                         free_disk_percentage <= State.tenants[1].cache.threshold_free_disk_percentage_high,
            'info_msg': info_msg_0,
            'alarm_level': 2,
            'accept_submissions': False
        },
        {
            'condition': free_disk_megabytes <= State.tenants[1].cache.threshold_free_disk_megabytes_low or
                         free_disk_percentage <= State.tenants[1].cache.threshold_free_disk_percentage_low,
            'info_msg': info_msg_1,
            'alarm_level': 1,
            'accept_submissions': True
        }
    ]


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


class Alarm(object):
    def __init__(self):
        self.last_alarm_email = datetime_null()

        self.event_matrix = {}

        self.measured_freespace = 0
        self.measured_totalspace = 0

        self.alarm_levels = {
            'disk_space': 0,
            'disk_message': None,
            'activity': 0
        }

    @inlineCallbacks
    def check_tenant_anomalies(self, tid):
        """
        This function update the Alarm level.

        """
        number_of_anomalies = 0

        self.event_matrix.clear()

        for event in State.tenants[tid].RecentEventQ:
            self.event_matrix.setdefault(event.event_type, 0)
            self.event_matrix[event.event_type] += 1

        for event_name, threshold in ANOMALY_MAP.items():
            if event_name in self.event_matrix:
                if self.event_matrix[event_name] > threshold:
                    number_of_anomalies += 1

        previous_activity_sl = self.alarm_levels['activity']

        log_function = log.debug
        self.alarm_levels['activity'] = 0

        if number_of_anomalies == 1:
            log_function = log.info
            self.alarm_levels['activity'] = 1
        elif number_of_anomalies > 1:
            log_function = log.info
            self.alarm_levels['activity'] = 2

        # if there are some anomaly or we're nearby, record it.
        if number_of_anomalies >= 1 or self.alarm_levels['activity'] >= 1:
            State.tenants[tid].AnomaliesQ.append(
                [datetime_now(), self.event_matrix, self.alarm_levels['activity']])

        if previous_activity_sl != self.alarm_levels['activity']:
            log_function("Alarm level changed from %d => %d" %
                         (previous_activity_sl,
                          self.alarm_levels['activity']))

        if State.tenants[1].cache.notification.enable_notification_emails_admin:
            return

        if not (self.alarm_levels['activity'] or self.alarm_levels['disk_space']):
            return

        if not is_expired(self.last_alarm_email, minutes=120):
            return

        self.last_alarm_email = datetime_now()

        alert = {
            'alarm_levels': self.alarm_levels,
            'measured_freespace': self.measured_freespace,
            'measured_totalspace': self.measured_totalspace,
            'event_matrix': self.event_matrix
        }

        yield generate_admin_alert_mail(tid, alert)

    def check_disk_anomalies(self):
        """
        Here in Alarm is written the threshold to say if we're in disk alarm
        or not. Therefore the function "report" the amount of free space and
        the evaluation + alarm shift is performed here.

        workingdir: is performed a percentage check (at least 1% and an absolute comparison)

        "unusable node" threshold: happen when the space is really shitty.
        https://github.com/globaleaks/globaleaks-whistleblowing-software/issues/297
        https://github.com/globaleaks/globaleaks-whistleblowing-software/issues/872
        """
        self.measured_freespace, self.measured_totalspace = get_disk_space(State.settings.working_path)

        disk_space = 0
        disk_message = ""
        accept_submissions = True
        old_accept_submissions = State.accept_submissions

        for c in get_disk_anomaly_conditions(self.measured_freespace, self.measured_totalspace):
            if not c['condition']:
                continue

            disk_space = c['alarm_level']

            info_msg = c['info_msg']()

            if disk_space == 2:
                disk_message = "[FATAL] Disk anomaly, submissions disabled: %s" % info_msg
            else:  # == 1
                disk_message = "[WARNING]: Disk anomaly: %s" % info_msg

            accept_submissions = c['accept_submissions']
            break

        # This check is temporarily, want to be verified that the switch can be
        # logged as part of the Anomalies via this function
        old_alarm_level = self.alarm_levels['disk_space']
        if old_alarm_level != disk_space:
            if disk_message:
                log.err(disk_message)
            else:
                log.err("Available disk space returned to normal levels")

        # the value is set here with a single assignment in order to
        # minimize possible race conditions resetting/settings the values
        self.alarm_levels['disk_space'] = disk_space
        self.alarm_levels['disk_message'] = disk_message

        State.accept_submissions = accept_submissions

        if old_accept_submissions != State.accept_submissions:
            log.info("Switching disk space availability from: %s to %s",
                     old_accept_submissions, accept_submissions)

            # Must invalidate the cache here becuase accept_subs served in /public has changed
            Cache.invalidate()


@inlineCallbacks
def check_anomalies():
    State.tenants[1].Alarm.check_disk_anomalies()

    for tid in State.tenants:
        yield State.tenants[tid].Alarm.check_tenant_anomalies(tid)
