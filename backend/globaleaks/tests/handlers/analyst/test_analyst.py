from datetime import timedelta

from globaleaks import models
from twisted.internet.defer import inlineCallbacks

from globaleaks.handlers import analyst
from globaleaks.handlers.recipient import rtip
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
        handler = self.request(user_id=self.dummyAnalyst['id'], role='analyst')
        stats = yield handler.get()
        self.assertEqual(stats['reports_count'], 2)
        self.assertEqual(stats['reports_with_no_access'], 2)
        self.assertEqual(stats['reports_anonymous'], 2)
        self.assertEqual(stats['reports_subscribed'], 0)
        self.assertEqual(stats['reports_initially_anonymous'], 0)
        self.assertEqual(stats['reports_mobile'], 0)
        self.assertEqual(stats['reports_tor'], 2)

    @inlineCallbacks
    def test_closure_time_preserves_short_intervals(self):
        rtip_desc = (yield self.get_rtips())[0]

        for status in ('opened', 'closed'):
            operation = {
              'operation': 'update_status',
              'args': {
                'status': status,
                'substatus': '',
                'motivation': ''
              }
            }

            handler = self.request(operation,
                                   role='receiver',
                                   user_id=rtip_desc['receiver_id'],
                                   handler_cls=rtip.RTipInstance)
            yield handler.put(rtip_desc['id'])
            self.assertEqual(handler.request.code, 200)

        yield self.set_tip_status_log_dates(rtip_desc['id'], 5, 10)

        handler = self.request(user_id=self.dummyAnalyst['id'], role='analyst')
        stats = yield handler.get()

        self.assertAlmostEqual(stats['avg_closure_time_hours'], 10 / 3600.0, places=4)

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

    @inlineCallbacks
    def test_first_reply_uses_first_recipient_response(self):
        yield self.set_tip_comment_dates(5 * 60, 15 * 60)

        handler = self.request(user_id=self.dummyAnalyst['id'], role='analyst')
        stats = yield handler.get()

        self.assertAlmostEqual(stats['avg_first_reply_time_hours'], 5 / 60.0, places=4)

    @transact
    def get_a_tip_day(self, session):
        return session.query(models.InternalTip).first().creation_date.strftime('%Y-%m-%d')

    @inlineCallbacks
    def test_date_filter_includes_the_last_day(self):
        day = yield self.get_a_tip_day()

        handler = self.request({'date_from': day, 'date_to': day},
                               user_id=self.dummyAnalyst['id'], role='analyst')
        stats = yield handler.post()

        self.assertEqual(stats['reports_count'], 2)

    @inlineCallbacks
    def test_first_reply_considers_receiver_files(self):
        yield self.set_tip_comment_dates(5 * 60, 15 * 60)
        yield self.add_receiver_file(2 * 60)

        handler = self.request(user_id=self.dummyAnalyst['id'], role='analyst')
        stats = yield handler.get()

        # One tip replied via file after 2 minutes, the other via comment after 5
        self.assertAlmostEqual(stats['avg_first_reply_time_hours'], (2 + 5) / 2 / 60.0, places=4)
