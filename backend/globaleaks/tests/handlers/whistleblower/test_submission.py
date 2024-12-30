# -*- coding: utf-8 -*-
from twisted.internet.defer import inlineCallbacks, returnValue

from globaleaks.handlers import auth
from globaleaks.handlers.whistleblower import submission, wbtip
from globaleaks.jobs import delivery
from globaleaks.models.config import db_set_config_variable
from globaleaks.orm import tw
from globaleaks.rest import errors
from globaleaks.tests import helpers


class TestSubmission(helpers.TestHandlerWithPopulatedDB):
    _handler = submission.SubmissionInstance

    complex_field_population = True

    files_created = 6

    @inlineCallbacks
    def setUp(self):
        yield helpers.TestHandlerWithPopulatedDB.setUp(self)
        yield tw(db_set_config_variable, 1, 'encryption', False)
        self.state.tenants[1].cache.encryption = False

    @inlineCallbacks
    def create_submission(self, request):
        self.submission_desc = yield self.get_dummy_submission(self.dummyContext['id'])
        handler = self.request(self.submission_desc, role='whistleblower')
        response = yield handler.post()
        returnValue(response['receipt'])

    @inlineCallbacks
    def create_submission_with_files(self, request):
        self.submission_desc = yield self.get_dummy_submission(self.dummyContext['id'])
        handler = self.request(self.submission_desc, role='whistleblower')
        self.emulate_file_upload(handler.session, 3)
        response = yield handler.post()
        returnValue(response['receipt'])

    @inlineCallbacks
    def test_create_submission_with_no_recipients(self):
        self.submission_desc = yield self.get_dummy_submission(self.dummyContext['id'])
        self.submission_desc['receivers'] = []
        handler = self.request(self.submission_desc, role='whistleblower')
        self.assertFailure(handler.post(), errors.InputValidationError)

    @inlineCallbacks
    def test_create_simple_submission(self):
        self.submission_desc = yield self.get_dummy_submission(self.dummyContext['id'])
        yield self.create_submission(self.submission_desc)

    @inlineCallbacks
    def test_create_submission_attach_files_finalize_and_verify_file_creation(self):
        self.submission_desc = yield self.get_dummy_submission(self.dummyContext['id'])
        yield self.create_submission_with_files(self.submission_desc)
        yield delivery.Delivery().run()

    @inlineCallbacks
    def test_update_submission(self):
        self.submission_desc = yield self.get_dummy_submission(self.dummyContext['id'])

        self.submission_desc['answers'] = yield self.fill_random_answers(self.dummyContext['questionnaire_id'])
        receipt = yield self.create_submission(self.submission_desc)

        session = yield auth.login_whistleblower(1, receipt, True)

        wbtip_desc, _ = yield wbtip.get_wbtip(session.user_id, 'en')

        self.assertTrue('data' in wbtip_desc)
