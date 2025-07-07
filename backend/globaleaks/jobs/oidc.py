# Implement reset of variables related to sessions
from globaleaks.jobs.job import LoopingJob

__all__ = ['OIDC']


class OIDC(LoopingJob):
    interval = 60
    monitor_interval = 10

    def operation(self):
        """
        This scheduler is responsible for:
            - Reset of failed login attempts counters
        """
        return self.state.oidcauth.fetch_jwks()
