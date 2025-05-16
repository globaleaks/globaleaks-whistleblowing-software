import shutil
from twisted.internet.defer import inlineCallbacks

from globaleaks.jobs.job import HourlyJob, LoopingJob
from globaleaks.utils.antivirus import launch_freshclam
from globaleaks.utils.log import log

class UpdateAntivirus(LoopingJob):
    interval = 60*60*24

    def operation(self):
        log.debug('Fetching latest antivirus database')

        if shutil.which("clamd"):
            return launch_freshclam(self.state.settings.conf_freshclam, self.state.settings.devel_mode)
