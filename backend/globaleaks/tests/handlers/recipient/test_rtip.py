import time
from datetime import datetime
from types import SimpleNamespace
from unittest.mock import patch
from uuid import uuid4
from sqlalchemy.orm.exc import NoResultFound
from twisted.internet import reactor, task
from twisted.internet.defer import DeferredLock, inlineCallbacks, succeed
from twisted.trial import unittest

from globaleaks import models
from globaleaks.handlers.recipient import rtip
from globaleaks.handlers.whistleblower import wbtip
from globaleaks.jobs.delivery import Delivery
from globaleaks.models.config import db_set_config_variable
from globaleaks.orm import transact
from globaleaks.rest import errors
from globaleaks.tests import helpers
from globaleaks.utils.utility import datetime_never, datetime_now


@transact
def create_substatus(session, submissionstatus_id):
    substatus = models.SubmissionSubStatus()
    substatus.tid = 1
    substatus.submissionstatus_id = submissionstatus_id
    substatus.label = {'en': 'Test'}
    substatus.order = 0
    session.add(substatus)
    session.flush()
    return substatus.id


@transact
def remove_receivertip(session, itip_id, receiver_id):
    session.query(models.ReceiverTip) \
           .filter(models.ReceiverTip.internaltip_id == itip_id,
                   models.ReceiverTip.receiver_id == receiver_id).delete()


