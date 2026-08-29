
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
    its own and a user profile carrying its users to the channel
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
        'permissions': {'can_forward_reports': True}
    }, sync_users=False)

    return {'questionnaire_id': questionnaire.id,
            'context_id': context.id,
            'profile_id': profile['id']}


@transact
def db_read_profile(session, tid):
    contexts = session.query(models.Context) \
                      .filter(models.Context.tid == tid).all()

    profiles = session.query(models.UserProfile) \
                      .filter(models.UserProfile.tid == tid).all()

    return {
        'contexts': [{'id': c.id,
                      'name': c.name,
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
    variables, its questionnaires, its channels and the user profiles that
    name them.
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
    def test_the_profile_is_carried_whole(self):
        exported = yield self.export()

        self.assertEqual([c['id'] for c in exported['contexts']],
                         [self.composed['context_id']])

        imported = yield self.import_of(exported)
        content = yield db_read_profile(imported['id'])

        # the channel is carried with what composes its reports and how long
        # they last, and the questionnaire it names is the one imported
        self.assertEqual(len(content['contexts']), 1)
        channel = content['contexts'][0]
        self.assertEqual(channel['name']['en'], 'Channel of the profile')
        self.assertEqual(channel['tip_timetolive'], 30)
        self.assertIn(channel['questionnaire_id'], content['questionnaires'])
        self.assertNotEqual(channel['questionnaire_id'],
                            self.composed['questionnaire_id'])

        # the user profile is carried with the roles it holds, the permissions
        # it grants and the channels its users are the recipients of
        self.assertEqual(len(content['profiles']), 1)
        profile = content['profiles'][0]
        self.assertEqual(profile['contexts'], [channel['id']])
        self.assertIn('can_forward_reports', profile['permissions'])
