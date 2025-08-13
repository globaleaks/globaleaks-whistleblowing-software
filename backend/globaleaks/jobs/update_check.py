from pkg_resources import parse_version
from twisted.internet.defer import inlineCallbacks

from globaleaks import __version__
from globaleaks.handlers.admin.node import db_admin_serialize_node
from globaleaks.handlers.admin.notification import db_get_notification
from globaleaks.handlers.admin.user import db_get_users
from globaleaks.jobs.job import HourlyJob
from globaleaks.models.config import ConfigFactory
from globaleaks.orm import transact
from globaleaks.rest.cache import Cache
from globaleaks.utils.agent import get_page
from globaleaks.utils.log import log

DEB_PACKAGE_URL = b'https://deb.globaleaks.org/trixie/Packages'


import re

def get_latest_version(packages_file):
    # Split the Packages file into individual package entries
    package_entries = packages_file.split('\n\n')

    latest_version = ""

    for entry in package_entries:
        # Extract package name and version using regular expressions
        match_name = re.search(r'^Package: (.+)$', entry, re.MULTILINE)
        match_version = re.search(r'^Version: (.+)$', entry, re.MULTILINE)

        if match_name and match_version:
            package_name = match_name.group(1)
            package_version = parse_version(match_version.group(1))

            # Update the dictionary with the latest version for each package
            if not latest_version or package_version > latest_version:
                latest_version = package_version

    return str(latest_version)



@transact
def evaluate_update_notification(session, state, latest_version):
    priv_fact = ConfigFactory(session, 1)

    stored_latest = priv_fact.get_val('latest_version')

    # Check if the running version is lower than the latest version
    if parse_version(stored_latest) >= parse_version(latest_version):
        return

    Cache.invalidate()

    priv_fact.set_val('latest_version', latest_version)

    # Check to reduce number of email notifications of new updates
    if parse_version(__version__) != parse_version(stored_latest):
        return

    for user_desc in db_get_users(session, 1, 'admin'):
        if not user_desc['notification']:
            continue

        lang = user_desc['language']
        template_vars = {
            'type': 'software_update_available',
            'latest_version': latest_version,
            'node': db_admin_serialize_node(session, 1, lang),
            'notification': db_get_notification(session, 1, lang),
            'user': user_desc,
        }

        state.format_and_send_mail(session, 1, user_desc['mail_address'], template_vars)


class UpdateCheck(HourlyJob):
    interval = 60*60*24

    def fetch_packages_file(self):
        return get_page(self.state.get_agent(), DEB_PACKAGE_URL)

    @inlineCallbacks
    def operation(self):
        try:
            log.debug('Fetching latest GlobaLeaks version from repository')
            packages_file = yield self.fetch_packages_file()
            latest_version = get_latest_version(packages_file.decode())

            if not self.state.tenants[1].cache.notification.enable_notification_emails_admin:
                yield evaluate_update_notification(self.state, latest_version)

            log.debug('The newest version in the repository is: %s', latest_version)
        except:
            pass
