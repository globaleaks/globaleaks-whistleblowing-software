import json

from nacl.encoding import Base64Encoder
from sqlalchemy import func
from twisted.internet.defer import inlineCallbacks
from twisted.trial import unittest

from globaleaks import models
from globaleaks.handlers.admin.node import db_admin_serialize_node, db_update_node
from globaleaks.handlers.recipient import forward
from globaleaks.handlers.recipient.rtip import create_comment as rtip_create_comment, \
                                               create_redaction, db_access_rfile, \
                                               db_forward_receipt_is_valid, db_get_rtip, \
                                               db_revoke_tip_access, delete_rtip, postpone_expiration, \
                                               register_rfile_on_db, set_internaltip_variable, \
                                               set_reminder, update_tip_submission_status
from globaleaks.models import serializers
from globaleaks.handlers.recipient.forward import db_accepts_forward, \
                                                  db_can_forward_report, \
                                                  db_can_request_forward, \
                                                  db_get_designated_channel, \
                                                  db_get_authorized_forward_request, \
                                                  db_get_forward_receivers
from globaleaks.handlers.recipient.export import get_tip_export
from globaleaks.jobs.notification import MailGenerator
from globaleaks.handlers.whistleblower import wbtip
from globaleaks.models.config import ConfigFactory, db_get_forward_channel_ids, db_set_config_variable
from globaleaks.orm import transact
from globaleaks.rest import errors
from globaleaks.state import State
from globaleaks.tests import helpers
from globaleaks.utils.crypto import GCE
from globaleaks.utils.objectdict import ObjectDict
from globaleaks.utils.utility import datetime_never, datetime_now, uuid4


@transact
def designate_forward_channel(session, receiver_ids, select_all_receivers):
    context = session.query(models.Context).filter(models.Context.tid == 1).first()
    context.select_all_receivers = select_all_receivers

    db_set_config_variable(session, 1, 'forward_channel', context.id)

    session.query(models.ReceiverContext) \
           .filter(models.ReceiverContext.context_id == context.id) \
           .delete()

    for order, receiver_id in enumerate(receiver_ids):
        session.add(models.ReceiverContext({'context_id': context.id,
                                            'receiver_id': receiver_id,
                                            'order': order}))

    return context.id


@transact
def get_forward_receivers(session, channel_id):
    receivers, _ = db_get_forward_receivers(session, 1, channel_id, False)
    return sorted(r.username for r in receivers)


class TestForwardChannel(helpers.TestGLWithPopulatedDB):
    @inlineCallbacks
    def test_the_receivers_of_the_channel_receive_the_forward(self):
        channel_id = yield designate_forward_channel([self.dummyReceiver_1['id']], False)

        self.assertEqual((yield get_forward_receivers(channel_id)), ['receiver1'])

        # a channel selecting every recipient hands the forward over to them all
        channel_id = yield designate_forward_channel([], True)

        self.assertEqual((yield get_forward_receivers(channel_id)), ['receiver1', 'receiver2'])


def db_pair_tenants(session, source_tid, target_tid):
    """
    Write on the root tenant the relationship letting a tenant forward to another
    """
    root = ConfigFactory(session, 1)
    relationships = root.get_val('forwarding_relationships') + \
        [{'from': [ConfigFactory(session, source_tid).get_val('uuid')],
          'to': [ConfigFactory(session, target_tid).get_val('uuid')]}]

    db_set_config_variable(session, 1, 'forwarding_relationships', relationships)


@transact
def pair_tenants(session, source_tid, target_tid, both_ways=True):
    db_pair_tenants(session, source_tid, target_tid)
    if both_ways:
        db_pair_tenants(session, target_tid, source_tid)


@transact
def unpair_tenants(session, tid):
    db_set_config_variable(session, 1, 'forwarding_relationships', [])


@transact
def set_forward_policy(session, tid, enabled, require_requests):
    other_tid = 2 if tid == 1 else 1

    db_set_config_variable(session, 1, 'forwarding_relationships', [])
    if enabled:
        db_pair_tenants(session, other_tid, tid)
        db_pair_tenants(session, tid, other_tid)

    db_set_config_variable(session, tid, 'require_forward_requests', require_requests)


@transact
def create_forward_request_of_tenant(session, source_tid, authorized):
    """
    Reproduce the state left on the root tenant by a request of forward
    """
    itip = models.InternalTip()
    itip.tid = 1
    itip.status = 'new'
    itip.type = 'forward-request'
    itip.allow_forward = authorized
    itip.context_id = session.query(models.Context).filter(models.Context.tid == 1).first().id
    itip.progressive = session.query(models.InternalTip).filter(models.InternalTip.tid == 1).count() + 1
    itip.receipt_hash = uuid4() + uuid4()
    session.add(itip)
    session.flush()

    data = models.InternalTipData()
    data.internaltip_id = itip.id
    data.key = 'forward_request'
    data.value = {'source_tid': source_tid}
    session.add(data)

    return itip.id


@transact
def get_authorized_request(session, source_tid):
    request = db_get_authorized_forward_request(session, source_tid, 1)
    return request.id if request is not None else None


@transact
def spend_request(session, request_id, target_itip_id):
    forwarding = models.InternalTipForwarding()
    forwarding.internaltip_id = request_id
    forwarding.forwarding_internaltip_id = target_itip_id
    session.add(forwarding)


@transact
def can_forward_a_submission(session, source_tid):
    itip = models.InternalTip()
    itip.type = 'submission'

    return db_can_forward_report(session, source_tid, itip)


class TestForwardAuthorization(helpers.TestGLWithPopulatedDB):
    @inlineCallbacks
    def setUp(self):
        yield helpers.TestGLWithPopulatedDB.setUp(self)
        yield designate_forward_channel([self.dummyReceiver_1['id']], False)
        yield set_forward_policy(1, True, True)
        yield pair_tenants(1, 2)

    @inlineCallbacks
    def test_only_an_authorized_request_enables_the_tenant_that_issued_it(self):
        yield create_forward_request_of_tenant(2, False)

        self.assertIsNone((yield get_authorized_request(2)))
        self.assertFalse((yield accepts_forward_from(1, 2)))

        yield create_forward_request_of_tenant(2, True)

        self.assertIsNotNone((yield get_authorized_request(2)))
        self.assertTrue((yield accepts_forward_from(1, 2)))

        # the authorization stays with the tenant that issued the request
        self.assertIsNone((yield get_authorized_request(3)))

    @inlineCallbacks
    def test_an_authorization_is_spent_by_the_forward_performed_under_it(self):
        request_id = yield create_forward_request_of_tenant(2, True)
        forwarded_id = yield create_forward_request_of_tenant(2, False)

        yield spend_request(request_id, forwarded_id)

        self.assertIsNone((yield get_authorized_request(2)))
        self.assertFalse((yield accepts_forward_from(1, 2)))


@transact
def accepts_forward_from(session, target_tid, source_tid):
    itip = models.InternalTip()
    itip.type = 'submission'

    return db_accepts_forward(session, target_tid, source_tid, itip)


@transact
def can_request_forward(session, source_tid, target_tid=1):
    return db_can_request_forward(session, source_tid, target_tid)


class TestForwardPolicy(helpers.TestGLWithPopulatedDB):
    @inlineCallbacks
    def setUp(self):
        yield helpers.TestGLWithPopulatedDB.setUp(self)
        yield designate_forward_channel([self.dummyReceiver_1['id']], False)
        yield pair_tenants(1, 2)

    @inlineCallbacks
    def test_a_tenant_paired_to_send_alone_receives_none_but_still_sends(self):
        yield unpair_tenants(1)
        yield pair_tenants(1, 2, both_ways=False)

        self.assertFalse((yield accepts_forward_from(1, 2)))
        self.assertFalse((yield can_request_forward(2)))
        self.assertTrue((yield can_forward_a_submission(1)))

    @inlineCallbacks
    def test_a_tenant_paired_to_receive_alone_sends_none_but_still_receives(self):
        yield unpair_tenants(1)
        yield pair_tenants(2, 1, both_ways=False)

        self.assertTrue((yield accepts_forward_from(1, 2)))
        self.assertFalse((yield can_forward_a_submission(1)))

    @inlineCallbacks
    def test_a_tenant_requiring_requests_accepts_only_the_authorized_ones(self):
        yield set_forward_policy(1, True, True)

        self.assertFalse((yield accepts_forward_from(1, 2)))

        yield create_forward_request_of_tenant(2, True)

        self.assertTrue((yield accepts_forward_from(1, 2)))

    @inlineCallbacks
    def test_a_tenant_not_requiring_requests_accepts_without_them_and_refuses_them(self):
        yield set_forward_policy(1, True, False)

        self.assertTrue((yield accepts_forward_from(1, 2)))
        self.assertFalse((yield can_request_forward(2)))


