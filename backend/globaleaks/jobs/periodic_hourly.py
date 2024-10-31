# -*- coding: utf-8 -*-
# Implement set of actions statistics actions executed on an hourly basis
from globaleaks.jobs.job import HourlyJob

__all__ = ['Periodic-Hourly']


class PeriodicHourly(HourlyJob):
    """
    Hourly
    """
    def operation(self):
        # Hourly Resets
        self.state.reset_hourly()
