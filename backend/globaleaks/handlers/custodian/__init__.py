# -*- coding: utf-8 -*-
#
# Handlers dealing with custodian user functionalities
import base64

from globaleaks import models
from globaleaks.handlers.admin.context import admin_serialize_context
from globaleaks.handlers.admin.node import db_admin_serialize_node
from globaleaks.handlers.admin.notification import db_get_notification
from globaleaks.handlers.base import BaseHandler
from globaleaks.handlers.user import user_serialize_user
from globaleaks.models import serializers
from globaleaks.orm import transact
from globaleaks.rest import requests
from globaleaks.utils.crypto import GCE
from globaleaks.utils.templating import Templating
from globaleaks.utils.utility import datetime_now


@transact
def get_identityaccessrequest_list(session, tid, user_id, user_key):
    ret = []

    for iarc, iar in session.query(models.IdentityAccessRequestCustodian, models.IdentityAccessRequest) \
                            .filter(models.IdentityAccessRequestCustodian.identityaccessrequest_id == models.IdentityAccessRequest.id,
                                    models.IdentityAccessRequestCustodian.custodian_id == user_id,
                                    models.IdentityAccessRequest.internaltip_id == models.InternalTip.id,
                                    models.InternalTip.tid == tid) \
                            .order_by(models.IdentityAccessRequest.request_date.desc()):
        elem = serializers.serialize_identityaccessrequest(session, iar)

        if iarc.crypto_tip_prv_key:
            crypto_tip_prv_key = GCE.asymmetric_decrypt(user_key, base64.b64decode(iarc.crypto_tip_prv_key))

            if elem['request_motivation']:
                elem['request_motivation'] = GCE.asymmetric_decrypt(crypto_tip_prv_key, base64.b64decode(elem['request_motivation'])).decode()

            if elem['reply_motivation']:
                elem['reply_motivation'] = GCE.asymmetric_decrypt(crypto_tip_prv_key, base64.b64decode(elem['reply_motivation'])).decode()

        ret.append(elem)

    return ret


def db_create_identity_access_reply_notifications(session, itip, iar):
    """
    Transaction for the creation of notifications related to identity access replies
    :param session: An ORM session
    :param itip: A itip ID of the tip involved in the request
    :param rtip: A rtip ID of the rtip involved in the request
    :param iar: A identity access request model
    """
    query = (session.query(models.User, models.ReceiverTip, models.UserProfile.language)
        .join(models.UserProfile, models.User.profile_id == models.UserProfile.id)
        .filter(
            models.User.id == models.ReceiverTip.receiver_id,
            models.ReceiverTip.internaltip_id == itip.id,
            models.UserProfile.notification.is_(True)
        ))
    for user, rtip, language in query:
        context = session.query(models.Context).filter(models.Context.id == itip.context_id).one()

        data = {
            'type': 'identity_access_authorized' if iar.reply == 'authorized' else 'identity_access_denied'
        }

        data['user'] = user_serialize_user(session, user, language)
        data['tip'] = serializers.serialize_rtip(session, itip, rtip, language)
        data['context'] = admin_serialize_context(session, context, language)
        data['iar'] = serializers.serialize_identityaccessrequest(session, iar)
        data['node'] = db_admin_serialize_node(session, user.tid, language)

        if data['node']['mode'] == 'default':
            data['notification'] = db_get_notification(session, user.tid, language)
        else:
            data['notification'] = db_get_notification(session, 1, language)

        subject, body = Templating().get_mail_subject_and_body(data)

        session.add(models.Mail({
            'address': data['user']['mail_address'],
            'subject': subject,
            'body': body,
            'tid': user.tid
        }))


@transact
def update_identityaccessrequest(session, tid, user_id, identityaccessrequest_id, request):
    iar, iarc, itip = session.query(models.IdentityAccessRequest, models.IdentityAccessRequestCustodian, models.InternalTip) \
                             .filter(models.IdentityAccessRequest.id == identityaccessrequest_id,
                                     models.IdentityAccessRequestCustodian.identityaccessrequest_id == models.IdentityAccessRequest.id,
                                     models.IdentityAccessRequestCustodian.custodian_id == user_id,
                                     models.InternalTip.id == models.IdentityAccessRequest.internaltip_id).one()

    if request['reply_motivation'] and itip.crypto_tip_pub_key:
        request['reply_motivation'] = base64.b64encode(GCE.asymmetric_encrypt(itip.crypto_tip_pub_key, request['reply_motivation']))

    if iar.reply == 'pending':
        iar.reply_date = datetime_now()
        iar.reply_user_id = user_id
        iar.reply = request['reply']
        iar.reply_motivation = request['reply_motivation']

        db_create_identity_access_reply_notifications(session, itip, iar)

    return serializers.serialize_identityaccessrequest(session, iar)


class IdentityAccessRequestInstance(BaseHandler):
    """
    This handler allow custodians to manage an identity access request by a receiver
    """
    check_roles = 'custodian'

    def put(self, identityaccessrequest_id):
        request = self.validate_request(self.request.content.read(), requests.CustodianIdentityAccessRequestDesc)
        return update_identityaccessrequest(self.request.tid,
                                            self.session.user_id,
                                            identityaccessrequest_id,
                                            request)


class IdentityAccessRequestsCollection(BaseHandler):
    """
    This handler allow custodians to manage an identity access request by a receiver
    """
    check_roles = 'custodian'

    def get(self):
        return get_identityaccessrequest_list(self.request.tid, self.session.user_id, self.session.cc)