@transact
def designate_channel_of_another_tenant(session, tid, channel_id):
    db_set_config_variable(session, tid, 'forward_channel', channel_id)


@transact
def get_forward_channel_ids(session, tid):
    return db_get_forward_channel_ids(session, tid)


@transact
def get_designated_channel(session, tid):
    channel = db_get_designated_channel(session, tid, 'forward_channel')
    return channel.id if channel is not None else None


@transact
def update_node_designating(session, tid, channel_id):
    request = db_admin_serialize_node(session, tid, 'en', 'admin_node')
    request['forward_channel'] = channel_id

    # the channels of the forwarding are designated by the administrators of
    # the platform: the update is performed under a session of theirs
    db_update_node(session, tid, ObjectDict({'user_tid': 1, 'role': 'admin'}), request, 'en')


@transact
def get_config_rows(session, var_name):
    return {c.tid: c.value for c in session.query(models.Config)
                                           .filter(models.Config.var_name == var_name)}


class TestForwardChannelDesignation(helpers.TestGLWithPopulatedDB):
    @inlineCallbacks
    def test_the_designation_is_not_inherited_from_the_profile_of_the_tenant(self):
        # the profile of the tenants designates a channel of its own, that is
        # not a channel of the tenants inheriting its configuration
        yield designate_channel_of_another_tenant(1000001, uuid4())

        self.assertEqual((yield get_forward_channel_ids(1)), set())
        self.assertIsNone((yield get_designated_channel(1)))

    @inlineCallbacks
    def test_the_designation_is_stored_on_the_tenant_and_not_on_its_profile(self):
        channel_id = yield designate_forward_channel([self.dummyReceiver_1['id']], False)
        yield designate_channel_of_another_tenant(1, '')

        yield update_node_designating(1, channel_id)

        rows = yield get_config_rows('forward_channel')

        self.assertEqual(rows.get(1), channel_id)
        self.assertEqual((yield get_designated_channel(1)), channel_id)


@transact
def grant_access_to_report(session, itip_id, user_id):
    rtip = models.ReceiverTip()
    rtip.internaltip_id = itip_id
    rtip.receiver_id = user_id
    rtip.crypto_tip_prv_key = ''
    session.add(rtip)


def authorize(tid, user_id, request_id):
    return set_internaltip_variable(tid, user_id, request_id, 'allow_forward', True)


@transact
def make_it_a_submission(session, request_id):
    session.query(models.InternalTip) \
           .filter(models.InternalTip.id == request_id) \
           .update({'type': 'submission'})


@transact
def is_authorized(session, request_id):
    return session.query(models.InternalTip).filter(models.InternalTip.id == request_id).one().allow_forward


class TestForwardRequestAuthorization(helpers.TestGLWithPopulatedDB):
    @inlineCallbacks
    def test_any_recipient_of_the_tenant_that_received_it_authorizes_it(self):
        request_id = yield create_forward_request_of_tenant(2, False)
        yield grant_access_to_report(request_id, self.dummyReceiver_1['id'])

        yield authorize(1, self.dummyReceiver_1['id'], request_id)

        self.assertTrue((yield is_authorized(request_id)))

    @inlineCallbacks
    def test_a_report_that_is_not_a_request_of_forward_cannot_be_authorized(self):
        request_id = yield create_forward_request_of_tenant(2, False)
        yield make_it_a_submission(request_id)
        yield grant_access_to_report(request_id, self.dummyReceiver_1['id'])

        yield self.assertFailure(authorize(1, self.dummyReceiver_1['id'], request_id),
                                 errors.ForbiddenOperation)

        self.assertFalse((yield is_authorized(request_id)))


@transact
def can_forward_the_request(session, source_tid, request_id):
    itip = session.query(models.InternalTip).filter(models.InternalTip.id == request_id).one()

    return db_can_forward_report(session, source_tid, itip)


class TestForwardOfTheRequest(helpers.TestGLWithPopulatedDB):
    @inlineCallbacks
    def setUp(self):
        yield helpers.TestGLWithPopulatedDB.setUp(self)
        yield designate_forward_channel([self.dummyReceiver_1['id']], False)
        yield set_forward_policy(1, True, True)
        yield pair_tenants(1, 2)

    @inlineCallbacks
    def test_an_authorized_request_is_forwarded_by_the_tenant_that_issued_it(self):
        request_id = yield create_forward_request_of_tenant(2, False)

        self.assertFalse((yield can_forward_the_request(2, request_id)))

        request_id = yield create_forward_request_of_tenant(2, True)

        self.assertTrue((yield can_forward_the_request(2, request_id)))

        # the request is never forwarded by a tenant other than the one that
        # issued it
        self.assertFalse((yield can_forward_the_request(3, request_id)))

    @inlineCallbacks
    def test_a_request_already_spent_is_not_forwarded_again(self):
        request_id = yield create_forward_request_of_tenant(2, True)
        forwarded_id = yield create_forward_request_of_tenant(2, False)

        yield spend_request(request_id, forwarded_id)

        self.assertFalse((yield can_forward_the_request(2, request_id)))


def deny(tid, user_id, request_id):
    return set_internaltip_variable(tid, user_id, request_id, 'allow_forward', False)


@transact
def get_request_state(session, request_id):
    itip = session.query(models.InternalTip).filter(models.InternalTip.id == request_id).one()
    return itip.status, itip.allow_forward


class TestForwardRequestDecision(helpers.TestGLWithPopulatedDB):
    @inlineCallbacks
    def test_denying_a_request_closes_it_and_enables_no_forward(self):
        request_id = yield create_forward_request_of_tenant(2, True)
        yield grant_access_to_report(request_id, self.dummyReceiver_1['id'])

        yield deny(1, self.dummyReceiver_1['id'], request_id)

        self.assertEqual((yield get_request_state(request_id)), ('closed', False))
        self.assertFalse((yield can_forward_the_request(2, request_id)))
        self.assertIsNone((yield get_authorized_request(2)))

    @inlineCallbacks
    def test_authorizing_a_denied_request_brings_it_back_among_the_open_ones(self):
        request_id = yield create_forward_request_of_tenant(2, False)
        yield grant_access_to_report(request_id, self.dummyReceiver_1['id'])

        yield deny(1, self.dummyReceiver_1['id'], request_id)
        yield authorize(1, self.dummyReceiver_1['id'], request_id)

        self.assertEqual((yield get_request_state(request_id)), ('opened', True))



@transact
def get_forwarded_report(session, request_id):
    return session.query(models.InternalTip) \
                  .join(models.InternalTipForwarding,
                        models.InternalTipForwarding.forwarding_internaltip_id == models.InternalTip.id) \
                  .filter(models.InternalTipForwarding.internaltip_id == request_id) \
                  .one()


@transact
def get_stored_receipt(session, request_id):
    data = session.query(models.InternalTipData) \
                  .filter(models.InternalTipData.internaltip_id == request_id,
                          models.InternalTipData.key == 'forward_receipt') \
                  .one_or_none()

    return data.value if data is not None else None


@transact
def link_forwarded_report(session, request_id, receipt_change_needed):
    itip = models.InternalTip()
    itip.tid = 1
    itip.status = 'new'
    itip.type = 'forward'
    itip.context_id = session.query(models.Context).filter(models.Context.tid == 1).first().id
    itip.progressive = session.query(models.InternalTip).filter(models.InternalTip.tid == 1).count() + 1
    itip.receipt_hash = uuid4() + uuid4()
    itip.receipt_change_needed = receipt_change_needed
    session.add(itip)
    session.flush()

    forwarding = models.InternalTipForwarding()
    forwarding.internaltip_id = request_id
    forwarding.forwarding_internaltip_id = itip.id
    session.add(forwarding)


@transact
def receipt_is_valid(session, request_id):
    itip = session.query(models.InternalTip).filter(models.InternalTip.id == request_id).one()

    return db_forward_receipt_is_valid(session, itip)


