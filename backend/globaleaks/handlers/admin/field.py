# -*- coding: utf-8
from sqlalchemy.sql.expression import not_

from globaleaks import models
from globaleaks.handlers.base import BaseHandler
from globaleaks.handlers.public import serialize_field, trigger_map
from globaleaks.models import fill_localized_keys
from globaleaks.orm import db_add, db_get, db_del, transact, tw
from globaleaks.rest import errors, requests
from globaleaks.settings import Settings
from globaleaks.utils.fs import read_json_file


def fieldtree_ancestors(session, field_id):
    """
    Transaction to extract the parents of a field

    :param session: An ORM session
    :param field_id: The field ID
    """
    field = session.query(models.Field).filter(models.Field.id == field_id).one_or_none()
    if field.fieldgroup_id is not None:
        yield field.fieldgroup_id
        yield fieldtree_ancestors(session, field.fieldgroup_id)


def db_create_option_trigger(session, option_id, type, object_id, sufficient):
    """
    Transaction for creating an option trigger

    :param session: An ORM session
    :param option_id: The option id
    :param type: The trigger type
    :param object_id: The object to be connected to the trigger
    :param sufficient: A boolean indicating if the condition is sufficient
    """
    o = trigger_map[type]()
    o.option_id = option_id
    o.object_id = object_id
    o.sufficient = sufficient
    session.add(o)


def db_reset_option_triggers(session, type, object_id):
    """
    Transaction for resetting every option trigger set on the specified object

    :param session: An ORM session
    :param type: The type of trigger to be reset
    :param object_id: The object on which reset the triggers
    """
    m = trigger_map[type]
    db_del(session, m, m.object_id == object_id)


def db_update_fieldoption(session, field_id, fieldoption_id, option_dict, language, idx):
    """
    Transaction to update a field option

    :param session: An ORM session
    :param field_id: The field ID of the field on which the option is set
    :param fieldoption_id: The option ID
    :param option_dict: The option configuration
    :param language: The language of the request
    :param idx: The order index with reference to the other options set
    :return: The serialized descriptor of the option
    """
    option_dict['fieldoption_id'] = fieldoption_id
    option_dict['field_id'] = field_id
    option_dict['idx'] = idx

    fill_localized_keys(option_dict, models.FieldOption.localized_keys, language)

    o = None
    if fieldoption_id is not None:
        o = session.query(models.FieldOption) \
                   .filter(models.FieldOption.id == fieldoption_id,
                           models.FieldOption.field_id == field_id).one_or_none()

    if o is None:
        o = db_add(session, models.FieldOption, option_dict)
    else:
        o.update(option_dict)

    o.order = idx

    return o.id


def db_update_fieldoptions(session, field_id, options, language):
    """
    Transaction to update a set of options at once

    :param session: An ORM session
    :param field_id: The field on which the options are set
    :param options: The list of options to be updated
    :param language: The language of the request
    """
    options_ids = [db_update_fieldoption(session, field_id, option['id'], option, language, idx) for idx, option in enumerate(options)]

    if not options_ids:
        return

    subquery = session.query(models.FieldOption.id) \
                      .filter(models.FieldOption.field_id == field_id,
                              not_(models.FieldOption.id.in_(options_ids))) \
                      .subquery()

    db_del(session,
           models.FieldOption,
           models.FieldOption.id.in_(subquery))


def db_update_fieldattr(session, field_id, attr_name, attr_dict, language):
    """
    Transaction for updating a fieldattr

    :param session: An ORM session
    :param field_id: The field on which the attribute is configured
    :param attr_name: The attribute name
    :param attr_dict: The attribute configuration
    :param language: The language of the request
    :return: The ID of the attribute
    """
    attr_dict['name'] = attr_name
    attr_dict['field_id'] = field_id

    if attr_dict['type'] == 'localized' and language is not None:
        fill_localized_keys(attr_dict, ['value'], language)

    o = session.query(models.FieldAttr) \
               .filter(models.FieldAttr.field_id == field_id,
                       models.FieldAttr.name == attr_name).one_or_none()

    if o is None:
        o = db_add(session, models.FieldAttr, attr_dict)
    else:
        o.update(attr_dict)

    return o.name


def db_update_fieldattrs(session, field_id, field_attrs, language):
    """
    Transaction to update a set of fieldattrs at once

    :param session: An ORM session
    :param field_id: The field on which the fieldattrs are set
    :param field_attrs: The list of fieldattrs to be updated
    :param language: The language of the request
    """
    attrs_names = [db_update_fieldattr(session, field_id, attr_name, attr, language) for attr_name, attr in field_attrs.items()]

    if not attrs_names:
        return

    session.query(models.FieldAttr) \
           .filter(models.FieldAttr.field_id == field_id,
                   not_(models.FieldAttr.name.in_(attrs_names))) \
           .delete(synchronize_session=False)


