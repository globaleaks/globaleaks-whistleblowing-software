import importlib
import os
import re
import shutil
import sys
from collections import OrderedDict

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

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
    'Redaction': 65,
    'InternalTipTransmission': 69,
    'ContextAdditionalQuestionnaire': 71,
    'Exchange': 71,
    'StatisticalReport': 71,
    'StatisticalReportTemplate': 71,
    'SupportMessage': 71,
    'SupportRequest': 71,
    'UserProfile': 71,
    'UserProfileContext': 71,
    'UserProfilePermission': 71,
    'UserProfileRole': 71
}


def load_snapshots():
    """
    Collect the snapshots of the models archived by the migrations

    :return: A dictionary {model_name: {version: snapshot}}
    """
    snapshots = {}

    for version in range(FIRST_DATABASE_VERSION_SUPPORTED, DATABASE_VERSION):
        module = importlib.import_module(f"globaleaks.db.migrations.update_{version + 1}")

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
        raise RuntimeError(f"FATAL: cannot complete the upgrade because the support for some of the enabled languages is currently incomplete ({removed_languages})\n")

    try:
        original_version = config.ConfigFactory(session, 1).get_val('version')
        if original_version != __version__:
            config.load_defaults(session, appdata)

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


def _migration_engine(version, j, new_db_file):
    """
    Return the engine holding the database at the version a migration step produces

    :param version: The version the migration step starts from
    :param j: The index of the version among the supported ones
    :param new_db_file: The path of the database file the last step writes
    :return: An engine with the schema of the produced version already created
    """
    if version == DATABASE_VERSION - 1:
        engine = get_engine(make_db_uri(new_db_file), foreign_keys=False, orm_lockdown=False)
    else:
        engine = create_engine("sqlite:///:memory:")

    if FIRST_DATABASE_VERSION_SUPPORTED + j + 1 == DATABASE_VERSION:
        Base.metadata.create_all(engine)
    else:
        Bases[j+1].metadata.create_all(engine)

    return engine


def _migrated_models(migration_script):
    """
    Return the name of the models that the migration step both reads and writes

    :param migration_script: The migration script of the step
    """
    for model_name in migration_mapping:
        if migration_script.model_from[model_name] is not None and migration_script.model_to[model_name] is not None:
            yield model_name


def _run_migration_script(migration_script):
    """
    Run a migration step: its prologue, every table it migrates and its epilogue

    :param migration_script: The migration script of the step
    """
    try:
        migration_script.prologue()
    except Exception as exception:
        log.err(f"Failure while executing migration prologue: {exception}")
        raise exception

    for model_name in _migrated_models(migration_script):
        try:
            migration_script.migrate_model(model_name)

            # Commit at every table migration in order to be able to detect
            # the precise migration that may fail.
            migration_script.commit()
        except Exception as exception:
            log.err(f"Failure while migrating table {model_name}: {exception} ")
            raise exception

    try:
        migration_script.epilogue()
        migration_script.commit()
    except Exception as exception:
        log.err(f"Failure while executing migration epilogue: {exception} ")
        raise exception


def _check_migration_stats(migration_script, session_new):
    """
    Verify that every migrated table holds the number of entries it started from

    :param migration_script: The migration script of the step
    :param session_new: An ORM session on the database the step produced
    """
    log.info("Migration stats:")

    for model_name in _migrated_models(migration_script):
        expected = migration_script.entries_count[model_name]
        count = session_new.query(migration_script.model_to[model_name]).count()

        if expected == count:
            log.info(f" * {model_name} table migrated ({expected} entry(s))")
        elif migration_script.skip_count_check.get(model_name, False):
            log.info(f" * {model_name} table migrated (entries count changed from {expected} to {count})")
        else:
            raise AssertionError(f"Integrity check failed on count equality for table {model_name}: {count} != {expected}")


def perform_migration(version):
    """
    Utility function for performing a database migration
    :param version: The current version of the database to update
    """
    if version < FIRST_DATABASE_VERSION_SUPPORTED:
        log.info(f"Migrations from DB version lower than {FIRST_DATABASE_VERSION_SUPPORTED} are no longer supported!")
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
            log.info(f"Updating DB from version {version} to version {version + 1}")

            j = version - FIRST_DATABASE_VERSION_SUPPORTED

            engine = _migration_engine(version, j, new_db_file)

            if session_new:
                session_old = session_new

            session_new = sessionmaker(bind=engine)()

            # Here is instanced the migration script
            migration_module = importlib.import_module(f"globaleaks.db.migrations.update_{version + 1}")
            migration_script = migration_module.MigrationScript(migration_mapping, version, session_old, session_new)

            log.info("Migrating table:")

            try:
                _run_migration_script(migration_script)
            finally:
                # the database should be always closed before leaving the application
                # in order to not keep leaking journal files.
                migration_script.close()

            log.info("Migration completed with success.")

            _check_migration_stats(migration_script, session_new)

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
