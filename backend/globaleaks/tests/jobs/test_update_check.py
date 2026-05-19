from twisted.internet.defer import inlineCallbacks, succeed

from globaleaks import __version__, models
from globaleaks.jobs.update_check import UpdateCheck
from globaleaks.models import config
from globaleaks.orm import tw
from globaleaks.state import State
from globaleaks.tests import helpers

packages = b"Package: globaleaks\n" \
           b"Version: 0.0.1\n" \
           b"Filename: trixie/globaleaks_0.0.1_all.deb\n\n" \
           b"Package: globaleaks\n" \
           b"Version: 1.0.0\n" \
           b"Filename: trixie/globaleaks_1.0.0_all.deb\n\n" \
           b"Package: globaleaks\n" \
           b"Version: 6.6.6\n" \
           b"Filename: trixie/globaleaks_6.6.6_all.deb\n\n"


class TestUpdateCheck(helpers.TestGLWithPopulatedDB):
    @inlineCallbacks
    def test_refresh_works(self):
        State.tenants[1].cache.anonymize_outgoing_connections = False

        yield tw(config.db_set_config_variable, 1, 'latest_version', __version__)
        yield self.test_model_count(models.Mail, 0)

        def fetch_packages_file_mock(self):
            return succeed(packages)

        UpdateCheck.fetch_packages_file = fetch_packages_file_mock

        yield UpdateCheck().operation()

        latest_version = yield tw(config.db_get_config_variable, 1, 'latest_version')
        self.assertEqual(latest_version, '6.6.6')
        yield self.test_model_count(models.Mail, 1)
