from twisted.internet.defer import inlineCallbacks

from globaleaks import models
from globaleaks.jobs import anomalies
from globaleaks.tests import helpers
from globaleaks.state import State

class TestAnomalies(helpers.TestGLWithPopulatedDB):
    def simulate_disk_space(self, free_bytes, total_bytes):
        # Patch get_disk_space to return fixed values
        anomalies.get_disk_space = lambda path: (free_bytes, total_bytes)

    @inlineCallbacks
    def test_accept_submissions_threshold_logic(self):
        state = State.tenants[1]

        # Set thresholds
        state.cache.threshold_free_disk_megabytes_high = 1000  # 1 GB
        state.cache.threshold_free_disk_percentage_high = 20
        state.cache.threshold_free_disk_megabytes_low = 2000   # 2 GB
        state.cache.threshold_free_disk_percentage_low = 40

        job = anomalies.Anomalies()
        job.state = state  # Ensure job uses tenant[1]'s state

        # Case 1: sufficient disk space (should do no-op)
        self.simulate_disk_space(free_bytes=5 * 1024 * 1024 * 1024, total_bytes=10 * 1024 * 1024 * 1024)  # 5GB free, 10GB total
        yield job.operation()
        self.assertTrue(State.accept_submissions)
        yield self.test_model_count(models.Mail, 0)

        # Case 2: critically low disk space (should disable submissions)
        self.simulate_disk_space(free_bytes=500 * 1024 * 1024, total_bytes=10 * 1024 * 1024 * 1024)  # 500MB free, 10GB total
        yield job.operation()
        self.assertFalse(State.accept_submissions)
        yield self.test_model_count(models.Mail, 1)

        # Case 3: sufficient disk space (should re-enable submissions)
        self.simulate_disk_space(free_bytes=5 * 1024 * 1024 * 1024, total_bytes=10 * 1024 * 1024 * 1024)  # 5GB free, 10GB total
        yield job.operation()
        self.assertTrue(State.accept_submissions)
        yield self.test_model_count(models.Mail, 2)
