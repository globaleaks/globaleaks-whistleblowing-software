# -*- coding: utf-8
import copy
import os

from datetime import datetime
from pyexpat import model

from globaleaks import models
from globaleaks.models.config import ConfigFactory
from globaleaks.orm import db_get, db_query, transact
from globaleaks.state import State
from globaleaks.utils.log import log
from sqlalchemy import or_, not_


def get_identity_files(data):
    ids = []

    def extract_from_children(children):
        for child in children:
            if child.get('type') in ['fileupload', 'voice']:
                ids.append(child.get('id'))
            elif child.get('type') == 'fieldgroup':
                extract_from_children(child.get('children', []))

    for questionnaire in data:
        for step in questionnaire.get('steps', []):
            for child in step.get('children', []):
                if child.get('template_id') == 'whistleblower_identity':
                    extract_from_children(child.get('children', []))
                    return ids

    return ids


def serialize_archived_field_recursively(field, language):
    for key, _ in field.get('attrs', {}).items():
        if key not in field['attrs']:
            continue

        if 'type' not in field['attrs'][key]:
            continue

        if field['attrs'][key]['type'] == 'localized':
            if language in field['attrs'][key].get('value', []):
                field['attrs'][key]['value'] = field['attrs'][key]['value'][language]
            else:
                field['attrs'][key]['value'] = ""

    for o in field.get('options', []):
        models.get_localized_values(o, o, models.FieldOption.localized_keys, language)

    for c in field.get('children', []):
        serialize_archived_field_recursively(c, language)

    return models.get_localized_values(field, field, models.Field.localized_keys, language)


def serialize_archived_questionnaire_schema(questionnaire_schema, language):
    questionnaire = copy.deepcopy(questionnaire_schema)

    for step in questionnaire:
        for field in step['children']:
            serialize_archived_field_recursively(field, language)

        models.get_localized_values(step, step, models.Step.localized_keys, language)

    return questionnaire


def serialize_identityaccessrequest(session, identityaccessrequest):
    itip, request_user = session.query(models.InternalTip, models.User) \
                                .filter(models.InternalTip.id == identityaccessrequest.internaltip_id,
                                        models.User.id == identityaccessrequest.request_user_id).one()

    reply_user = session.query(models.User) \
                        .filter(models.User.id == identityaccessrequest.reply_user_id).one_or_none()

    return {
        'id': identityaccessrequest.id,
        'internaltip_id': identityaccessrequest.internaltip_id,
        'request_date': identityaccessrequest.request_date,
        'request_user_name': request_user.name,
        'request_motivation': identityaccessrequest.request_motivation,
        'reply_date': identityaccessrequest.reply_date,
        'reply_user_name': reply_user.id if reply_user is not None else '',
        'reply': identityaccessrequest.reply,
        'reply_motivation': identityaccessrequest.reply_motivation,
        'submission_progressive': itip.progressive,
        'submission_date': itip.creation_date
    }


def serialize_comment(session, comment):
    """
    Transaction returning a serialized descriptor of a comment

    :param session: An ORM session
    :param comment: A model to be serialized
    :return: A serialized description of the model specified
    """
    return {
        'id': comment.id,
        'creation_date': comment.creation_date,
        'content': comment.content,
        'author_id': comment.author_id,
        'visibility': comment.visibility
    }


def serialize_redaction(session, redaction):
    """
    Transaction returning a serialized descriptor of a redaction

    :param session: An ORM session
    :param redaction: A model to be serialized
    :return: A serialized description of the model specified
    """
    return {
        'id': redaction.id,
        'reference_id': redaction.reference_id,
        'entry': redaction.entry,
        'internaltip_id': redaction.internaltip_id,
        'update_date': redaction.update_date,
        'temporary_redaction': redaction.temporary_redaction,
        'permanent_redaction': redaction.permanent_redaction
    }


