from globaleaks.utils.file_analysis.ScanData import ScanData


class ScanResponse:
    def __init__(self, success, data):
        self.success = success
        self.data = data

    @classmethod
    def from_dict(cls, data):
        return cls(
            success=data.get('success'),
            data=ScanData.from_dict(data.get('data', {}))
        )