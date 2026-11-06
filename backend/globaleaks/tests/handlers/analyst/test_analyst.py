
from datetime import timedelta

from nacl.encoding import Base64Encoder
from twisted.internet.defer import inlineCallbacks

from globaleaks import models

from globaleaks.handlers import analyst
from globaleaks.handlers.admin.questionnaire import db_get_questionnaire
from globaleaks.orm import transact
from globaleaks.tests import helpers
from globaleaks.utils.crypto import GCE


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


def a_choice_of(fields):
    """
    Return the first choice among some fields of a questionnaire, at any depth
    """
    for field in fields:
        if field['type'] in models.STATISTICAL_CHOICE_TYPES:
            return field['id']

        found = a_choice_of(field['children'])
        if found:
            return found


@transact
def make_a_choice_statistical(session, analyst_id, questionnaire_id):
    """
    Turn a choice the reports answered into the instance of a statistical question template, and
    give the analyst the statistical key; return the template
    """
    analyst_user = session.get(models.User, analyst_id)
    analyst_user.crypto_global_stat_prv_key = Base64Encoder.encode(GCE.asymmetric_encrypt(helpers.USER_PUB_KEY, helpers.STAT_PRV_KEY))

    questionnaire = db_get_questionnaire(session, 1, questionnaire_id, 'en')
    field = session.get(models.Field, a_choice_of([f for step in questionnaire['steps'] for f in step['children']]))

    template = models.Field()
    template.tid = 1
    template.type = field.type
    template.instance = 'template'
    template.statistical = True
    template.label = {'en': 'Statistical question'}
    session.add(template)
    session.flush()

    field.instance = 'reference'
    field.template_id = template.id

    return template.id


@transact
def set_statistical(session, template_id, statistical):
    session.get(models.Field, template_id).statistical = statistical


@transact
def drop_stat_copies(session):
    session.query(models.InternalTip).update({'crypto_stat_tip_prv_key': ''})


class TestStatisticalAnswers(helpers.TestHandlerWithPopulatedDB):
    """
    The statistics open the answers of the reports through the copy of their key kept for the
    statistical key, and count what the statistical questions, as configured now, ask
    """
    _handler = analyst.Statistics

    @inlineCallbacks
    def setUp(self):
        yield helpers.TestHandlerWithPopulatedDB.setUp(self)
        yield self.perform_full_submission_actions()
        self.template_id = yield make_a_choice_statistical(self.dummy_analyst['id'], self.dummy_context['questionnaire_id'])

    @inlineCallbacks
    def answers_counted(self):
        stats = yield self.request(user_id=self.dummy_analyst['id'], role='analyst').get()
        metrics = {m['template_id']: m for m in stats['question_template_dropdown_metrics']}
        return metrics[self.template_id]['total_answers'] if self.template_id in metrics else 0

    @inlineCallbacks
    def test_the_answers_of_the_reports_are_counted(self):
        self.assertEqual((yield self.answers_counted()), 2)

    @inlineCallbacks
    def test_a_question_no_longer_statistical_is_not_counted(self):
        yield set_statistical(self.template_id, False)
        self.assertEqual((yield self.answers_counted()), 0)

    @inlineCallbacks
    def test_a_report_without_the_copy_of_its_key_is_not_counted(self):
        yield drop_stat_copies()
        self.assertEqual((yield self.answers_counted()), 0)


class TestStatisticalTemplates(helpers.TestHandlerWithPopulatedDB):
    _handler = analyst.StatisticalReportTemplates

    permissions = {'can_configure_statistical_report_templates': True}

    def analyst(self, body='', handler_cls=None, permissions=None):
        return self.request(body,
                            user_id=self.dummy_analyst['id'],
                            role='analyst',
                            permissions=permissions,
                            handler_cls=handler_cls)
