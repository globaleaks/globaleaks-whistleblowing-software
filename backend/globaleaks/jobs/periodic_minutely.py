# -*- coding: utf-8 -*-
# Implement set of actions statistics actions executed on an minutely basis
from globaleaks.jobs.job import MinutelyJob

__all__ = ['Periodic-Minutely']


class PeriodicMinutely(MinutelyJob):
    """
    Minutely
    """
    def operation(self):
        # Minutely Resets
        self.state.reset_minutely()
