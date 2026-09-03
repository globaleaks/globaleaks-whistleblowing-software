from twisted.internet.defer import inlineCallbacks

from globaleaks import models
from globaleaks.handlers.admin import submission_statuses
from globaleaks.handlers.public import db_get_submission_status, db_get_submission_statuses
from globaleaks.orm import tw, transact
from globaleaks.tests import helpers


@transact
def count_submission_statuses(session, tid):
    """Counts all submission statuses in the system"""
    return session.query(models.SubmissionStatus) \
                  .filter(models.SubmissionStatus.tid == tid).count()


@transact
def create_substatus(session, submissionstatus_id):
    """Creates a test substatus"""
    substatus = models.SubmissionSubStatus()
    substatus.submissionstatus_id = submissionstatus_id
    substatus.label = {'en': "Test1"}
    substatus.order = 0
    session.add(substatus)


class SubmissionStatusCollectionDesc(helpers.TestHandlerWithPopulatedDB):
    _handler = submission_statuses.SubmissionStatusCollection

    def setUp(self):
        return helpers.TestHandlerWithPopulatedDB.setUp(self)

    @inlineCallbacks
    def test_get(self):
        handler = self.request({}, role='admin')
        response = yield handler.get()

        self.assertEqual(len(response), 3)

    @inlineCallbacks
    def test_post(self):
        # Create a submission status
        data_request = {
            'label': 'test_status',
            'order': 0
        }

        handler = self.request(data_request, role='admin')
        yield handler.post()

        session_status_count = yield count_submission_statuses(1)
        self.assertEqual(session_status_count, 4)

    @inlineCallbacks
    def test_get_with_substatuses(self):
        yield create_substatus('new')

        handler = self.request({}, role='admin')
        response = yield handler.get()

        self.assertEqual(len(response), 3)

        check_status = None
        for status in response:
            if status['id'] == 'new':
                check_status = status
                break

        self.assertNotEqual(check_status, None)
        self.assertEqual(len(check_status['substatuses']), 1)
        substatus = check_status['substatuses'].pop()
        self.assertEqual(substatus['label'], "Test1")


class SubmissionStatusInstanceDesc(helpers.TestHandlerWithPopulatedDB):
    _handler = submission_statuses.SubmissionStatusInstance

    def setUp(self):
        return helpers.TestHandlerWithPopulatedDB.setUp(self)

    def create_test_status(self):
        self._handler = submission_statuses.SubmissionStatusCollection

        data_request = {
            'label': 'test_status',
            'order': 0
        }
        handler = self.request(data_request, role='admin')

        return handler.post()

    @inlineCallbacks
    def test_put(self):
        """Create a new status and then edit it"""
        status_id = ''
        yield self.create_test_status()
        statuses = yield tw(db_get_submission_statuses, 1, 'en')

        for status in statuses:
            if status['label'] == 'test_status':
                status_id = status['id']

        # Change the submission status info
        data_request = {
            'label': '12345',
            'order': 0
        }

        self._handler = submission_statuses.SubmissionStatusInstance
        handler = self.request(data_request, role='admin')
        yield handler.put(status_id)
        statuses = yield tw(db_get_submission_statuses, 1, 'en')

        found_label = False

        for status in statuses:
            if status['label'] == '12345':
                found_label = True
                break

        self.assertEqual(found_label, True)

    @inlineCallbacks
    def test_delete(self):
        """Delete a status (if possible)"""
        status_id = ''
        yield self.create_test_status()
        statuses = yield tw(db_get_submission_statuses, 1, 'en')

        for status in statuses:
            if status['label'] == 'test_status':
                status_id = status['id']

        self._handler = submission_statuses.SubmissionStatusInstance
        handler = self.request(role='admin')
        yield handler.delete(status_id)

        session_status_count = yield count_submission_statuses(1)
        self.assertEqual(session_status_count, 3)

    @inlineCallbacks
    def test_delete_with_substatuses(self):
        """Delete a status (if possible)"""
        status_id = ''
        yield self.create_test_status()
        statuses = yield tw(db_get_submission_statuses, 1, 'en')

        for status in statuses:
            if status['label'] == 'test_status':
                status_id = status['id']
        yield create_substatus(status_id)

        self._handler = submission_statuses.SubmissionStatusInstance
        handler = self.request(role='admin')
        yield handler.delete(status_id)

        session_status_count = yield count_submission_statuses(1)
        self.assertEqual(session_status_count, 3)


class SubmissionSubStatusCollectionDesc(helpers.TestHandlerWithPopulatedDB):
    _handler = submission_statuses.SubmissionSubStatusCollection

    def setUp(self):
        return helpers.TestHandlerWithPopulatedDB.setUp(self)

    @inlineCallbacks
    def test_get(self):
        yield create_substatus('new')

        handler = self.request({}, role='admin')
        response = yield handler.get('new')
        self.assertEqual(len(response), 1)

    @inlineCallbacks
    def test_post(self):
        data_request = {
            'label': '12345',
            'order': 0,
            'tip_timetolive': 30
        }
        handler = self.request(data_request, role='admin')
        yield handler.post('new')

        submission_status = yield tw(db_get_submission_status, 1, 'new', 'en')
        self.assertEqual(len(submission_status['substatuses']), 1)


class SubmissionSubStatusInstanceDesc(helpers.TestHandlerWithPopulatedDB):
    _handler = submission_statuses.SubmissionSubStatusInstance

    def setUp(self):
        return helpers.TestHandlerWithPopulatedDB.setUp(self)

    @inlineCallbacks
    def test_put(self):
        yield create_substatus('new')

        submission_status = yield tw(db_get_submission_status, 1, 'new', 'en')
        substatus_id = submission_status['substatuses'][0]['id']

        data_request = {
            'label': '12345',
            'order': 0,
            'tip_timetolive': 30
        }

        handler = self.request(data_request, role='admin')
        yield handler.put('new', substatus_id)

        submission_status = yield tw(db_get_submission_status, 1, 'new', 'en')
        self.assertEqual(submission_status['substatuses'][0]['label'], '12345')

    @inlineCallbacks
    def test_delete(self):
        yield create_substatus('new')

        submission_status = yield tw(db_get_submission_status, 1, 'new', 'en')
        substatus_id = submission_status['substatuses'][0]['id']

        handler = self.request({}, role='admin')
        yield handler.delete('new', substatus_id)

        submission_status = yield tw(db_get_submission_status, 1, 'new', 'en')
        self.assertEqual(len(submission_status['substatuses']), 0)
