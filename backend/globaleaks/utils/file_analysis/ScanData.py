from globaleaks.utils.file_analysis.VirusScanResult import VirusScanResult


class ScanData:
    def __init__(self, result):
        self.result = result

    @classmethod
    def from_dict(cls, data):
        result_list = [VirusScanResult.from_dict(item) for item in data.get('result', [])]
        return cls(result=result_list)