class TestRTipInstance(helpers.TestHandlerWithPopulatedDB):
    _handler = rtip.RTipInstance

    @inlineCallbacks
    def setUp(self):
        now = int(time.time())

        self.one_year_from_now_timestamp = now + 365 * 86400
        self.one_year_from_now_datetime = datetime.fromtimestamp(self.one_year_from_now_timestamp)

        self.two_year_from_now_timestamp = now + 2 * 365 * 86400
        self.two_year_from_now_datetime = datetime.fromtimestamp(self.two_year_from_now_timestamp)

        yield helpers.TestHandlerWithPopulatedDB.setUp(self)
        yield self.perform_full_submission_actions()
        yield Delivery().run()

    @inlineCallbacks
    def test_get(self):
        rtip_descs = yield self.get_rtips()
        for rtip_desc in rtip_descs:
            handler = self.request(role='receiver', user_id=rtip_desc['receiver_id'])
            yield handler.get(rtip_desc['id'])

    @inlineCallbacks
    def test_questionnaire_hashes(self):
        # The hashes are sealed to the report as the answers they attest are,
        # so they are read on the report as it is delivered to its recipients
        rtip_descs = yield self.get_rtips()
        for rtip_desc in rtip_descs:
            handler = self.request(role='receiver', user_id=rtip_desc['receiver_id'])

            self.verify_questionnaire_hashes((yield handler.get(rtip_desc['id'])))

    @inlineCallbacks
    def test_postpone(self):
        expiration = datetime_now()

        yield self.set_itips_expiration(expiration)

        rtip_descs = yield self.get_rtips()

        for rtip_desc in rtip_descs:
            operation = {
              'operation': 'postpone',
              'args': {
                'value': self.one_year_from_now_timestamp * 1000
              }
            }

            handler = self.request(operation, role='receiver', user_id=rtip_desc['receiver_id'])
            yield handler.put(rtip_desc['id'])
            self.assertEqual(handler.request.code, 200)

        rtip_descs = yield self.get_rtips()
        for rtip_desc in rtip_descs:
            self.assertTrue(rtip_desc['expiration_date'] == self.one_year_from_now_datetime)

    @inlineCallbacks
    def test_postpone_of_reports_with_no_expiration(self):
        yield self.set_itips_expiration(datetime_never())

        rtip_descs = yield self.get_rtips()

        for rtip_desc in rtip_descs:
            operation = {
              'operation': 'postpone',
              'args': {
                'value': self.one_year_from_now_timestamp * 1000
              }
            }

            handler = self.request(operation, role='receiver', user_id=rtip_desc['receiver_id'])
            yield handler.put(rtip_desc['id'])
            self.assertEqual(handler.request.code, 200)

        rtip_descs = yield self.get_rtips()
        for rtip_desc in rtip_descs:
            self.assertTrue(rtip_desc['expiration_date'] == self.one_year_from_now_datetime)

    @inlineCallbacks
    def test_postpone_of_reports_with_date_below_minimum_threshold(self):
        expiration = datetime_now()

        yield self.set_itips_expiration(expiration)

        rtip_descs = yield self.get_rtips()

        for rtip_desc in rtip_descs:
            operation = {
              'operation': 'postpone',
              'args': {
                'value': self.one_year_from_now_timestamp * 1000
              }
            }

            handler = self.request(operation, role='receiver', user_id=rtip_desc['receiver_id'])
            yield handler.put(rtip_desc['id'])
            self.assertEqual(handler.request.code, 200)

        rtip_descs = yield self.get_rtips()
        for rtip_desc in rtip_descs:
            self.assertTrue(rtip_desc['expiration_date'] > expiration)
            self.assertTrue(rtip_desc['expiration_date'] < self.two_year_from_now_datetime)

    @inlineCallbacks
    def test_postpone_of_reports_with_date_over_maximum_threshold(self):
        expiration = datetime_now()

        yield self.set_itips_expiration(expiration)

        rtip_descs = yield self.get_rtips()

        for rtip_desc in rtip_descs:
            operation = {
              'operation': 'postpone',
              'args': {
                'value': 0
              }
            }

            handler = self.request(operation, role='receiver', user_id=rtip_desc['receiver_id'])
            yield handler.put(rtip_desc['id'])
            self.assertEqual(handler.request.code, 200)

        rtip_descs = yield self.get_rtips()
        for rtip_desc in rtip_descs:
            self.assertTrue(rtip_desc['expiration_date'] == expiration)

    @inlineCallbacks
    def test_grant_and_revoke_access(self):
        count = yield self.get_model_count(models.ReceiverTip)

        # Perform two cycles of revoke ensuring the second cycle results in a nop
        for cycle in range(0, 1):
            rtip_descs = yield self.get_rtips()
            for rtip_desc in rtip_descs:
                # Decrement should happen only during the first cycle
                if cycle == 0:
                    count -= 1

                operation = {
                    'operation': 'revoke',
                    'args': {
                        'receiver':  self.dummyReceiver_2['id']
                    }
                }

                handler = self.request(operation, role='receiver', user_id=rtip_desc['receiver_id'],
                                       permissions={'can_grant_access_to_reports': True})
                yield handler.put(rtip_desc['id'])
                self.assertEqual(handler.request.code, 200)
                yield self.test_model_count(models.ReceiverTip, count)

        # Perform two cycles of grant ensuring the second cycle results in a nop
        for cycle in range(0, 1):
            for rtip_desc in rtip_descs:
                # Increment should happen only during the first cycle
                if cycle == 0:
                    count += 1

                operation = {
                    'operation': 'grant',
                    'args': {
                        'receiver':  self.dummyReceiver_2['id']
                    }
                }

                handler = self.request(operation, role='receiver', user_id=rtip_desc['receiver_id'],
                                       permissions={'can_grant_access_to_reports': True})
                yield handler.put(rtip_desc['id'])
                self.assertEqual(handler.request.code, 200)
                yield self.test_model_count(models.ReceiverTip, count)

    @inlineCallbacks
    def test_transfer(self):
        rtip_descs = yield self.get_rtips()

        for rtip_desc in rtip_descs:
            operation = {
              'operation': 'revoke',
              'args': {
                'receiver':  self.dummyReceiver_2['id']
              }
            }

            handler = self.request(operation, role='receiver', user_id=rtip_desc['receiver_id'],
                                   permissions={'can_grant_access_to_reports': True})
            yield handler.put(rtip_desc['id'])
            self.assertEqual(handler.request.code, 200)

        rtip_descs = yield self.get_rtips()
        count = len(rtip_descs)

        for rtip_desc in rtip_descs:
            operation = {
              'operation': 'transfer',
              'args': {
                'receiver':  self.dummyReceiver_2['id']
              }
            }

            handler = self.request(operation, role='receiver', user_id=rtip_desc['receiver_id'],
                                   permissions={'can_transfer_access_to_reports': True})
            yield handler.put(rtip_desc['id'])
            self.assertEqual(handler.request.code, 200)
            yield self.test_model_count(models.ReceiverTip, count)

    @inlineCallbacks
    def switch_enabler(self, key):
        rtip_descs = yield self.get_rtips()
        for rtip_desc in rtip_descs:
            operation = {
                'operation': 'set',
                'args': {
                  'key': key,
                  'value': True
                }
            }

            handler = self.request(operation, role='receiver', user_id=rtip_desc['receiver_id'])
            yield handler.put(rtip_desc['id'])
            self.assertEqual(handler.request.code, 200)

            response = yield handler.get(rtip_desc['id'])
            self.assertEqual(response[key], True)

            operation = {
                'operation': 'set',
                'args': {
                  'key': key,
                  'value': False
                }
            }

            handler = self.request(operation, role='receiver', user_id=rtip_desc['receiver_id'])
            yield handler.put(rtip_desc['id'])
            self.assertEqual(handler.request.code, 200)

            response = yield handler.get(rtip_desc['id'])
            self.assertEqual(response[key], False)

            operation = {
                'operation': 'set',
                'args': {
                  'key': key,
                  'value': True
                }
            }

            handler = self.request(operation, role='receiver', user_id=rtip_desc['receiver_id'])
            yield handler.put(rtip_desc['id'])
            self.assertEqual(handler.request.code, 200)

            response = yield handler.get(rtip_desc['id'])
            self.assertEqual(response[key], True)

    @inlineCallbacks
    def test_update_status(self):
        rtip_descs = yield self.get_rtips()

        for rtip_desc in rtip_descs:
            operation = {
              'operation': 'update_status',
              'args': {
                'status': 'closed',
                'substatus': '',
                'motivation': ''
              }
            }

            handler = self.request(operation, role='receiver', user_id=rtip_desc['receiver_id'])
            yield handler.put(rtip_desc['id'])
            self.assertEqual(handler.request.code, 200)

        rtip_descs = yield self.get_rtips()
        for rtip_desc in rtip_descs:
            self.assertEqual(rtip_desc['status'], 'closed')

        for rtip_desc in rtip_descs:
            operation = {
              'operation': 'update_status',
              'args': {
                'status': 'new',
                'substatus': '',
                'motivation': ''
              }
            }

            handler = self.request(operation, role='receiver', user_id=rtip_desc['receiver_id'])
            yield handler.put(rtip_desc['id'])
            self.assertEqual(handler.request.code, 200)

        rtip_descs = yield self.get_rtips()
        for rtip_desc in rtip_descs:
            self.assertEqual(rtip_desc['status'], 'closed')

        yield self.test_postpone()

        for rtip_desc in rtip_descs:
            operation = {
              'operation': 'update_status',
              'args': {
                'status': 'opened',
                'substatus': '',
                'motivation': ''
              }
            }

            handler = self.request(operation, role='receiver', user_id=rtip_desc['receiver_id'])
            yield handler.put(rtip_desc['id'])
            self.assertEqual(handler.request.code, 200)

        rtip_descs = yield self.get_rtips()
        for rtip_desc in rtip_descs:
            self.assertEqual(rtip_desc['status'], 'opened')

    @inlineCallbacks
    def test_update_status_with_invalid_values(self):
        opened_substatus_id = yield create_substatus('opened')
        closed_substatus_id = yield create_substatus('closed')

        rtip_descs = yield self.get_rtips()

        for rtip_desc in rtip_descs:
            for args in [{'status': 'unexistent_status', 'substatus': ''},
                         {'status': 'closed', 'substatus': 'unexistent_substatus'},
                         {'status': 'closed', 'substatus': opened_substatus_id}]:
                args['motivation'] = ''
                operation = {
                  'operation': 'update_status',
                  'args': args
                }

                handler = self.request(operation, role='receiver', user_id=rtip_desc['receiver_id'])
                yield self.assertFailure(handler.put(rtip_desc['id']), NoResultFound)

        rtip_descs = yield self.get_rtips()
        for rtip_desc in rtip_descs:
            self.assertNotEqual(rtip_desc['status'], 'closed')

        for rtip_desc in rtip_descs:
            operation = {
              'operation': 'update_status',
              'args': {
                'status': 'closed',
                'substatus': closed_substatus_id,
                'motivation': ''
              }
            }

            handler = self.request(operation, role='receiver', user_id=rtip_desc['receiver_id'])
            yield handler.put(rtip_desc['id'])
            self.assertEqual(handler.request.code, 200)

        rtip_descs = yield self.get_rtips()
        for rtip_desc in rtip_descs:
            self.assertEqual(rtip_desc['status'], 'closed')
            self.assertEqual(rtip_desc['substatus'], closed_substatus_id)

    def test_mark_important(self):
        return self.switch_enabler('important')

    @inlineCallbacks
    def test_update_label(self):
        rtip_descs = yield self.get_rtips()
        for rtip_desc in rtip_descs:
            operation = {
              'operation': 'set',
              'args': {
                'key': 'label',
                'value': 'PASSANTEDIPROFESSIONE'
              }
            }

            handler = self.request(operation, role='receiver', user_id=rtip_desc['receiver_id'])
            yield handler.put(rtip_desc['id'])
            self.assertEqual(handler.request.code, 200)

            response = yield handler.get(rtip_desc['id'])
            self.assertEqual(response['label'], operation['args']['value'])

    @inlineCallbacks
    def test_set_status_forbidden(self):
        rtip_descs = yield self.get_rtips()
        for rtip_desc in rtip_descs:
            operation = {
              'operation': 'set',
              'args': {
                'key': 'status',
                'value': 'closed'
              }
            }

            handler = self.request(operation, role='receiver', user_id=rtip_desc['receiver_id'])

            with self.assertRaises(errors.ForbiddenOperation):
                yield handler.put(rtip_desc['id'])

    @inlineCallbacks
    def test_silence_notify(self):
        rtip_descs = yield self.get_rtips()
        for rtip_desc in rtip_descs:
            operation = {
              'operation': 'set',
              'args': {
                'key': 'enable_notifications',
                'value': False
              }
            }

            handler = self.request(operation, role='receiver', user_id=rtip_desc['receiver_id'])
            yield handler.put(rtip_desc['id'])
            self.assertEqual(handler.request.code, 200)

            response = yield handler.get(rtip_desc['id'])
            self.assertEqual(response['enable_notifications'], operation['args']['value'])

    @inlineCallbacks
    def test_delete(self):
        rtip_descs = yield self.get_rtips()
        self.assertEqual(len(rtip_descs) * 2, self.population_of_submissions * self.population_of_recipients)

        # we delete the first and then we verify that the second does not exist anymore
        handler = self.request(role='receiver', user_id=rtip_descs[0]['receiver_id'],
                               permissions={'can_delete_submission': True})
        yield handler.delete(rtip_descs[0]['id'])

        rtip_descs = yield self.get_rtips()

        self.assertEqual(len(rtip_descs) * 2, self.population_of_submissions * self.population_of_recipients - self.population_of_recipients)

    @inlineCallbacks
    def test_delete_unexistent_tip_by_existent_and_logged_receiver(self):
        rtip_descs = yield self.get_rtips()

        for rtip_desc in rtip_descs:
            handler = self.request(role='receiver', user_id=rtip_desc['receiver_id'])
            yield self.assertFailure(handler.delete(u"unexistent_tip"), NoResultFound)

    @inlineCallbacks
    def test_delete_existent_tip_by_existent_and_logged_but_wrong_receiver(self):
        rtip_descs = yield self.get_rtips()

        # Drop receiver2's access to the report so it becomes a report the
        # receiver is logged in but not entitled to.
        itip_id = rtip_descs[0]['id']
        yield remove_receivertip(itip_id, self.dummyReceiver_2['id'])

        handler = self.request(role='receiver', user_id=self.dummyReceiver_2['id'])
        yield self.assertFailure(handler.delete(itip_id), NoResultFound)

    @inlineCallbacks
    def test_get_existent_tip_by_existent_and_logged_but_wrong_receiver(self):
        rtip_descs = yield self.get_rtips()

        # A receiver without a ReceiverTip on the report cannot read it.
        itip_id = rtip_descs[0]['id']
        yield remove_receivertip(itip_id, self.dummyReceiver_2['id'])

        handler = self.request(role='receiver', user_id=self.dummyReceiver_2['id'])
        yield self.assertFailure(handler.get(itip_id), NoResultFound)

    @inlineCallbacks
    def test_set_reminder_and_reset_upon_close(self):
        rtip_descs = yield self.get_rtips()

        for rtip_desc in rtip_descs:
            self.assertEqual(rtip_desc['reminder_date'], datetime_never())

            operation = {
              'operation': 'set_reminder',
              'args': {
                'value': datetime_now().timestamp() + 7 * 22 * 3600 * 1000,
                'substatus': '',
                'motivation': ''
              }
            }

            handler = self.request(operation, role='receiver', user_id=rtip_desc['receiver_id'])
            yield handler.put(rtip_desc['id'])
            self.assertEqual(handler.request.code, 200)

        rtip_descs = yield self.get_rtips()
        for rtip_desc in rtip_descs:
            self.assertNotEqual(rtip_desc['reminder_date'], datetime_never())

            operation = {
              'operation': 'update_status',
              'args': {
                'status': 'closed',
                'substatus': '',
                'motivation': ''
              }
            }

            handler = self.request(operation, role='receiver', user_id=rtip_desc['receiver_id'])
            yield handler.put(rtip_desc['id'])
            self.assertEqual(handler.request.code, 200)

        rtip_descs = yield self.get_rtips()
        for rtip_desc in rtip_descs:
            self.assertEqual(rtip_desc['reminder_date'], datetime_never())


