# -*- coding: utf-8 -*-
from globaleaks import models
from globaleaks.models import config
from globaleaks.orm import transact
from globaleaks.tests import helpers


class TestModels(helpers.TestGL):
    initialize_test_database_using_archived_db = False

    def test_initialize_config(self):
        @transact
        def transaction(session):
            session.query(models.Config).filter(models.Config.tid == 1).delete()
            config.initialize_config(session, 1, {'mode': 'default'})

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
