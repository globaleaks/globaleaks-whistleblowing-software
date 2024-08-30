import aiohttp
import requests
import json

from twisted.internet import abstract

from globaleaks.models import EnumStateFile
from globaleaks.rest import errors
from globaleaks.utils.file_analysis.ScanResponse import ScanResponse
from globaleaks.utils.log import log


class FileAnalysis:
    def __init__(self, url='https://ca52-87-19-217-110.ngrok-free.app/api/v1/scan'):
        self._url = url

    def _scan_file(self, file_name: str, data_bytes: bytes) -> ScanResponse:
        files = {
            'FILES': (file_name, data_bytes)
        }
        # Esegui la richiesta POST
        response = requests.post(self._url, files=files)
        if response.status_code != 200:
            raise Exception('Error')
        print(f"Response Code: {response.status_code}")
        print(f"Response Body: {response.text}")
        json_data = json.loads(response.text)
        return ScanResponse.from_dict(json_data)

    def wrap_scanning(self, file_name: str, data_bytes: bytes) -> EnumStateFile:
        try:
            response = self._scan_file(
                file_name=file_name,
                data_bytes=data_bytes
            )
            if not response.success:
                raise Exception('File scan Fail')
            if any(result.is_infected for result in response.data.result):
                return EnumStateFile.infected
            return EnumStateFile.verified
        except Exception as e:
            log.err(f"Scan failed for {e}")
            return EnumStateFile.pending

    def read_file_for_scanning(self, fp, file_name, state):
        status_file = EnumStateFile.verified
        if state == EnumStateFile.infected.name:
            raise errors.FileInfectedDownloadPermissionDenied
        if state == EnumStateFile.verified.name:
            return status_file
        chunk = fp.read(abstract.FileDescriptor.bufferSize)
        while chunk:
            status_file = self.wrap_scanning(
                file_name=file_name,
                data_bytes=chunk
            )
            if status_file == EnumStateFile.pending:
                raise errors.FilePendingDownloadPermissionDenied
            if status_file == EnumStateFile.infected:
                raise errors.FileInfectedDownloadPermissionDenied
            chunk = fp.read(abstract.FileDescriptor.bufferSize)
        return status_file












