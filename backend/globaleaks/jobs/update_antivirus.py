import shutil
from twisted.internet.defer import succeed

from globaleaks.jobs.job import LoopingJob
from globaleaks.utils.antivirus import launch_freshclam
from globaleaks.utils.log import log


class UpdateAntivirus(LoopingJob):
    interval = 60*60*24

    def __init__(self):
        self.process = None
        super().__init__()

    def _clear_process(self, _):
        self.process = None
        return _

    def stop(self):
        stop_deferred = super().stop()

        if self.process is None:
            return stop_deferred or succeed(None)

        process = self.process
        self.process = None
        return process.stop()

    def operation(self):
        log.debug('Fetching latest antivirus database')

        if shutil.which("clamd"):
            self.process = launch_freshclam(self.state.settings.conf_freshclam, self.state.settings.devel_mode)
            self.process.deferred.addBoth(self._clear_process)
            return self.process.deferred
