import json

from globaleaks.state import State
from twisted.internet.defer import inlineCallbacks, returnValue

from globaleaks import models, LANGUAGES_SUPPORTED_CODES, LANGUAGES_SUPPORTED
from globaleaks.handlers.base import BaseHandler
from globaleaks.handlers.public import db_get_languages
from globaleaks.models import EnabledLanguage
from globaleaks.models.enums import EnumStateFile
from globaleaks.models.config import ConfigFactory, ConfigL10NFactory, DEFAULT_PROFILE_ID, db_get_pid_by_profile
from globaleaks.orm import db_del, tw
from globaleaks.rest import errors, requests
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

    for lang in languages:
        if lang not in LANGUAGES_SUPPORTED_CODES:
            raise errors.InputValidationError("Invalid lang code: %s" % lang)

        if lang not in cur_enabled_langs:
            session.add(EnabledLanguage({'tid': tid, 'name': lang}))

    to_remove = list(set(cur_enabled_langs) - set(languages))
    if to_remove:
        user_ids = session.query(models.User.id).filter(models.User.tid == tid, models.User.language.in_(to_remove)).all()
        user_ids = [pid[0] for pid in user_ids]

        if user_ids:
            session.query(models.User) \
                .filter(models.User.id.in_(user_ids)) \
                .update({'language': default_language}, synchronize_session=False)

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
        'logo': True if logo else False,
        'tid': tid
    })

    if 'version' in ret:
        ret['update_available'] = ret['version'] != ret['latest_version']

    ret.update(ConfigL10NFactory(session, tid).serialize(config_desc, language))

    return ret


def db_reset_antivirus_verification(session, tid):
    for ifile in session.query(models.InternalFile) \
                        .join(models.InternalTip, models.InternalFile.internaltip_id == models.InternalTip.id) \
                        .filter(models.InternalTip.tid == tid):
        ifile.state = EnumStateFile.pending.name
        ifile.verification_date = None

    for rfile in session.query(models.ReceiverFile) \
                        .join(models.InternalTip, models.ReceiverFile.internaltip_id == models.InternalTip.id) \
                        .filter(models.InternalTip.tid == tid):
        rfile.state = EnumStateFile.pending.name
        rfile.verification_date = None


def clear_queued_antivirus_scans_for_tenant(session, tid):
    from globaleaks.state import State

    queued_file_ids = {file_id for file_id, _ in State.antivirus_files}
    if not queued_file_ids:
        return

    tenant_file_ids = set()

    tenant_file_ids.update(
        file_id for (file_id,) in session.query(models.InternalFile.id)
                                     .join(models.InternalTip, models.InternalFile.internaltip_id == models.InternalTip.id)
                                     .filter(models.InternalTip.tid == tid,
                                             models.InternalFile.id.in_(queued_file_ids))
    )
    tenant_file_ids.update(
        file_id for (file_id,) in session.query(models.ReceiverFile.id)
                                     .join(models.InternalTip, models.ReceiverFile.internaltip_id == models.InternalTip.id)
                                     .filter(models.InternalTip.tid == tid,
                                             models.ReceiverFile.id.in_(queued_file_ids))
    )

    if not tenant_file_ids:
        return

    State.antivirus_files = [(file_id, tip_prv_key) for file_id, tip_prv_key in State.antivirus_files
                             if file_id not in tenant_file_ids]
    State.antivirus_file_ids.difference_update(tenant_file_ids)


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

    # The sites created via signup can only be assigned to the default profile
    # or to one of the profiles configured on the platform; any other reference,
    # like the one of a profile deleted in the meantime, falls back on the default
    if request.get('signup_profile', 'default') != 'default':
        pid = db_get_pid_by_profile(session, request['signup_profile'])
        if pid is None or pid <= DEFAULT_PROFILE_ID:
            request['signup_profile'] = 'default'

    config = ConfigFactory(session, tid)
    antivirus_was_enabled = config.get_val('antivirus_enabled')

    config.update('node', request)

    antivirus_is_enabled = request.get('antivirus_enabled', antivirus_was_enabled)
    if antivirus_was_enabled and not antivirus_is_enabled:
        db_reset_antivirus_verification(session, tid)
        clear_queued_antivirus_scans_for_tenant(session, tid)

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
        if self.session.role == 'admin':
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
        ret["is_profile"] = True if self.request.tid > 1000001 else False

        if ret.get("backup_enabled"):
            backup_job = State.jobs_status.get("Backup", None)
            if backup_job:
                ret["backup_job_status"] = backup_job["status"]

        returnValue(ret)

    @inlineCallbacks
    def put(self):
        """
        Update the node infos.
        """
        config = yield self.determine_allow_config_filter()

        raw_request = self.request.content.read()
        if config[1] == requests.AdminNodeDesc:
            try:
                parsed_request = json.loads(raw_request)
            except:
                raise errors.InputValidationError

            if 'default_user_profile' not in parsed_request:
                parsed_request['default_user_profile'] = State.tenants[self.request.tid].cache['default_user_profile']

            raw_request = json.dumps(parsed_request)

        request = yield self.validate_request(raw_request, config[1])

        if request['idp'] and not request['idp_issuer']:
            raise errors.InputValidationError('IDP issuer is required when IDP is enabled')

        # When a local IDP issuer is configured, validate server-side that it is
        # reachable and exposes a usable JWKS before persisting the change.
        if request['idp']:
            if not request.get('idp_client_id'):
                raise errors.InputValidationError('No IdP client identifier configured')

            try:
                yield State.oidcauth.validate_issuer(request['idp_issuer'])
            except Exception:
                raise errors.InputValidationError('Unable to validate the configured IdP issuer')

        ret = yield tw(db_update_node,
                       self.request.tid,
                       self.session,
                       request,
                       self.request.language)

        # Backup is a global (tenant 1) feature: keep the Backup job lifecycle
        # in sync with its configuration so that disabling it actually stops the
        # running job rather than leaving it looping as a no-op.
        if self.request.tid == 1 and 'backup_enabled' in request:
            # Imported lazily: the jobs package imports this module at load time.
            from globaleaks.jobs.job import reschedule_job, stop_job
            if request['backup_enabled']:
                # Re-arm rather than start: the job is already running since
                # startup, so this is what makes a changed backup time/period
                # actually take effect (get_delay is recomputed).
                reschedule_job("Backup")
                backup_job = State.jobs_status.get("Backup", None)
                if backup_job:
                    ret["backup_job_status"] = backup_job["status"]
            else:
                yield stop_job("Backup")

        tenant = self.state.tenants.get(self.request.tid)
        if tenant is not None:
            for key in ('antivirus_enabled', 'antivirus_clamd_ip', 'antivirus_clamd_port'):
                if key in ret:
                    tenant.cache[key] = ret[key]

        returnValue(ret)
