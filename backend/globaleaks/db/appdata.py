import os

from globaleaks import models
from globaleaks.handlers.admin.field import db_create_field
from globaleaks.handlers.admin.questionnaire import db_create_questionnaire
from globaleaks.orm import db_del
from globaleaks.settings import Settings
from globaleaks.utils.fs import read_json_file


def extract_ids(obj, ret=[]):
    """
    Utility function to extract ids from questionnaires
    and questions data structures.
    """
    if obj.get('id', None):
        ret.append(obj['id'])

    for c in obj['children']:
        ret = extract_ids(c, ret)

    return ret


def load_appdata():
    """
    Utility function to load the application data file

    :return: Return the parsed application data file
    """
    return read_json_file(Settings.appdata_file)


def db_load_default_questionnaires(session):
    """
    Transaction for loading default questionnaires
    :param session: An ORM session
    """
    qfiles = [os.path.join(Settings.questionnaires_path, path)
              for path in os.listdir(Settings.questionnaires_path)]
    questionnaires = []
    ids = []

    for qfile in qfiles:
        questionnaires.append(read_json_file(qfile))
        ids.append(questionnaires[-1]['id'])

        for s in questionnaires[-1]['steps']:
            extract_ids(s, ids)

    db_del(session, models.Questionnaire, models.Questionnaire.id.in_(ids))
    db_del(session, models.Step, models.Step.questionnaire_id.in_(ids))
    db_del(session, models.Field, models.Field.id.in_(ids))
    db_del(session, models.FieldAttr, models.FieldAttr.field_id.in_(ids))
    db_del(session, models.FieldOption, models.FieldOption.field_id.in_(ids))
    db_del(session, models.FieldOptionTriggerField, models.FieldOptionTriggerField.object_id.in_(ids))
    db_del(session, models.FieldOptionTriggerStep, models.FieldOptionTriggerStep.object_id.in_(ids))

    for questionnaire in questionnaires:
        db_create_questionnaire(session, 1, None, questionnaire, None)


def db_load_default_fields(session):
    """
    Transaction for loading default questions
    :param session: An ORM session
    """
    ffiles = [os.path.join(Settings.questions_path, path)
              for path in os.listdir(Settings.questions_path)]
    questions = []
    ids = []

    for ffile in ffiles:
        questions.append(read_json_file(ffile))
        extract_ids(questions[-1], ids)

    db_del(session, models.Field, models.Field.id.in_(ids))
    db_del(session, models.Field, models.Field.fieldgroup_id.in_(ids))
    db_del(session, models.FieldAttr, models.FieldAttr.field_id.in_(ids))
    db_del(session, models.FieldOption, models.FieldOption.field_id.in_(ids))
    db_del(session, models.FieldOptionTriggerField, models.FieldOptionTriggerField.object_id.in_(ids))
    db_del(session, models.FieldOptionTriggerStep, models.FieldOptionTriggerStep.object_id.in_(ids))

    for question in questions:
        db_create_field(session, 1, question, None)


def db_load_defaults(session):
    """
    Transaction for updating application defaults

    :param session: An ORM session
    """
    db_load_default_questionnaires(session)
    db_load_default_fields(session)