def serialize_ifile(session, ifile):
    """
    Transaction for serializing ifiles

    :param session: An ORM session
    :param ifile: The ifile to be serialized
    :return: The serialized ifile
    """
    error = not os.path.exists(os.path.join(State.settings.attachments_path, ifile.id))

    return {
        'id': ifile.id,
        'creation_date': ifile.creation_date,
        'name': ifile.name,
        'size': ifile.size,
        'type': ifile.content_type,
        'reference_id': ifile.reference_id,
        'status': "PENDING" if ifile.state is None or ifile.state == '' else ifile.state.upper(),
        'verification_date': ifile.verification_date,
        'error': error
    }


def serialize_wbfile(session, ifile, wbfile):
    """
    Transaction for serializing wbfile

    :param session: An ORM session
    :param ifile: The ifile to be serialized
    :param wbfile: The wbfile to be serialized
    :return: The serialized wbfile
    """
    error = not os.path.exists(os.path.join(State.settings.attachments_path, ifile.id)) and \
        not os.path.exists(os.path.join(State.settings.attachments_path, wbfile.id))

    return {
        'id': wbfile.id,
        'ifile_id': ifile.id,
        'creation_date': ifile.creation_date,
        'name': ifile.name,
        'size': ifile.size,
        'type': ifile.content_type,
        'reference_id': ifile.reference_id,
        'status': "PENDING" if ifile.state is None or ifile.state == '' else ifile.state.upper(),
        'verification_date': ifile.verification_date,
        'error': error
    }


def serialize_rfile(session, rfile):
    """
    Transaction for serializing rfile

    :param session: An ORM session
    :param rfile: The rfile to be serialized
    :return: The serialized rfile
    """
    error = not os.path.exists(os.path.join(State.settings.attachments_path, rfile.id))

    return {
        'id': rfile.id,
        'creation_date': rfile.creation_date,
        'name': rfile.name,
        'size': rfile.size,
        'type': rfile.content_type,
        'description': rfile.description,
        'visibility': rfile.visibility,
        'error': error,
        'status': "PENDING" if rfile.state is None or rfile.state == '' else rfile.state.upper(),
        'verification_date': rfile.verification_date
    }

def serialize_itip(session, internaltip, language):
    x = session.query(models.InternalTipAnswers, models.ArchivedSchema) \
               .filter(models.ArchivedSchema.hash == models.InternalTipAnswers.questionnaire_hash,
                       models.InternalTipAnswers.internaltip_id == internaltip.id) \
               .order_by(models.InternalTipAnswers.creation_date.asc())

    questionnaires = []
    for ita, aqs in x:
        questionnaires.append({
            'steps': serialize_archived_questionnaire_schema(aqs.schema, language),
            'answers': ita.answers
        })

    ret = {
        'id': internaltip.id,
        'creation_date': internaltip.creation_date,
        'update_date': internaltip.update_date,
        'expiration_date': internaltip.expiration_date,
        'context_id': internaltip.context_id,
        'questionnaires': questionnaires,
        'tor': internaltip.tor,
        'mobile': internaltip.mobile,
        'reminder_date': internaltip.reminder_date,
        'enable_whistleblower_identity': internaltip.enable_whistleblower_identity,
        'enable_whistleblower_download': not internaltip.deprecated_crypto_files_pub_key,
        'last_access': internaltip.last_access,
        'score': internaltip.score,
        'status': internaltip.status,
        'substatus': internaltip.substatus,
        'receivers': [],
        'comments': [],
        'wbfiles': [],
        'rfiles': [],
        'redactions': [],
        'data': {},
        "receipt_change_needed": internaltip.receipt_change_needed
    }

    for itd in session.query(models.InternalTipData).filter(models.InternalTipData.internaltip_id == internaltip.id):
        ret['data'][itd.key] = itd.value
        ret['data'][itd.key + "_date"] = itd.creation_date

    for redaction in session.query(models.Redaction) \
                            .filter(models.Redaction.internaltip_id == internaltip.id):
        ret['redactions'].append(serialize_redaction(session, redaction))

    return ret