class TestRTipCommentCollection(helpers.TestHandlerWithPopulatedDB):
    _handler = rtip.RTipCommentCollection

    @inlineCallbacks
    def setUp(self):
        yield helpers.TestHandlerWithPopulatedDB.setUp(self)
        yield self.perform_full_submission_actions()

    @inlineCallbacks
    def test_post(self):
        body = {
            'content': "can you provide an evidence of what you are telling?",
            'visibility': "public"
        }

        rtip_descs = yield self.get_rtips()
        for rtip_desc in rtip_descs:
            handler = self.request(body, role='receiver', user_id=rtip_desc['receiver_id'])
            yield handler.post(rtip_desc['id'])


class TestRedactContent(unittest.TestCase):
    def test_inclusive_range(self):
        self.assertEqual(rtip.redact_content('hello', [{'start': 1, 'end': 3}], '0x2591'), 'h░░░o')

    def test_oversized_range_is_bounded_to_content_length(self):
        # A type-valid but oversized range must not allocate more than the content length
        out = rtip.redact_content('x', [{'start': 0, 'end': 1000000000}], '0x2591')
        self.assertEqual(out, '░')

    def test_non_integer_ranges_are_ignored(self):
        for ranges in ([{'start': 1.5, 'end': 3.5}],
                       [{'start': None, 'end': None}],
                       [{'start': '-inf', 'end': 'inf'}],
                       [{'start': True, 'end': False}]):
            self.assertEqual(rtip.redact_content('hello', ranges, '0x2591'), 'hello')

    def test_negative_start_is_clamped(self):
        self.assertEqual(rtip.redact_content('hello', [{'start': -5, 'end': 1}], '0x2591'), '░░llo')

    def test_non_mapping_ranges_are_ignored(self):
        # The stored temporary_redaction comes from an unvalidated JSON column;
        # a non-list container or non-dict element must not crash consumption.
        for ranges in (None, 'abc', 123, [1, 2, 3], [None], [[0, 1]], ['x']):
            self.assertEqual(rtip.redact_content('hello', ranges, '0x2591'), 'hello')

    def test_astral_chars_before_range_do_not_leak(self):
        # The client measures selection offsets in UTF-16 code units; an astral
        # character (U+10000+) before a redacted token must not shift the mask
        # and leak the leading character(s) of the redacted value. This is not an
        # emoji-only edge case: supplementary-plane CJK ideographs occur in
        # ordinary personal and place names (here U+20BB7 '𠮷', the variant of
        # '吉' used in the surname Yoshida), so the redacted PII can itself carry
        # the astral character that triggers the leak.

        # A redacted phone number after a name containing a supplementary-plane
        # ideograph: '𠮷' = 2 UTF-16 units, '田' = 1, ': ' = 2 -> phone at 5..11.
        content = '𠮷田: 5551234'
        out = rtip.redact_content(content, [{'start': 5, 'end': 11}], '0x2588')
        self.assertEqual(out, '𠮷田: ███████')

        # The redacted name itself, with the astral character at its start:
        # 'Source: ' = 8 units, then '𠮷田' spans units 8..10.
        content = 'Source: 𠮷田 called'
        out = rtip.redact_content(content, [{'start': 8, 'end': 10}], '0x2588')
        self.assertEqual(out, 'Source: ███ called')