def check_field_association(session, tid, request):
    """
    Transaction to check consistency of field association

    :param session: The ORM session
    :param tid: The tenant ID
    :param request: The request data to be verified
    """
    if request.get('fieldgroup_id', '') and session.query(models.Field).filter(models.Field.id == request['fieldgroup_id'],
                                                                               models.Field.tid != tid).count():
        raise errors.InputValidationError

    if request.get('template_id', '') and session.query(models.Field).filter(models.Field.id == request['template_id'],
                                                                             not_(models.Field.tid.in_(
                                                                                 {1, tid}))).count():
        raise errors.InputValidationError

    if request.get('step_id', '') and session.query(models.Field).filter(models.Step.id == request['step_id'],
                                                                         models.Questionnaire.id == models.Step.questionnaire_id,
                                                                         not_(models.Questionnaire.tid.in_(
                                                                             {1, tid}))).count():
        raise errors.InputValidationError

    if request.get('fieldgroup_id', ''):
        ancestors = set(fieldtree_ancestors(session, request['fieldgroup_id']))
        if request['id'] == request['fieldgroup_id'] or request['id'] in ancestors:
            raise errors.InputValidationError("Provided field association would cause recursion loop")


def db_get_field(session, tid, field_id, language=None, data=None, serialize_templates=False):
    field = db_get(session,
                   models.Field,
                   (models.Field.tid == tid,
                    models.Field.id == field_id))

    return serialize_field(session, tid, field, language, data, serialize_templates)


def db_create_field(session, tid, request, language):
    """
    Transaction for creating a field

    :param session: An ORM session
    :param tid: The tenant ID
    :param request: The request data
    :param language: The language of the request
    :return: The created field
    """
    request['tid'] = tid

    fill_localized_keys(request, models.Field.localized_keys, language)

    check_field_association(session, tid, request)

    field_attrs = read_json_file(Settings.field_attrs_file)

    if not request.get('template_id'):
        field = db_add(session, models.Field, request)
        field.statistical = request.get('statistical', False)

        attrs = request.get('attrs')
        if not attrs:
            attrs = field_attrs.get(field.type, {})

        options = request.get('options')

        db_update_fieldattrs(session, field.id, attrs, language)
        db_update_fieldoptions(session, field.id, options, language)

        for trigger in request.get('triggered_by_options', []):
            db_create_option_trigger(session, trigger['option'], 'field', field.id, trigger.get('sufficient', True))
    else:
        if request['template_id'] == 'whistleblower_identity':
            if request.get('step_id', '') == '':
                raise errors.InputValidationError("Cannot associate whistleblower identity field to a fieldgroup")

            q_id = session.query(models.Questionnaire.id) \
                          .filter(models.Questionnaire.id == models.Step.questionnaire_id,
                                  models.Step.id == request['step_id'])

            field = session.query(models.Field) \
                           .filter(models.Field.template_id == 'whistleblower_identity',
                                   models.Field.step_id == models.Step.id,
                                   models.Step.questionnaire_id.in_(q_id.subquery())).one_or_none()

            if field is not None:
                raise errors.InputValidationError("Whistleblower identity field already present")

        field = db_add(session, models.Field, request)

        template = session.query(models.Field).filter(models.Field.id == request['template_id']).one()

        field.label = template.label
        field.description = template.description
        field.hint = template.hint
        field.placeholder = template.placeholder

        attrs = request.get('attrs')
        if not attrs:
            attrs = field_attrs.get(field.template_id, {})

        db_update_fieldattrs(session, field.id, attrs, None)

    for c in request.get('children', []):
        c['tid'] = field.tid
        c['fieldgroup_id'] = field.id
        db_create_field(session, tid, c, language)

    return field


@transact
def create_field(session, tid, request, language):
    """
    Transaction for creating a field

    :param session: An ORM session
    :param tid: The tenant ID
    :param request: The request data
    :param language: The language of the request
    :return: The serializated descriptor of the created field
    """
    field = db_create_field(session, tid, request, language)

    return serialize_field(session, tid, field, language)


