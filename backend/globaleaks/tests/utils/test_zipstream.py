import os

from io import BytesIO
from twisted.internet.defer import inlineCallbacks
from twisted.web.test.requesthelper import DummyRequest
from zipfile import ZipFile

from globaleaks.tests import helpers
from globaleaks.utils.zipstream import ZipStream, ZipStreamProducer

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

    def test_zipstreamproducer_streams_complete_archive(self):
        # Content larger than a single producer chunk forces multiple
        # resumeProducing() iterations. A non-persistent iterator would create
        # a fresh generator on each call, restarting from the first file and
        # never terminating; this asserts the producer streams each file
        # exactly once and yields a complete, valid archive.
        payload = b'A' * (256 * 1024)
        files = [
            {'name': 'a.bin', 'fo': BytesIO(payload)},
            {'name': 'b.bin', 'fo': BytesIO(payload)},
        ]

        request = DummyRequest([b''])

        class FakeHandler:
            pass

        handler = FakeHandler()
        handler.request = request

        # DummyRequest.registerProducer drives resumeProducing() to completion.
        ZipStreamProducer(handler, ZipStream(files)).start()

        body = b''.join(request.written)

        with ZipFile(BytesIO(body), 'r') as f:
            self.assertIsNone(f.testzip())
            self.assertEqual(sorted(f.namelist()), ['a.bin', 'b.bin'])
            for ff in f.infolist():
                self.assertEqual(ff.file_size, len(payload))