class TestRedactionHelpers(unittest.TestCase):
    def test_validate_ranges(self):
        current = [{'start': 0, 'end': 10}]
        # A new range fully contained in the current mask is accepted
        self.assertTrue(rtip.validate_ranges(current, [{'start': 2, 'end': 5}]))
        # A new range exceeding the current mask is rejected
        self.assertFalse(rtip.validate_ranges(current, [{'start': 5, 'end': 15}]))

    def test_merge_and_sort_ranges(self):
        self.assertEqual(rtip.merge_and_sort_ranges([], []), [])
        # Adjacent ranges in list2 are coalesced, then disjoint ranges stay split
        self.assertEqual(rtip.merge_and_sort_ranges([{'start': 0, 'end': 2}],
                                                    [{'start': 4, 'end': 6}, {'start': 7, 'end': 9}]),
                         [{'start': 0, 'end': 2}, {'start': 4, 'end': 9}])
        # Overlapping ranges across the two lists are merged into one
        self.assertEqual(rtip.merge_and_sort_ranges([{'start': 0, 'end': 5}],
                                                    [{'start': 3, 'end': 8}]),
                         [{'start': 0, 'end': 8}])

    def test_get_new_temporary_redaction(self):
        # Redacting the middle of a temporary range splits it in two
        self.assertEqual(rtip.get_new_temporary_redaction([{'start': 0, 'end': 10}],
                                                          [{'start': 3, 'end': 5}]),
                         [{'start': 0, 'end': 2}, {'start': 6, 'end': 10}])
        # A non-overlapping redaction leaves the temporary range untouched
        self.assertEqual(rtip.get_new_temporary_redaction([{'start': 0, 'end': 2}],
                                                          [{'start': 5, 'end': 7}]),
                         [{'start': 0, 'end': 2}])

    def test_db_redact_answers(self):
        key = str(uuid4())
        answers = {key: [{'index': '0', 'value': 'hello'}]}
        redaction = SimpleNamespace(reference_id=key, entry='0',
                                    permanent_redaction=[{'start': 1, 'end': 3}])
        rtip.db_redact_answers(answers, redaction)
        self.assertEqual(answers[key][0]['value'], 'h███o')

    def test_db_redact_answers_recurses_and_skips_non_uuid_keys(self):
        outer, inner = str(uuid4()), str(uuid4())
        answers = {
            'not-a-uuid': 'ignored',
            outer: [{'index': '0', inner: [{'index': '0-0', 'value': 'secret'}]}]
        }
        redaction = SimpleNamespace(reference_id=inner, entry='0-0',
                                    permanent_redaction=[{'start': 0, 'end': 5}])
        rtip.db_redact_answers(answers, redaction)
        self.assertEqual(answers[outer][0][inner][0]['value'], '██████')

    def test_db_redact_whistleblower_identities(self):
        key, group, leaf = str(uuid4()), str(uuid4()), str(uuid4())
        identities = {
            'enabled': True,  # boolean entries must be skipped
            key: [{'value': 'secret'}],
            group: [{leaf: [{'value': 'nested'}]}]
        }
        rtip.db_redact_whistleblower_identities(identities,
            SimpleNamespace(reference_id=key, permanent_redaction=[{'start': 0, 'end': 5}]))
        self.assertEqual(identities[key][0]['value'], '██████')
        # The recursion reaches values nested under a group field
        rtip.db_redact_whistleblower_identities(identities,
            SimpleNamespace(reference_id=leaf, permanent_redaction=[{'start': 0, 'end': 5}]))
        self.assertEqual(identities[group][0][leaf][0]['value'], '██████')