def serialize_rtip(session, itip, rtip, language):
    """
    Transaction returning a serialized descriptor of a tip

    :param session: An ORM session
    :param rtip: A model to be serialized
    :param itip: A itip object referenced by the model to be serialized
    :param language: A language of the serialization
    :return: A serialized description of the model specified
    """
    user_id = rtip.receiver_id

    ret = serialize_itip(session, itip, language)

    ret['id'] = itip.id
    ret['progressive'] = itip.progressive
    ret['receiver_id'] = user_id
    ret['custodian'] = State.tenants[itip.tid].cache['custodian']
    ret['important'] = itip.important
    ret['label'] = itip.label
    ret['enable_notifications'] = rtip.enable_notifications

    iar = session.query(models.IdentityAccessRequest) \
                 .filter(models.IdentityAccessRequest.internaltip_id == itip.id) \
                 .order_by(models.IdentityAccessRequest.request_date.desc()).first()

    if iar:
        ret['iar'] = serialize_identityaccessrequest(session, iar)

    for receiver in session.query(models.User) \
                           .filter(models.User.id == models.ReceiverTip.receiver_id,
                                   models.ReceiverTip.internaltip_id == itip.id):
        ret['receivers'].append({
          'id': receiver.id,
          'name': receiver.name
        })

    denied_identity_files = ['1']
    if 'whistleblower_identity' in ret['data']:
        ret['data']['whistleblower_identity_provided'] = True

    if 'iar' not in ret or ret['iar']['reply'] in ('denied', 'pending'):
        if 'data' in ret and 'whistleblower_identity' in ret['data']:
            del ret['data']['whistleblower_identity']

        denied_identity_files = get_identity_files(ret.get('questionnaires', []))

    for ifile, wbfile in session.query(models.InternalFile, models.WhistleblowerFile) \
                               .filter(models.InternalFile.id == models.WhistleblowerFile.internalfile_id,
                                       not_(models.InternalFile.reference_id.in_(denied_identity_files)),
                                       models.WhistleblowerFile.receivertip_id == rtip.id):
        ret['wbfiles'].append(serialize_wbfile(session, ifile, wbfile))

    for rfile in session.query(models.ReceiverFile) \
                         .filter(models.ReceiverFile.internaltip_id == itip.id,
                                 or_(models.ReceiverFile.visibility not in (models.EnumVisibility.personal.value, models.EnumVisibility.whistleblower.value),
                                     models.ReceiverFile.author_id == user_id)):
        ret['rfiles'].append(serialize_rfile(session, rfile))

    for comment in session.query(models.Comment) \
                          .filter(models.Comment.internaltip_id == itip.id,
                                  or_(models.Comment.visibility not in (models.EnumVisibility.personal.value, models.EnumVisibility.whistleblower.value),
                                      models.Comment.author_id == user_id)):
        ret['comments'].append(serialize_comment(session, comment))

    forwardings = []
    internaltip_forwardings = db_query(session, models.InternalTipForwarding, models.InternalTipForwarding.internaltip_id == itip.id).all()
    for internaltip_forwarding in internaltip_forwardings:
        forwarding = dict()
        forwarding['id'] = internaltip_forwarding.oe_internaltip_id
        forwarding['tid'] = internaltip_forwarding.tid
        forwarding['name'] = db_get(session, models.Config, (models.Config.tid == internaltip_forwarding.tid, models.Config.var_name == 'name')).value
        forwarding['state'] = internaltip_forwarding.state
        forwarding['creation_date'] = internaltip_forwarding.creation_date
        contents = db_query(session, models.ContentForwarding, models.ContentForwarding.internaltip_forwarding_id == internaltip_forwarding.id).all()
        files = []
        comments = []
        for content in contents:
            if content.content_origin == models.EnumContentForwarding.comment.name:
                comment = dict()
                comment['id'] = content.content_id
                comment['author_type'] = content.author_type
                comments.append(comment)
            elif content.content_origin == models.EnumContentForwarding.internal_file.name:
                internal_file = dict()
                internal_file['id'] = content.content_id
                internal_file['author_type'] = content.author_type
                files.append(internal_file)
            elif content.content_origin == models.EnumContentForwarding.receiver_file.name:
                rfile = dict()
                rfile['id'] = content.content_id
                rfile['author_type'] = content.author_type
                files.append(rfile)
        forwarding['files'] = files
        forwarding['comments'] = comments

        aqs = session.query(models.ArchivedSchema) \
            .filter(models.ArchivedSchema.hash == internaltip_forwarding.questionnaire_hash) \
            .one_or_none()

        forwarding['questionnaire'] = {
                'steps': serialize_archived_questionnaire_schema(aqs.schema, language),
                'answers': internaltip_forwarding.data
            }

        forwardings.append(forwarding)
    ret['forwardings'] = forwardings

    return ret


