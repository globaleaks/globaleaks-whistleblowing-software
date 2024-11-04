# -*- coding: utf-8 -*-
import importlib
import os
import shutil
import sys
from collections import OrderedDict

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

from globaleaks import __version__, models, \
    DATABASE_VERSION, FIRST_DATABASE_VERSION_SUPPORTED, LANGUAGES_SUPPORTED_CODES
from globaleaks.db.appdata import load_appdata, db_load_defaults
from globaleaks.db.migrations.update_69 import Field_v_68, InternalTipAnswers_v_68, User_v_68, Tenant_v_68, \
    Subscriber_v_68, InternalFile_v_68, \
    ReceiverFile_v_68, Mail_v_68
from globaleaks.orm import db_log

from globaleaks.db.migrations.update_53 import FieldAttr_v_52, InternalTip_v_52, \
    ReceiverTip_v_52, Subscriber_v_52, \
    Tenant_v_52, User_v_52
from globaleaks.db.migrations.update_54 import File_v_53
from globaleaks.db.migrations.update_55 import SubmissionStatusChange_v_54, User_v_54
from globaleaks.db.migrations.update_57 import User_v_56
from globaleaks.db.migrations.update_58 import InternalTip_v_57, \
    WhistleblowerFile_v_57, ReceiverTip_v_57, ReceiverFile_v_57
from globaleaks.db.migrations.update_59 import ReceiverTip_v_58
from globaleaks.db.migrations.update_60 import InternalTip_v_59, ReceiverTip_v_59, WhistleblowerTip_v_59
from globaleaks.db.migrations.update_62 import AuditLog_v_61, Context_v_61, ReceiverTip_v_61, User_v_61
from globaleaks.db.migrations.update_63 import Subscriber_v_62
from globaleaks.db.migrations.update_64 import Context_v_63, InternalTip_v_63
from globaleaks.db.migrations.update_65 import Comment_v_64, \
    IdentityAccessRequest_v_64, InternalFile_v_64, InternalTip_v_64, \
    Message_v_64, ReceiverTip_v_64, \
    SubmissionStatus_v_64, SubmissionSubStatus_v_64, \
    User_v_64, ReceiverFile_v_64, WhistleblowerFile_v_64
from globaleaks.db.migrations.update_66 import SubmissionSubStatus_v_65
from globaleaks.db.migrations.update_67 import \
        InternalTip_v_66, ReceiverFile_v_66, Redaction_v_66, User_v_66, WhistleblowerFile_v_66
from globaleaks.db.migrations.update_68 import Subscriber_v_67


from globaleaks.orm import get_engine, get_session, make_db_uri
from globaleaks.models import config, Base
from globaleaks.settings import Settings
from globaleaks.utils.fs import srm
from globaleaks.utils.log import log
from globaleaks.utils.utility import datetime_now


