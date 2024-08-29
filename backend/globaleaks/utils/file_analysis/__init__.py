import aiohttp
import requests
import json

from globaleaks.models import EnumStateFile
from globaleaks.utils.file_analysis.ScanResponse import ScanResponse
from globaleaks.utils.log import log


class FileAnalysis:
    def __init__(self, url='https://93d4-79-33-219-117.ngrok-free.app/api/v1/scan'):
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











