from globaleaks.handlers.base import BaseHandler
from globaleaks.models.config import ConfigFactory, ConfigL10NFactory
from globaleaks.models.config_desc import ConfigL10NFilters
from globaleaks.orm import db_log, transact, tw
from globaleaks.rest import requests


def db_get_notification(session, tid, language):
    """
    Transaction to get the notification settings for the specified tenant

    :param session: An ORM session
    :param tid: A tenant ID
    :param language: The language to be used in the serialization
    :return: the serialization of notification settings for the specified tenant
    """
    ret = ConfigFactory(session, tid).serialize('notification')

    ret.update(ConfigL10NFactory(session, tid).serialize('notification', language))

    ret['templates'] = ConfigL10NFilters['notification']

    return ret


@transact
def update_notification(session, tid, user_id, request, language):
    ConfigFactory(session, tid).update('notification', request)
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