class TestForwardReceipt(helpers.TestGLWithPopulatedDB):
    @inlineCallbacks
    def test_the_receipt_stays_valid_until_the_whistleblower_replaces_it(self):
        # a request that has not been forwarded yet hands over no receipt
        request_id = yield create_forward_request_of_tenant(2, True)

        self.assertFalse((yield receipt_is_valid(request_id)))

        yield link_forwarded_report(request_id, True)

        self.assertTrue((yield receipt_is_valid(request_id)))

        # the receipt of the forward is spent once its whistleblower replaced
        # it with one of its own
        replaced_id = yield create_forward_request_of_tenant(2, True)
        yield link_forwarded_report(replaced_id, False)

        self.assertFalse((yield receipt_is_valid(replaced_id)))


@transact
def get_attachments(session, itip_id):
    return session.query(models.InternalFile) \
                  .filter(models.InternalFile.internaltip_id == itip_id) \
                  .count()


class TestForwardAttachment(helpers.TestHandlerWithPopulatedDB):
    _handler = forward.RTipForwardAttachment

    @inlineCallbacks
    def test_the_uploaded_files_are_held_on_the_session_of_the_sender(self):
        handler = self.request(role='receiver', user_id=self.dummyReceiver_1['id'],
                               permissions={'can_forward_reports': True})
        yield handler.post(uuid4())

        self.assertEqual(len(handler.session.files), 1)

    @inlineCallbacks
    def test_a_recipient_that_cannot_forward_cannot_upload(self):
        handler = self.request(role='receiver', user_id=self.dummyReceiver_1['id'],
                               permissions={'can_forward_reports': False})

        yield self.assertRaises(errors.ForbiddenOperation, handler.post, uuid4())


@transact
def create_report_of_tenant(session, tid, type, receiver_ids=()):
    itip = models.InternalTip()
    itip.tid = tid
    itip.status = 'new'
    itip.type = type
    itip.context_id = session.query(models.Context).filter(models.Context.tid == 1).first().id
    itip.progressive = session.query(models.InternalTip).filter(models.InternalTip.tid == tid).count() + 1
    itip.receipt_hash = uuid4() + uuid4()
    session.add(itip)
    session.flush()

    for receiver_id in receiver_ids:
        rtip = models.ReceiverTip()
        rtip.internaltip_id = itip.id
        rtip.receiver_id = receiver_id
        rtip.crypto_tip_prv_key = ''
        session.add(rtip)

    return itip.id


@transact
def create_receiver_of_tenant(session, tid, encryption=False):
    profile_id = session.query(models.User.profile_id) \
                        .filter(models.User.role == 'receiver',
                                models.User.tid == 1).first()[0]

    user = models.User()
    user.tid = tid
    user.username = uuid4()
    user.name = 'Recipient of tenant %d' % tid
    user.role = 'receiver'
    user.language = 'en'
    user.profile_id = profile_id
    user.crypto_pub_key = GCE.generate_keypair()[1] if encryption else ''
    user.mail_address = 'recipient-of-tenant-%d@example.org' % tid
    session.add(user)
    session.flush()

    # the recipients of a channel are the ones a forward filed on it reaches
    for order, context in enumerate(session.query(models.Context)
                                           .filter(models.Context.tid == tid)):
        session.add(models.ReceiverContext({'context_id': context.id,
                                            'receiver_id': user.id,
                                            'order': order}))

    return user.id


@transact
def set_user_key(session, user_id, crypto_pub_key):
    session.query(models.User).filter(models.User.id == user_id).one().crypto_pub_key = crypto_pub_key


@transact
def add_source_tenant_receivertips(session, source_id, target_id,
                                   target_receiver_ids=(), encryption=False, tip_prv_key=b''):
    source_itip = session.query(models.InternalTip).filter(models.InternalTip.id == source_id).one()
    target_itip = session.query(models.InternalTip).filter(models.InternalTip.id == target_id).one()
    target_receivers = session.query(models.User) \
                              .filter(models.User.id.in_(target_receiver_ids)).all()

    forward.db_create_source_tenant_receivertips(session, 1, source_itip, target_itip,
                                                 target_receivers, encryption, tip_prv_key)


@transact
def get_report_receiver_ids(session, itip_id):
    return sorted(receiver_id for (receiver_id,) in
                  session.query(models.ReceiverTip.receiver_id)
                         .filter(models.ReceiverTip.internaltip_id == itip_id))


class TestForwardFollowup(helpers.TestGLWithPopulatedDB):
    @inlineCallbacks
    def test_the_recipients_of_the_forwarding_tenant_alone_follow_the_forward(self):
        foreign_id = yield create_receiver_of_tenant(2)
        source_id = yield create_report_of_tenant(1, 'submission', [self.dummyReceiver_1['id'],
                                                                    self.dummyReceiver_2['id'],
                                                                    foreign_id])
        target_id = yield create_report_of_tenant(2, 'forward')

        yield add_source_tenant_receivertips(source_id, target_id)

        self.assertEqual((yield get_report_receiver_ids(target_id)),
                         sorted([self.dummyReceiver_1['id'], self.dummyReceiver_2['id']]))

    @inlineCallbacks
    def test_a_recipient_receiving_the_forward_on_its_channel_is_not_duplicated(self):
        source_id = yield create_report_of_tenant(1, 'submission', [self.dummyReceiver_1['id'],
                                                                    self.dummyReceiver_2['id']])
        target_id = yield create_report_of_tenant(2, 'forward', [self.dummyReceiver_1['id']])

        yield add_source_tenant_receivertips(source_id, target_id,
                                             target_receiver_ids=[self.dummyReceiver_1['id']])

        self.assertEqual((yield get_report_receiver_ids(target_id)),
                         sorted([self.dummyReceiver_1['id'], self.dummyReceiver_2['id']]))

    @inlineCallbacks
    def test_a_recipient_without_an_encryption_key_is_left_out(self):
        prv_key, pub_key = GCE.generate_keypair()
        yield set_user_key(self.dummyReceiver_1['id'], pub_key)
        yield set_user_key(self.dummyReceiver_2['id'], '')

        source_id = yield create_report_of_tenant(1, 'submission', [self.dummyReceiver_1['id'],
                                                                    self.dummyReceiver_2['id']])
        target_id = yield create_report_of_tenant(2, 'forward')

        yield add_source_tenant_receivertips(source_id, target_id,
                                             encryption=True, tip_prv_key=prv_key)

        self.assertEqual((yield get_report_receiver_ids(target_id)), [self.dummyReceiver_1['id']])


@transact
def add_comment(session, itip_id, author_id, visibility):
    comment = models.Comment()
    comment.internaltip_id = itip_id
    comment.author_id = author_id
    comment.content = visibility
    comment.visibility = visibility
    session.add(comment)
    session.flush()

    return comment.id


@transact
def add_rfile(session, itip_id, author_id, visibility):
    rfile = models.ReceiverFile()
    rfile.internaltip_id = itip_id
    rfile.author_id = author_id
    rfile.name = visibility
    rfile.size = 1
    rfile.content_type = 'text/plain'
    rfile.visibility = visibility
    session.add(rfile)
    session.flush()

    return rfile.id


def db_serialize_rtip_of(session, itip_id, user_id):
    """
    Serialize a report as the recipient handed over reads it
    """
    itip = session.query(models.InternalTip).filter(models.InternalTip.id == itip_id).one()
    rtip = session.query(models.ReceiverTip) \
                  .filter(models.ReceiverTip.internaltip_id == itip_id,
                          models.ReceiverTip.receiver_id == user_id).one()

    return serializers.serialize_rtip(session, itip, rtip, 'en')


@transact
def get_shown_element_ids(session, itip_id, user_id):
    report = db_serialize_rtip_of(session, itip_id, user_id)

    return ([comment['id'] for comment in report['comments']],
            [rfile['id'] for rfile in report['rfiles']])


@transact
def get_shown_receiver_names(session, itip_id, user_id):
    report = db_serialize_rtip_of(session, itip_id, user_id)

    return {receiver['id']: receiver['name'] for receiver in report['receivers']}


@transact
def open_report(session, tid, user_id, itip_id):
    db_get_rtip(session, tid, user_id, itip_id, 'en')


@transact
def get_report_status(session, itip_id):
    return session.query(models.InternalTip.status) \
                  .filter(models.InternalTip.id == itip_id).scalar()


