import os

from datetime import datetime, timezone

from tempfile import TemporaryDirectory

from gnupg import GPG

from globaleaks.rest import errors
from globaleaks.utils.log import log


class PGPContext:
    def __init__(self, key):
        """
        :param key: The PGP key to be loaded
        """
        self.fingerprint = ''
        self.expiration = datetime.fromtimestamp(0, timezone.utc).replace(tzinfo=None)

        self.tempdir = TemporaryDirectory()

        try:
            self.gnupg = GPG(gnupghome=self.tempdir.name, options=['--trust-model', 'always'])
            self.gnupg.encoding = "UTF-8"
        except Exception as excep:
            log.err("Unable to instance GnuPGP: %s" % excep)
            raise

        try:
            import_result = self.gnupg.import_keys(key)

            if not import_result.fingerprints:
                raise errors.InputValidationError

            self.fingerprint = import_result.fingerprints[0]

            # looking if the key is effectively reachable
            all_keys = self.gnupg.list_keys()

            for k in all_keys:
                if k['fingerprint'] == self.fingerprint:
                    if k['expires']:
                        self.expiration = datetime.fromtimestamp(int(k['expires']), timezone.utc).replace(tzinfo=None)
                    break

        except Exception as excep:
            log.err("Error in PGP import_keys: %s", excep)
            raise errors.InputValidationError

    def encrypt_file(self, input_file, output_path):
        """
        Encrypt a file with the specified PGP key
        """
        encrypted_obj = self.gnupg.encrypt_file(input_file, self.fingerprint, output=output_path)

        if not encrypted_obj.ok:
            raise errors.InputValidationError

        return encrypted_obj, os.stat(output_path).st_size

    def encrypt_message(self, plaintext):
        """
        Encrypt a text message with the specified key
        """
        encrypted_obj = self.gnupg.encrypt(plaintext, self.fingerprint)

        if not encrypted_obj.ok:
            raise errors.InputValidationError

        return str(encrypted_obj)