class TestRTipRedactionCollection(helpers.TestHandlerWithPopulatedDB):
    _handler = rtip.RTipRedactionCollection

    @inlineCallbacks
    def setUp(self):
        yield helpers.TestHandlerWithPopulatedDB.setUp(self)
        yield self.perform_full_submission_actions()

    @inlineCallbacks
    def test_post_and_put(self):
        rtip_descs = yield self.get_rtips()
        for rtip_desc in rtip_descs:
            body = {
                'internaltip_id': rtip_desc['id'],
                'reference_id': rtip_desc['questionnaires'][0]['steps'][0]['id'],
                'entry': '0',
                'permanent_redaction': '',
                'temporary_redaction': [{"start": 0, "end": 0}]
            }

            handler = self.request(body, role='receiver', user_id=rtip_desc['receiver_id'])
            yield handler.post()

        rtip_descs = yield self.get_rtips()
        for rtip_desc in rtip_descs:
            body = {
                'id': rtip_desc['redactions'][0]['id'],
                'operation': 'mask',
                'content_type': 'answer',
                'internaltip_id': rtip_desc['id'],
                'reference_id': '',
                'entry': '0',
                'permanent_redaction': '',
                'temporary_redaction': [{"start": 0, "end": 1}]
            }

            handler = self.request(body, role='receiver', user_id=rtip_desc['receiver_id'])
            yield handler.put(rtip_desc['redactions'][0]['id'])

        rtip_descs = yield self.get_rtips()
        for rtip_desc in rtip_descs:
            body = {
                'id': rtip_desc['redactions'][0]['id'],
                'operation': 'redact',
                'content_type': 'answer',
                'internaltip_id': rtip_desc['id'],
                'reference_id': '',
                'entry': '0',
                'permanent_redaction': [{"start": 0, "end": 0}],
                'temporary_redaction': [{"start": 1, "end": 1}]
            }

            handler = self.request(body, role='receiver', user_id=rtip_desc['receiver_id'])
            yield handler.put(rtip_desc['redactions'][0]['id'])

        rtip_descs = yield self.get_rtips()
        for rtip_desc in rtip_descs:
            body = {
                'id': rtip_desc['redactions'][0]['id'],
                'operation': 'full-unmask',
                'content_type': 'answer',
                'internaltip_id': rtip_desc['id'],
                'reference_id': '',
                'entry': '0',
                'permanent_redaction': '',
                'temporary_redaction': ''
            }

            handler = self.request(body, role='receiver', user_id=rtip_desc['receiver_id'])
            yield handler.put(rtip_desc['redactions'][0]['id'])

    @transact
    def get_answer_field_id(self, session):
        # The step-level inputbox is a top-level questionnaire answer entry
        # (index '0'), so it can be redacted via the 'answer' content type.
        field = session.query(models.Field) \
                       .filter(models.Field.type == 'inputbox',
                               models.Field.step_id != '').first()
        return field.id

    @inlineCallbacks
    def post_redaction(self, rtip_desc, reference_id, temporary_redaction):
        body = {
            'internaltip_id': rtip_desc['id'],
            'reference_id': reference_id,
            'entry': '0',
            'permanent_redaction': '',
            'temporary_redaction': temporary_redaction
        }

        handler = self.request(body, role='receiver', user_id=rtip_desc['receiver_id'])
        yield handler.post()

    @inlineCallbacks
    def put_redaction(self, rtip_desc, redaction_id, content_type, reference_id,
                      permanent_redaction, temporary_redaction):
        body = {
            'id': redaction_id,
            'operation': 'redact',
            'content_type': content_type,
            'internaltip_id': rtip_desc['id'],
            'reference_id': reference_id,
            'entry': '0',
            'permanent_redaction': permanent_redaction,
            'temporary_redaction': temporary_redaction
        }

        handler = self.request(body, role='receiver', user_id=rtip_desc['receiver_id'])
        yield handler.put(redaction_id)

    @inlineCallbacks
    def test_redact_answer(self):
        field_id = yield self.get_answer_field_id()

        rtip_descs = yield self.get_rtips()
        for rtip_desc in rtip_descs:
            yield self.post_redaction(rtip_desc, field_id, [{'start': 0, 'end': 10}])

        rtip_descs = yield self.get_rtips()
        for rtip_desc in rtip_descs:
            yield self.put_redaction(rtip_desc, rtip_desc['redactions'][0]['id'],
                                     'answer', field_id,
                                     [{'start': 0, 'end': 3}], [{'start': 0, 'end': 10}])

    @inlineCallbacks
    def test_redact_comment(self):
        rtip_descs = yield self.get_rtips()
        comment_ids = {}
        for rtip_desc in rtip_descs:
            comment = yield rtip.create_comment(1, rtip_desc['receiver_id'],
                                                rtip_desc['id'], 'sensitive comment')
            comment_ids[rtip_desc['id']] = comment['id']
            yield self.post_redaction(rtip_desc, comment['id'], [{'start': 0, 'end': 16}])

        rtip_descs = yield self.get_rtips()
        for rtip_desc in rtip_descs:
            yield self.put_redaction(rtip_desc, rtip_desc['redactions'][0]['id'],
                                     'comment', comment_ids[rtip_desc['id']],
                                     [{'start': 0, 'end': 5}], [{'start': 0, 'end': 16}])

    @transact
    def add_receiver_files(self, session, itip_id, author_id):
        # Insert a personal and a public receiver file authored by author_id,
        # bypassing the upload machinery which is irrelevant to this guard.
        ids = {}
        for visibility in ('personal', 'public'):
            rfile = models.ReceiverFile()
            rfile.internaltip_id = itip_id
            rfile.author_id = author_id
            rfile.name = 'attachment.txt'
            rfile.size = 1
            rfile.content_type = 'text/plain'
            rfile.visibility = visibility
            session.add(rfile)
            session.flush()
            ids[visibility] = rfile.id

        return ids

    @inlineCallbacks
    def test_create_redaction_rejects_personal_object_of_other_recipient(self):
        # A personal (visibility == 2) comment or receiver file is visible only
        # to its author. A second recipient must not be able to reference either
        # one in a redaction -- mirroring db_access_rfile and serialize_rtip's
        # per-recipient visibility filter -- while a public object of the same
        # kind stays referenceable.
        itip_id = (yield self.get_rtips())[0]['id']
        other = self.dummyReceiver_2['id']

        references = {'personal': [], 'public': []}

        for visibility in ('personal', 'public'):
            comment = yield rtip.create_comment(1, other, itip_id, 'note', visibility)
            references[visibility].append(comment['id'])

        file_ids = yield self.add_receiver_files(itip_id, other)
        for visibility in ('personal', 'public'):
            references[visibility].append(file_ids[visibility])

        body = {
            'internaltip_id': itip_id,
            'reference_id': None,
            'entry': '0',
            'permanent_redaction': '',
            'temporary_redaction': [{'start': 0, 'end': 5}]
        }

        # Personal objects owned by the other recipient are rejected.
        for reference_id in references['personal']:
            body['reference_id'] = reference_id
            handler = self.request(body, role='receiver', user_id=self.dummyReceiver_1['id'])
            yield self.assertFailure(handler.post(), errors.InputValidationError)

        # Public objects of the same kinds stay referenceable.
        for reference_id in references['public']:
            body['reference_id'] = reference_id
            handler = self.request(body, role='receiver', user_id=self.dummyReceiver_1['id'])
            yield handler.post()

    @inlineCallbacks
    def test_redact_file(self):
        yield Delivery().run()

        rtip_descs = yield self.get_rtips()
        for rtip_desc in rtip_descs:
            wbfile_ids = yield self.get_wbfiles(rtip_desc['rtip_id'])
            # The 'file' redaction path triggers deletion of the referenced file
            # and is keyed by the sentinel temporary range [-inf, inf].
            yield self.post_redaction(rtip_desc, wbfile_ids[0],
                                      [{'start': '-inf', 'end': 'inf'}])

        rtip_descs = yield self.get_rtips()
        for rtip_desc in rtip_descs:
            redaction = rtip_desc['redactions'][0]
            yield self.put_redaction(rtip_desc, redaction['id'], 'file',
                                     redaction['reference_id'], [], [{'start': '-inf', 'end': 'inf'}])