migration_mapping = OrderedDict([
    ('ArchivedSchema', [models._ArchivedSchema, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]),
    ('AuditLog', [-1, -1, AuditLog_v_61, 0, 0, 0, 0, 0, 0, 0, models._AuditLog, 0, 0, 0, 0, 0, 0, 0]),
    ('Comment', [Comment_v_64, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, models._Comment, 0, 0, 0, 0]),
    ('Config', [models._Config, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]),
    ('ConfigL10N', [models._ConfigL10N, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]),
    ('Context', [Context_v_61, 0, 0, 0, 0, 0, 0, 0, 0, 0, Context_v_63, 0, models._Context, 0, 0, 0, 0, 0]),
    ('CustomTexts', [models._CustomTexts, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]),
    ('EnabledLanguage', [models._EnabledLanguage, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]),
    ('Field', [Field_v_68, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, models._Field]),
    ('FieldAttr', [FieldAttr_v_52, models._FieldAttr, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]),
    ('FieldOption', [models._FieldOption, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]),
    ('FieldOptionTriggerField', [models._FieldOptionTriggerField, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]),
    ('FieldOptionTriggerStep', [models._FieldOptionTriggerStep, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]),
    ('File', [File_v_53, 0, models._File, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]),
    ('IdentityAccessRequest', [IdentityAccessRequest_v_64, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, models._IdentityAccessRequest, 0, 0, 0, 0]),
    ('IdentityAccessRequestCustodian', [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, models._IdentityAccessRequestCustodian, 0, 0, 0, 0]),
    ('InternalFile', [InternalFile_v_64, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, InternalFile_v_68, 0, 0, 0, models._InternalFile]),
    ('InternalTip', [InternalTip_v_52, InternalTip_v_57, 0, 0, 0, 0, InternalTip_v_59, 0, InternalTip_v_63, 0, 0, 0, InternalTip_v_64, InternalTip_v_66, 0, models._InternalTip, 0, 0]),
    ('InternalTipAnswers', [InternalTipAnswers_v_68, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, models._InternalTipAnswers]),
    ('InternalTipData', [models._InternalTipData, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]),
    ('Mail', [Mail_v_68, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, models._Mail]),
    ('Message', [Message_v_64, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, -1, -1, -1, -1, -1]),
    ('Questionnaire', [models._Questionnaire, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]),
    ('ReceiverContext', [models._ReceiverContext, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]),
    ('ReceiverFile', [ReceiverFile_v_57, 0, 0, 0, 0, 0, ReceiverFile_v_64, 0, 0, 0, 0, 0, 0, ReceiverFile_v_66, 0, ReceiverFile_v_68, 0, models._ReceiverFile]),
    ('ReceiverTip', [ReceiverTip_v_52, ReceiverTip_v_57, 0, 0, 0, 0, ReceiverTip_v_58, ReceiverTip_v_59, ReceiverTip_v_61, 0, ReceiverTip_v_64, 0, 0, models._ReceiverTip, 0, 0, 0, 0]),
    ('Redaction', [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, Redaction_v_66, 0, models._Redaction, 0, 0]),
    ('Redirect', [models._Redirect, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]),
    ('SubmissionStatus', [SubmissionStatus_v_64, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, models._SubmissionStatus, 0, 0, 0]),
    ('SubmissionSubStatus', [SubmissionSubStatus_v_64, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, SubmissionSubStatus_v_65, 0, models._SubmissionSubStatus, 0, 0]),
    ('SubmissionStatusChange', [SubmissionStatusChange_v_54, 0, 0, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1]),
    ('Step', [models._Step, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]),
    ('Subscriber', [Subscriber_v_52, Subscriber_v_62, 0, 0, 0, 0, 0, 0, 0, 0, 0, Subscriber_v_67, 0, 0, 0, 0, Subscriber_v_68, models._Subscriber]),
    ('Tenant', [Tenant_v_52, Tenant_v_68, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, models._Tenant]),
    ('User', [User_v_52, User_v_54, 0, User_v_56, 0, User_v_61, 0, 0, 0, 0, User_v_64, 0, 0, User_v_66, 0, User_v_68, 0, models._User]),
    ('WhistleblowerFile', [WhistleblowerFile_v_57, 0, 0, 0, 0, 0, WhistleblowerFile_v_64, 0, 0, 0, 0, 0, 0, WhistleblowerFile_v_66, 0, models._WhistleblowerFile, 0, 0]),
    ('InternalTipForwarding', [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, models._InternalTipForwarding]),
    ('ContentForwarding', [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, models._ContentForwarding]),
    ('WhistleblowerTip', [WhistleblowerTip_v_59, 0, 0, 0, 0, 0, 0, 0, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1])
])


def get_right_model(migration_mapping, model_name, version):
    """
    Utility function to retrieve the model corresponding to a specific model name in a specific database version
    :param migration_mapping: The model mappung table
    :param model_name: The model name
    :param version: The database version
    :return: The model corresponding to a specific model name in a specific database version
    """
    table_index = (version - FIRST_DATABASE_VERSION_SUPPORTED)

    if migration_mapping[model_name][table_index] == -1:
        return None

    while table_index >= 0:
        if migration_mapping[model_name][table_index] != 0:
            return migration_mapping[model_name][table_index]
        table_index -= 1

    return None


def perform_data_update(db_file):
    """
    Update the database including up-to-date application data
    :param db_file: The database file path
    """
    now = datetime_now()

    appdata = load_appdata()

    session = get_session(make_db_uri(db_file), foreign_keys = False)

    enabled_languages = [lang.name for lang in session.query(models.EnabledLanguage)]

    removed_languages = list(set(enabled_languages) - set(LANGUAGES_SUPPORTED_CODES))

    if removed_languages:
        removed_languages.sort()
        removed_languages = ', '.join(removed_languages)
        raise Exception("FATAL: cannot complete the upgrade because the support for some of the enabled languages is currently incomplete (%s)\n" % removed_languages)

    try:
        original_version = config.ConfigFactory(session, 1).get_val('version')
        if original_version != __version__:
            for tid in [t[0] for t in session.query(models.Tenant.id)]:
                config.update_defaults(session, tid, appdata)

            db_load_defaults(session)

            session.query(models.Config).filter_by(var_name='version') \
                   .update({'value': __version__, 'update_date': now})

            session.query(models.Config).filter_by(var_name='latest_version') \
                   .update({'value': __version__, 'update_date': now})

            session.query(models.Config).filter_by(var_name='version_db') \
                   .update({'value': DATABASE_VERSION, 'update_date': now})

            db_log(session, tid=1, type='version_update', user_id='system', data={'from': original_version, 'to': __version__})

        session.commit()
    except:
        session.rollback()
        raise
    finally:
        session.close()