@transact
def revoke_access(session, tid, itip_id, receiver_id):
    itip = session.query(models.InternalTip).filter(models.InternalTip.id == itip_id).one()
    return db_revoke_tip_access(session, tid, None, itip, receiver_id)


@transact
def can_access_rfile(session, tid, user_id, rfile_id):
    return db_access_rfile(session, tid, user_id, rfile_id) is not None


class TestForwardVisibility(helpers.TestGLWithPopulatedDB):
    """
    The report created by a forward is shared by the recipients of its two
    tenants: a forward element addresses all of them, a public element stays
    between the whistleblower and the receiving tenant, an internal element
    among the recipients of the tenant of its author, a personal element with
    its author alone.
    """
    @inlineCallbacks
    def setUp(self):
        yield helpers.TestGLWithPopulatedDB.setUp(self)

        self.foreign_id = yield create_receiver_of_tenant(2)
        self.itip_id = yield create_report_of_tenant(2, 'forward', [self.foreign_id,
                                                                    self.dummyReceiver_1['id'],
                                                                    self.dummyReceiver_2['id']])

        self.forward_comment = yield add_comment(self.itip_id, self.foreign_id, 'forward')
        self.public_comment = yield add_comment(self.itip_id, self.foreign_id, 'public')
        self.foreign_internal_comment = yield add_comment(self.itip_id, self.foreign_id, 'internal')
        self.internal_comment = yield add_comment(self.itip_id, self.dummyReceiver_1['id'], 'internal')
        self.personal_comment = yield add_comment(self.itip_id, self.dummyReceiver_1['id'], 'personal')

        self.forward_rfile = yield add_rfile(self.itip_id, self.foreign_id, 'forward')
        self.public_rfile = yield add_rfile(self.itip_id, self.foreign_id, 'public')
        self.foreign_internal_rfile = yield add_rfile(self.itip_id, self.foreign_id, 'internal')
        self.internal_rfile = yield add_rfile(self.itip_id, self.dummyReceiver_1['id'], 'internal')
        self.personal_rfile = yield add_rfile(self.itip_id, self.dummyReceiver_1['id'], 'personal')

    @inlineCallbacks
    def test_every_element_is_shown_to_the_recipients_its_visibility_addresses(self):
        # each element, with the recipients it is addressed to: every other
        # recipient of the report is required not to be shown it
        addressed = [
            (self.forward_comment, self.forward_rfile,
             {self.dummyReceiver_1['id'], self.dummyReceiver_2['id'], self.foreign_id}),
            (self.public_comment, self.public_rfile,
             {self.foreign_id}),
            (self.internal_comment, self.internal_rfile,
             {self.dummyReceiver_1['id'], self.dummyReceiver_2['id']}),
            (self.foreign_internal_comment, self.foreign_internal_rfile,
             {self.foreign_id}),
            (self.personal_comment, self.personal_rfile,
             {self.dummyReceiver_1['id']})
        ]

        for user_id in [self.dummyReceiver_1['id'], self.dummyReceiver_2['id'], self.foreign_id]:
            comments, rfiles = yield get_shown_element_ids(self.itip_id, user_id)

            for comment_id, rfile_id, recipients in addressed:
                self.assertEqual(comment_id in comments, user_id in recipients)
                self.assertEqual(rfile_id in rfiles, user_id in recipients)

    @inlineCallbacks
    def test_each_tenant_is_presented_its_own_recipients_alone(self):
        names = yield get_shown_receiver_names(self.itip_id, self.dummyReceiver_1['id'])
        self.assertEqual(set(names), {self.dummyReceiver_1['id'], self.dummyReceiver_2['id']})

        names = yield get_shown_receiver_names(self.itip_id, self.foreign_id)
        self.assertEqual(set(names), {self.foreign_id})

    @inlineCallbacks
    def test_a_tenant_cannot_revoke_the_recipients_of_the_other(self):
        self.assertFalse((yield revoke_access(2, self.itip_id, self.dummyReceiver_1['id'])))
        self.assertFalse((yield revoke_access(1, self.itip_id, self.foreign_id)))

        self.assertTrue((yield revoke_access(2, self.itip_id, self.foreign_id)))

    @inlineCallbacks
    def test_the_file_access_follows_the_same_confinement(self):
        self.assertTrue((yield can_access_rfile(1, self.dummyReceiver_2['id'], self.forward_rfile)))
        self.assertTrue((yield can_access_rfile(2, self.foreign_id, self.forward_rfile)))

        self.assertTrue((yield can_access_rfile(1, self.dummyReceiver_2['id'], self.internal_rfile)))
        self.assertFalse((yield can_access_rfile(2, self.foreign_id, self.internal_rfile)))
        self.assertFalse((yield can_access_rfile(1, self.dummyReceiver_2['id'], self.foreign_internal_rfile)))

        self.assertFalse((yield can_access_rfile(1, self.dummyReceiver_2['id'], self.personal_rfile)))
        self.assertTrue((yield can_access_rfile(1, self.dummyReceiver_1['id'], self.personal_rfile)))


def make_uploaded_file(visibility):
    return {
        'filename': uuid4(),
        'name': 'file.txt',
        'description': '',
        'type': 'text/plain',
        'size': 1,
        'hash_sha256': '',
        'hash_sha512': '',
        'visibility': visibility
    }


class FakeMessagingSession:
    def __init__(self, user_id, cc=b''):
        self.user_id = user_id
        self.cc = cc


class FakeUserSession(FakeMessagingSession):
    def __init__(self, user_id, cc=b'', **permissions):
        FakeMessagingSession.__init__(self, user_id, cc)
        self.permissions = ObjectDict(permissions)
        # the attachments of a forward are held on the session of the sender
        self.files = []

    def has_permission(self, permission):
        return self.permissions.get(permission, False)


@transact
def link_forward(session, source_id, target_id, crypto_tip_prv_key=''):
    forwarding = models.InternalTipForwarding()
    forwarding.internaltip_id = source_id
    forwarding.forwarding_internaltip_id = target_id
    forwarding.crypto_tip_prv_key = crypto_tip_prv_key
    session.add(forwarding)


@transact
def get_forwarding_update_date(session, target_id):
    return forward.db_get_forwarding(session, target_id).update_date


@transact
def set_tip_keys(session, itip_id, crypto_pub_key=None, crypto_tip_prv_key=None, crypto_tip_pub_key=None):
    itip = session.query(models.InternalTip).filter(models.InternalTip.id == itip_id).one()
    if crypto_pub_key is not None:
        itip.crypto_pub_key = crypto_pub_key
    if crypto_tip_prv_key is not None:
        itip.crypto_tip_prv_key = crypto_tip_prv_key
    if crypto_tip_pub_key is not None:
        itip.crypto_tip_pub_key = crypto_tip_pub_key


@transact
def set_receivertip_key(session, itip_id, user_id, crypto_tip_prv_key):
    rtip = session.query(models.ReceiverTip) \
                  .filter(models.ReceiverTip.internaltip_id == itip_id,
                          models.ReceiverTip.receiver_id == user_id).one()
    rtip.crypto_tip_prv_key = crypto_tip_prv_key


@transact
def get_wbtip_forwards(session, itip_id):
    itip = session.query(models.InternalTip).filter(models.InternalTip.id == itip_id).one()
    return serializers.serialize_wbtip(session, itip, 'en')['forwards']


@transact
def get_rtip_forwarding(session, itip_id, user_id):
    return db_serialize_rtip_of(session, itip_id, user_id)['forwarding']


@transact
def get_serialized_rtip(session, itip_id, user_id):
    return db_serialize_rtip_of(session, itip_id, user_id)