class TestReportTemporaryRedaction(helpers.TestHandlerWithPopulatedDB):
    """
    A temporary (display-time) redaction over a comment or an answer must be
    masked on every non-privileged read path -- a recipient lacking the
    masking/redaction permission and the whistleblower -- while a privileged
    recipient keeps reading the original content.
    """
    @inlineCallbacks
    def setUp(self):
        yield helpers.TestHandlerWithPopulatedDB.setUp(self)
        yield self.perform_full_submission_actions()

    @inlineCallbacks
    def read_rtip(self, itip_id, receiver_id):
        self._handler = rtip.RTipInstance
        handler = self.request(role='receiver', user_id=receiver_id)
        ret = yield handler.get(itip_id)
        return ret

    @inlineCallbacks
    def read_wbtip(self, itip_id):
        self._handler = wbtip.WBTipInstance
        handler = self.request(role='whistleblower', user_id=itip_id)
        ret = yield handler.get()
        return ret

    def find_redactable_answer(self, tip):
        # A top-level questionnaire answer holding a non-empty string value,
        # suitable for a text redaction.
        for q in tip['questionnaires']:
            for field_id, entries in q['answers'].items():
                for entry in entries:
                    value = entry.get('value')
                    if isinstance(value, str) and value:
                        return field_id, entry['index'], value
        return None, None, None

    def answer_value(self, tip, field_id, entry):
        for q in tip['questionnaires']:
            for a in q['answers'].get(field_id, []):
                if a.get('index') == entry:
                    return a.get('value')
        return None

    def comment_content(self, tip, comment_id):
        for comment in tip['comments']:
            if comment['id'] == comment_id:
                return comment['content']
        return None

    @inlineCallbacks
    def test_temporary_redaction_enforced_on_recipient_and_whistleblower_reads(self):
        mask = chr(0x2591)

        rtip_descs = yield self.get_rtips()
        for rtip_desc in rtip_descs:
            itip_id = rtip_desc['id']
            receiver_id = rtip_desc['receiver_id']

            comment = yield rtip.create_comment(1, receiver_id, itip_id, 'SECRET comment')

            tip = yield self.read_rtip(itip_id, receiver_id)
            field_id, entry, original_answer = self.find_redactable_answer(tip)
            self.assertTrue(original_answer)

            yield self.add_redaction(itip_id, comment['id'], [{'start': 0, 'end': 100}])
            yield self.add_redaction(itip_id, field_id, [{'start': 0, 'end': 100}], entry)

            # A privileged recipient reads the original content.
            tip = yield self.read_rtip(itip_id, receiver_id)
            self.assertEqual(self.comment_content(tip, comment['id']), 'SECRET comment')
            self.assertEqual(self.answer_value(tip, field_id, entry), original_answer)

            # A recipient without the permission reads the masked content.
            yield self.set_redaction_privileges(receiver_id, False)
            tip = yield self.read_rtip(itip_id, receiver_id)
            self.assertNotIn('SECRET', self.comment_content(tip, comment['id']))
            self.assertIn(mask, self.comment_content(tip, comment['id']))
            self.assertIn(mask, self.answer_value(tip, field_id, entry))

            # The whistleblower (no User record, hence non-privileged) reads the
            # masked content too.
            tip = yield self.read_wbtip(itip_id)
            self.assertNotIn('SECRET', self.comment_content(tip, comment['id']))
            self.assertIn(mask, self.comment_content(tip, comment['id']))
            self.assertIn(mask, self.answer_value(tip, field_id, entry))

            # Restore the permission for the next report iteration.
            yield self.set_redaction_privileges(receiver_id, True)

    @inlineCallbacks
    def test_temporary_redaction_masks_whistleblower_identity(self):
        # The whistleblower identity is masked on the consumption-time pass
        # (redact_report, shared by the rtip detail, wbtip and export paths): a
        # temporary mask over an identity field must hide it from a non-privileged
        # recipient while a privileged one keeps reading it. The identity is
        # extracted from the questionnaire answers and, unlike them, is not
        # indexed at read time, so it is matched by reference id only -- masking
        # it as a plain answer (which requires an 'index') would raise KeyError.
        mask = chr(0x2591)
        identity_field_id = 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa'

        def build_report(itip_id):
            return {
                'id': itip_id,
                'questionnaires': [],
                'comments': [],
                'wbfiles': [],
                'rfiles': [],
                'data': {'whistleblower_identity': {
                    identity_field_id: [{'value': 'SECRET identity'}]
                }}
            }

        rtip_descs = yield self.get_rtips()
        for rtip_desc in rtip_descs:
            itip_id = rtip_desc['id']
            receiver_id = rtip_desc['receiver_id']

            yield self.add_redaction(itip_id, identity_field_id, [{'start': 0, 'end': 100}])

            # A privileged recipient reads the original identity.
            report = yield rtip.redact_report(SimpleNamespace(user_id=receiver_id), build_report(itip_id))
            self.assertEqual(report['data']['whistleblower_identity'][identity_field_id][0]['value'],
                             'SECRET identity')

            # A recipient without the permission reads the masked identity.
            yield self.set_redaction_privileges(receiver_id, False)
            report = yield rtip.redact_report(SimpleNamespace(user_id=receiver_id), build_report(itip_id))
            value = report['data']['whistleblower_identity'][identity_field_id][0]['value']
            self.assertNotIn('SECRET', value)
            self.assertIn(mask, value)

            yield self.set_redaction_privileges(receiver_id, True)


