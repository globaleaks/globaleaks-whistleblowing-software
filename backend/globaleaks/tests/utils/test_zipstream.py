import os

from io import BytesIO
from twisted.internet.defer import inlineCallbacks
from zipfile import ZipFile

from globaleaks.tests import helpers
from globaleaks.utils.zipstream import ZipStream

_THIS_FILE = os.path.abspath(__file__)


class TestZipStream(helpers.TestGL):
    @inlineCallbacks
    def setUp(self):
        yield helpers.TestGL.setUp(self)

        self.unicode_seq = ''.join(chr(x) for x in range(0x400, 0x40A))

        self.files = [
          {'name': _THIS_FILE, 'fo': open(_THIS_FILE, 'rb')},  # noqa: SIM115 - handle consumed by the zipstream fixture
          {'name': _THIS_FILE, 'path': _THIS_FILE},
          {'name': self.unicode_seq, 'fo': BytesIO(self.unicode_seq.encode())}
        ]

    def test_zipstream(self):
        output = BytesIO()

        for data in ZipStream(self.files):
            output.write(data)

        with ZipFile(output, 'r') as f:
            self.assertIsNone(f.testzip())

        with ZipFile(output, 'r') as f:
            infolist = f.infolist()
            self.assertTrue(len(infolist), 2)
            for ff in infolist:
                if ff.filename == self.unicode_seq:
                    self.assertTrue(ff.file_size == len(self.unicode_seq.encode()))
                else:
                    self.assertTrue(ff.file_size == os.stat(_THIS_FILE).st_size)