def db_update_field(session, tid, field_id, request, language):
    """
    Transaction for updating a field

    :param session: An ORM session
    :param tid: The tenant ID
    :param field_id: The ID of the object to be updated
    :param request: The request data
    :param language: The language of the request
    :return: The updated field
    """
    field = db_get(session,
                   models.Field,
                   (models.Field.tid == tid,
                    models.Field.id == field_id))

    check_field_association(session, tid, request)

    fill_localized_keys(request, models.Field.localized_keys, language)

    if field.instance != 'reference' or field.template_id == 'whistleblower_identity':
        db_update_fieldattrs(session, field.id, request['attrs'], language)

    db_reset_option_triggers(session, 'field', field.id)

    for trigger in request.get('triggered_by_options', []):
        db_create_option_trigger(session, trigger['option'], 'field', field.id, trigger.get('sufficient', True))

    if field.instance != 'reference':
        db_update_fieldoptions(session, field.id, request['options'], language)

        # full update
        field.update(request)

    else:
        # partial update
        field.update({
            'label': request['label'],
            'hint': request['hint'],
            'description': request['description'],
            'placeholder': request['placeholder'],
            'template_override_id': request['template_override_id'],
            'x': request['x'],
            'y': request['y'],
            'width': request['width'],
            'required': request['required'],
            'statistical': request['statistical']
        })

    return field


@transact
def update_field(session, tid, field_id, field, language):
    """
    Transaction for updating a field
    :param session: An ORM session
    :param tid: The tenant ID
    :param field_id: A field ID of the field to be updated
    :param field: A descriptor of field configuration
    :param language: The language of the request
    :return: The serialized descriptor of the updated field
    """
    field = db_update_field(session, tid, field_id, field, language)

    return serialize_field(session, tid, field, language)


@transact
def delete_field(session, tid, field_id):
    """
    Transaction to delete a field

    :param session: An ORM session
    :param tid: The tenant ID
    :param field_id: The id of the field to be deleted
    """
    field = db_get(session,
                   models.Field,
                   (models.Field.tid == tid,
                    models.Field.id == field_id))

    if field.instance == 'template' and session.query(models.Field).filter(models.Field.tid == tid, models.Field.template_id == field.id).count():
        raise errors.InputValidationError("Cannot remove the field template as it is used by one or more questionnaires")

    session.delete(field)


@transact
def get_fieldtemplate_list(session, tid, language):
    """
    Transaction to retrieve the list of the field templates defined on a tenant

    :param session: An ORM session
    :param tid: The tenant ID on which perform the lookup
    :param language: The language of the request
    :return: The list of serialized field template descriptors
    """
    templates = session.query(models.Field).filter(models.Field.tid.in_({1, tid}),
                                                   models.Field.instance == 'template',
                                                   models.Field.fieldgroup_id.is_(None))

    return [serialize_field(session, tid, f, language) for f in templates]


class FieldTemplatesCollection(BaseHandler):
    check_roles = 'admin'
    invalidate_cache = True

    def get(self):
        """
        Return a list of all the fields templates.
        """
        return get_fieldtemplate_list(self.request.tid, self.request.language)

    def post(self):
        """
        Create a field template.
        """
        if self.request.multilang:
            language = None
            validator = requests.AdminFieldDescRaw
        else:
            language = self.request.language
            validator = requests.AdminFieldDesc

        request = self.validate_request(self.request.content.read(), validator)

        request['instance'] = 'template'
        for k in ['fieldgroup_id', 'step_id', 'template_id', 'template_override_id', 'triggered_by_options']:
            del request[k]

        return create_field(self.request.tid, request, language)


class FieldTemplateInstance(BaseHandler):
    check_roles = 'admin'
    invalidate_cache = True

    def get(self, field_id):
        """
        Export field template
        """
        return tw(db_get_field, self.request.tid, field_id, None)

    def put(self, field_id):
        """
        Update a field template
        """
        request = self.validate_request(self.request.content.read(),
                                        requests.AdminFieldDesc)

        return update_field(self.request.tid,
                            field_id,
                            request,
                            self.request.language)

    def delete(self, field_id):
        """
        Delete a field template.
        """
        return delete_field(self.request.tid, field_id)


class FieldsCollection(BaseHandler):
    check_roles = 'admin'
    invalidate_cache = True

    def post(self):
        """
        Create a field.
        """
        request = self.validate_request(self.request.content.read(),
                                        requests.AdminFieldDesc)

        return create_field(self.request.tid,
                            request,
                            self.request.language)


class FieldInstance(BaseHandler):
    check_roles = 'admin'
    invalidate_cache = True

    def put(self, field_id):
        """
        Update a field.
        """
        request = self.validate_request(self.request.content.read(),
                                        requests.AdminFieldDesc)

        return update_field(self.request.tid,
                            field_id,
                            request,
                            self.request.language)

    def delete(self, field_id):
        """
        Delete a field.
        """
        return delete_field(self.request.tid, field_id)
