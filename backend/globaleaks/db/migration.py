import importlib
import os
import re
import shutil
import sys
from collections import OrderedDict

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

try:
    from sqlalchemy.orm import declarative_base
except ImportError:
    from sqlalchemy.ext.declarative import declarative_base

from globaleaks import __version__, models, \
    DATABASE_VERSION, FIRST_DATABASE_VERSION_SUPPORTED, LANGUAGES_SUPPORTED_CODES
from globaleaks.db.appdata import load_appdata, db_load_defaults
from globaleaks.orm import db_log

from globaleaks.orm import get_engine, get_session, make_db_uri
from globaleaks.models import config, Base, Model
from globaleaks.settings import Settings
from globaleaks.utils.fs import srm
from globaleaks.utils.log import log
from globaleaks.utils.utility import datetime_now


# The schema of a table at a given version is described by the snapshot of
# its model archived by the migration that changed it: the class X_v_N in the
# module update_{N+1} is the model of X up to version N included. A table
# lacking a snapshot from a version on is described by its current model.
#
# The tables that do not exist over the whole range of the supported versions
# are the only ones needing a declaration: the version they were introduced at
# (a table missing a current model is dropped after its last snapshot).
tables_since = {
    'AuditLog': 54,
    'IdentityAccessRequestCustodian': 65,
    'Redaction': 65
}


def load_snapshots():
    """
    Collect the snapshots of the models archived by the migrations

    :return: A dictionary {model_name: {version: snapshot}}
    """
    snapshots = {}

    for version in range(FIRST_DATABASE_VERSION_SUPPORTED, DATABASE_VERSION):
        module = importlib.import_module("globaleaks.db.migrations.update_%d" % (version + 1))

        for name, cls in vars(module).items():
            match = re.fullmatch(r'(\w+)_v_(\d+)', name)
            if match and isinstance(cls, type) and issubclass(cls, Model) and cls.__module__ == module.__name__:
                snapshots.setdefault(match.group(1), {})[int(match.group(2))] = cls

    return snapshots


def load_models():
    """
    Collect the current models of the application

    :return: A dictionary {model_name: model}
    """
    return {name[1:]: cls for name, cls in vars(models).items()
            if name.startswith('_') and isinstance(cls, type) and issubclass(cls, Model) and '__tablename__' in vars(cls)}


def get_right_model(snapshots, current, model_name, version):
    """
    Utility function to retrieve the model corresponding to a specific model name in a specific database version
    :param snapshots: The snapshots archived by the migrations
    :param current: The current models
    :param model_name: The model name
    :param version: The database version
    :return: The model corresponding to a specific model name in a specific database version
    """
    if version < tables_since.get(model_name, FIRST_DATABASE_VERSION_SUPPORTED):
        return None

    archived = [v for v in snapshots.get(model_name, {}) if v >= version]
    if archived:
        return snapshots[model_name][min(archived)]

    return current.get(model_name)


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
    except Exception:
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
    except Exception:
        raise
    else:
        # in case of success first copy the new migrated db, then as last action delete the original db file
        shutil.move(new_db_file, db_file)
    finally:
        # Always cleanup the temporary directory used for the migration
        for f in os.listdir(tmpdir):
            srm(os.path.join(tmpdir, f))

        shutil.rmtree(tmpdir)


snapshots = load_snapshots()
current = load_models()

migration_mapping = OrderedDict()
Bases = {}
for i in range(DATABASE_VERSION - FIRST_DATABASE_VERSION_SUPPORTED + 1):
    Bases[i] = declarative_base()
    for k in sorted(set(snapshots) | set(current)):
        if k not in migration_mapping:
            migration_mapping[k] = []

        x = get_right_model(snapshots, current, k, FIRST_DATABASE_VERSION_SUPPORTED + i)
        if x is not None:
            class_name = f"MigrationModel_{k}_v{FIRST_DATABASE_VERSION_SUPPORTED + i}"
            y = type(class_name, (x, Bases[i]), {})
            migration_mapping[k].append(y)
        else:
            migration_mapping[k].append(None)
