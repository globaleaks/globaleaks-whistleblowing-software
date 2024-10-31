# -*- coding: utf-8
from twisted.internet.defer import inlineCallbacks, returnValue

from globaleaks import models, LANGUAGES_SUPPORTED_CODES, LANGUAGES_SUPPORTED
from globaleaks.db.appdata import load_appdata
from globaleaks.handlers.base import BaseHandler
from globaleaks.handlers.public import db_get_languages
from globaleaks.models.config import ConfigFactory, ConfigL10NFactory
from globaleaks.orm import db_del, tw
from globaleaks.rest import errors, requests
from globaleaks.utils.crypto import GCE
from globaleaks.utils.fs import read_file
from globaleaks.utils.log import log


def db_update_enabled_languages(session, tid, languages, default_language):
    """
    Transaction for updating the enabled languages for a tenant

    :param session: An ORM session
    :param tid: A tenant id
    :param languages: The list of the languages to be enabled
    :param default_language: The language to be set as default
    """
    cur_enabled_langs = db_get_languages(session, tid)

    if len(languages) < 1:
        raise errors.InputValidationError("No languages enabled!")

    # get sure that the default language is included in the enabled languages
    languages = set(languages + [default_language])

    appdata = None
    for lang_code in languages:
        if lang_code not in LANGUAGES_SUPPORTED_CODES:
            raise errors.InputValidationError("Invalid lang code: %s" % lang_code)

        if lang_code not in cur_enabled_langs:
            if appdata is None:
                appdata = load_appdata()
            models.config.add_new_lang(session, tid, lang_code, appdata)

    to_remove = list(set(cur_enabled_langs) - set(languages))
    if to_remove:
        session.query(models.User).filter(models.User.tid == tid, models.User.language.in_(to_remove)).update({'language': default_language}, synchronize_session=False)
        db_del(session, models.EnabledLanguage, (models.EnabledLanguage.tid == tid, models.EnabledLanguage.name.in_(to_remove)))


def db_admin_serialize_node(session, tid, language, config_desc='node'):
    """
    Transaction for fetching the node configuration as admin

    :param session: An ORM session
    :param tid: A tenant ID
    :param language: The language to be used on serialization
    :param config_desc: The set of variables to be serialized
    :return: Return the serialized configuration for the specified tenant
    """
    config = ConfigFactory(session, tid)
    root_config = ConfigFactory(session, tid)

    ret = config.serialize(config_desc)

    logo = session.query(models.File.id).filter(models.File.tid == tid, models.File.name == 'logo').one_or_none()

    ret.update({
        'changelog': read_file('/usr/share/globaleaks/CHANGELOG'),
        'license': read_file('/usr/share/globaleaks/LICENSE'),
        'languages_supported': LANGUAGES_SUPPORTED,
        'languages_enabled': db_get_languages(session, tid),
        'root_tenant': tid == 1,
        'https_possible': tid == 1 or root_config.get_val('reachable_via_web'),
        'encryption_possible': tid == 1 or root_config.get_val('encryption'),
        'escrow': config.get_val('crypto_escrow_pub_key') != '',
        'logo': True if logo else False
    })

    if 'version' in ret:
        ret['update_available'] = ret['version'] != ret['latest_version']

    ret.update(ConfigL10NFactory(session, tid).serialize(config_desc, language))

    return ret


def db_update_node(session, tid, user_session, request, language):
    """
    Transaction to update the node configuration

    :param session: An ORM session
    :param tid: A tenant ID
    :param user_session: The current user session
    :param request: The request data
    :param language: the language in which to localize data
    :return: Return the serialized configuration for the specified tenant
    """
    root_config = ConfigFactory(session, 1)

    config = ConfigFactory(session, tid)

    config.update('node', request)

    if 'languages_enabled' in request and 'default_language' in request:
        db_update_enabled_languages(session,
                                    tid,
                                    request['languages_enabled'],
                                    request['default_language'])

    if language in db_get_languages(session, tid):
        ConfigL10NFactory(session, tid).update('node', request, language)

    if tid == 1:
        log.setloglevel(config.get_val('log_level'))

    return db_admin_serialize_node(session, tid, language)


class NodeInstance(BaseHandler):
    check_roles = 'user'
    invalidate_cache = True

    def determine_allow_config_filter(self):
        if self.session.user_role == 'admin':
            node = ('admin_node', requests.AdminNodeDesc)
        elif self.session.has_permission('can_edit_general_settings'):
            node = ('general_settings', requests.SiteSettingsDesc)
        else:
            raise errors.InvalidAuthentication

        return node

    @inlineCallbacks
    def get(self):
        """
        Get the node infos.
        """
        config = yield self.determine_allow_config_filter()

        ret = yield tw(db_admin_serialize_node,
                       self.request.tid,
                       self.request.language,
                       config_desc=config[0])

        returnValue(ret)

    @inlineCallbacks
    def put(self):
        """
        Update the node infos.
        """
        config = yield self.determine_allow_config_filter()

        request = yield self.validate_request(self.request.content.read(),
                                              config[1])

        ret = yield tw(db_update_node,
                       self.request.tid,
                       self.session,
                       request,
                       self.request.language)

        returnValue(ret)
