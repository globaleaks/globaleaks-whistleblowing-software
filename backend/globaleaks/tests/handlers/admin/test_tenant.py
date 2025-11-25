from twisted.internet.defer import inlineCallbacks

from globaleaks.handlers.admin import tenant
from globaleaks.models import config
from globaleaks.orm import tw
from globaleaks.rest import errors
from globaleaks.tests import helpers


def get_dummy_tenant_desc():
    return {
        'label': 'tenant-xxx',
        'active': True,
        'name': 'GlobaLeaks',
        'mode': 'default',
        'subdomain': 'subdomain',
        'profile': 'default'
    }


class TestTenantCollection(helpers.TestHandlerWithPopulatedDB):
    _handler = tenant.TenantCollection

    @inlineCallbacks
    def test_get(self):
        n = 3

        for i in range(n):
            yield tenant.create(get_dummy_tenant_desc())

        handler = self.request(role='admin')
        response = yield handler.get()

        self.assertEqual(len(response), self.population_of_tenants + n)

    @inlineCallbacks
    def test_post(self):
        r = {}
        for i in range(0, 3):
            handler = self.request(get_dummy_tenant_desc(), role='admin')
            t = yield handler.post()
            r[i] = yield tw(config.db_get_config_variable, t['id'], 'receipt_salt')

        # Checks that the salt is actually modified from create to another
        self.assertNotEqual(r[0], r[1])
        self.assertNotEqual(r[1], r[2])
        self.assertNotEqual(r[2], r[0])


class TestTenantInstance(helpers.TestHandlerWithPopulatedDB):
    _handler = tenant.TenantInstance

    @inlineCallbacks
    def setUp(self):
        yield helpers.TestHandlerWithPopulatedDB.setUp(self)
        t = yield tenant.create(get_dummy_tenant_desc())
        t['profile'] = 'default'
        self.tenant_id = t['id']
        self.handler = self.request(t, role='admin')

    def test_get(self):
        return self.handler.get(self.tenant_id)

    def test_put(self):
        return self.handler.put(self.tenant_id)

    @inlineCallbacks
    def test_delete(self):
        yield self.handler.delete(self.tenant_id)

    @inlineCallbacks
    def test_delete_with_valid_stats(self):
        """Test deletion succeeds when expected stats match current stats"""
        # Get current stats
        stats = yield tenant.get_tenant_stats(self.tenant_id)

        # Create handler with expected stats as query params
        handler = self.request({}, role='admin')
        handler.request.args[b'expected_open'] = [str(stats['open_reports']).encode()]
        handler.request.args[b'expected_total'] = [str(stats['total_reports']).encode()]

        yield handler.delete(self.tenant_id)

    @inlineCallbacks
    def test_delete_with_mismatched_stats(self):
        """Test deletion fails when expected stats don't match current stats"""
        # Create handler with wrong expected stats
        handler = self.request({}, role='admin')
        handler.request.args[b'expected_open'] = [b'999']
        handler.request.args[b'expected_total'] = [b'999']

        yield self.assertFailure(handler.delete(self.tenant_id), errors.TenantStatsChanged)


class TestTenantStats(helpers.TestHandlerWithPopulatedDB):
    _handler = tenant.TenantStats

    @inlineCallbacks
    def setUp(self):
        yield helpers.TestHandlerWithPopulatedDB.setUp(self)
        t = yield tenant.create(get_dummy_tenant_desc())
        self.tenant_id = t['id']

    @inlineCallbacks
    def test_get(self):
        """Test retrieving tenant stats"""
        handler = self.request(role='admin')
        response = yield handler.get(self.tenant_id)

        self.assertIn('open_reports', response)
        self.assertIn('total_reports', response)
        self.assertIsInstance(response['open_reports'], int)
        self.assertIsInstance(response['total_reports'], int)
        self.assertGreaterEqual(response['total_reports'], response['open_reports'])
