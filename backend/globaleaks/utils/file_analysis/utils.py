import logging
from datetime import datetime

from globaleaks import models
from globaleaks.models import EnumStateFile
from globaleaks.orm import transact


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
        except Exception as e:
            logging.debug(f"Unexpected error updating {model.__name__} with id {file_id}: {e}")
            session.rollback()
        return False

    # Prova con InternalFile e ReceiverFile
    if process_file(models.InternalFile):
        return True
    return process_file(models.ReceiverFile)