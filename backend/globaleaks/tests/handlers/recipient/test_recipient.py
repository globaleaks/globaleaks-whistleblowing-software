from twisted.internet.defer import inlineCallbacks

from globaleaks.handlers import recipient
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
            self.assertEqual(rtips[idx]['file_count'], 2)
            self.assertEqual(rtips[idx]['comment_count'], 2)
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