class TestForwardMessages(helpers.TestGLWithPopulatedDB):
    """
    The messages the receiving tenant addresses to the whistleblower are the
    public comments of the report created by the forward: the whistleblower
    reads them without being able to write, and the recipients following the
    report from the forwarding tenant stay out of that space.
    """
    @inlineCallbacks
    def setUp(self):
        yield helpers.TestGLWithPopulatedDB.setUp(self)

        self.foreign_id = yield create_receiver_of_tenant(2)
        self.source_id = yield create_report_of_tenant(1, 'submission', [self.dummyReceiver_1['id']])
        self.target_id = yield create_report_of_tenant(2, 'forward', [self.foreign_id,
                                                                      self.dummyReceiver_1['id']])
        yield link_forward(self.source_id, self.target_id)

        self.wb_session = FakeMessagingSession(self.source_id)

    @inlineCallbacks
    def test_the_whistleblower_reads_the_messages_of_the_receiving_tenant(self):
        yield rtip_create_comment(2, self.foreign_id, self.target_id, 'welcome', 'public')
        yield rtip_create_comment(2, self.foreign_id, self.target_id, 'again', 'public')

        # the space between the tenants is not part of the exchange
        yield rtip_create_comment(2, self.foreign_id, self.target_id, 'between tenants', 'forward')

        messages = yield forward.get_forward_messages_as_whistleblower(self.wb_session, self.target_id)
        self.assertEqual([m['content'] for m in messages], ['welcome', 'again'])

        comments, _ = yield get_shown_element_ids(self.target_id, self.foreign_id)
        for message in messages:
            self.assertIn(message['id'], comments)

        # the authors reach the whistleblower named after their organization
        self.assertNotEqual(messages[0]['author_name'], 'Recipient of tenant 2')

    def test_the_whistleblower_cannot_write_into_the_exchange(self):
        # The API dispatcher answers any method the handler misses with a 405
        self.assertFalse(hasattr(wbtip.WBTipForwardMessages, 'post'))

    @inlineCallbacks
    def test_the_recipients_of_the_forwarding_tenant_stay_out_of_the_exchange(self):
        message = yield rtip_create_comment(2, self.foreign_id, self.target_id, 'welcome', 'public')

        yield self.assertFailure(
            rtip_create_comment(1, self.dummyReceiver_1['id'], self.target_id, 'x', 'public'),
            errors.InputValidationError)

        comments, _ = yield get_shown_element_ids(self.target_id, self.dummyReceiver_1['id'])
        self.assertNotIn(message['id'], comments)

        # and the tenant that received the forward answers the one that
        # performed it with the messages of the space between them alone
        for visibility in ('forward', 'internal', 'personal'):
            yield register_rfile_on_db(1, self.dummyReceiver_1['id'], self.target_id,
                                       make_uploaded_file(visibility))
            yield self.assertFailure(
                register_rfile_on_db(2, self.foreign_id, self.target_id,
                                     make_uploaded_file(visibility)),
                errors.InputValidationError)

        for visibility in ('internal', 'personal'):
            yield rtip_create_comment(1, self.dummyReceiver_1['id'], self.target_id, 'x', visibility)
            yield self.assertFailure(
                rtip_create_comment(2, self.foreign_id, self.target_id, 'x', visibility),
                errors.InputValidationError)

        yield rtip_create_comment(2, self.foreign_id, self.target_id, 'reply', 'forward')
        yield rtip_create_comment(2, self.foreign_id, self.target_id, 'hello', 'public')

    @inlineCallbacks
    def test_the_forward_visibility_is_confined_to_forwarded_reports(self):
        yield self.assertFailure(
            rtip_create_comment(1, self.dummyReceiver_1['id'], self.source_id, 'x', 'forward'),
            errors.InputValidationError)

    @inlineCallbacks
    def test_the_whistleblower_of_another_report_is_turned_away(self):
        other_id = yield create_report_of_tenant(1, 'submission', [self.dummyReceiver_1['id']])

        yield self.assertFailure(
            forward.get_forward_messages_as_whistleblower(FakeMessagingSession(other_id), self.target_id),
            errors.ForbiddenOperation)

    @inlineCallbacks
    def test_a_message_marks_the_forwarding_as_updated(self):
        before = yield get_forwarding_update_date(self.target_id)
        yield rtip_create_comment(2, self.foreign_id, self.target_id, 'welcome', 'public')
        after = yield get_forwarding_update_date(self.target_id)

        self.assertGreater(after, before)

    @inlineCallbacks
    def test_the_exchange_is_unavailable_without_the_whistleblower_key(self):
        prv_key, pub_key = GCE.generate_keypair()
        yield set_tip_keys(self.target_id, crypto_tip_pub_key=pub_key)

        yield self.assertFailure(
            forward.get_forward_messages_as_whistleblower(self.wb_session, self.target_id),
            errors.ForbiddenOperation)

        forwarding = yield get_rtip_forwarding(self.target_id, self.foreign_id)
        self.assertFalse(forwarding['messages_enabled'])

    @inlineCallbacks
    def test_the_whistleblower_is_presented_the_forwards_of_its_report(self):
        forwards = yield get_wbtip_forwards(self.source_id)

        self.assertEqual(len(forwards), 1)
        self.assertEqual(forwards[0]['id'], self.target_id)
        self.assertTrue(forwards[0]['messages_enabled'])

    @inlineCallbacks
    def test_the_forward_is_presented_to_each_of_its_two_sides(self):
        forwarding = yield get_rtip_forwarding(self.target_id, self.foreign_id)
        self.assertTrue(forwarding['messages_enabled'])
        self.assertEqual(forwarding['internaltip_id'], '')

        forwarding = yield get_rtip_forwarding(self.target_id, self.dummyReceiver_1['id'])
        self.assertFalse(forwarding['messages_enabled'])
        self.assertEqual(forwarding['internaltip_id'], self.source_id)

        # both sides are told the organizations the forward runs between
        for user_id in [self.foreign_id, self.dummyReceiver_1['id']]:
            forwarding = yield get_rtip_forwarding(self.target_id, user_id)

            self.assertNotEqual(forwarding['from_tenant_name'], '')
            self.assertNotEqual(forwarding['to_tenant_name'], '')

    @inlineCallbacks
    def test_the_access_of_the_forwarding_tenant_leaves_the_report_untouched(self):
        yield set_reminder(2, self.foreign_id, self.target_id, 1000)

        yield open_report(1, self.dummyReceiver_1['id'], self.target_id)

        # neither the opening indicator nor the reminder are resolved by the
        # access of a recipient following the forward from the other side
        self.assertEqual((yield get_report_status(self.target_id)), 'new')
        report = yield get_serialized_rtip(self.target_id, self.foreign_id)
        self.assertNotEqual(report['reminder_date'], datetime_never())

        yield open_report(2, self.foreign_id, self.target_id)

        self.assertEqual((yield get_report_status(self.target_id)), 'opened')
        report = yield get_serialized_rtip(self.target_id, self.foreign_id)
        self.assertEqual(report['reminder_date'], datetime_never())

    @inlineCallbacks
    def test_the_operations_are_refused_to_the_forwarding_tenant(self):
        follower_id = self.dummyReceiver_1['id']
        follower = FakeUserSession(follower_id,
                                   can_postpone_expiration=True,
                                   can_delete_submission=True,
                                   can_mask_information=True)

        yield self.assertFailure(
            set_reminder(1, follower_id, self.target_id, datetime_now()),
            errors.ForbiddenOperation)
        yield self.assertFailure(
            update_tip_submission_status(1, follower_id, self.target_id, 'closed', ''),
            errors.ForbiddenOperation)
        yield self.assertFailure(
            set_internaltip_variable(1, follower_id, self.target_id, 'label', 'x'),
            errors.ForbiddenOperation)
        yield self.assertFailure(
            set_internaltip_variable(1, follower_id, self.target_id, 'important', True),
            errors.ForbiddenOperation)
        yield self.assertFailure(
            postpone_expiration(1, follower, self.target_id, 32503680000000),
            errors.ForbiddenOperation)
        yield self.assertFailure(
            create_redaction(1, follower, {'internaltip_id': self.target_id,
                                           'reference_id': uuid4(),
                                           'temporary_redaction': []}),
            errors.ForbiddenOperation)
        yield self.assertFailure(
            delete_rtip(1, follower, self.target_id),
            errors.ForbiddenOperation)

    @inlineCallbacks
    def test_the_operations_are_performed_by_the_receiving_tenant(self):
        receiver = FakeUserSession(self.foreign_id,
                                   can_postpone_expiration=True,
                                   can_mask_information=True)

        comment = yield rtip_create_comment(2, self.foreign_id, self.target_id, 'x', 'public')

        yield postpone_expiration(2, receiver, self.target_id, 32503680000000)
        yield create_redaction(2, receiver, {'internaltip_id': self.target_id,
                                             'reference_id': comment['id'],
                                             'temporary_redaction': []})

        yield delete_rtip(2, FakeUserSession(self.foreign_id, can_delete_submission=True),
                          self.target_id)

    @inlineCallbacks
    def test_the_metadata_are_operated_by_the_receiving_tenant(self):
        yield set_internaltip_variable(2, self.foreign_id, self.target_id, 'label', 'x')
        yield set_internaltip_variable(2, self.foreign_id, self.target_id, 'important', True)
        yield update_tip_submission_status(2, self.foreign_id, self.target_id, 'closed', '')

        self.assertEqual((yield get_report_status(self.target_id)), 'closed')

        yield update_tip_submission_status(2, self.foreign_id, self.target_id, 'opened', '')
        self.assertEqual((yield get_report_status(self.target_id)), 'opened')

        yield set_reminder(2, self.foreign_id, self.target_id, 1893456000000)

        report = yield get_serialized_rtip(self.target_id, self.foreign_id)
        self.assertEqual(report['label'], 'x')
        self.assertTrue(report['important'])
        self.assertNotEqual(report['reminder_date'], datetime_never())

        # the metadata of the receiving tenant stay with it: the tenant that
        # performed the forward reads its own, left untouched
        report = yield get_serialized_rtip(self.target_id, self.dummyReceiver_1['id'])
        self.assertEqual(report['label'], '')
        self.assertFalse(report['important'])
        self.assertEqual(report['reminder_date'], datetime_never())

    @inlineCallbacks
    def test_the_read_receipt_reports_the_other_side_of_the_forward(self):
        yield rtip_create_comment(1, self.dummyReceiver_1['id'], self.target_id, 'x', 'forward')

        report = yield get_serialized_rtip(self.target_id, self.dummyReceiver_1['id'])
        self.assertLess(report['counterpart_last_access'], report['update_date'])

        yield open_report(2, self.foreign_id, self.target_id)

        report = yield get_serialized_rtip(self.target_id, self.dummyReceiver_1['id'])
        self.assertGreaterEqual(report['counterpart_last_access'], report['update_date'])


