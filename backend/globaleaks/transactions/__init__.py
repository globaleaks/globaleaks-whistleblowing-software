# -*- coding: utf-8
"""
ORM Transactions definitions.
"""
from globaleaks import models
from globaleaks.orm import db_add, db_get


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


def db_schedule_email(session, tid, address, subject, body, is_pec:bool=False):
    return db_add(session,
                  models.Mail,
                  {
                    'address': address,
                    'subject': subject,
                    'body': body,
                    'tid': tid,
                    'is_pec': is_pec
                  })
