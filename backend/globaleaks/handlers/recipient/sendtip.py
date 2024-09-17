# -*- coding: utf-8 -*-
#
# Handlers dealing with forwarding submission to an external organization
import base64
from code import interact
import os
import json
from globaleaks.settings import Settings
from globaleaks.utils.securetempfile import SecureTemporaryFile
from globaleaks.models import serializers
from globaleaks.handlers.base import BaseHandler
from globaleaks.handlers.admin.questionnaire import db_get_questionnaire
from globaleaks.handlers.whistleblower.submission import db_archive_questionnaire_schema, db_assign_submission_progressive, db_create_receivertip, db_set_internaltip_answers
from globaleaks.utils.log import log
from globaleaks.utils.crypto import GCE
from globaleaks.utils.utility import datetime_now, get_expiration
from globaleaks import models
from globaleaks.orm import db_get, db_query, transact
from globaleaks.rest import requests, errors

class CloseForwardedSubmission(BaseHandler):
    """
    Handler responsible for closing a previously forwarded submission to an external organization
    """
    check_roles = 'receiver'

    @transact
    def close_forwarded_submission(self, session, request, itip_id, user_session):
        itip = db_get(session, models.InternalTip, models.InternalTip.id == itip_id)
        itip_answers = db_get(session, models.InternalTipAnswers, models.InternalTipAnswers.internaltip_id == itip.id)

        internaltip_forwarding = session.query(models.InternalTipForwarding)\
                .filter(models.InternalTipForwarding.tid == itip.tid, models.InternalTipForwarding.oe_internaltip_id == itip.id)\
                    .one_or_none()

        if(internaltip_forwarding is None):
                raise errors.ResourceNotFound()
        elif(internaltip_forwarding.state == models.EnumForwardingState.closed.name):
             raise errors.InputValidationError("Forwarded submission already closed")

        original_itip = db_get(session, models.InternalTip, models.InternalTip.id == internaltip_forwarding.internaltip_id)
        answers = request['answers']
        
        crypto_answers = base64.b64encode(GCE.asymmetric_encrypt(itip.crypto_tip_pub_key, json.dumps(answers, cls=json.JSONEncoder).encode())).decode()
        crypto_forwarded_answers = base64.b64encode(GCE.asymmetric_encrypt(original_itip.crypto_tip_pub_key, json.dumps(answers, cls=json.JSONEncoder).encode())).decode()
        
        now = datetime_now()
        
        itip_answers.answers = crypto_answers

        itip.update_date = now

        # TODO inserire i campi di interesse statistico in apposita colonna
        internaltip_forwarding.state = models.EnumForwardingState.closed.value
        internaltip_forwarding.data = crypto_forwarded_answers
        internaltip_forwarding.update_date = now

        session.flush()
        
        return internaltip_forwarding.id
    
    def post(self, itip_id):
        request = self.validate_request(self.request.content.read(), requests.CloseForwardedSubmissionDesc)
        return self.close_forwarded_submission(request, itip_id, self.session)