class TestForwardMessagesEncryption(helpers.TestGLWithPopulatedDB):
    """
    Reproduce the keys handed over by a forward and verify that the messages
    of the receiving tenant reach the whistleblower encrypted end to end
    """
    @inlineCallbacks
    def setUp(self):
        yield helpers.TestGLWithPopulatedDB.setUp(self)

        self.foreign_id = yield create_receiver_of_tenant(2)
        self.source_id = yield create_report_of_tenant(1, 'submission', [self.dummyReceiver_1['id']])
        self.target_id = yield create_report_of_tenant(2, 'forward', [self.foreign_id])

        wb_prv_key, wb_pub_key = GCE.generate_keypair()
        source_tip_prv_key, source_tip_pub_key = GCE.generate_keypair()
        target_tip_prv_key, target_tip_pub_key = GCE.generate_keypair()
        user_prv_key, user_pub_key = GCE.generate_keypair()

        yield set_tip_keys(self.source_id,
                           crypto_pub_key=wb_pub_key,
                           crypto_tip_prv_key=Base64Encoder.encode(
                               GCE.asymmetric_encrypt(wb_pub_key, source_tip_prv_key)).decode(),
                           crypto_tip_pub_key=source_tip_pub_key)
        yield set_tip_keys(self.target_id, crypto_tip_pub_key=target_tip_pub_key)
        yield set_receivertip_key(self.target_id, self.foreign_id,
                                  Base64Encoder.encode(
                                      GCE.asymmetric_encrypt(user_pub_key, target_tip_prv_key)).decode())
        yield link_forward(self.source_id, self.target_id,
                           Base64Encoder.encode(
                               GCE.asymmetric_encrypt(source_tip_pub_key, target_tip_prv_key)).decode())

        self.wb_session = FakeMessagingSession(self.source_id, wb_prv_key)

    @inlineCallbacks
    def test_the_encrypted_exchange_round_trip(self):
        yield rtip_create_comment(2, self.foreign_id, self.target_id, 'welcome', 'public')

        messages = yield forward.get_forward_messages_as_whistleblower(self.wb_session, self.target_id)
        self.assertEqual([m['content'] for m in messages], ['welcome'])

        # what the whistleblower reads is decrypted on the way out and is
        # never stored in the clear
        self.assertNotIn('welcome', (yield self.get_stored_message_contents()))

    @transact
    def get_stored_message_contents(self, session):
        return [c.content for c in session.query(models.Comment)
                                          .filter(models.Comment.internaltip_id == self.target_id,
                                                  models.Comment.visibility == models.EnumVisibility.public.value)]


@transact
def align_progressive_counter(session, tid):
    """
    Align the counter of the reports of a tenant with the ones already filed

    The fixtures file the reports directly and leave the counter behind: a
    forward filed through the ordinary assignment would collide with them.
    """
    highest = session.query(func.max(models.InternalTip.progressive)) \
                     .filter(models.InternalTip.tid == tid).scalar() or 0

    counter = session.query(models.Config) \
                     .filter(models.Config.tid == tid,
                             models.Config.var_name == 'counter_submissions').one()
    counter.value = max(counter.value, highest)


@transact
def designate_channel_of(session, tid, var_name='forward_channel'):
    context = session.query(models.Context).filter(models.Context.tid == tid).first()
    context.select_all_receivers = True
    db_set_config_variable(session, tid, var_name, context.id)

    return context.id


@transact
def set_policy_of(session, tid, **variables):
    for var_name, value in variables.items():
        db_set_config_variable(session, tid, var_name, value)


@transact
def create_forwardable_report(session, tid, receiver_id):
    itip = models.InternalTip()
    itip.tid = tid
    itip.status = 'new'
    itip.type = 'submission'
    itip.context_id = session.query(models.Context).filter(models.Context.tid == tid).first().id
    itip.progressive = session.query(models.InternalTip) \
                              .filter(models.InternalTip.tid == tid).count() + 1000
    itip.receipt_hash = uuid4() + uuid4()
    session.add(itip)
    session.flush()

    rtip = models.ReceiverTip()
    rtip.internaltip_id = itip.id
    rtip.receiver_id = receiver_id
    rtip.crypto_tip_prv_key = ''
    session.add(rtip)

    return itip.id


@transact
def get_report_summary(session, itip_id):
    itip = session.query(models.InternalTip).filter(models.InternalTip.id == itip_id).one()

    return {'tid': itip.tid,
            'type': itip.type,
            'context_id': itip.context_id,
            'status': itip.status}


@transact
def get_stored_answers(session, itip_id):
    itip = session.query(models.InternalTip).filter(models.InternalTip.id == itip_id).one()
    answers = session.query(models.InternalTipAnswers) \
                     .filter(models.InternalTipAnswers.internaltip_id == itip_id).one().answers

    if itip.crypto_tip_pub_key:
        return None

    return answers


@transact
def get_channel_questionnaire_fields(session, tid, var_name='forward_channel'):
    channel = forward.db_get_designated_channel(session, tid, var_name)
    questionnaire = forward.db_get_channel_questionnaire(session, tid, channel, 'en')

    fields = {}

    def walk(children):
        for field in children:
            fields[field['id']] = field
            walk(field.get('children', []))

    for step in questionnaire['steps']:
        walk(step.get('children', []))

    return fields


