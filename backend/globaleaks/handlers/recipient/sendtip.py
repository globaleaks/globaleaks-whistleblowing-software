# -*- coding: utf-8 -*-
#
# Handlers dealing with forwarding submission to an external organization
import base64
import os
import json
from globaleaks.settings import Settings
from globaleaks.utils.securetempfile import SecureTemporaryFile
from globaleaks.state import State
from globaleaks.models import InternalFile, serializers
from globaleaks.handlers.base import BaseHandler
from globaleaks.handlers.admin.questionnaire import db_get_questionnaire
from globaleaks.handlers.whistleblower.submission import db_archive_questionnaire_schema, db_assign_submission_progressive, db_create_receivertip, db_set_internaltip_answers
from globaleaks.utils.json import JSONEncoder
from globaleaks.utils.log import log
from globaleaks.utils.crypto import GCE
from globaleaks.utils.utility import datetime_null, get_expiration
from globaleaks import models
from globaleaks.orm import db_get, db_query, transact
from globaleaks.rest import requests, errors

def db_set_forwarded_internaltip_answers(session, itip_id, questionnaire_hash, answers, date=None):
    x = session.query(models.InternalTipAnswers) \
               .filter(models.InternalTipAnswers.internaltip_id == itip_id,
                       models.InternalTipAnswers.questionnaire_hash == questionnaire_hash).one_or_none()

    ita = models.InternalTipAnswers()
    ita.internaltip_id = itip_id
    ita.questionnaire_hash = questionnaire_hash
    ita.answers = answers

    if date:
        ita.creation_date = date

    session.add(ita)

    return ita