class TestWhistleblowerFileDownload(helpers.TestHandlerWithPopulatedDB):
    _handler = rtip.WhistleblowerFileDownload

    @transact
    def set_antivirus_enabled(self, session, enabled):
        db_set_config_variable(session, 1, 'antivirus_enabled', enabled)

    @transact
    def set_wbfile_antivirus_state(self, session, file_id, state):
        db_set_config_variable(session, 1, 'antivirus_enabled', True)
        ifile = session.query(models.InternalFile) \
                       .join(models.WhistleblowerFile,
                             models.InternalFile.id == models.WhistleblowerFile.internalfile_id) \
                       .filter(models.WhistleblowerFile.id == file_id).one()
        ifile.state = state
        ifile.verification_date = datetime_now()


    @inlineCallbacks
    def test_get(self):
        yield self.perform_minimal_submission_actions()
        yield Delivery().run()

        rtip_descs = yield self.get_rtips()
        for rtip_desc in rtip_descs:
            wbfile_ids = yield self.get_wbfiles(rtip_desc['rtip_id'])
            for wbfile_id in wbfile_ids:
                handler = self.request(role='receiver', user_id=rtip_desc['receiver_id'])
                yield handler.get(wbfile_id)
                self.assertNotEqual(handler.request.getResponseBody(), '')

    @inlineCallbacks
    def test_pgp_download_serialized_per_user(self):
        # The recipient has a PGP key (pgp_configuration='ALL'), so the download
        # is PGP-wrapped and must be serialized per user: while one is in flight
        # a second waits its turn rather than running in parallel, and the lock
        # is dropped once idle.
        yield self.perform_minimal_submission_actions()
        yield Delivery().run()

        rtip_descs = yield self.get_rtips()
        rtip_desc = rtip_descs[0]
        receiver_id = rtip_desc['receiver_id']
        wbfile_ids = yield self.get_wbfiles(rtip_desc['rtip_id'])

        self.assertEqual(self.state.download_locks, {})

        # Hold the receiver's lock to stand in for an in-flight heavy download.
        lock = DeferredLock()
        self.state.download_locks[receiver_id] = lock
        yield lock.acquire()

        handler = self.request(role='receiver', user_id=receiver_id)
        d = handler.get(wbfile_ids[0])

        # With the lock held, the PGP download must park rather than complete.
        yield task.deferLater(reactor, 0.5)
        self.assertFalse(d.called)

        # Releasing the lock lets the queued download finish and the lock is
        # then removed from the mapping.
        lock.release()
        yield d
        self.assertNotEqual(handler.request.getResponseBody(), b'')
        self.assertEqual(self.state.download_locks, {})


class TestIdentityAccessRequestsCollection(helpers.TestHandlerWithPopulatedDB):
    _handler = rtip.IdentityAccessRequestsCollection

    @inlineCallbacks
    def setUp(self):
        yield helpers.TestHandlerWithPopulatedDB.setUp(self)
        yield self.perform_minimal_submission_actions()

    @inlineCallbacks
    def test_post(self):
        body = {
            'request_motivation': ''
        }

        rtip_descs = yield self.get_rtips()
        for rtip_desc in rtip_descs:
            handler = self.request(body, role='receiver', user_id=rtip_desc['receiver_id'])
            yield handler.post(rtip_desc['id'])