def perform_migration(version):
    """
    Utility function for performing a database migration
    :param version: The current version of the database to update
    """
    if version < FIRST_DATABASE_VERSION_SUPPORTED:
        log.info("Migrations from DB version lower than %d are no longer supported!" % FIRST_DATABASE_VERSION_SUPPORTED)
        sys.exit(1)

    tmpdir = os.path.abspath(os.path.join(Settings.tmp_path, 'tmp'))
    db_file = os.path.abspath(os.path.join(Settings.working_path, 'globaleaks.db'))

    shutil.rmtree(tmpdir, True)
    os.mkdir(tmpdir)
    shutil.copy(db_file, os.path.join(tmpdir, 'old.db'))

    old_db_file = os.path.abspath(os.path.join(tmpdir, 'old.db'))
    session_old = get_session(make_db_uri(old_db_file))

    new_db_file = os.path.abspath(os.path.join(tmpdir, 'new.db'))
    session_new = None

    Settings.enable_input_length_checks = False

    try:
        while version < DATABASE_VERSION:
            log.info("Updating DB from version %d to version %d" %
                     (version, version + 1))

            j = version - FIRST_DATABASE_VERSION_SUPPORTED

            if version == DATABASE_VERSION - 1:
                engine = get_engine(make_db_uri(new_db_file), foreign_keys=False, orm_lockdown=False)
            else:
                engine = create_engine("sqlite:///:memory:")

            if FIRST_DATABASE_VERSION_SUPPORTED + j + 1 == DATABASE_VERSION:
                Base.metadata.create_all(engine)
            else:
                Bases[j+1].metadata.create_all(engine)

            if session_new:
                session_old = session_new

            session_new = sessionmaker(bind=engine)()

            # Here is instanced the migration script
            MigrationModule = importlib.import_module("globaleaks.db.migrations.update_%d" % (version + 1))
            migration_script = MigrationModule.MigrationScript(migration_mapping, version, session_old, session_new)

            log.info("Migrating table:")

            try:
                try:
                    migration_script.prologue()
                except Exception as exception:
                    log.err("Failure while executing migration prologue: %s" % exception)
                    raise exception

                for model_name, _ in migration_mapping.items():
                    if migration_script.model_from[model_name] is not None and migration_script.model_to[model_name] is not None:
                        try:
                            migration_script.migrate_model(model_name)

                            # Commit at every table migration in order to be able to detect
                            # the precise migration that may fail.
                            migration_script.commit()
                        except Exception as exception:
                            log.err("Failure while migrating table %s: %s " % (model_name, exception))
                            raise exception
                try:
                    migration_script.epilogue()
                    migration_script.commit()
                except Exception as exception:
                    log.err("Failure while executing migration epilogue: %s " % exception)
                    raise exception

            finally:
                # the database should be always closed before leaving the application
                # in order to not keep leaking journal files.
                migration_script.close()

            log.info("Migration completed with success.")

            log.info("Migration stats:")

            for model_name, _ in migration_mapping.items():
                if migration_script.model_from[model_name] is not None and migration_script.model_to[model_name] is not None:
                    count = session_new.query(migration_script.model_to[model_name]).count()
                    if migration_script.entries_count[model_name] != count:
                        if migration_script.skip_count_check.get(model_name, False):
                            log.info(" * %s table migrated (entries count changed from %d to %d)" %
                                     (model_name, migration_script.entries_count[model_name], count))
                        else:
                            raise AssertionError("Integrity check failed on count equality for table %s: %d != %d" %
                                                 (model_name, count, migration_script.entries_count[model_name]))
                    else:
                        log.info(" * %s table migrated (%d entry(s))" %
                                             (model_name, migration_script.entries_count[model_name]))

            version += 1

        perform_data_update(new_db_file)
    except:
        raise
    else:
        # in case of success first copy the new migrated db, then as last action delete the original db file
        shutil.move(new_db_file, db_file)
    finally:
        # Always cleanup the temporary directory used for the migration
        for f in os.listdir(tmpdir):
            srm(os.path.join(tmpdir, f))

        shutil.rmtree(tmpdir)


mp = OrderedDict()
Bases = {}
for i in range(DATABASE_VERSION - FIRST_DATABASE_VERSION_SUPPORTED + 1):
    Bases[i] = declarative_base()
    for k in migration_mapping:
        if k not in mp:
            mp[k] = []

        x = get_right_model(migration_mapping, k,
                            FIRST_DATABASE_VERSION_SUPPORTED + i)
        if x is not None:
            class y(x, Bases[i]):
                pass

            mp[k].append(y)
        else:
            mp[k].append(None)


migration_mapping = mp
