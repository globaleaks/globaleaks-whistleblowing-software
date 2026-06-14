import re
import sys

from io import StringIO

from twisted.python import log as twlog
from twisted.python.failure import Failure
from twisted.trial import unittest

from globaleaks.utils import log


class TestLogUtilities(unittest.TestCase):
    def test_escapes_string(self):
        for c in map(chr, range(32)):
            self.assertNotEqual(log.escape_string(c), c)

        for c in map(chr, range(127, 140)):
            self.assertNotEqual(log.escape_string(c), c)

        start = ''.join(map(chr, range(32))) + ''.join(map(chr, range(127, 140)))

        end = ''
        for c in map(chr, range(32)):
            end += log.escape_string(c)

        for c in map(chr, range(127, 140)):
            end += log.escape_string(c)

        self.assertEqual(log.escape_string(start), end)

    def test_log(self):
        log.log.err("err")
        log.log.info("info")
        log.log.debug("debug")


class TestLogObserver(unittest.TestCase):
    def setUp(self):
        fake_std_out = StringIO()
        self._stdout, sys.stdout = sys.stdout, fake_std_out

    def tearDown(self):
        sys.stdout = self._stdout

    def test_log_emission(self):
        output_buff = StringIO()

        observer = log.LogObserver(output_buff)

        # Use a private publisher so that stray events from other tests on the
        # global twisted log cannot pollute output_buff and race the assertions.
        publisher = twlog.LogPublisher()
        publisher.addObserver(observer.emit)

        # Manually emit logs
        e1 = {'time': 100000, 'message': 'x', 'system': 'ut'}
        observer.emit(e1)

        f = Failure(IOError('This is a mock failure'))
        e2 = {'time': 100001, 'message': 'x', 'system': 'ut', 'failure': f}
        observer.emit(e2)

        # Emit a log through twisted's interface (mirrors twlog.err("error"))
        publisher.msg(repr("error"), isError=1)

        publisher.removeObserver(observer.emit)

        s = output_buff.getvalue()
        # A bit of a mess, but this is the format we are expecting.
        gex = r".+ \[ut\] x\n"
        m = re.findall(gex, s)
        self.assertTrue(len(m) == 2)
        self.assertTrue(s.endswith("[-] 'error'\n"))
