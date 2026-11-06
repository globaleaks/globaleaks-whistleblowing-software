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


def db_stat_key(session, itip, prv_key):
    """
    Keep a copy of the private key of a report encrypted to the statistical key of its site, the
    statistics reading its answers through it. The reports an exchange files are not accounted for

    :param session: An ORM session
    :param itip: The report
    :param prv_key: Its private key
    """
    if itip.type in ('request', 'exchange'):
        return

    stat_pub_key = ConfigFactory(session, itip.tid).get_val('crypto_stat_pub_key')
    if stat_pub_key:
        itip.crypto_stat_tip_prv_key = Base64Encoder.encode(GCE.asymmetric_encrypt(stat_pub_key, prv_key))


def db_complete_report_key_copies(session, itip, encrypted_prv_key, cc):
    """
    Complete the copies of the private key of a report for the escrow and for the statistics that it
    misses, as the reports filed before them, or before the escrow was enabled, do: whoever
    decrypts the key on access protects it

    :param session: An ORM session
    :param itip: The report
    :param encrypted_prv_key: Its private key, encrypted to the one decrypting it
    :param cc: The private key decrypting it
    """
    if not encrypted_prv_key or not cc:
        return

    root_config, config = ConfigFactory(session, 1), ConfigFactory(session, itip.tid)

    escrow_missing = not itip.crypto_escrow_bkp1_key and root_config.get_val('crypto_escrow_pub_key') or \
        itip.tid != 1 and not itip.crypto_escrow_bkp2_key and config.get_val('crypto_escrow_pub_key')

    stat_missing = not itip.crypto_stat_tip_prv_key and itip.type not in ('request', 'exchange') and \
        config.get_val('crypto_stat_pub_key')

    if not escrow_missing and not stat_missing:
        return

    prv_key = GCE.asymmetric_decrypt(cc, Base64Encoder.decode(encrypted_prv_key))

    if escrow_missing:
        db_escrow_key(session, itip.tid, itip, prv_key)

    if stat_missing:
        db_stat_key(session, itip, prv_key)


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