def serialize_wbtip(session, itip, language):
    ret = serialize_itip(session, itip, language)

    for receiver in session.query(models.User) \
                           .filter(models.User.id == models.ReceiverTip.receiver_id,
                                   models.ReceiverTip.internaltip_id == itip.id):
        ret['receivers'].append({
          'id': receiver.id,
          'name': receiver.public_name
        })

    for ifile in session.query(models.InternalFile) \
                        .filter(models.InternalFile.internaltip_id == itip.id):
        ret['wbfiles'].append(serialize_ifile(session, ifile))

    for rfile in session.query(models.ReceiverFile) \
                         .filter(models.ReceiverFile.internaltip_id == itip.id,
                                 models.ReceiverFile.visibility == models.EnumVisibility.public.value):
        ret['rfiles'].append(serialize_rfile(session, rfile))

    for comment in session.query(models.Comment) \
                          .filter(models.Comment.internaltip_id == itip.id,
                                  models.Comment.visibility in (models.EnumVisibility.public.value, models.EnumVisibility.whistleblower.value)):
        ret['comments'].append(serialize_comment(session, comment))

    return ret


def serialize_redirect(redirect):
    """
    Transact for serializing a redirect

    :param redirect: The redirect to be serialized
    :return: The serialized redirect
    """
    return {
        'id': redirect.id,
        'path1': redirect.path1,
        'path2': redirect.path2
    }


def serialize_signup(signup):
    """
    Transaction serializing the signup descriptor

    :param signup: A signup model
    :return: A serialization of the provided model
    """
    return {
        'name': signup.name,
        'surname': signup.surname,
        'email': signup.email,
        'phone': signup.phone,
        'subdomain': signup.subdomain,
        'language': signup.language,
        'activation_token': signup.activation_token,
        'registration_date': signup.registration_date,
        'organization_name': signup.organization_name,
        'organization.tax_code': signup.organization_tax_code,
        'organization_vat_code': signup.organization_vat_code,
        'organization_location': signup.organization_location,
        'tos1': signup.tos1,
        'tos2': signup.tos2
    }


def serialize_tenant(session, tenant, config=None):
    ret = {
      'id': tenant.id,
      'creation_date': tenant.creation_date,
      'active': tenant.active
    }

    if config:
        ret.update(config)
    else:
        ret.update(ConfigFactory(session, tenant.id).serialize('tenant'))

    return ret


def serialize_auditlog_as_comment(log):
    """
    Serialize an audit log entry for external use.
    """
    return {
        'id': log.id,
        'creation_date': log.date,
        'content': '',
        'data': log.data,
        'author_id': log.user_id,
        'visibility': 'public',
        'type': 'auditlog_' + log.type
    }


def get_label(session, label_id, table):
    """
    Fetch the label for a given UUID from the specified table.
    """
    result = session.query(table).filter_by(id=label_id).first()
    return result.label['en'] if result else f"Unknown {table.__tablename__}"


def format_date(date):
    """
    Format the date to the desired string format.
    """
    return date.strftime("%B %d, %Y")


@transact
def process_logs(session, tip, tip_id):
    """
    Process a list of logs to append their details to a tip dictionary.
    """
    logs = session.query(models.AuditLog).filter(
        models.AuditLog.object_id == tip_id,
        models.AuditLog.type.in_(['update_report_status', 'update_report_expiration'])
    )

    for log in logs:
        tip['comments'].append(serialize_auditlog_as_comment(log))

    return tip
