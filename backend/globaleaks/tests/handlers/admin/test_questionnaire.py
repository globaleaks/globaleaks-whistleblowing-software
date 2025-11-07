import os

from twisted.internet.defer import inlineCallbacks

from globaleaks import models
from globaleaks.handlers.admin import questionnaire
from globaleaks.models import Questionnaire
from globaleaks.rest import errors
from globaleaks.tests import helpers
from globaleaks.utils.fs import read_json_file


class TestQuestionnairesCollection(helpers.TestCollectionHandler):
    _handler = questionnaire.QuestionnairesCollection
    _test_desc = {
        'model': Questionnaire,
        'create': questionnaire.create_questionnaire,
        'data': {
            'name': 'test'
        }
    }

    @inlineCallbacks
    def test_post_invalid_json(self):
        self.test_data_dir = os.path.join(helpers.DATA_DIR, 'questionnaires')

        invalid_test_cases = [
            ('cyclic_groupid.json', errors.InputValidationError)
        ]

        for fname, err in invalid_test_cases:
            new_q = read_json_file(os.path.join(self.test_data_dir, fname))

            handler = self.request(new_q, role='admin')
            handler.request.language = None

            yield self.assertFailure(handler.post(), err)

    @inlineCallbacks
    def test_post_valid_json(self):
        self.test_data_dir = os.path.join(helpers.DATA_DIR, 'questionnaires')

        new_q = read_json_file(os.path.join(self.test_data_dir, 'valid.json'))

        handler = self.request(new_q, role='admin')
        handler.request.language = None

        yield handler.post()


class TestQuestionnaireInstance(helpers.TestInstanceHandler):
    _handler = questionnaire.QuestionnaireInstance
    _test_desc = {
        'model': Questionnaire,
        'create': questionnaire.create_questionnaire,
        'data': {
            'name': 'test'
        }
    }


class TestQuestionnareDuplication(helpers.TestHandlerWithPopulatedDB):
    _handler = questionnaire.QuestionnareDuplication

    def setUp(self):
        return helpers.TestHandlerWithPopulatedDB.setUp(self)

    @inlineCallbacks
    def test_duplicate_questionnaire(self):
        # Sanity check our base behavior
        yield self.test_model_count(models.Questionnaire, 2)

        data_request = {
            'questionnaire_id': 'default',
            'new_name': 'Duplicated Default'
        }

        handler = self.request(data_request, role='admin')
        yield handler.post()

        yield self.test_model_count(models.Questionnaire, 3)
