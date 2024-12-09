import logging
from twisted.internet import abstract
from globaleaks.models import EnumStateFile
from globaleaks.rest import errors
import pyclamd


class FileAnalysis:
    def __init__(self, host='localhost', port=3310):
        self._host = host
        self._port = port

    def _scan_file(self, file_name: str, data_bytes: bytes) -> EnumStateFile:
        logging.info(file_name)
        try: 
            cd = pyclamd.ClamdNetworkSocket(self._host, int(self._port))
            result = cd.scan_stream(data_bytes)
            
            if result:
                return EnumStateFile.infected
            
            return EnumStateFile.verified
        except Exception as e:
            logging.error(e)
            return EnumStateFile.pending

    def wrap_scanning(self, file_name: str, data_bytes: bytes, antivirus_enabled:bool=True) -> EnumStateFile:
        if not antivirus_enabled:
            return EnumStateFile.pending
        
        return self._scan_file(
            file_name=file_name,
            data_bytes=data_bytes
        )

    def read_file_for_scanning(self, fp, file_name, state, antivirus_enabled: bool = True):
        status_file = EnumStateFile.verified
        if state == EnumStateFile.infected.name:
            raise errors.FileInfectedDownloadPermissionDenied
        if state == EnumStateFile.verified.name:
            return status_file
        chunk = fp.read(abstract.FileDescriptor.bufferSize)
        while chunk:
            status_file = self.wrap_scanning(
                file_name=file_name,
                data_bytes=chunk,
                antivirus_enabled=antivirus_enabled
            )
            if status_file == EnumStateFile.pending:
                raise errors.FilePendingDownloadPermissionDenied
            if status_file == EnumStateFile.infected:
                raise errors.FileInfectedDownloadPermissionDenied
            chunk = fp.read(abstract.FileDescriptor.bufferSize)
        return status_file












