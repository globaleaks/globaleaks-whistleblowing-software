"""
The entities an administrative page offers to choose from.

Every administrative area is gated on its own permission, reads included, so an
administrator scoped to the channels does not read the users. Composing a
channel however requires choosing its recipients, and configuring the platform
requires choosing a channel or a questionnaire: this handler serves those
choices - the names, and the few traits the choice is made on - to every
administrator, and nothing more. Picking a recipient is not managing the users.
"""
from globaleaks import models
from globaleaks.handlers.base import BaseHandler
from globaleaks.models import get_localized_values
from globaleaks.orm import transact


def serialize_selectable_user(user):
    """
    Serialize an account as an option: what names it and what the pages select
    it by, which is its role and, for the key escrow, whether it holds the keys
    """
    return {
        'id': user.id,
        'name': user.name,
        'role': user.role,
        'encryption': user.crypto_pub_key != '',
        'escrow': user.crypto_escrow_prv_key != ''
    }


@transact
def get_selectables(session, tid, language):
    users = session.query(models.User).filter(models.User.tid == tid)

    contexts = session.query(models.Context).filter(models.Context.tid == tid)

    questionnaires = session.query(models.Questionnaire) \
                            .filter(models.Questionnaire.tid == tid)

    return {
        'users': [serialize_selectable_user(user) for user in users],
        'contexts': [get_localized_values({'id': context.id}, context, ['name'], language)
                     for context in contexts],
        'questionnaires': [{'id': questionnaire.id, 'name': questionnaire.name}
                           for questionnaire in questionnaires]
    }


class SelectablesCollection(BaseHandler):
    """
    Handler serving the entities the administrative pages choose from
    """
    check_roles = 'admin'

    def get(self):
        return get_selectables(self.request.tid, self.request.language)
