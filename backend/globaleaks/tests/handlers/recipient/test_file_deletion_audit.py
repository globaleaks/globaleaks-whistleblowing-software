from twisted.internet.defer import inlineCallbacks

from globaleaks import models
from globaleaks.handlers.recipient import rtip
from globaleaks.jobs.delivery import Delivery
from globaleaks.orm import transact
from globaleaks.tests import helpers


@transact
def get_delete_file_logs(session, file_id):
    return [
        {
            'user_id': log.user_id,
            'object_id': log.object_id,
            'data': log.data
        }
        for log in session.query(models.AuditLog)
                          .filter(models.AuditLog.type == 'delete_file',
                                  models.AuditLog.object_id == file_id)
                          .all()
    ]


class TestFileDeletionAudit(helpers.TestHandlerWithPopulatedDB):
    _handler = rtip.RTipRedactionCollection

    @inlineCallbacks
    def setUp(self):
        yield helpers.TestHandlerWithPopulatedDB.setUp(self)
        yield self.perform_full_submission_actions()
        yield Delivery().run()

    @inlineCallbacks
    def test_permanent_file_redaction_is_audited_as_deletion(self):
        rtip_desc = (yield self.get_rtips())[0]
        receiver_id = rtip_desc['receiver_id']
        itip_id = rtip_desc['id']
        file_id = (yield self.get_wbfiles(rtip_desc['rtip_id']))[0]

        body = {
            'internaltip_id': itip_id,
            'reference_id': file_id,
            'entry': '0',
            'permanent_redaction': '',
            'temporary_redaction': [{'start': '-inf', 'end': 'inf'}]
        }
        handler = self.request(body, role='receiver', user_id=receiver_id)
        yield handler.post()

        rtip_desc = next(rtip_desc for rtip_desc in (yield self.get_rtips())
                         if rtip_desc['id'] == itip_id and rtip_desc['receiver_id'] == receiver_id)
        redaction = next(redaction for redaction in rtip_desc['redactions']
                         if redaction['reference_id'] == file_id)

        body = {
            'id': redaction['id'],
            'operation': 'redact',
            'content_type': 'file',
            'internaltip_id': itip_id,
            'reference_id': file_id,
            'entry': '0',
            'permanent_redaction': [],
            'temporary_redaction': [{'start': '-inf', 'end': 'inf'}]
        }
        handler = self.request(body, role='receiver', user_id=receiver_id)
        yield handler.put(redaction['id'])

        logs = yield get_delete_file_logs(file_id)
        self.assertEqual(logs, [{
            'user_id': receiver_id,
            'object_id': file_id,
            'data': {'internaltip_id': itip_id}
        }])
