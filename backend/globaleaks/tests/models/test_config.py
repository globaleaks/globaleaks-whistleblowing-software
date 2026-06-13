import os
import re

import globaleaks
from globaleaks import models
from globaleaks.models import config
from globaleaks.models.config_desc import ConfigDescriptor
from globaleaks.orm import transact
from globaleaks.tests import helpers


class TestModels(helpers.TestGL):
    initialize_test_database_using_archived_db = False

    def test_threshold_config_references_are_consistent(self):
        # Every threshold_* knob declared in ConfigDescriptor must be read from
        # the tenant cache somewhere in the backend, and every threshold_*
        # attribute read from the cache must be declared. This catches typos in
        # cache attribute names (a wrong name would only fail at runtime when
        # the endpoint is hit) and configuration knobs left as dead code.
        declared = {k for k in ConfigDescriptor if k.startswith('threshold_')}

        referenced = set()
        pattern = re.compile(r'\.(threshold_[a-z0-9_]+)')
        root = os.path.dirname(globaleaks.__file__)
        for dirpath, _, filenames in os.walk(root):
            if 'tests' in dirpath.split(os.sep):
                continue
            for filename in filenames:
                if not filename.endswith('.py'):
                    continue
                with open(os.path.join(dirpath, filename), encoding='utf-8') as fd:
                    referenced.update(pattern.findall(fd.read()))

        self.assertEqual(referenced - declared, set(),
                         'threshold(s) read from cache but missing from ConfigDescriptor')
        self.assertEqual(declared - referenced, set(),
                         'threshold(s) declared in ConfigDescriptor but never read')

    def test_initialize_config(self):
        @transact
        def transaction(session):
            session.query(models.Config).filter(models.Config.tid == 1).delete()
            config.initialize_config(session, 1, 'default')

        return transaction()

    def test_config_update_defaults(self):
        @transact
        def transaction(session):
            # Rename 'name' variable with the effect of:
            # - simuulating missing variable
            # - simulating the presence of a variable not anymore defined
            session.query(models.Config).filter(models.Config.tid == 1, models.Config.var_name == u'name').one().var_name = u'removed'

            # Delete a variable that requires initialization via a constructor
            session.query(models.Config).filter(models.Config.tid == 1, models.Config.var_name == u'receipt_salt').delete()

            config.ConfigFactory(session, 1).update_defaults()

        return transaction()
