import os
import sqlalchemy
from sqlalchemy import text
from twisted.internet.defer import inlineCallbacks

from globaleaks.models import Tenant
from globaleaks.orm import get_engine, get_session, transact
from globaleaks.settings import Settings
from globaleaks.tests import helpers


class TestORM(helpers.TestGL):
    initialize_test_database_using_archived_db = False

    @transact
    def _transact_with_success(self, session):
        self.db_add_config(session)

    @transact
    def _transact_with_exception(self, session):
        self.db_add_config(session)
        raise Exception("antani")

    def db_add_config(self, session):
        session.add(Tenant())

    @inlineCallbacks
    def test_transact_with_stuff(self):
        yield self._transact_with_success()

        # now check data actually written
        session = get_session()
        self.assertEqual(session.query(Tenant).count(), 2)

    @inlineCallbacks
    def test_transaction_with_exception(self):
        session = get_session()
        count1 = session.query(Tenant).count()

        yield self.assertFailure(self._transact_with_exception(), Exception)

        count2 = session.query(Tenant).count()

        self.assertEqual(count1, count2)

    def test_transact_decorate_function(self):
        @transact
        def transaction(session):
            self.assertTrue(getattr(session, 'query'))

        return transaction()

    @inlineCallbacks
    def test_authorizer_callback_denied(self):
        session = get_session()

        # Denied operation, such as DROP TABLE (we expect an exception)
        yield self.assertRaises(sqlalchemy.exc.DatabaseError, session.execute, sqlalchemy.text("DROP TABLE Tenant"))

    def test_do_connect_pragmas_values(self):
        # Create an engine with foreign_keys=True and orm_lockdown=False
        dstpath = os.path.join(Settings.working_path, 'globaleaks.db')
        engine = get_engine(db_uri="sqlite:////" + dstpath, foreign_keys=True, orm_lockdown=False)

        # Connect to the database
        with engine.connect() as conn:
            # Check that PRAGMA settings are applied with correct values
            result = conn.execute(text("PRAGMA temp_store")).fetchone()
            self.assertEqual(result[0], 2)  # MEMORY = 2

            result = conn.execute(text("PRAGMA trusted_schema")).fetchone()
            self.assertEqual(result[0], 0)  # OFF = 0

            # Check that foreign_keys is enabled
            result = conn.execute(text("PRAGMA foreign_keys")).fetchone()
            self.assertEqual(result[0], 1)  # ON = 1
