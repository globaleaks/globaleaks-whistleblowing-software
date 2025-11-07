from globaleaks.handlers import report
from globaleaks.tests import helpers


class TestReportHandler(helpers.TestHandler):
    _handler = report.ReportHandler

    def test_post(self):
        return self.request({}).post()