class TestForwardExecution(helpers.TestGLWithPopulatedDB):
    """
    The forward is performed by create_forward: the report is filed on the
    channel the receiving tenant designated, its recipients receive it and the
    recipients of the tenant that performed it follow it.
    """
    @inlineCallbacks
    def setUp(self):
        yield helpers.TestGLWithPopulatedDB.setUp(self)

        self.foreign_id = yield create_receiver_of_tenant(2, encryption=True)
        self.target_channel_id = yield designate_channel_of(2)
        yield pair_tenants(1, 2)
        yield set_policy_of(2, require_forward_requests=False)

        self.source_id = yield create_forwardable_report(1, self.dummyReceiver_1['id'])
        self.sender = FakeUserSession(self.dummyReceiver_1['id'], can_forward_reports=True)

        yield align_progressive_counter(1)
        yield align_progressive_counter(2)

    @inlineCallbacks
    def perform_forward(self, target_tid=2, answers=None):
        result = yield forward.create_forward(1, self.sender, self.source_id,
                                              {'target_tid': target_tid,
                                               'answers': answers if answers is not None else {}},
                                              'en')
        return result

    @inlineCallbacks
    def test_the_report_is_filed_on_the_channel_of_the_receiving_tenant(self):
        result = yield self.perform_forward()

        summary = yield get_report_summary(result['id'])
        self.assertEqual(summary['tid'], 2)
        self.assertEqual(summary['type'], 'forward')
        self.assertEqual(summary['context_id'], self.target_channel_id)

        # the recipients of the channel receive it and the ones of the tenant
        # that performed the forward follow it
        receiver_ids = yield get_report_receiver_ids(result['id'])
        self.assertIn(self.foreign_id, receiver_ids)
        self.assertIn(self.dummyReceiver_1['id'], receiver_ids)

    @inlineCallbacks
    def test_a_report_created_by_a_forward_is_never_forwarded_again(self):
        result = yield self.perform_forward()

        yield self.assertFailure(
            forward.create_forward(2, FakeUserSession(self.foreign_id, can_forward_reports=True),
                                   result['id'], {'target_tid': 1, 'answers': {}}, 'en'),
            errors.ForbiddenOperation)

    @inlineCallbacks
    def test_a_recipient_without_the_permission_does_not_forward(self):
        yield self.assertFailure(
            forward.create_forward(1, FakeUserSession(self.dummyReceiver_1['id']),
                                   self.source_id, {'target_tid': 2, 'answers': {}}, 'en'),
            errors.ForbiddenOperation)

    @inlineCallbacks
    def test_a_tenant_that_disabled_the_forwarding_is_not_forwarded_to(self):
        yield unpair_tenants(2)

        yield self.assertFailure(self.perform_forward(), errors.ForbiddenOperation)


class TestForwardToTheAcceptingTenant(helpers.TestGLWithPopulatedDB):
    """
    A tenant forwards to the tenant that accepts the forwards: it spends a
    request of forward where one is required and is forwarded to directly where
    it is not, the two conditions the guards and the forward agree upon.
    """
    @inlineCallbacks
    def setUp(self):
        yield helpers.TestGLWithPopulatedDB.setUp(self)

        yield designate_channel_of(1)
        yield designate_channel_of(1, 'forward_request_channel')
        yield pair_tenants(1, 2)

        self.foreign_id = yield create_receiver_of_tenant(2, encryption=True)
        self.source_id = yield create_forwardable_report(2, self.foreign_id)
        self.sender = FakeUserSession(self.foreign_id, can_forward_reports=True)

        yield align_progressive_counter(1)
        yield align_progressive_counter(2)

    def perform_forward(self):
        return forward.create_forward(2, self.sender, self.source_id,
                                      {'target_tid': 1, 'answers': {}}, 'en')

    @inlineCallbacks
    def test_a_tenant_accepting_without_a_request_is_forwarded_to_directly(self):
        yield set_policy_of(1, require_forward_requests=False)

        self.assertTrue((yield accepts_forward_from(1, 2)))

        result = yield self.perform_forward()

        summary = yield get_report_summary(result['id'])
        self.assertEqual(summary['tid'], 1)
        self.assertEqual(summary['type'], 'forward')

    @inlineCallbacks
    def test_a_tenant_requiring_a_request_refuses_a_forward_without_one(self):
        yield set_policy_of(1, require_forward_requests=True)

        self.assertFalse((yield accepts_forward_from(1, 2)))
        yield self.assertFailure(self.perform_forward(), errors.ForbiddenOperation)

    @inlineCallbacks
    def test_the_forward_spends_the_request_that_authorized_it(self):
        yield set_policy_of(1, require_forward_requests=True)
        yield create_forward_request_of_tenant(2, True)
        yield align_progressive_counter(1)

        self.assertTrue((yield accepts_forward_from(1, 2)))

        yield self.perform_forward()

        # the authorization enables a single forward and is spent by it
        self.assertIsNone((yield get_authorized_request(2)))
        self.assertFalse((yield accepts_forward_from(1, 2)))


class TestForwardRequestExecution(helpers.TestGLWithPopulatedDB):
    """
    The request of forward is filed by create_forward_request on the channel
    the accepting tenant designated to receive them.
    """
    @inlineCallbacks
    def setUp(self):
        yield helpers.TestGLWithPopulatedDB.setUp(self)

        self.request_channel_id = yield designate_channel_of(1, 'forward_request_channel')
        yield pair_tenants(1, 2)
        yield set_policy_of(1, require_forward_requests=True)

        self.foreign_id = yield create_receiver_of_tenant(2, encryption=True)
        self.requester = FakeUserSession(self.foreign_id, can_forward_reports=True)

        yield align_progressive_counter(1)

    @inlineCallbacks
    def test_the_request_is_filed_on_the_designated_channel(self):
        result = yield forward.create_forward_request(2, self.requester,
                                                      {'target_tid': 1, 'answers': {}})

        summary = yield get_report_summary(result['id'])
        self.assertEqual(summary['tid'], 1)
        self.assertEqual(summary['type'], 'forward-request')
        self.assertEqual(summary['context_id'], self.request_channel_id)

    @inlineCallbacks
    def test_a_recipient_without_the_permission_does_not_request_a_forward(self):
        yield self.assertFailure(
            forward.create_forward_request(2, FakeUserSession(self.foreign_id),
                                           {'target_tid': 1, 'answers': {}}),
            errors.ForbiddenOperation)

    @inlineCallbacks
    def test_a_tenant_with_a_request_pending_does_not_file_another_one(self):
        yield forward.create_forward_request(2, self.requester, {'target_tid': 1, 'answers': {}})

        yield self.assertFailure(
            forward.create_forward_request(2, self.requester, {'target_tid': 1, 'answers': {}}),
            errors.ForbiddenOperation)


class TestForwardAnswers(helpers.TestGLWithPopulatedDB):
    """
    The answers of a forward are composed by a recipient of another tenant:
    they are validated against the questionnaire of the channel that receives
    them exactly as the ones of a submission are, and the identity of the
    whistleblower is never transferred.
    """
    @inlineCallbacks
    def setUp(self):
        yield helpers.TestGLWithPopulatedDB.setUp(self)

        yield create_receiver_of_tenant(2, encryption=True)
        yield designate_channel_of(2)
        yield pair_tenants(1, 2)

        # the answers are read back as they are stored
        State.tenants[2].cache.encryption = False

        self.source_id = yield create_forwardable_report(1, self.dummyReceiver_1['id'])
        self.sender = FakeUserSession(self.dummyReceiver_1['id'], can_forward_reports=True)
        self.fields = yield get_channel_questionnaire_fields(2)

        yield align_progressive_counter(2)

    def perform_forward(self, answers):
        return forward.create_forward(1, self.sender, self.source_id,
                                      {'target_tid': 2, 'answers': answers}, 'en')

    def a_text_field(self):
        for field_id, field in self.fields.items():
            if field['type'] in ('inputbox', 'textarea'):
                return field_id

        self.fail('the questionnaire carries no text field')

    @inlineCallbacks
    def test_a_key_the_questionnaire_does_not_define_is_never_stored(self):
        field_id = self.a_text_field()

        result = yield self.perform_forward({field_id: [{'value': 'kept'}],
                                             uuid4(): [{'value': 'smuggled under a key'}]})

        answers = yield get_stored_answers(result['id'])
        self.assertIn(field_id, answers)
        self.assertNotIn('smuggled under a key', json.dumps(answers))

    @inlineCallbacks
    def test_the_content_smuggled_into_an_answer_is_never_stored(self):
        field_id = self.a_text_field()

        result = yield self.perform_forward({field_id: [{'value': 'kept',
                                                         'smuggled': 'smuggled into an entry',
                                                         'children': {uuid4(): [{'value': 'nested'}]}}]})

        answers = yield get_stored_answers(result['id'])
        self.assertNotIn('smuggled into an entry', json.dumps(answers))
        self.assertNotIn('nested', json.dumps(answers))

    @inlineCallbacks
    def test_an_answer_the_questionnaire_refuses_is_not_forwarded(self):
        field_id = self.a_text_field()

        yield self.assertFailure(
            self.perform_forward({field_id: [{'value': 'x' * 100000}]}),
            errors.InputValidationError)


