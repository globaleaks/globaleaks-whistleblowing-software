# -*- coding: utf-8 -*-
from sqlalchemy.orm.exc import NoResultFound
from twisted.internet.defer import inlineCallbacks

from globaleaks import models
from globaleaks.handlers.recipient import rtip
from globaleaks.jobs.delivery import Delivery
from globaleaks.tests import helpers
from globaleaks.utils.utility import datetime_now


class TestRTipInstance(helpers.TestHandlerWithPopulatedDB):
    _handler = rtip.RTipInstance

    @inlineCallbacks
    def setUp(self):
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
    def test_postpone(self):
        now = datetime_now()

        yield self.force_itip_expiration()

        rtip_descs = yield self.get_rtips()

        for rtip_desc in rtip_descs:
            operation = {
              'operation': 'postpone',
              'args': {
                'value': 9999999999999999
              }
            }

            handler = self.request(operation, role='receiver', user_id=rtip_desc['receiver_id'])
            yield handler.put(rtip_desc['id'])
            self.assertEqual(handler.request.code, 200)

        rtip_descs = yield self.get_rtips()
        for rtip_desc in rtip_descs:
            self.assertTrue(rtip_desc['expiration_date'] >= now)

    @inlineCallbacks
    def test_grant_and_revoke_access(self):
        rtip_descs = yield self.get_rtips()

        count = len(rtip_descs)

        yield self.test_model_count(models.ReceiverTip, count)

        for rtip_desc in rtip_descs:
            if rtip_desc['receiver_id'] != self.dummyReceiver_1['id']:
                continue

            count -= 1

            operation = {
              'operation': 'revoke',
              'args': {
                'receiver':  self.dummyReceiver_2['id']
              }
            }

            handler = self.request(operation, role='receiver', user_id=rtip_desc['receiver_id'])
            yield handler.put(rtip_desc['id'])
            self.assertEqual(handler.request.code, 200)
            yield self.test_model_count(models.ReceiverTip, count)

        for rtip_desc in rtip_descs:
            if rtip_desc['receiver_id'] != self.dummyReceiver_1['id']:
                return

            count += 1

            operation = {
              'operation': 'grant',
              'args': {
                'receiver':  self.dummyReceiver_2['id']
              }
            }

            handler = self.request(operation, role='receiver', user_id=rtip_desc['receiver_id'])
            yield handler.put(rtip_desc['id'])
            self.assertEqual(handler.request.code, 200)
            yield self.test_model_count(models.ReceiverTip, count)

    @inlineCallbacks
    def test_transfer(self):
        rtip_descs = yield self.get_rtips()

        for rtip_desc in rtip_descs:
            if rtip_desc['receiver_id'] != self.dummyReceiver_1['id']:
                continue

            operation = {
              'operation': 'revoke',
              'args': {
                'receiver':  self.dummyReceiver_2['id']
              }
            }

            handler = self.request(operation, role='receiver', user_id=rtip_desc['receiver_id'])
            yield handler.put(rtip_desc['id'])
            self.assertEqual(handler.request.code, 200)

        rtip_descs = yield self.get_rtips()
        count = len(rtip_descs)

        for rtip_desc in rtip_descs:
            if rtip_desc['receiver_id'] != self.dummyReceiver_1['id']:
                return

            operation = {
              'operation': 'transfer',
              'args': {
                'receiver':  self.dummyReceiver_2['id']
              }
            }

            handler = self.request(operation, role='receiver', user_id=rtip_desc['receiver_id'])
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
        self.assertEqual(len(rtip_descs), self.population_of_submissions * self.population_of_recipients)

        # we delete the first and then we verify that the second does not exist anymore
        handler = self.request(role='receiver', user_id=rtip_descs[0]['receiver_id'])
        yield handler.delete(rtip_descs[0]['id'])

        rtip_descs = yield self.get_rtips()

        self.assertEqual(len(rtip_descs), self.population_of_submissions * self.population_of_recipients - self.population_of_recipients)

    @inlineCallbacks
    def test_delete_unexistent_tip_by_existent_and_logged_receiver(self):
        rtip_descs = yield self.get_rtips()

        for rtip_desc in rtip_descs:
            handler = self.request(role='receiver', user_id=rtip_desc['receiver_id'])
            yield self.assertFailure(handler.delete(u"unexistent_tip"), NoResultFound)

    @inlineCallbacks
    def test_delete_existent_tip_by_existent_and_logged_but_wrong_receiver(self):
        rtip_descs = yield self.get_rtips()

        for rtip_desc in rtip_descs:
            handler = self.request(role='receiver', user_id=rtip_desc['receiver_id'])
            yield self.assertFailure(handler.delete(u"unexistent_tip"), NoResultFound)


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
            'visibility': "public",
            'tids': []
        }

        rtip_descs = yield self.get_rtips()
        for rtip_desc in rtip_descs:
            handler = self.request(body, role='receiver', user_id=rtip_desc['receiver_id'])
            yield handler.post(rtip_desc['id'])


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


class TestWhistleblowerFileDownload(helpers.TestHandlerWithPopulatedDB):
    _handler = rtip.WhistleblowerFileDownload

    @inlineCallbacks
    def test_get(self):
        yield self.perform_minimal_submission_actions()
        yield Delivery().run()

        rtip_descs = yield self.get_rtips()
        for rtip_desc in rtip_descs:
            wbfile_ids = yield self.get_wbfiles(rtip_desc['id'])
            for wbfile_id in wbfile_ids:
                handler = self.request(role='receiver', user_id=rtip_desc['receiver_id'])
                yield handler.get(wbfile_id)
                self.assertNotEqual(handler.request.getResponseBody(), '')


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
