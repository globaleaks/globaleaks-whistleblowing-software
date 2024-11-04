# -*- coding: utf-8 -*-
import logging
import os
from urllib.parse import parse_qs
from globaleaks.handlers.base import BaseHandler
from globaleaks.utils.crypto import GCE
class Secret(BaseHandler):
    check_roles = 'any'
    def post(self):
        try:
            with open(os.path.join(self.state.settings.working_path, "secret_key_hash.txt"), "r") as f:
                secret_key_hash, salt = f.read().split(':', 1)
            data = parse_qs(self.request.content.read())
            secret_key = data[b'secret'][0]
            if GCE.hash_password(secret_key, salt) == secret_key_hash:
                self.state.secret_key = secret_key
        except Exception as e:
            logging.debug(e)