class TestForwardAnswersSanitization(unittest.TestCase):
    """
    The identity of the whistleblower is never transferred by a forward,
    wherever the questionnaire of the receiving channel carries it.
    """
    def test_the_identity_of_the_whistleblower_is_never_transferred(self):
        identity_id, nested_identity_id, plain_id = uuid4(), uuid4(), uuid4()

        schema = [{'children': [
            {'id': identity_id, 'template_id': 'whistleblower_identity', 'children': []},
            {'id': plain_id, 'template_id': '', 'children': [
                {'id': nested_identity_id, 'template_id': 'whistleblower_identity', 'children': []}
            ]}
        ]}]

        answers = {identity_id: [{'value': 'the name of the source'}],
                   nested_identity_id: [{'value': 'the address of the source'}],
                   plain_id: [{'value': 'the account of the facts'}]}

        sanitized = forward.sanitize_forward_answers(schema, answers)

        self.assertEqual(sanitized[identity_id], '')
        self.assertEqual(sanitized[nested_identity_id], '')
        self.assertEqual(sanitized[plain_id], [{'value': 'the account of the facts'}])

        # the answers handed over are left untouched
        self.assertEqual(answers[identity_id], [{'value': 'the name of the source'}])


class TestForwardMetadataOfTheSourceReport(helpers.TestGLWithPopulatedDB):
    """
    The report a tenant forwards stays its own report: forwarding it takes
    away none of the operations its recipients perform on it.
    """
    @inlineCallbacks
    def setUp(self):
        yield helpers.TestGLWithPopulatedDB.setUp(self)

        yield create_receiver_of_tenant(2, encryption=True)
        yield designate_channel_of(2)
        yield pair_tenants(1, 2)

        self.source_id = yield create_forwardable_report(1, self.dummyReceiver_1['id'])
        yield align_progressive_counter(2)
        yield forward.create_forward(1, FakeUserSession(self.dummyReceiver_1['id'],
                                                        can_forward_reports=True),
                                     self.source_id, {'target_tid': 2, 'answers': {}}, 'en')

    @inlineCallbacks
    def test_the_forwarding_tenant_keeps_the_metadata_of_its_own_report(self):
        yield set_internaltip_variable(1, self.dummyReceiver_1['id'], self.source_id, 'label', 'x')
        yield set_internaltip_variable(1, self.dummyReceiver_1['id'], self.source_id, 'important', True)
        yield set_reminder(1, self.dummyReceiver_1['id'], self.source_id, 1893456000000)

        report = yield get_serialized_rtip(self.source_id, self.dummyReceiver_1['id'])
        self.assertTrue(report['owned'])
        self.assertTrue(report['important'])
        self.assertNotEqual(report['reminder_date'], datetime_never())


class TestForwardExportedChannel(helpers.TestGLWithPopulatedDB):
    """
    The export of a report carries the channel of the tenant that reads it and
    never the definition of a channel of the other tenant of a forward.
    """
    @inlineCallbacks
    def setUp(self):
        yield helpers.TestGLWithPopulatedDB.setUp(self)

        self.foreign_id = yield create_receiver_of_tenant(2, encryption=True)
        self.target_channel_id = yield designate_channel_of(2)
        self.source_channel_id = yield designate_channel_of(1)
        yield pair_tenants(1, 2)

        self.source_id = yield create_forwardable_report(1, self.dummyReceiver_1['id'])
        yield align_progressive_counter(2)
        result = yield forward.create_forward(1, FakeUserSession(self.dummyReceiver_1['id'],
                                                                 can_forward_reports=True),
                                              self.source_id, {'target_tid': 2, 'answers': {}}, 'en')
        self.target_id = result['id']

    @inlineCallbacks
    def test_the_export_of_the_forwarding_tenant_carries_its_own_channel(self):
        _, tip_export = yield get_tip_export(1, self.dummyReceiver_1['id'], self.target_id, 'en')

        self.assertEqual(tip_export['context']['id'], self.source_channel_id)

    @inlineCallbacks
    def test_the_export_of_the_receiving_tenant_carries_the_channel_of_the_report(self):
        _, tip_export = yield get_tip_export(2, self.foreign_id, self.target_id, 'en')

        self.assertEqual(tip_export['context']['id'], self.target_channel_id)


@transact
def set_forward_templates(session, tid, title, template):
    from globaleaks.models.config import ConfigL10NFactory

    factory = ConfigL10NFactory(session, tid)
    factory.set_val('en', 'forward_mail_title', title)
    factory.set_val('en', 'forward_mail_template', template)


@transact
def get_tenant_name(session, tid):
    from globaleaks.models.config import ConfigFactory
    return ConfigFactory(session, tid).get_val('name')


@transact
def silence_pending_notifications(session):
    """
    Drop the notifications the fixtures leave pending, so that the ones a test
    provokes are the only ones generated
    """
    for model in (models.ReceiverTip, models.Comment,
                  models.ReceiverFile, models.WhistleblowerFile):
        session.query(model).update({'new': False})

    session.query(models.Mail).delete()


@transact
def get_generated_mails(session):
    return [{'tid': mail.tid,
             'address': mail.address,
             'subject': mail.subject,
             'body': mail.body} for mail in session.query(models.Mail)]


class TestForwardNotifications(helpers.TestGLWithPopulatedDB):
    """
    The forward is announced to the recipients of the two tenants it runs
    between, naming the tenant the report has been forwarded to, and it is
    never announced to the recipient that performed it.
    """
    @inlineCallbacks
    def setUp(self):
        yield helpers.TestGLWithPopulatedDB.setUp(self)

        self.foreign_id = yield create_receiver_of_tenant(2, encryption=True)
        yield designate_channel_of(2)
        yield pair_tenants(1, 2)

        # the text of the templates is supplied by the translation pipeline:
        # the announcement is exercised on a text the test states itself
        for tid in (1, 2):
            yield set_forward_templates(tid, 'New forward',
                                        'A report has been forwarded to: {ForwardTenantName}')

        self.source_id = yield create_forwardable_report(1, self.dummyReceiver_1['id'])
        yield grant_access_to_report(self.source_id, self.dummyReceiver_2['id'])
        yield align_progressive_counter(2)

        # the report and its recipients are already known: the announcement of
        # the forward is the only notification the tests provoke
        yield silence_pending_notifications()

        result = yield forward.create_forward(1, FakeUserSession(self.dummyReceiver_1['id'],
                                                                 can_forward_reports=True),
                                              self.source_id, {'target_tid': 2, 'answers': {}}, 'en')
        self.target_id = result['id']

    @inlineCallbacks
    def test_the_forward_is_announced_to_the_recipients_of_both_tenants(self):
        yield MailGenerator(State).generate()

        addresses = [mail['address'] for mail in (yield get_generated_mails())]

        self.assertIn(self.dummyReceiver_2['mail_address'], addresses)
        self.assertIn('recipient-of-tenant-2@example.org', addresses)

        # the recipient that performed the forward is never announced its own
        self.assertNotIn(self.dummyReceiver_1['mail_address'], addresses)

    @inlineCallbacks
    def test_the_announcement_names_the_tenant_the_report_was_forwarded_to(self):
        yield MailGenerator(State).generate()

        mails = yield get_generated_mails()
        self.assertTrue(mails)

        tenant_name = yield get_tenant_name(2)

        for mail in mails:
            self.assertIn('forward', mail['subject'].lower())

        # the body of a recipient holding a PGP key is delivered encrypted and
        # is not readable here: the announcement is read on the ones in clear
        readable = [mail for mail in mails
                    if not mail['body'].startswith('-----BEGIN PGP MESSAGE-----')]
        self.assertTrue(readable)

        for mail in readable:
            self.assertIn(tenant_name, mail['body'])

    @inlineCallbacks
    def test_the_exchange_with_the_whistleblower_notifies_the_receiving_tenant_alone(self):
        # the announcement of the forward is left ungenerated: a report already
        # notified would not be notified again within the same access
        yield silence_pending_notifications()

        yield rtip_create_comment(2, self.foreign_id, self.target_id, 'a message', 'public')
        yield MailGenerator(State).generate()

        addresses = [mail['address'] for mail in (yield get_generated_mails())]

        self.assertNotIn(self.dummyReceiver_1['mail_address'], addresses)
        self.assertNotIn(self.dummyReceiver_2['mail_address'], addresses)

    @inlineCallbacks
    def test_the_space_between_the_tenants_notifies_the_other_side(self):
        yield silence_pending_notifications()

        yield rtip_create_comment(1, self.dummyReceiver_1['id'], self.target_id, 'a message', 'forward')
        yield MailGenerator(State).generate()

        addresses = [mail['address'] for mail in (yield get_generated_mails())]

        self.assertIn('recipient-of-tenant-2@example.org', addresses)
        self.assertNotIn(self.dummyReceiver_1['mail_address'], addresses)
