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

    # A channel names user profiles: a shared profile by itself, a personal one by its account
    profile_names = {user.profile_id: user.name for user in users}

    # A channel is received on by the accounts entitled to receive: the
    # profiles that do not hold the role are no choice at all
    user_profiles = session.query(models.UserProfile) \
                           .filter(models.UserProfile.tid == tid,
                                   models.UserProfileRole.profile_id == models.UserProfile.id,
                                   models.UserProfileRole.role == 'receiver')

    return {
        'users': [serialize_selectable_user(user) for user in users],
        'contexts': [get_localized_values({'id': context.id}, context, ['name'], language)
                     for context in contexts],
        'questionnaires': [{'id': questionnaire.id, 'name': questionnaire.name}
                           for questionnaire in questionnaires],
        'user_profiles': [{'id': profile.id,
                           'name': profile.name or profile_names.get(profile.id, '')}
                          for profile in user_profiles
                          if profile.name or profile.id in profile_names]
    }


class SelectablesCollection(BaseHandler):
    """
    Handler serving the entities the administrative pages choose from
    """
    check_roles = 'admin'

    def get(self):
        return get_selectables(self.request.tid, self.request.language)
