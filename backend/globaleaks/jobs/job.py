import contextlib
import time

from twisted.internet import task, defer, reactor

from globaleaks.state import State, extract_exception_traceback_and_schedule_email
from globaleaks.utils.log import log
from globaleaks.utils.utility import datetime_now
from twisted.internet.defer import inlineCallbacks, returnValue

TRACK_LAST_N_EXECUTIONS = 10


class Job(task.LoopingCall):
    state = State
    interval = 1
    low_time = -1
    high_time = -1
    mean_time = -1
    start_time = -1
    active = None
    last_executions = []

    def __init__(self):
        self.name = self.__class__.__name__

        task.LoopingCall.__init__(self, self.run)

        self.clock = reactor

        self._scheduled_call = None
        self.schedule()

    def schedule(self):
        # (Re)arm the next run using the current get_delay()/interval. Calling
        # this again (e.g. after a configuration change) cancels any pending
        # start so the job is never armed twice.
        if self._scheduled_call is not None and self._scheduled_call.active():
            self._scheduled_call.cancel()

        delay = self.get_delay()
        delay = delay if delay > 0 else 0
        self._scheduled_call = self.clock.callLater(delay, self.start, self.interval)
        self.state.jobs_status[self.name] = {"status": "pending", "execution_time": 0}

    def start(self, interval):
        task.LoopingCall.start(self, interval)
        self.state.jobs_status[self.name]["status"] = "running"

    def stop(self):
        if self.running:
            task.LoopingCall.stop(self)
            self.state.jobs_status[self.name]["status"] = "stopped"

        return self.active if self.active is not None else defer.succeed(None)

    @defer.inlineCallbacks
    def run(self):
        try:
            self.begin()

            try:
                yield self.operation()
            except Exception as e:
                if not self.state.shutdown:
                    self.on_error(e)

        finally:
            # always call end, even if operation() or on_error() raises
            # Best-effort cleanup: swallow application errors so that shutdown
            # completes, while letting KeyboardInterrupt/SystemExit propagate
            # (contextlib.suppress(Exception) does not catch those).
            if self.active is not None:
                with contextlib.suppress(Exception):
                    self.end()

    def begin(self):
        self.active = defer.Deferred()
        self.start_time = int(time.time() * 1000)

    def end(self):
        end_time = int(time.time() * 1000)
        self.last_executions = self.last_executions[:TRACK_LAST_N_EXECUTIONS - 1]
        self.last_executions.append((self.start_time, end_time))

        current_run_time = end_time - self.start_time

        # discard empty cycles from stats
        if self.mean_time == -1:
            self.mean_time = current_run_time
        else:
            self.mean_time = (self.mean_time * 0.7) + (current_run_time * 0.3)

        if self.low_time == -1 or current_run_time < self.low_time:
            self.low_time = current_run_time

        if self.high_time == -1 or current_run_time > self.high_time:
            self.high_time = current_run_time

        self.active.callback(None)
        self.active = None
        self.state.jobs_status[self.name]["execution_time"] = round((end_time - self.start_time) / 1000, 2)
        self.state.jobs_status[self.name]["status"] = "idle" if self.running else "stopped"

    def operation(self):
        return

    def get_delay(self):
        return 0

    def on_error(self, excep):
        log.err("Exception while running %s" % self.name)
        log.exception(excep)
        extract_exception_traceback_and_schedule_email(excep)
        self.state.jobs_status[self.name]["status"] = "failed"


class LoopingJob(Job):
    interval = 60

    # The minimum interval (seconds) the job has taken to execute before an
    # exception will be recorded. If the job does not finish, every monitor_interval
    # after the first exception another will be generated.
    monitor_interval = 60
    monitor_period = 5 * 60
    last_monitor_check_failed = 0  # Epoch start

    def on_error(self, excep):
        error = "Job %s died with runtime %.4f [low: %.4f, high: %.4f]" % \
                (self.name, self.mean_time, self.low_time, self.high_time)
        log.err(error)
        log.exception(excep)
        extract_exception_traceback_and_schedule_email(excep)


class PeriodJob(LoopingJob):
    interval = 3600
    monitor_interval = 5 * 60

    def get_delay(self):
        current_time = datetime_now()
        return 3600 - (current_time.minute * 60) - current_time.second

class MinutelyJob(LoopingJob):
    interval = 60
    monitor_interval = 10

    def get_delay(self):
        current_time = datetime_now()
        return 60 - current_time.second


class HourlyJob(LoopingJob):
    interval = 3600
    monitor_interval = 5 * 60

    def get_delay(self):
        current_time = datetime_now()
        return 3600 - (current_time.minute * 60) - current_time.second


class DailyJob(LoopingJob):
    interval = 24 * 3600
    monitor_interval = 3600

    def get_delay(self):
        current_time = datetime_now()
        return (3600 * 24) - (current_time.hour * 3600) - (current_time.minute * 60) - current_time.second


class JobsMonitor(LoopingJob):
    interval = 1

    def __init__(self, jobs_list):
        LoopingJob.__init__(self)
        self.jobs_list = jobs_list

    def operation(self):
        current_time = time.time()

        error_msg = ""
        for job in self.jobs_list:
            if job.active is None:
                continue

            execution_time = current_time - job.start_time

            time_from_last_failed_check = current_time - job.last_monitor_check_failed

            if (execution_time > job.monitor_interval
                and time_from_last_failed_check > job.monitor_interval):

                job.last_monitor_check_failed = current_time

                if execution_time < 60:
                    error = "Job %s is taking more than %d seconds to execute" % (job.name, execution_time)
                elif execution_time < 3600:
                    minutes = execution_time // 60
                    error = "Job %s is taking more than %d minutes to execute" % (job.name, minutes)
                else:
                    hours = execution_time // 3600
                    error = "Job %s is taking more than %d hours to execute" % (job.name, hours)
                error_msg += error + '\n'
                log.err(error)

        if error_msg:
            self.state.schedule_exception_email(1, error_msg)

def get_job_instance_by_name(name):
    for job in State.jobs:
        if job.name == name:
            return job
    return None


@inlineCallbacks
def start_job(name):
    job = get_job_instance_by_name(name)
    if job and not job.running:
        yield job.start(job.interval)
        State.jobs_status[name]["status"] = "running"
        returnValue(True)
    returnValue(False)


@inlineCallbacks
def stop_job(name):
    job = get_job_instance_by_name(name)
    if job and job.running:
        yield job.stop()
        State.jobs_status[name]["status"] = "stopped"
        returnValue(True)
    returnValue(False)


def reschedule_job(name):
    # Re-arm a job so that a configuration change affecting its schedule
    # (e.g. the backup time/period) is picked up: the looping is stopped and
    # the next run is recomputed via get_delay(). The in-flight run, if any, is
    # left to complete on its own (its deferred is intentionally not awaited)
    # so callers are never blocked by a long-running operation.
    job = get_job_instance_by_name(name)
    if job is None:
        return False

    if job.running:
        job.stop()

    job.schedule()
    return True