class ForwardSubmission(BaseHandler):
    """
    Handler responsible for forwarding a submission to an external organization
    """
    check_roles = 'receiver'
    
    def fs_copy_file(self, source_id, source_prv_key):
        source_file = os.path.join(self.state.settings.attachments_path, source_id)
        self.check_file_presence(source_file)
        temp_file = SecureTemporaryFile(Settings.tmp_path)
        
        self.state.TempUploadFiles[temp_file.key_id] = temp_file
        with temp_file.open('w') as output_fd,\
             GCE.streaming_encryption_open('DECRYPT', source_prv_key, source_file) as seo:
            while True:
                last, data = seo.decrypt_chunk()
                output_fd.write(data)
                if last:
                    break
    
        return temp_file.key_id
    
    def copy_internalfile(self, session, tid, forwarded_itip, source_id, source_prv_key):
        internalfile = db_get(session, models.InternalFile, models.InternalFile.id == source_id)
        name = GCE.asymmetric_decrypt(source_prv_key, base64.b64decode(internalfile.name))
        content_type = GCE.asymmetric_decrypt(source_prv_key, base64.b64decode(internalfile.content_type))
        size = GCE.asymmetric_decrypt(source_prv_key, base64.b64decode(internalfile.size))
        reference = internalfile.reference_id
        new_file_id = self.fs_copy_file(internalfile.id, source_prv_key)
        new_file = models.InternalFile()
        new_file.id = new_file_id
        new_file.name = base64.b64encode(GCE.asymmetric_encrypt(forwarded_itip.crypto_tip_pub_key, name))
        new_file.content_type = base64.b64encode(GCE.asymmetric_encrypt(forwarded_itip.crypto_tip_pub_key, content_type))
        new_file.size = base64.b64encode(GCE.asymmetric_encrypt(forwarded_itip.crypto_tip_pub_key, size))
        new_file.tid = forwarded_itip.tid
        new_file.internaltip_id = forwarded_itip.id
        new_file.reference_id = reference
        new_file.creation_date = forwarded_itip.creation_date
        session.add(new_file)
        
        return new_file
    
    def copy_receiverfile(self, session, tid, forwarded_itip, source_id, source_prv_key, visibility):
        receiverfile = db_get(session, models.ReceiverFile, models.ReceiverFile.id == source_id)
        name = GCE.asymmetric_decrypt(source_prv_key, base64.b64decode(receiverfile.name))
        content_type = GCE.asymmetric_decrypt(source_prv_key, base64.b64decode(receiverfile.content_type))
        size = GCE.asymmetric_decrypt(source_prv_key, base64.b64decode(receiverfile.size))
        description = GCE.asymmetric_decrypt(source_prv_key, base64.b64decode(receiverfile.description))
        author_id = receiverfile.author_id
        creation_date = receiverfile.creation_date
        new_file_id = self.fs_copy_file(receiverfile.id, source_prv_key)
        new_file = models.ReceiverFile()
        new_file.id = new_file_id
        new_file.name = base64.b64encode(GCE.asymmetric_encrypt(forwarded_itip.crypto_tip_pub_key, name))
        new_file.content_type = base64.b64encode(GCE.asymmetric_encrypt(forwarded_itip.crypto_tip_pub_key, content_type))
        new_file.size = base64.b64encode(GCE.asymmetric_encrypt(forwarded_itip.crypto_tip_pub_key, size))
        new_file.description = base64.b64encode(GCE.asymmetric_encrypt(forwarded_itip.crypto_tip_pub_key, description))
        new_file.author_id = author_id
        new_file.internaltip_id = forwarded_itip.id
        new_file.creation_date = creation_date
        new_file.visibility = visibility
        session.add(new_file)
        
        return new_file
    
    def add_file_forwarding(self, session, internaltip_forwarding_id, file, original_file_id):

        file_forwarding = models.ContentForwarding()
        file_forwarding.internaltip_forwarding_id = internaltip_forwarding_id
        file_forwarding.oe_content_id = file.id
        file_forwarding.content_id = original_file_id
        file_forwarding.author_type = models.EnumAuthorType.main
        if isinstance(file, models.ReceiverFile):  
            file_forwarding.content_origin = models.EnumContentForwarding.receiver_file.value
        elif isinstance(file, models.InternalFile):
            file_forwarding.content_origin = models.EnumContentForwarding.internal_file.value
        else:
            raise errors.InputValidationError("Unable to deliver the file's origin")
        
        session.add(file_forwarding)
        return file_forwarding
    
    def add_internaltip_forwarding(self, session, tid, original_itip_id, forwarded_itip, data, questionnaire_id):
        internaltip_forwarding = models.InternalTipForwarding()
        internaltip_forwarding.internaltip_id = original_itip_id
        internaltip_forwarding.oe_internaltip_id = forwarded_itip.id
        internaltip_forwarding.tid = tid
        internaltip_forwarding.creation_date = forwarded_itip.creation_date
        internaltip_forwarding.update_date = forwarded_itip.update_date
        internaltip_forwarding.data = data
        internaltip_forwarding.questionnaire_id = questionnaire_id
        internaltip_forwarding.state = models.EnumForwardingState.open.value
        session.add(internaltip_forwarding)
        
        return internaltip_forwarding
        
    def copy_file(self, session, tid, forwarded_itip, file, source_prv_key):
        if file['origin'] == 'whistleblower':
            new_file = self.copy_internalfile(session, tid, forwarded_itip, file['id'], source_prv_key)
        elif file['origin'] == 'recipient':
            new_file = self.copy_receiverfile(session, tid, forwarded_itip, file['id'], source_prv_key, models.EnumVisibility.public.name)
        elif file['origin'] == 'oe':
            new_file = self.copy_receiverfile(session, tid, forwarded_itip, file['id'], source_prv_key, models.EnumVisibility.public.name)
        elif file['origin'] == 'new':
            new_file = db_get(session, models.ReceiverFile, models.ReceiverFile.id == file['id'])
        else:
            raise errors.InputValidationError("Unable to deliver the file's origin")
        return new_file
    
    def validate_steps(self, session, tid, questionnaire_id):
        questionnaire = db_get(session, models.Questionnaire,(models.Questionnaire.id == questionnaire_id))
        steps = db_get_questionnaire(session, tid, questionnaire.id, None, True)['steps']
        first_field = steps[0]['children'][0]
        if first_field['type'] != 'textarea' or bool(first_field['editable']):
            raise errors.InputValidationError("Unable to forward the submission with this questionnaire")
        return steps
    
    def set_answer(self, text, steps):
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
    
    
    @transact
    def forward_submission(self, session, request, itip_id, user_session):
        
        itip = db_get(session, models.InternalTip, models.InternalTip.id == itip_id)
        user = db_get(session, models.User, models.User.id == user_session.user_id)
        rtip = db_get(session, models.ReceiverTip, (models.ReceiverTip.receiver_id == user.id, 
                                                        models.ReceiverTip.internaltip_id == itip.id))
        
        if rtip is None or user.tid != 1:
            raise errors.ForbiddenOperation()

        original_itip_private_key = GCE.asymmetric_decrypt(self.session.cc, base64.b64decode(rtip.crypto_tip_prv_key))
        
        for tid in request['tids']:
            previous_forwarding = session.query(models.InternalTipForwarding)\
                .filter(models.InternalTipForwarding.tid == tid, models.InternalTipForwarding.internaltip_id == itip.id)\
                    .one_or_none()
            if(previous_forwarding is not None):
                raise errors.InputValidationError("Forwarding already present for one or more selected tenants")

            steps = self.validate_steps(session, tid, request['questionnaire_id'])
            answers = self.set_answer(request['text'], steps)
            questionnaire_hash = db_archive_questionnaire_schema(session, steps)
            default_context = db_get(session, models.Context, (models.Context.tid == tid, models.Context.order == 0))
            receivers = db_query(session, models.User, 
                            (models.ReceiverContext.context_id == default_context.id, 
                            models.User.id == models.ReceiverContext.receiver_id)).all()
            
            if not receivers:
                raise errors.InputValidationError("Unable to deliver the submission to at least one recipient")

            if 0 < default_context.maximum_selectable_receivers < len(request['receivers']):
                raise errors.InputValidationError("The number of recipients selected exceed the configured limit")

            forwarded_itip = models.InternalTip()
            forwarded_itip.tid = tid
            forwarded_itip.status = 'new'
            forwarded_itip.update_date = forwarded_itip.creation_date
            forwarded_itip.progressive = db_assign_submission_progressive(session, tid)

            if default_context.tip_timetolive > 0:
                forwarded_itip.expiration_date = get_expiration(default_context.tip_timetolive)

            if default_context.tip_reminder > 0:
                forwarded_itip.reminder_date = get_expiration(default_context.tip_reminder)

            forwarded_itip.context_id = default_context.id
            forwarded_itip.receipt_hash =  GCE.generate_receipt()

            session.add(forwarded_itip)
            session.flush()

            crypto_tip_prv_key, forwarded_itip.crypto_tip_pub_key = GCE.generate_keypair()
            
            crypto_answers = base64.b64encode(GCE.asymmetric_encrypt(forwarded_itip.crypto_tip_pub_key, json.dumps(answers, cls=json.JSONEncoder).encode())).decode()
            crypto_forwarded_answers = base64.b64encode(GCE.asymmetric_encrypt(itip.crypto_tip_pub_key, json.dumps(answers, cls=json.JSONEncoder).encode())).decode()
            db_set_internaltip_answers(session, forwarded_itip.id, questionnaire_hash, crypto_answers, forwarded_itip.creation_date)
            # TODO inserire i campi di interesse statistico in apposita colonna

            for user in receivers:
                _tip_key = GCE.asymmetric_encrypt(user.crypto_pub_key, crypto_tip_prv_key)
                db_create_receivertip(session, user, forwarded_itip, _tip_key)
                
            internaltip_forwarding = self.add_internaltip_forwarding(session, tid, itip_id, forwarded_itip, crypto_forwarded_answers, request['questionnaire_id'])
            for file in request['files']:
                copied_file = self.copy_file(session, tid, forwarded_itip, file, original_itip_private_key)
                self.add_file_forwarding(session, internaltip_forwarding.id, copied_file, file['id'])

        return internaltip_forwarding.id
    
    def post(self, itip_id):
        
        request = self.validate_request(self.request.content.read(), requests.ForwardSubmissionDesc)
        return self.forward_submission(request, itip_id, self.session)
