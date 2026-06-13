# API handling recipient user functionalities
import json

from datetime import datetime

from nacl.encoding import Base64Encoder
from sqlalchemy.sql.expression import distinct, func, and_, or_

from globaleaks import models
from globaleaks.handlers.base import BaseHandler
from globaleaks.orm import transact
from globaleaks.utils.crypto import GCE

import globaleaks.handlers.recipient.export


@transact
def get_receivertips(session, tid, receiver_id, user_key, language, args=None):
    """
    Return list of submissions received by the specified receiver

    :param session: An ORM session
    :param tid: The tenant ID
    :param receiver_id: The receiver ID
    :param user_key: The user key to be used for decrypting data
    :param language: The language to be used during data serialization
    :return: A list of submissions descriptors
    """
    if args is None:
        args = {}

    updated_after = datetime.fromtimestamp(int(args.get(b'updated_after', [b'0'])[0]))
    updated_before = datetime.fromtimestamp(int(args.get(b'updated_before', [b'32503680000'])[0]))

    comments_by_itip = {}
    files_by_itip = {}

    # Fetch comments count
    for itip_id, count in session.query(models.InternalTip.id,
                                        func.count(distinct(models.Comment.id))) \
                                 .filter(models.ReceiverTip.receiver_id == receiver_id,
                                         models.ReceiverTip.internaltip_id == models.InternalTip.id,
                                         models.Comment.internaltip_id == models.InternalTip.id,
                                         models.Comment.visibility == 0) \
                                 .group_by(models.InternalTip.id):
        comments_by_itip[itip_id] = count

    # Fetch files count
    for itip_id, count in session.query(models.InternalTip.id,
                                        func.count(distinct(models.InternalFile.id))) \
                                 .filter(models.ReceiverTip.receiver_id == receiver_id,
                                         models.ReceiverTip.internaltip_id == models.InternalTip.id,
                                         models.InternalFile.internaltip_id == models.InternalTip.id) \
                                 .group_by(models.InternalTip.id):
        files_by_itip[itip_id] = count

    # Retrieve all channels that include this recipient, but only if
    # the recipients of those channels are not selectable.
    receiver_contexts = [
        context_id[0] for context_id in session.query(models.Context.id)
                                               .join(models.ReceiverContext,
                                                     models.Context.id == models.ReceiverContext.context_id)
                                               .filter(models.Context.allow_recipients_selection == False,
                                                       models.ReceiverContext.receiver_id == receiver_id
                                                      ).all()
    ]

    dict_ret = dict()
    # Fetch rtip, internaltip and associated questionnaire schema
    for rtip, itip, answers, data in session.query(models.ReceiverTip,
                                                   models.InternalTip,
                                                   models.InternalTipAnswers,
                                                   models.InternalTipData) \
                                            .join(models.InternalTipData,
                                                  and_(models.InternalTipData.internaltip_id == models.InternalTip.id,
                                                       models.InternalTipData.key == 'whistleblower_identity'),
                                                  isouter=True) \
                                            .filter(or_(models.InternalTip.context_id.in_(receiver_contexts),
                                                        models.ReceiverTip.receiver_id == receiver_id),
                                                    models.InternalTip.tid == tid,
                                                    models.InternalTip.update_date >= updated_after,
                                                    models.InternalTip.update_date <= updated_before,
                                                    models.InternalTip.id == models.ReceiverTip.internaltip_id,
                                                    models.InternalTipAnswers.internaltip_id == models.ReceiverTip.internaltip_id) \
                                            .group_by(models.ReceiverTip.id):
        answers = answers.answers  # noqa: PLW2901
        label = itip.label
        accessible = rtip.receiver_id == receiver_id
        if itip.crypto_tip_pub_key and accessible:
            tip_key = GCE.asymmetric_decrypt(user_key, Base64Encoder.decode(rtip.crypto_tip_prv_key))

            if label:
                label = GCE.asymmetric_decrypt(tip_key, Base64Encoder.decode(label.encode())).decode()

            answers = json.loads(GCE.asymmetric_decrypt(tip_key, Base64Encoder.decode(answers.encode())).decode())  # noqa: PLW2901
        elif itip.crypto_tip_pub_key:
            # remove useless and unusable crypted data
            answers = ""  # noqa: PLW2901
            label = ""

        if data is None:
            subscription = 0
        elif data.creation_date == itip.creation_date:
            subscription = 1
        else:
            subscription = 2

        if accessible or itip.id not in dict_ret:
            dict_ret[itip.id] = {
                'id': itip.id,
                'creation_date': itip.creation_date,
                'access_date': rtip.access_date,
                'last_access': itip.last_access,
                'update_date': itip.update_date,
                'expiration_date': itip.expiration_date,
                'reminder_date': itip.reminder_date,
                'progressive': itip.progressive,
                'important': itip.important,
                'label': label,
                'updated': rtip.last_access < itip.update_date,
                'context_id': itip.context_id,
                'tor': itip.tor,
                'answers': answers,
                'score': itip.score,
                'status': itip.status,
                'substatus': itip.substatus,
                'file_count': files_by_itip.get(itip.id, 0),
                'comment_count': comments_by_itip.get(itip.id, 0),
                'receiver_count': 0,
                'subscription': subscription,
                'accessible': accessible
            }

    # Fetch number of receivers who have access to each visible report
    if dict_ret:
        for itip_id, count in session.query(models.ReceiverTip.internaltip_id,
                                            func.count(models.ReceiverTip.id)) \
                                     .filter(models.ReceiverTip.internaltip_id.in_(dict_ret.keys())) \
                                     .group_by(models.ReceiverTip.internaltip_id):
            dict_ret[itip_id]['receiver_count'] = count

    return list(dict_ret.values())


class TipsCollection(BaseHandler):
    """

    Handler dealing with submissions fetch
    """
    check_roles = 'receiver'

    def get(self):
        return get_receivertips(self.request.tid,
                                self.session.user_id,
                                self.session.cc,
                                self.request.language,
                                self.request.args)
