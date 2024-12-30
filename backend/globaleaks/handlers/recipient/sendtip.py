# -*- coding: utf-8 -*-
#
# Handlers dealing with forwarding submission to an external organization
import base64
import logging
import json
from globaleaks.handlers.admin.node import db_admin_serialize_node
from globaleaks.handlers.admin.notification import db_get_notification
from globaleaks.models.config import ConfigFactory
from globaleaks.handlers.public import db_get_receivers, serialize_questionnaire
from globaleaks.handlers.admin.tenant import db_get_tenant_list
from globaleaks.utils.json import JSONEncoder
from globaleaks.handlers.base import BaseHandler
from globaleaks.handlers.admin.questionnaire import db_get_questionnaire
from globaleaks.handlers.whistleblower.submission import db_archive_questionnaire_schema, \
    db_assign_submission_progressive, db_create_receivertip, db_set_internaltip_answers, find_statistical_info
from globaleaks.utils.crypto import GCE
from globaleaks.utils.utility import datetime_now, get_expiration
from globaleaks import models
from globaleaks.orm import db_get, db_query, transact
from globaleaks.rest import requests, errors
from globaleaks.state import State

@transact
def check_forwarding_enabled(session):
    if not ConfigFactory(session, 1).get_val('forwarding_enabled'):
        raise errors.ForbiddenOperation()

def send_email_close_forwarding(session, original_tip_id, original_tip_progressive, eo_name):
    """
    Send forwarding closed emails to the all receivers.

    Args:
        session: The database session.
        original_tip_id: The forwarded tip's id.
        eo_name: The external organization's name.
    """
    language = ConfigFactory(session, 1).get_val('default_language')
    node = db_admin_serialize_node(session, 1, language)
    notification = db_get_notification(session, 1, language)
    receivers = db_get_receivers(session, 1, language)
    for receiver in receivers:
        user = db_get(session, models.User, models.User.id == receiver['id'])
        template_vars = {
            'type': 'close_forwarding_external_organization',
            'node': node,
            'notification': notification,
            'original_tip_id': original_tip_id,
            'original_tip_progressive': original_tip_progressive,
            'eo_name': eo_name,
            'recipient_name': user.public_name
        }

        State.format_and_send_mail(session, 1, user.mail_address, template_vars)


def add_internaltip_forwarding(session, tid, original_itip_id, forwarded_itip, data, questionnaire_id, questionnaire_hash):
    internaltip_forwarding = models.InternalTipForwarding()
    internaltip_forwarding.internaltip_id = original_itip_id
    internaltip_forwarding.forwarding_internaltip_id = forwarded_itip.id
    internaltip_forwarding.tid = tid
    internaltip_forwarding.creation_date = forwarded_itip.creation_date
    internaltip_forwarding.update_date = forwarded_itip.update_date
    internaltip_forwarding.data = data
    internaltip_forwarding.questionnaire_id = questionnaire_id
    internaltip_forwarding.state = models.EnumForwardingState.open.value
    internaltip_forwarding.stat_data = '{}'
    internaltip_forwarding.questionnaire_hash = questionnaire_hash
    session.add(internaltip_forwarding)

    return internaltip_forwarding


def add_file_forwarding(session, internaltip_forwarding_id, file, original_file_id):

    file_forwarding = models.ContentForwarding()
    file_forwarding.internaltip_forwarding_id = internaltip_forwarding_id
    file_forwarding.forwarding_content_id = file.id
    file_forwarding.content_id = original_file_id
    file_forwarding.author_type = models.EnumAuthorType.main.value
    if isinstance(file, models.ReceiverFile):
        file_forwarding.content_origin = models.EnumContentForwarding.receiver_file.value
    elif isinstance(file, models.InternalFile):
        file_forwarding.content_origin = models.EnumContentForwarding.internal_file.value
    else:
        raise errors.InputValidationError(
            "Unable to deliver the file's origin")

    session.add(file_forwarding)
    return file_forwarding


def validate_forwarding_questionnaire(session, questionnaire_id):
    valid_field_type = ['inputbox', 'textarea', 'selectbox', 'multichoice', 'checkbox', 'number', 'email', 'date', 'daterange']
    questionnaire = db_get(session, models.Questionnaire,
                           (models.Questionnaire.id == questionnaire_id))
    steps = db_get_questionnaire(
        session, 1, questionnaire.id, None, True)['steps']
    first_field = steps[0]['children'][0]
    if first_field['type'] != 'textarea' or not bool(first_field['editable']):
        return None
    for s in steps:
        for f in s['children']:
            if f['type'] not in valid_field_type:
                return None
    return steps


