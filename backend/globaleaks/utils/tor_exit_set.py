import re

from globaleaks.utils.agent import get_page


EXIT_ADDR_URL = b'https://deb.globaleaks.org/app/exit-addresses'


class TorExitSet(set):
    """Set that keep the list of Tor exit nodes ip using check.torproject.org"""

    def process_data(self, data):
        self.clear()

        for ip in re.findall(r'ExitAddress ([^ ]*) ', data.decode()):
            self.add(ip)

    def update(self, agent):
        return get_page(agent, EXIT_ADDR_URL).addCallback(self.process_data)
