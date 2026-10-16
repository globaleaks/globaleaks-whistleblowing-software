from globaleaks.handlers.base import BaseHandler
from globaleaks.models.config import ConfigFactory, ConfigL10NFactory
from globaleaks.models.config_desc import ConfigL10NFilters
from globaleaks.orm import db_log, transact, tw
from globaleaks.rest import errors, requests


def db_get_notification(session, tid, language):
    """
    Transaction to get the notification settings for the specified tenant

    :param session: An ORM session
    :param tid: A tenant ID
    :param language: The language to be used in the serialization
    :return: the serialization of notification settings for the specified tenant
    """
    ret = ConfigFactory(session, tid).serialize('notification')

    # The password of the server is written and never read back: what is told is only whether
    # there is one, and an empty password sent back leaves it as it is
    ret['smtp_password_set'] = bool(ret['smtp_password'])
    ret['smtp_password'] = ''

    ret.update(ConfigL10NFactory(session, tid).serialize('notification', language))

    ret['templates'] = ConfigL10NFilters['notification']

    return ret


@transact
def update_notification(session, tid, user_id, request, language):
    config = ConfigFactory(session, tid)

    # A server asking for no authentication keeps no password; one asking for it keeps the one
    # it holds unless a new one is given, and is not left without
    if not request['smtp_authentication']:
        request['smtp_password'] = ''
    elif not request['smtp_password']:
        if not config.get_val('smtp_password'):
            raise errors.InputValidationError("The authentication requires a password")

        del request['smtp_password']

    config.update('notification', request)
    ConfigL10NFactory(session, tid).update('notification', request, language)

    db_log(session, tid=tid, type='update_notification', user_id=user_id)

    return db_get_notification(session, tid, language)


class NotificationInstance(BaseHandler):
    """
    Manage Notification settings (account details and template)
    """
    check_roles = 'admin'
    invalidate_cache = True

    def get(self):
        return tw(db_get_notification, self.request.tid, self.request.language)

    def put(self):
        """
        Changes the node notification settings.
        """
        request = self.validate_request(self.request.content.read(),
                                        requests.AdminNotificationDesc)

        return update_notification(self.request.tid, self.session.user_id, request, self.request.language)
