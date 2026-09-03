from twisted.internet import task, defer

from globaleaks.state import State, extract_exception_traceback_and_schedule_email
from globaleaks.utils.log import log


class Service(task.LoopingCall):
    state = State

    def __init__(self):
        self.name = self.__class__.__name__

        task.LoopingCall.__init__(self, self.run)

        self.start(0)

    def stop(self):
        if self.running:
            task.LoopingCall.stop(self)

    @defer.inlineCallbacks
    def run(self):
        try:
            yield self.operation()
        except Exception as e:
            if not self.state.shutdown:
                self.on_error(e)

    def operation(self):
        return

    def on_error(self, excep):
        log.err(f"Exception while running {self.name}")
        log.exception(excep)
        extract_exception_traceback_and_schedule_email(excep)
