import logging
from datetime import datetime

from sqlalchemy.exc import NoResultFound

from globaleaks import models
from globaleaks.models import EnumStateFile
from globaleaks.models.config import ConfigFactory
from globaleaks.orm import transact
from globaleaks.rest import errors
from globaleaks.utils.file_analysis import FileAnalysis


@transact
def save_status_file_scanning(session, file_id: str, status_file: EnumStateFile) -> bool:
    def update_file_state(file_obj):
        file_obj.state = status_file.name
        if status_file != EnumStateFile.pending:
            file_obj.verification_date = datetime.now()

    def process_file(model):
        try:
            # Tenta di aggiornare il file del modello passato
            file_obj = session.query(model).filter(model.id == file_id).one()
            update_file_state(file_obj)
            session.commit()
            return True
        except NoResultFound as e:
            logging.debug(e)
        except Exception as e:
            logging.debug(f"Unexpected error updating {model.__name__} with id {file_id}: {e}")
            session.rollback()
        return False

    # Prova con InternalFile e ReceiverFile
    if process_file(models.InternalFile):
        return True
    return process_file(models.ReceiverFile)


@transact
def is_download(session, file_location, name, state, can_download_infected, ifile):
    antivirus_enabled = ConfigFactory(session, 1).get_val('antivirus_enabled')
    if not antivirus_enabled:
        return EnumStateFile.pending, True
    antivirus_clamd_ip = ConfigFactory(session, 1).get_val('antivirus_clamd_ip')
    antivirus_clamd_port = ConfigFactory(session, 1).get_val('antivirus_clamd_port')
    af = FileAnalysis(host=antivirus_clamd_ip, port=antivirus_clamd_port)
    try:
        status = af.read_file_for_scanning(file_location, name, state, antivirus_enabled)
    except (errors.FilePendingDownloadPermissionDenied, errors.FileInfectedDownloadPermissionDenied) as e_p:
        logging.debug(e_p)
        status = EnumStateFile.pending if isinstance(
            e_p, errors.FilePendingDownloadPermissionDenied) else EnumStateFile.infected
        if can_download_infected:
            save_status_file_scanning(ifile, status)
            return status, True
        return status, False
    except Exception as e:
        logging.debug(e)
        status = EnumStateFile.pending
        if can_download_infected:
            return status, True
        return status, False
    if not (status.value == state or status.name == state):
        save_status_file_scanning(ifile, status)
    return status, True

@transact
def is_exportable(session, files: list, user_id: str) -> bool:
    """
    Check if the report is exportable based on file statuses and user permissions.

    Args:
        session: Database session object.
        files (list): List of file dictionaries containing 'status' keys.
        user_id (str): ID of the user performing the check.

    Returns:
        bool: True if the report is exportable, False otherwise.
    """
    # Fetch user and configuration settings
    user = session.query(models.User).get(user_id)
    antivirus_enabled = ConfigFactory(session, 1).get_val('antivirus_enabled')

    # Check conditions
    if antivirus_enabled and any(file.get('status', '').upper() == EnumStateFile.pending.name.upper() for file in files):
        return False

    if not user.can_download_infected and any(file.get('status', '').upper() != EnumStateFile.infected.name.upper() for file in files):
        return False

    return True