class ForwardSubmission(BaseHandler):
    """
    Handler responsible for forwarding a submission to an external organization
    """
    check_roles = 'any'
    
    def copy_file(self, source_id, source_prv_key):
        source_file = os.path.join(self.state.settings.attachments_path, source_id)
        self.check_file_presence(source_file)
        temp_file = SecureTemporaryFile(Settings.tmp_path)
        filepath = os.path.join(Settings.tmp_path, temp_file.key_id)
        
        self.state.TempUploadFiles[temp_file.key_id] = temp_file
        with temp_file.open('w') as output_fd,\
             GCE.streaming_encryption_open('DECRYPT', source_prv_key, source_file) as seo:
            while True:
                last, data = seo.decrypt_chunk()
                log.info("POST FORWARD DATA %s" % data)
                output_fd.write(data)
                if last:
                    break
    
        return temp_file.key_id
    
    def forward_internalfile(self, session, forwarded_itip, source_id, source_prv_key, crypto_is_available):
        internalfile = db_get(session, models.InternalFile, models.InternalFile.id == source_id)
        name = GCE.asymmetric_decrypt(source_prv_key, base64.b64decode(internalfile.name))
        content_type = GCE.asymmetric_decrypt(source_prv_key, base64.b64decode(internalfile.content_type))
        size = GCE.asymmetric_decrypt(source_prv_key, base64.b64decode(internalfile.size))
        reference = internalfile.reference_id
        new_file_id = self.copy_file(internalfile.id, source_prv_key)
        
        new_file = models.InternalFile()
        new_file.id = new_file_id
        if crypto_is_available:
            new_file.name = base64.b64encode(GCE.asymmetric_encrypt(forwarded_itip.crypto_tip_pub_key, name))
            new_file.content_type = base64.b64encode(GCE.asymmetric_encrypt(forwarded_itip.crypto_tip_pub_key, content_type))
            new_file.size = base64.b64encode(GCE.asymmetric_encrypt(forwarded_itip.crypto_tip_pub_key, size))
        else:
            new_file.name = name
            new_file.content_type = content_type
            new_file.size = size

        new_file.tid = forwarded_itip.tid
        new_file.internaltip_id = forwarded_itip.id
        new_file.reference_id = reference
        new_file.creation_date = forwarded_itip.creation_date
        session.add(new_file)
        
        # TODO add row in file_forwarding
        return new_file
    
    def forward_receiverfile(self, session, forwarded_itip, source_id, source_prv_key, crypto_is_available, visibility):
        receiverfile = db_get(session, models.ReceiverFile, models.ReceiverFile.id == source_id)
        name = GCE.asymmetric_decrypt(source_prv_key, base64.b64decode(receiverfile.name))
        content_type = GCE.asymmetric_decrypt(source_prv_key, base64.b64decode(receiverfile.content_type))
        size = GCE.asymmetric_decrypt(source_prv_key, base64.b64decode(receiverfile.size))
        description = GCE.asymmetric_decrypt(source_prv_key, base64.b64decode(receiverfile.description))
        author_id = receiverfile.author_id
        creation_date = receiverfile.creation_date
        new_file_id = self.copy_file(receiverfile.id, source_prv_key)
        
        new_file = models.ReceiverFile()
        new_file.id = new_file_id
        if crypto_is_available:
            new_file.name = base64.b64encode(GCE.asymmetric_encrypt(forwarded_itip.crypto_tip_pub_key, name))
            new_file.content_type = base64.b64encode(GCE.asymmetric_encrypt(forwarded_itip.crypto_tip_pub_key, content_type))
            new_file.size = base64.b64encode(GCE.asymmetric_encrypt(forwarded_itip.crypto_tip_pub_key, size))
            new_file.description = base64.b64encode(GCE.asymmetric_encrypt(forwarded_itip.crypto_tip_pub_key, description))
        else:
            new_file.name = name
            new_file.content_type = content_type
            new_file.size = size
            new_file.description = description

        new_file.author_id = author_id
        new_file.internaltip_id = forwarded_itip.id
        new_file.creation_date = creation_date
        new_file.visibility = visibility
        session.add(new_file)
        
        # TODO add row in file_forwarding
        return new_file
    
    def forward_files(self, session, forwarded_itip, files, source_prv_key, crypto_is_available):
        for f in files:
            if f['origin'] == 'whistleblower':
                new_file = self.forward_internalfile(session, forwarded_itip, f['id'], source_prv_key, crypto_is_available)
            elif f['origin'] == 'recipient':
                new_file = self.forward_receiverfile(session, forwarded_itip, f['id'], source_prv_key, crypto_is_available, models.EnumVisibility.public.name)
            elif f['origin'] == 'oe':
                new_file = self.forward_receiverfile(session, forwarded_itip, f['id'], source_prv_key, crypto_is_available, models.EnumVisibility.public.name)
            elif f['origin'] == 'new':
                break;
            else:
                raise errors.InputValidationError("Unable to deliver the file's origin")
        return id
    
    @transact
    def forward_submission(self, session, request, itip_id, user_session):
        
        itip = db_get(session, models.InternalTip, models.InternalTip.id == itip_id)
        user = db_get(session, models.User, models.User.id == user_session.user_id)
        rtip = db_get(session, models.ReceiverTip, (models.ReceiverTip.receiver_id == user.id, 
                                                        models.ReceiverTip.internaltip_id == itip.id))
        original_itip_private_key = GCE.asymmetric_decrypt(self.session.cc, base64.b64decode(rtip.crypto_tip_prv_key))
        
        for tid in request['tid']:
            encryption = db_get(session, models.Config, (models.Config.tid == tid, models.Config.var_name == 'encryption'))
            crypto_is_available = encryption.value
            
            default_context = db_get(session, models.Context, (models.Context.tid == tid, models.Context.order == 0))
            questionnaire = db_get(session, models.Questionnaire,(models.Questionnaire.id == request['questionnaire_id']))

            # # TODO Verificare che il questionario abbia le caratteristiche di inoltro (prima domanda testo libero, ultima domanda esito)
            # # TODO Inserire il testo libero all'interno del json delle answers
            answers = request['text']
            steps = db_get_questionnaire(session, tid, questionnaire.id, None, True)['steps']
            fields = db_query(session, models.Field)
            # log.info("STEPS %s" % steps)
            questionnaire_hash = db_archive_questionnaire_schema(session, steps)

            receivers = []
            context_users = db_query(session, models.User, 
                            (models.ReceiverContext.context_id == default_context.id, 
                            models.User.id == models.ReceiverContext.receiver_id)).all()
            for r in context_users:
                if crypto_is_available:
                    if r.crypto_pub_key:
                        # This is the regular condition of systems setup on Globaleaks 4
                        # Since this version, encryption is enabled by default and
                        # users need to perform their first access before they
                        # could receive reports.
                        receivers.append(r)
                    elif encryption.update_date != datetime_null():
                        # This is the exceptional condition of systems setup when
                        # encryption was implemented via PGP.
                        # For continuity reason of those production systems
                        # encryption could not be enforced.
                        receivers.append(r)
                        crypto_is_available = False
                else:
                    receivers.append(r)

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

            if crypto_is_available:
                crypto_tip_prv_key, forwarded_itip.crypto_tip_pub_key = GCE.generate_keypair()
                log.info("original key %s" % crypto_tip_prv_key)

            if crypto_is_available:
                crypto_answers = base64.b64encode(GCE.asymmetric_encrypt(forwarded_itip.crypto_tip_pub_key, json.dumps(answers, cls=json.JSONEncoder).encode())).decode()

            db_set_internaltip_answers(session, forwarded_itip.id, questionnaire_hash, crypto_answers, forwarded_itip.creation_date)

            self.forward_files(session, forwarded_itip, request['files'], original_itip_private_key, crypto_is_available)

            for user in receivers:
                if crypto_is_available:
                    _tip_key = GCE.asymmetric_encrypt(user.crypto_pub_key, crypto_tip_prv_key)
                else:
                    _tip_key = b''
                db_create_receivertip(session, user, forwarded_itip, _tip_key)
                
            # # TODO ADD ROW IN INTERNALTIP_FORWARDING

        return serializers.serialize_itip(session, forwarded_itip, user.language)
    
    def post(self, itip_id):
        
        request = self.validate_request(self.request.content.read(), requests.ForwardSubmissionDesc)
        return self.forward_submission(request, itip_id, self.session)
