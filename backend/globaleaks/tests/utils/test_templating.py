from twisted.internet.defer import inlineCallbacks
from twisted.trial import unittest
from globaleaks.handlers import admin, public, recipient, user
from globaleaks.jobs.delivery import Delivery
from globaleaks.orm import tw
from globaleaks.tests import helpers
from globaleaks.utils.objectdict import ObjectDict
from globaleaks.utils.templating import Templating, mail_uses_smtp2, supported_template_types


class notifTemplateTest(helpers.TestGLWithPopulatedDB):
    @inlineCallbacks
    def test_keywords_conversion(self):
        tip_id = ''

        yield self.perform_full_submission_actions()
        yield Delivery().run()

        data = {}
        data['type'] = 'tip'
        data['user'] = yield user.get_user(1, self.dummyReceiver_1['id'], 'en')
        data['context'] = yield admin.context.get_context(1, self.dummyContext['id'], 'en')
        data['notification'] = yield tw(admin.notification.db_get_notification, 1, 'en')
        data['node'] = yield tw(admin.node.db_admin_serialize_node, 1, 'en')
        data['submission_statuses'] = yield tw(public.db_get_submission_statuses, 1, 'en')

        for tip in self.dummyRTips:
            if tip['receiver_id'] == self.dummyReceiver_1['id']:
                tip_id = tip['id']
                break

        data['tip'], _ = yield recipient.rtip.get_rtip(1, self.dummyReceiver_1['id'], tip_id, 'en')

        data['comments'] = data['tip']['comments']

        for key in ['tip', 'comment', 'file']:
            if key == 'tip':
                data['type'] = 'tip'
            else:
                data['type'] = 'tip_update'

            template = ''.join(supported_template_types[data['type']].keyword_list)
            Templating().format_template(template, data)


class TestSecondarySmtpRouting(unittest.TestCase):
    """
    A site may deliver some of its mail through a second server: the ones whose
    """
    def routing(self, **kwargs):
        notification = {'smtp2_enabled': False, 'smtp2_template_types': []}
        notification.update(kwargs)

        return notification

    def test_the_second_server_carries_the_types_it_was_given(self):
        cases = [
            ("enabled, and the type is among the chosen ones",
             {'smtp2_enabled': True, 'smtp2_template_types': ['tip', 'comment']}, 'tip', True),
            ("enabled, and the type is not among them",
             {'smtp2_enabled': True, 'smtp2_template_types': ['comment']}, 'tip', False),
            ("enabled, and nothing has been chosen",
             {'smtp2_enabled': True, 'smtp2_template_types': []}, 'tip', False),
            ("disabled, whatever has been chosen",
             {'smtp2_enabled': False, 'smtp2_template_types': ['tip']}, 'tip', False),
            ("configured with nothing at all",
             {}, 'tip', False)
        ]

        for reason, configuration, mail_type, expected in cases:
            self.assertEqual(
                mail_uses_smtp2(self.routing(**configuration), mail_type),
                expected,
                "with the second server {}, a {} mail {} routed to it".format(reason, mail_type, "is not" if expected else "is"))

    def test_the_configuration_is_read_the_same_from_the_cache_of_a_site(self):
        # The configuration reaches this function either as the serialized
        # notification or as the cache of the tenant: the two are read alike
        cached = ObjectDict({'smtp2_enabled': True, 'smtp2_template_types': ['tip']})

        self.assertTrue(mail_uses_smtp2(cached, 'tip'))
        self.assertFalse(mail_uses_smtp2(cached, 'comment'))
