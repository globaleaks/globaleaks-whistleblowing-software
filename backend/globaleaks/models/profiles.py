import os

from globaleaks.models.config import ConfigFactory
from globaleaks.settings import Settings
from globaleaks.utils.fs import read_json_file


def load_profile(session, tid, name):
    """
    Transaction for loading a configuration profile

    :param session: An ORM session
    :param tid: The tenant id of the tenant to be configured
    :param name: The name of the profile to be used
    """
    if not name or not all(c.isalnum() or c in ('_', '-') for c in name):
        raise ValueError('Invalid profile name')

    profiles_dir = os.path.abspath(os.path.join(Settings.client_path, 'data/profiles'))
    path = os.path.abspath(os.path.join(profiles_dir, '{}.json'.format(name)))

    if os.path.commonpath([profiles_dir, path]) != profiles_dir:
        raise ValueError('Invalid profile name')

    prof = read_json_file(path)

    ConfigFactory(session, tid).update('node', prof['node'])
