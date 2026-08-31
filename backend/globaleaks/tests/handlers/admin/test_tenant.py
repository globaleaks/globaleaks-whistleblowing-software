
from twisted.internet.defer import inlineCallbacks

from globaleaks import models
from globaleaks.handlers.admin import tenant
from globaleaks.handlers.admin.user_profile import db_create_user_profile
from globaleaks.handlers.base import BaseHandler
from globaleaks.models import config
from globaleaks.models.config import ConfigFactory
from globaleaks.orm import transact, tw
from globaleaks.rest import errors
from globaleaks.tests import helpers


def get_dummy_tenant_desc(subdomain='subdomain'):
    return {
        'label': 'tenant-xxx',
        'active': True,
        'name': 'GlobaLeaks',
        'subdomain': subdomain,
        'profile': 'default'
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
        t['profile'] = 'default'
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
        return self.request(None, role='admin').delete(4)

    def test_delete_requires_confirmation(self):
        self.patch(BaseHandler, 'check_confirmation', BaseHandler.real_check_confirmation)

        return self.assertFailure(self.request(None, role='admin').delete(4), errors.InvalidAuthentication)

    @inlineCallbacks
    def test_delete_with_confirmation(self):
        self.patch(BaseHandler, 'check_confirmation', BaseHandler.real_check_confirmation)

        confirmation = helpers.VALID_CONFIRMATION

        handler = self.request(None, role='admin', headers={'x-confirmation': confirmation})

        yield handler.delete(4)

@transact
def db_compose_profile(session, tid):
    """
    Compose a profile as an administrator would: a channel, a questionnaire of
    """
    questionnaire = models.Questionnaire()
    questionnaire.tid = tid
    questionnaire.name = 'intake'
    session.add(questionnaire)
    session.flush()

    step = models.Step()
    step.questionnaire_id = questionnaire.id
    step.label = {'en': 'step'}
    step.order = 0
    session.add(step)

    context = models.Context()
    context.tid = tid
    context.name = {'en': 'Channel of the profile'}
    context.questionnaire_id = questionnaire.id
    context.tip_timetolive = 30
    session.add(context)
    session.flush()

    profile = db_create_user_profile(session, tid, {
        'name': 'Recipients of the profile',
        'role': 'receiver',
        'roles': ['receiver'],
        'contexts': [context.id],
        'permissions': {'can_send_communications': True}
    }, sync_users=False)

    return {'questionnaire_id': questionnaire.id,
            'context_id': context.id,
            'profile_id': profile['id']}


@transact
def db_declare_exchange_channel(session, tid):
    """
    Declare on an object a channel the exchanges run through
    """
    channel = models.Context()
    channel.tid = tid
    channel.exchange = True
    channel.name = {'en': 'Channel of the exchanges'}
    session.add(channel)
    session.flush()

    return channel.id


@transact
def db_read_profile(session, tid):
    contexts = session.query(models.Context) \
                      .filter(models.Context.tid == tid).all()

    profiles = session.query(models.UserProfile) \
                      .filter(models.UserProfile.tid == tid).all()

    return {
        'contexts': [{'id': c.id,
                      'name': c.name,
                      'exchange': c.exchange,
                      'questionnaire_id': c.questionnaire_id,
                      'tip_timetolive': c.tip_timetolive} for c in contexts],
        'questionnaires': [q.id for q in session.query(models.Questionnaire)
                                                .filter(models.Questionnaire.tid == tid)],
        'profiles': [{'id': p.id,
                      'name': p.name,
                      'contexts': sorted(p.contexts_list),
                      'permissions': sorted(p.permissions_list)} for p in profiles]
    }


class TestProfileExportAndImport(helpers.TestHandlerWithPopulatedDB):
    """
    A profile composed on a platform is carried into another one whole: its
    """
    _handler = tenant.TenantCollection

    @inlineCallbacks
    def setUp(self):
        yield helpers.TestHandlerWithPopulatedDB.setUp(self)

        profile = yield tenant.create(get_dummy_tenant_desc('exported'), is_profile=True)
        self.source_tid = profile['id']
        self.composed = yield db_compose_profile(self.source_tid)

    @inlineCallbacks
    def export(self):
        handler = self.request(role='admin')
        exported = yield tenant.get(handler, self.source_tid)
        return exported

    @inlineCallbacks
    def import_of(self, exported, subdomain='imported'):
        content = dict(exported)
        content['tenant'] = dict(exported['tenant'])
        content['tenant'].update(get_dummy_tenant_desc(subdomain))

        handler = self.request(content, role='admin')
        imported = yield handler.post()

        return imported

    @inlineCallbacks
    def test_a_profile_is_carried_whole(self):
        composed = yield db_read_profile(self.source_tid)

        exported = yield self.export()
        imported = yield self.import_of(exported)

        carried = yield db_read_profile(imported['id'])

        self.assertEqual([c['name'] for c in carried['contexts']],
                         [c['name'] for c in composed['contexts']])
        self.assertEqual([p['name'] for p in carried['profiles']],
                         [p['name'] for p in composed['profiles']])
        self.assertEqual([p['permissions'] for p in carried['profiles']],
                         [p['permissions'] for p in composed['profiles']])

    @inlineCallbacks
    def test_the_channels_named_by_a_profile_are_the_ones_it_carries(self):
        # A user profile names the channels its users receive on. What is
        # imported has to name the channels of the object it landed on, and
        # not the ones of the object it was composed on, or its users would be
        # carried to channels of somebody else
        exported = yield self.export()
        imported = yield self.import_of(exported)

        carried = yield db_read_profile(imported['id'])
        channels = [context['id'] for context in carried['contexts']]

        self.assertTrue(carried['profiles'])
        for profile in carried['profiles']:
            self.assertTrue(profile['contexts'])
            for context_id in profile['contexts']:
                self.assertIn(context_id, channels)

    @inlineCallbacks
    def test_what_relates_two_objects_is_not_carried(self):
        # The channel the exchanges run through belongs to the object and
        # travels with it; the exchange relates two objects and is established
        # again where the object is carried, so it must not be duplicated
        counterpart = yield tenant.create(get_dummy_tenant_desc('counterpart'),
                                          is_profile=True)
        yield db_declare_exchange_channel(self.source_tid)
        yield db_establish_exchange(self.source_tid, counterpart['id'])

        established = yield db_exchanges()

        exported = yield self.export()
        imported = yield self.import_of(exported)

        self.assertEqual(established, (yield db_exchanges()))

        carried = yield db_read_profile(imported['id'])
        self.assertTrue([c for c in carried['contexts'] if c['exchange']])


@transact
def db_establish_exchange(session, source_tid, target_tid):
    """
    Establish an exchange between two objects, as the platform would
    """
    exchange = models.Exchange()
    exchange.type = 'transmission'
    exchange.source = ConfigFactory(session, source_tid).get_val('uuid')
    exchange.target = ConfigFactory(session, target_tid).get_val('uuid')
    session.add(exchange)
    session.flush()

    return exchange.id


@transact
def db_exchanges(session):
    return [exchange.id for exchange in session.query(models.Exchange)]
