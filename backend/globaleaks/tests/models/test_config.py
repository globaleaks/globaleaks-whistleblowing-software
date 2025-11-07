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
