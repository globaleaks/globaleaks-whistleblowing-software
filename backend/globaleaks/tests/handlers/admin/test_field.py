
from globaleaks import models
from globaleaks.handlers import admin
from globaleaks.handlers.admin.field import create_field, delete_field
from globaleaks.orm import transact
from globaleaks.rest import errors
from globaleaks.tests import helpers
from twisted.internet.defer import inlineCallbacks


@transact
def get_id_of_first_step_of_questionnaire(session, questionnaire_id):
    return session.query(models.Step).filter(models.Step.questionnaire_id == questionnaire_id)[0].id


class TestFieldCreate(helpers.TestHandler):
    _handler = admin.field.FieldsCollection

    @inlineCallbacks
    def test_post(self):
        """
        Attempt to create a new field via a post request.
        """
        values = helpers.get_dummy_field()
        values['instance'] = 'instance'
        values['step_id'] = yield get_id_of_first_step_of_questionnaire('default')
        handler = self.request(values, role='admin')
        response = yield handler.post()
        self.assertIn('id', response)
        self.assertNotEqual(response.get('options'), None)

    @inlineCallbacks
    def test_post_create_from_template(self):
        """
        Attempt to create a new field from template via post request
        """
        values = helpers.get_dummy_field()
        values['instance'] = 'template'
        field_template = yield create_field(1, values, 'en')

        values = helpers.get_dummy_field()
        values['instance'] = 'reference'
        values['template_id'] = field_template['id']
        values['step_id'] = yield get_id_of_first_step_of_questionnaire('default')

        handler = self.request(values, role='admin')
        response = yield handler.post()
        self.assertIn('id', response)
        self.assertNotEqual(response.get('options'), None)

        # Ensure it is not possible to delete a template that is in use
        yield self.assertFailure(delete_field(1, field_template['id']), errors.InputValidationError)


class TestFieldInstance(helpers.TestHandler):
    _handler = admin.field.FieldInstance

    @inlineCallbacks
    def test_put(self):
        """
        Attempt to update a field, changing its type via a put request.
        """
        values = helpers.get_dummy_field()
        values['instance'] = 'instance'
        values['step_id'] = yield get_id_of_first_step_of_questionnaire('default')
        field = yield create_field(1, values, 'en')

        updated_sample_field = helpers.get_dummy_field()
        updated_sample_field['instance'] = 'instance'
        updated_sample_field['step_id'] = yield get_id_of_first_step_of_questionnaire('default')
        updated_sample_field.update(type=u'inputbox', options=[], x=3, y=3)

        handler = self.request(updated_sample_field, role='admin')
        response = yield handler.put(field['id'])

        self.assertEqual(field['id'], response['id'])
        self.assertEqual(3, response['x'])
        self.assertEqual(3, response['y'])

        wrong_sample_field = helpers.get_dummy_field()
        values['instance'] = 'instance'
        values['step_id'] = yield get_id_of_first_step_of_questionnaire('default')
        wrong_sample_field.update(type='nonexistingfieldtype')
        handler = self.request(wrong_sample_field, role='admin')

        self.assertRaises(errors.InputValidationError, handler.put, field['id'])

    @inlineCallbacks
    def test_delete(self):
        """
        Create a new field, then attempt to delete it.
        """
        values = helpers.get_dummy_field()
        values['instance'] = 'instance'
        values['step_id'] = yield get_id_of_first_step_of_questionnaire('default')
        field = yield create_field(1, values, 'en')

        handler = self.request(role='admin')
        yield handler.delete(field['id'])


class TestFieldTemplateInstance(helpers.TestHandlerWithPopulatedDB):
    _handler = admin.field.FieldTemplateInstance

    @inlineCallbacks
    def test_get(self):
        """
        Attempt to update a field, changing its type via a put request.
        """
        values = helpers.get_dummy_field()
        values['instance'] = 'template'
        field = yield create_field(1, values, 'en')

        handler = self.request(role='admin')
        yield handler.get(field['id'])

    @inlineCallbacks
    def test_put(self):
        """
        Attempt to update a field, changing its type via a put request.
        """
        values = helpers.get_dummy_field()
        values['instance'] = 'template'
        field = yield create_field(1, values, 'en')

        updated_sample_field = helpers.get_dummy_field()
        updated_sample_field['instance'] = 'template'
        updated_sample_field['type'] = 'inputbox'
        updated_sample_field['options'] = []
        updated_sample_field['x'] = 3
        updated_sample_field['y'] = 3

        handler = self.request(updated_sample_field, role='admin')
        response = yield handler.put(field['id'])
        self.assertEqual(field['id'], response['id'])
        self.assertEqual(3, response['x'])
        self.assertEqual(3, response['y'])

        wrong_sample_field = helpers.get_dummy_field()
        wrong_sample_field.update(type='nonexistingfieldtype')
        handler = self.request(wrong_sample_field, role='admin')

        self.assertRaises(errors.InputValidationError, handler.put, field['id'])

    @inlineCallbacks
    def test_delete(self):
        """
        Create a new field template, then attempt to delete it.
        """
        values = helpers.get_dummy_field()
        values['instance'] = 'template'
        field = yield create_field(1, values, 'en')

        handler = self.request(role='admin')
        yield handler.delete(field['id'])


class TestFieldTemplatesCollection(helpers.TestHandlerWithPopulatedDB):
    _handler = admin.field.FieldTemplatesCollection

    @inlineCallbacks
    def test_get(self):
        """
        Retrieve a list of all fields, and verify that they do exist in the
        database.
        """
        n = 3
        ids = []
        for _ in range(n):
            values = helpers.get_dummy_field()
            values['instance'] = 'template'
            handler = self.request(values, role='admin')
            response = yield handler.post()
            ids.append(response['id'])

        handler = self.request(role='admin')
        fields = yield handler.get()

        check_ids = [field.get('id') for field in fields]
        self.assertGreater(len(fields), n)
        self.assertNotIn(None, ids)

        for x in ids:
            self.assertIn(x, check_ids)

        # check tha childrens are not present in the list
        # as the list should contain only parents fields
        for field in fields:
            for child in field['children']:
                self.assertNotIn(child, ids)

    @inlineCallbacks
    def test_post(self):
        """
        Attempt to create a new field via a post request.
        """
        values = helpers.get_dummy_field()
        values['instance'] = 'template'
        handler = self.request(values, role='admin')
        response = yield handler.post()
        self.assertIn('id', response)
        self.assertNotEqual(response.get('options'), None)
