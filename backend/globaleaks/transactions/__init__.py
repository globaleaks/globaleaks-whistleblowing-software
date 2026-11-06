"""
ORM Transactions definitions.
"""
from nacl.encoding import Base64Encoder

from globaleaks import models
from globaleaks.models.config import ConfigFactory
from globaleaks.orm import db_add, db_get
from globaleaks.utils.crypto import GCE


def db_get_user(session, tid, user_id):
    """
    Transaction for retrieving a user model given an id

    :param session: An ORM session
    :param tid: A tenant ID
    :param user_id: A id of the user to retrieve
    :return: A retrieved model
    """
    return db_get(session,
                  models.User,
                  (models.User.id == user_id,
                   models.User.tid == tid))


def db_escrow_key(session, tid, obj, prv_key):
    """
    Keep copies of the private key of an account or of a report encrypted to the escrow key of the
    root site and to the one of its site

    :param session: An ORM session
    :param tid: The tenant ID of the site the account or the report belongs to
    :param obj: The account or the report
    :param prv_key: Its private key
    """
    escrow_pub_key_1 = ConfigFactory(session, 1).get_val('crypto_escrow_pub_key')
    if escrow_pub_key_1:
        obj.crypto_escrow_bkp1_key = Base64Encoder.encode(GCE.asymmetric_encrypt(escrow_pub_key_1, prv_key))

    if tid != 1:
        escrow_pub_key_n = ConfigFactory(session, tid).get_val('crypto_escrow_pub_key')
        if escrow_pub_key_n:
            obj.crypto_escrow_bkp2_key = Base64Encoder.encode(GCE.asymmetric_encrypt(escrow_pub_key_n, prv_key))


def db_schedule_email(session, tid, address, subject, body, secondary_smtp=False):
    return db_add(session,
                  models.Mail,
                  {
                    'address': address,
                    'subject': subject,
                    'body': body,
                    'tid': tid,
                    'secondary_smtp': secondary_smtp,
                  })