def set_answer(text, steps):
    first_field_id = steps[0]['children'][0]['id']
    answers = dict()
    empty_content = dict()
    required_status = False
    empty_content['required_status'] = required_status
    empty_content['value'] = ''
    empty_content['editable'] = True
    empty_content_list = [1]
    empty_content_list[0] = empty_content
    for s in steps:
        for f in s['children']:
            answers[f['id']] = empty_content_list

    content = dict()
    content_list = [1]
    content['required_status'] = required_status
    content['value'] = text
    content_list[0] = content
    answers[first_field_id] = content_list
    return answers


def check_default_context_receivers(default_context, receivers, request):
    if not receivers:
        raise errors.InputValidationError(
            "Unable to deliver the submission to at least one recipient")

    if 0 < default_context.maximum_selectable_receivers < len(request['receivers']):
        raise errors.InputValidationError(
            "The number of recipients selected exceed the configured limit")


def copy_internalfile(session, destination_itip, source_internalfile, source_prv_key, destination_id):
    name = GCE.asymmetric_decrypt(
        source_prv_key, base64.b64decode(source_internalfile.name))
    content_type = GCE.asymmetric_decrypt(
        source_prv_key, base64.b64decode(source_internalfile.content_type))
    size = GCE.asymmetric_decrypt(
        source_prv_key, base64.b64decode(source_internalfile.size))
    reference = source_internalfile.reference_id
    new_file = models.InternalFile()
    new_file.id = destination_id
    new_file.name = base64.b64encode(GCE.asymmetric_encrypt(
        destination_itip.crypto_tip_pub_key, name))
    new_file.content_type = base64.b64encode(GCE.asymmetric_encrypt(
        destination_itip.crypto_tip_pub_key, content_type))
    new_file.size = base64.b64encode(GCE.asymmetric_encrypt(
        destination_itip.crypto_tip_pub_key, size))
    new_file.tid = destination_itip.tid
    new_file.internaltip_id = destination_itip.id
    new_file.reference_id = reference
    new_file.creation_date = destination_itip.creation_date
    session.add(new_file)

    return new_file


def copy_receiverfile(session, destination_itip, source_rfile, source_prv_key, visibility, destination_id):
    name = GCE.asymmetric_decrypt(
        source_prv_key, base64.b64decode(source_rfile.name))
    content_type = GCE.asymmetric_decrypt(
        source_prv_key, base64.b64decode(source_rfile.content_type))
    size = GCE.asymmetric_decrypt(
        source_prv_key, base64.b64decode(source_rfile.size))
    description = GCE.asymmetric_decrypt(
        source_prv_key, base64.b64decode(source_rfile.description))
    author_id = source_rfile.author_id
    creation_date = source_rfile.creation_date
    new_file = models.ReceiverFile()
    new_file.id = destination_id
    new_file.name = base64.b64encode(GCE.asymmetric_encrypt(
        destination_itip.crypto_tip_pub_key, name))
    new_file.content_type = base64.b64encode(GCE.asymmetric_encrypt(
        destination_itip.crypto_tip_pub_key, content_type))
    new_file.size = base64.b64encode(GCE.asymmetric_encrypt(
        destination_itip.crypto_tip_pub_key, size))
    new_file.description = base64.b64encode(GCE.asymmetric_encrypt(
        destination_itip.crypto_tip_pub_key, description))
    new_file.author_id = author_id
    new_file.internaltip_id = destination_itip.id
    new_file.creation_date = creation_date
    new_file.visibility = visibility
    session.add(new_file)

    return new_file


