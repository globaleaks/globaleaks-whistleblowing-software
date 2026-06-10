from twisted.internet.defer import inlineCallbacks

from globaleaks.handlers.admin import tenant
from globaleaks.models import config
from globaleaks.orm import tw
from globaleaks.rest import errors
from globaleaks.tests import helpers


def get_dummy_tenant_desc(subdomain='subdomain'):
    return {
        'label': 'tenant-xxx',
        'active': True,
        'name': 'GlobaLeaks',
        'mode': 'default',
        'subdomain': subdomain,
    }


class TestTenantCollection(helpers.TestHandlerWithPopulatedDB):
    _handler = tenant.TenantCollection

    @inlineCallbacks
    def test_get(self):
        n = 3

        for i in range(n):
            yield tenant.create(get_dummy_tenant_desc('subdomain-%d' % i))

        handler = self.request(role='admin')
        response = yield handler.get()

        self.assertEqual(len(response), self.population_of_tenants + n)

    @inlineCallbacks
    def test_post(self):
        r = {}
        for i in range(0, 3):
            handler = self.request(get_dummy_tenant_desc('subdomain-%d' % i), role='admin')
            t = yield handler.post()
            r[i] = yield tw(config.db_get_config_variable, t['id'], 'receipt_salt')

        # Checks that the salt is actually modified from create to another
        self.assertNotEqual(r[0], r[1])
        self.assertNotEqual(r[1], r[2])
        self.assertNotEqual(r[2], r[0])

    @inlineCallbacks
    def test_post_rejects_duplicate_subdomain(self):
        # Tenant 2 already owns the subdomain 'tenant-2'
        handler = self.request(get_dummy_tenant_desc('tenant-2'), role='admin')
        yield self.assertFailure(handler.post(), errors.ForbiddenOperation)

    @inlineCallbacks
    def test_post_rejects_subdomain_colliding_with_hostname(self):
        # A hostname starting with the requested label blocks the subdomain
        yield tw(config.db_set_config_variable, 2, 'hostname', 'pippo.example.org')

        handler = self.request(get_dummy_tenant_desc('pippo'), role='admin')
        yield self.assertFailure(handler.post(), errors.ForbiddenOperation)


class TestTenantInstance(helpers.TestHandlerWithPopulatedDB):
    _handler = tenant.TenantInstance

    @inlineCallbacks
    def setUp(self):
        yield helpers.TestHandlerWithPopulatedDB.setUp(self)
        t = yield tenant.create(get_dummy_tenant_desc())
        self.handler = self.request(t, role='admin')

    def test_get(self):
        return self.handler.get(4)

    def test_put(self):
        return self.handler.put(4)

    @inlineCallbacks
    def test_put_rejects_duplicate_subdomain(self):
        # Tenant 4 must not be able to take the subdomain owned by tenant 2
        handler = self.request(get_dummy_tenant_desc('tenant-2'), role='admin')
        yield self.assertFailure(handler.put(4), errors.ForbiddenOperation)

    def test_delete(self):
        return self.handler.delete(4)
