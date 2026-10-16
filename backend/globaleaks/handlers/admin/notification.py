from globaleaks.handlers.base import BaseHandler
from globaleaks.models.config import ConfigFactory, ConfigL10NFactory, get_default
from globaleaks.models.config_desc import ConfigDescriptor, ConfigFilters, ConfigL10NFilters
from globaleaks.orm import db_log, transact, tw
from globaleaks.rest import errors, requests

# The variables of each server are named by its prefix: the administration reads and writes them
# without it, so that the two servers are served by the same handler in the same shape
SMTP_PREFIXES = {
    'smtp1': 'smtp_',
    'smtp2': 'smtp2_'
}

# What a reset brings back to the defaults: whether a server is in use, and for which notifications
# the secondary one is, is a choice of the administrator and not a part of the server
SMTP_RESET_KEYS = ['authentication', 'password', 'port', 'security', 'server', 'source_email', 'username']


def db_get_notification(session, tid, language):
    """
    Transaction to get the notification settings for the specified tenant

    This is what the mails are composed with: the settings, the templates, and whether a mail goes
    through the secondary server. The passwords of the servers are not part of it.

    :param session: An ORM session
    :param tid: A tenant ID
    :param language: The language to be used in the serialization
    :return: the serialization of notification settings for the specified tenant
    """
    ret = ConfigFactory(session, tid).serialize('notification')
    del ret['smtp_password'], ret['smtp2_password']

    ret.update(ConfigL10NFactory(session, tid).serialize('notification', language))

    return ret


def db_get_notification_settings(session, tid):
    return ConfigFactory(session, tid).serialize('notification_settings')


@transact
def update_notification_settings(session, tid, user_id, request):
    ConfigFactory(session, tid).update('notification_settings', request)

    db_log(session, tid=tid, type='update_notification_settings', user_id=user_id)

    return db_get_notification_settings(session, tid)


def db_get_notification_templates(session, tid, language):
    ret = ConfigL10NFactory(session, tid).serialize('notification', language)

    ret['templates'] = ConfigL10NFilters['notification']

    return ret


@transact
def update_notification_templates(session, tid, user_id, request, language):
    ConfigL10NFactory(session, tid).update('notification', request, language)

    db_log(session, tid=tid, type='update_notification_templates', user_id=user_id)

    return db_get_notification_templates(session, tid, language)


def db_get_smtp(session, tid, name):
    """
    Serialize one of the two servers without the prefix of its variables

    The password is never read back: the administration is told only whether there is one.
    """
    prefix = SMTP_PREFIXES[name]
    ret = {k[len(prefix):]: v for k, v in ConfigFactory(session, tid).serialize(name).items()}
    ret['password_set'] = bool(ret.pop('password'))

    return ret


def db_update_smtp(session, tid, user_id, name, request, log_type):
    prefix = SMTP_PREFIXES[name]
    config = ConfigFactory(session, tid)

    # A server asking for no authentication keeps no password; one asking for it keeps the one
    # it holds unless a new one is given, and is not left without
    if not request['authentication']:
        request['password'] = ''
    elif not request['password']:
        if not config.get_val(prefix + 'password'):
            raise errors.InputValidationError("The authentication requires a password")

        del request['password']

    config.update(name, {prefix + k: v for k, v in request.items()})

    db_log(session, tid=tid, type=log_type, user_id=user_id)

    return db_get_smtp(session, tid, name)


@transact
def update_smtp(session, tid, user_id, name, request):
    return db_update_smtp(session, tid, user_id, name, request, 'update_' + name)


@transact
def reset_smtp(session, tid, user_id, name):
    prefix = SMTP_PREFIXES[name]
    request = {k: get_default(ConfigDescriptor[prefix + k].default) for k in SMTP_RESET_KEYS}

    return db_update_smtp(session, tid, user_id, name, request, 'reset_' + name)


class NotificationSettingsInstance(BaseHandler):
    """
    Manage which roles are notified, and when the expiration of a report is announced
    """
    check_roles = 'admin'
    require_permission = 'can_manage_notifications'
    invalidate_cache = True

    def get(self):
        return tw(db_get_notification_settings, self.request.tid)

    def put(self):
        request = self.validate_request(self.request.content.read(),
                                        requests.AdminNotificationSettingsDesc)

        return update_notification_settings(self.request.tid, self.session.user_id, request)


class NotificationTemplatesInstance(BaseHandler):
    """
    Manage the templates of the mails, in the language of the request
    """
    check_roles = 'admin'
    require_permission = 'can_manage_notifications'
    invalidate_cache = True

    def get(self):
        return tw(db_get_notification_templates, self.request.tid, self.request.language)

    def put(self):
        request = self.validate_request(self.request.content.read(),
                                        requests.AdminNotificationTemplatesDesc)

        return update_notification_templates(self.request.tid, self.session.user_id, request, self.request.language)


class SMTPInstance(BaseHandler):
    """
    Manage one of the two servers the mails are sent through: smtp1, the main one, or smtp2,
    the secondary one delivering the notifications chosen for it. Each is turned on and off on
    its own: the main server on by default, the secondary one off.

    Deleting a server brings it back to the defaults of the application.
    """
    check_roles = 'admin'
    require_permission = 'can_manage_notifications'
    invalidate_cache = True

    def get(self, name):
        return tw(db_get_smtp, self.request.tid, name)

    def put(self, name):
        request = self.validate_request(self.request.content.read(),
                                        requests.AdminSMTP2Desc if name == 'smtp2' else requests.AdminSMTPDesc)

        return update_smtp(self.request.tid, self.session.user_id, name, request)

    def delete(self, name):
        return reset_smtp(self.request.tid, self.session.user_id, name)