class CloseForwardedSubmission(BaseHandler):
    """
    Handler responsible for closing a previously forwarded submission to an external organization
    """
    check_roles = 'receiver'

    @transact
    def close_forwarded_submission(self, session, request, itip_id, user_session):
        itip = db_get(session, models.InternalTip,
                      models.InternalTip.id == itip_id)
        itip_answers = db_get(session, models.InternalTipAnswers,
                              models.InternalTipAnswers.internaltip_id == itip.id)

        internaltip_forwarding = session.query(models.InternalTipForwarding)\
            .filter(models.InternalTipForwarding.tid == itip.tid, models.InternalTipForwarding.forwarding_internaltip_id == itip.id)\
            .one_or_none()

        if (internaltip_forwarding is None):
            raise errors.ResourceNotFound()
        elif (internaltip_forwarding.state == models.EnumForwardingState.closed.name):
            raise errors.InputValidationError(
                "Forwarded submission already closed")

        original_itip = db_get(session, models.InternalTip,
                               models.InternalTip.id == internaltip_forwarding.internaltip_id)
        answers = request['answers']
        try:
            default_language = db_get(
                session, models.Config.value,(
                models.Config.tid == original_itip.tid,
                models.Config.var_name == 'default_language')
            )
            analyst_encrypt = db_get(
                session,
                models.Config.value,(
                    models.Config.tid == original_itip.tid,
                    models.Config.var_name == 'global_stat_pub_key')
            )
            stat_answers = find_statistical_info(
                session,
                original_itip.tid,
                answers,
                default_language
            )
            if stat_answers != {}:
                    stat_answers = base64.b64encode(
                        GCE.asymmetric_encrypt(
                            analyst_encrypt[0],
                            json.dumps(stat_answers, cls=JSONEncoder).encode()
                        )
                    ).decode()
        except Exception as e:
            logging.debug(e)
            stat_answers = '{}'

        crypto_answers = base64.b64encode(GCE.asymmetric_encrypt(
            itip.crypto_tip_pub_key, json.dumps(answers, cls=json.JSONEncoder).encode())).decode()
        crypto_forwarded_answers = base64.b64encode(GCE.asymmetric_encrypt(
            original_itip.crypto_tip_pub_key, json.dumps(answers, cls=json.JSONEncoder).encode())).decode()

        now = datetime_now()

        itip_answers.answers = crypto_answers

        itip.update_date = now
        itip.status = 'closed'

        internaltip_forwarding.state = models.EnumForwardingState.closed.value
        internaltip_forwarding.data = crypto_forwarded_answers
        internaltip_forwarding.update_date = now
        internaltip_forwarding.stat_data = stat_answers

        eo_name = ConfigFactory(session, internaltip_forwarding.tid).get_val('name')
        send_email_close_forwarding(session, original_itip.id, original_itip.progressive, eo_name)

        session.flush()
        return internaltip_forwarding.id

    def post(self, itip_id):
        check_forwarding_enabled()
        request = self.validate_request(
            self.request.content.read(), requests.CloseForwardedSubmissionDesc)
        return self.close_forwarded_submission(request, itip_id, self.session)


