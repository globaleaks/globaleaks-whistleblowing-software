
from datetime import timedelta

from globaleaks import models
from twisted.internet.defer import inlineCallbacks

from globaleaks.handlers import analyst
from globaleaks.orm import transact
from globaleaks.tests import helpers


class TestStatistics(helpers.TestHandlerWithPopulatedDB):
    _handler = analyst.Statistics

    @inlineCallbacks
    def setUp(self):
        yield helpers.TestHandlerWithPopulatedDB.setUp(self)
        yield self.perform_full_submission_actions()

    @transact
    def set_tip_status_log_dates(self, session, tip_id, opened_after_seconds, closed_after_seconds):
        tip = session.query(models.InternalTip).filter(models.InternalTip.id == tip_id).one()
        status_logs = session.query(models.AuditLog) \
                             .filter(models.AuditLog.object_id == tip_id,
                                     models.AuditLog.type == 'update_report_status') \
                             .order_by(models.AuditLog.date.asc()).all()

        opened_log = None
        closed_log = None
        for log in status_logs:
            status = log.data.get('status') if isinstance(log.data, dict) else None
            if status == 'opened' and opened_log is None:
                opened_log = log
            elif status == 'closed' and closed_log is None:
                closed_log = log

        self.assertIsNotNone(opened_log)
        self.assertIsNotNone(closed_log)

        opened_log.date = tip.creation_date + timedelta(seconds=opened_after_seconds)
        closed_log.date = opened_log.date + timedelta(seconds=closed_after_seconds)

    @transact
    def set_tip_comment_dates(self, session, recipient_after_seconds, whistleblower_after_seconds):
        tip_rows = session.query(models.InternalTip.id, models.InternalTip.creation_date).all()

        for tip_id, creation_date in tip_rows:
            comment_rows = session.query(models.Comment) \
                                  .filter(models.Comment.internaltip_id == tip_id) \
                                  .order_by(models.Comment.creation_date.asc()).all()

            recipient_comment = None
            whistleblower_comment = None
            for comment in comment_rows:
                if comment.author_id is None and whistleblower_comment is None:
                    whistleblower_comment = comment
                elif comment.author_id is not None and recipient_comment is None:
                    recipient_comment = comment

            self.assertIsNotNone(recipient_comment)
            self.assertIsNotNone(whistleblower_comment)

            recipient_comment.creation_date = creation_date + timedelta(seconds=recipient_after_seconds)
            whistleblower_comment.creation_date = creation_date + timedelta(seconds=whistleblower_after_seconds)

    @inlineCallbacks
    def test_get(self):
        handler = self.request(user_id=self.dummy_analyst['id'], role='analyst')
        stats = yield handler.get()
        self.assertEqual(stats['reports_count'], 2)
        self.assertEqual(stats['reports_with_no_access'], 2)
        self.assertEqual(stats['reports_anonymous'], 2)
        self.assertEqual(stats['reports_subscribed'], 0)
        self.assertEqual(stats['reports_initially_anonymous'], 0)
        self.assertEqual(stats['reports_mobile'], 0)
        self.assertEqual(stats['reports_tor'], 2)


    @transact
    def add_receiver_file(self, session, after_seconds):
        tip = session.query(models.InternalTip).first()

        rfile = models.ReceiverFile()
        rfile.internaltip_id = tip.id
        rfile.name = 'reply.pdf'
        rfile.size = 100
        rfile.content_type = 'application/pdf'
        rfile.creation_date = tip.creation_date + timedelta(seconds=after_seconds)
        session.add(rfile)


    @transact
    def get_a_tip_day(self, session):
        return session.query(models.InternalTip).first().creation_date.strftime('%Y-%m-%d')


class TestStatisticalTemplates(helpers.TestHandlerWithPopulatedDB):
    _handler = analyst.StatisticalReportTemplates

    permissions = {'can_configure_statistical_report_templates': True}

    def analyst(self, body='', handler_cls=None, permissions=None):
        return self.request(body,
                            user_id=self.dummy_analyst['id'],
                            role='analyst',
                            permissions=permissions,
                            handler_cls=handler_cls)
