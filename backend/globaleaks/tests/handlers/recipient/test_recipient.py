from twisted.internet.defer import inlineCallbacks

from globaleaks import models
from globaleaks.handlers import recipient
from globaleaks.handlers.admin.user import create_user
from globaleaks.orm import transact
from globaleaks.rest import errors
from globaleaks.tests import helpers


class TestTipsCollection(helpers.TestHandlerWithPopulatedDB):
    _handler = recipient.TipsCollection

    @inlineCallbacks
    def setUp(self):
        yield helpers.TestHandlerWithPopulatedDB.setUp(self)
        yield self.perform_full_submission_actions()

    @inlineCallbacks
    def test_get(self):
        handler = self.request(user_id=self.dummyReceiver_1['id'], role='receiver')
        rtips = yield handler.get()
        for idx in range(len(rtips)):
            self.assertEqual(rtips[idx]['receiver_count'], 2)

    @staticmethod
    def find_answer(answers):
        for field_id, entries in answers.items():
            for entry in entries:
                value = entry.get('value')
                if isinstance(value, str) and value:
                    return field_id, entry['index'], value
        return None, None, None

    @classmethod
    def answer_value(cls, answers, field_id, index):
        for a in answers.get(field_id, []):
            if a.get('index') == index:
                return a.get('value')
        return None

    @inlineCallbacks
    def test_temporary_redaction_masked_on_listing(self):
        # A temporary mask over an answer must be applied on the report listing
        # for a non-privileged recipient exactly as on the report detail;
        # otherwise the mask is bypassed through GET /api/recipient/rtips.
        mask = chr(0x2591)
        receiver_id = self.dummyReceiver_1['id']

        handler = self.request(user_id=receiver_id, role='receiver')
        rtips = yield handler.get()

        target = None
        for entry in rtips:
            field_id, index, value = self.find_answer(entry['answers'])
            if field_id is not None:
                target = (entry['id'], field_id, index, value)
                break

        self.assertIsNotNone(target)
        itip_id, field_id, index, original = target

        yield self.add_redaction(itip_id, field_id, [{'start': 0, 'end': 100}], index)

        # A privileged recipient reads the original answer.
        handler = self.request(user_id=receiver_id, role='receiver')
        rtips = yield handler.get()
        entry = next(e for e in rtips if e['id'] == itip_id)
        self.assertEqual(self.answer_value(entry['answers'], field_id, index), original)

        # A recipient without the permission reads the masked answer.
        yield self.set_redaction_privileges(receiver_id, False)
        handler = self.request(user_id=receiver_id, role='receiver')
        rtips = yield handler.get()
        entry = next(e for e in rtips if e['id'] == itip_id)
        value = self.answer_value(entry['answers'], field_id, index)
        self.assertNotEqual(value, original)
        self.assertIn(mask, value)


@transact
def reports_held_by(session, receiver_id):
    return {rtip.internaltip_id for rtip in session.query(models.ReceiverTip)
                                                    .filter(models.ReceiverTip.receiver_id == receiver_id)}


@transact
def audit_entries(session, type):
    return session.query(models.AuditLog).filter(models.AuditLog.type == type).count()


@transact
def give_dummy_keys(session, user_id):
    user = session.query(models.User).get(user_id)
    user.salt = helpers.VALID_SALT
    user.hash = helpers.VALID_HASH
    user.crypto_prv_key = helpers.USER_PRV_KEY_ENC
    user.crypto_pub_key = helpers.USER_PUB_KEY
    user.crypto_bkp_key = helpers.USER_BKP_KEY
    user.crypto_rec_key = helpers.USER_REC_KEY


class TestOperations(helpers.TestHandlerWithPopulatedDB):
    """
    Access to many reports at once is granted and revoked from the list
    """
    _handler = recipient.Operations

    @inlineCallbacks
    def setUp(self):
        yield helpers.TestHandlerWithPopulatedDB.setUp(self)
        yield self.perform_full_submission_actions()

        self.newcomer = yield create_user(1, None, self.get_dummy_receiver('newcomer'), 'en')
        yield give_dummy_keys(self.newcomer['id'])

        self.report_ids = [rtip['id'] for rtip in (yield self.get_rtips())]

    def operate(self, operation, can_grant=True):
        return self.request({'operation': operation,
                             'args': {'rtips': self.report_ids, 'receiver': self.newcomer['id']}},
                            role='receiver', permissions={'can_grant_access_to_reports': can_grant}).put()

    @inlineCallbacks
    def test_access_is_granted_to_every_report_listed(self):
        yield self.operate('grant')

        self.assertEqual((yield reports_held_by(self.newcomer['id'])), set(self.report_ids))
        self.assertEqual((yield audit_entries('grant_access')), len(self.report_ids))

    @inlineCallbacks
    def test_access_is_revoked_from_every_report_listed(self):
        yield self.operate('grant')
        yield self.operate('revoke')

        self.assertEqual((yield reports_held_by(self.newcomer['id'])), set())
        self.assertEqual((yield audit_entries('revoke_access')), len(self.report_ids))

    @inlineCallbacks
    def test_nothing_is_granted_without_the_permission(self):
        yield self.assertFailure(self.operate('grant', can_grant=False),
                                 errors.ForbiddenOperation)

        self.assertEqual((yield reports_held_by(self.newcomer['id'])), set())

    @inlineCallbacks
    def test_an_operation_that_is_not_offered_is_refused(self):
        yield self.assertFailure(self.operate('transfer'), errors.ForbiddenOperation)