class ForwardSubmission(BaseHandler):
    """
    Handler responsible for forwarding a submission to an external organization
    """
    check_roles = 'receiver'

    def forward_file(self, session, destination_itip, file, source_prv_key):
        if file['origin'] == 'whistleblower':
            source_internalfile = db_get(
                session, models.InternalFile, models.InternalFile.id == file['id'])
            if source_internalfile is not None:
                destination_id = self.fs_copy_file(
                    source_internalfile.id, source_prv_key)
                new_file = copy_internalfile(
                    session, destination_itip, source_internalfile, source_prv_key, destination_id)
        elif file['origin'] in ('recipient', 'eo'):
            source_rfile = db_get(
                session, models.ReceiverFile, models.ReceiverFile.id == file['id'])
            if source_rfile is not None:
                destination_id = self.fs_copy_file(
                    source_rfile.id, source_prv_key)
                new_file = copy_receiverfile(
                    session, destination_itip, source_rfile, source_prv_key, models.EnumVisibility.eo.name, destination_id)
        elif file['origin'] == 'new':
            new_file = db_get(session, models.ReceiverFile,
                              models.ReceiverFile.id == file['id'])
        else:
            raise errors.InputValidationError(
                "Unable to deliver the file's origin")
        return new_file

    @transact
    def forward_submission(self, session, request, itip_id, user_session):
        itip = db_get(session, models.InternalTip,
                      models.InternalTip.id == itip_id)
        user = db_get(session, models.User,
                      models.User.id == user_session.user_id)
        rtip = db_get(session, models.ReceiverTip, (models.ReceiverTip.receiver_id == user.id,
                                                    models.ReceiverTip.internaltip_id == itip.id))

        if rtip is None or user.tid != 1:
            raise errors.ForbiddenOperation()

        original_itip_private_key = GCE.asymmetric_decrypt(
            self.session.cc, base64.b64decode(rtip.crypto_tip_prv_key))

        steps = validate_forwarding_questionnaire(
            session, request['questionnaire_id'])
        if steps is None:
            raise errors.InputValidationError(
                "Unable to forward the submission with this questionnaire")

        for tid in request['tids']:
            previous_forwarding = session.query(models.InternalTipForwarding)\
                .filter(models.InternalTipForwarding.tid == tid, models.InternalTipForwarding.internaltip_id == itip.id)\
                .one_or_none()
            if (previous_forwarding is not None):
                raise errors.InputValidationError(
                    "Forwarding already present for one or more selected tenants")

            answers = set_answer(request['text'], steps)
            questionnaire_hash = db_archive_questionnaire_schema(
                session, steps)
            default_context = db_get(
                session, models.Context, (models.Context.tid == tid, models.Context.order == 0))
            receivers = db_query(session, models.User,
                                 (models.ReceiverContext.context_id == default_context.id,
                                  models.User.id == models.ReceiverContext.receiver_id)).all()

            check_default_context_receivers(
                default_context, receivers, request)

            forwarded_itip = models.InternalTip()
            forwarded_itip.tid = tid
            forwarded_itip.status = 'new'
            forwarded_itip.update_date = forwarded_itip.creation_date
            forwarded_itip.progressive = db_assign_submission_progressive(
                session, tid)

            if default_context.tip_timetolive > 0:
                forwarded_itip.expiration_date = get_expiration(
                    default_context.tip_timetolive)

            if default_context.tip_reminder > 0:
                forwarded_itip.reminder_date = get_expiration(
                    default_context.tip_reminder)

            forwarded_itip.context_id = default_context.id
            forwarded_itip.receipt_hash = GCE.generate_receipt()

            session.add(forwarded_itip)
            session.flush()

            crypto_tip_prv_key, forwarded_itip.crypto_tip_pub_key = GCE.generate_keypair()

            crypto_answers = base64.b64encode(GCE.asymmetric_encrypt(
                forwarded_itip.crypto_tip_pub_key, json.dumps(answers, cls=json.JSONEncoder).encode())).decode()
            crypto_forwarded_answers = base64.b64encode(GCE.asymmetric_encrypt(
                itip.crypto_tip_pub_key, json.dumps(answers, cls=json.JSONEncoder).encode())).decode()
            db_set_internaltip_answers(
                session, forwarded_itip.id, questionnaire_hash, crypto_answers, forwarded_itip.creation_date)

            for user in receivers:
                _tip_key = GCE.asymmetric_encrypt(
                    user.crypto_pub_key, crypto_tip_prv_key)
                db_create_receivertip(session, user, forwarded_itip, _tip_key)

            internaltip_forwarding = add_internaltip_forwarding(
                session, tid, itip_id, forwarded_itip, crypto_forwarded_answers, request['questionnaire_id'], questionnaire_hash)
            for file in request['files']:
                copied_file = self.forward_file(
                    session, forwarded_itip, file, original_itip_private_key)
                add_file_forwarding(
                    session, internaltip_forwarding.id, copied_file, file['id'])

        return internaltip_forwarding.id

    def post(self, itip_id):
        check_forwarding_enabled()
        request = self.validate_request(
            self.request.content.read(), requests.ForwardSubmissionDesc)
        return self.forward_submission(request, itip_id, self.session)


class ForwardingsTenantCollection(BaseHandler):
    """
    Handler responsible for collect external tenants to forward tips
    """
    check_roles = 'receiver'
    invalidate_cache = True

    @transact
    def get_external_tenants(self, session):
        return db_get_tenant_list(session, True)

    def get(self):
        check_forwarding_enabled()
        return self.get_external_tenants()


class ForwardingsQuestionnaireCollection(BaseHandler):
    """
    Handler responsible for collect valid questionaire to be used in send tip process
    """
    check_roles = 'receiver'
    invalidate_cache = True

    @transact
    def get_questionnaires(self, session, tid, language):
        valid_questionnaires = []
        questionnaires = session.query(models.Questionnaire) \
            .filter(models.Questionnaire.tid == 1).all()

        for q in questionnaires:
            steps = validate_forwarding_questionnaire(session, q.id)
            if steps is not None:
                valid_questionnaires.append(q)
        return [serialize_questionnaire(session, tid, questionnaire, language) for questionnaire in valid_questionnaires]

    def get(self):
        check_forwarding_enabled()
        return self.get_questionnaires(self.request.tid, self.request.language)
