import copy

from twisted.internet.defer import inlineCallbacks

from globaleaks import models
from globaleaks.handlers.admin.user_profile import sync_permissions
from globaleaks.handlers.recipient import rtip
from globaleaks.orm import transact
from globaleaks.rest import errors
from globaleaks.tests import helpers
from globaleaks.utils.utility import uuid4


@transact
def set_identity_permissions(session, user_id, view, request):
    user = session.get(models.User, user_id)
    permissions = {key: True for key in user.permissions_list}
    permissions['can_view_whistleblower_identity'] = view
    permissions['can_request_whistleblower_identity'] = request
    sync_permissions(session, user.profile, {'permissions': permissions})


@transact
def disable_custodians(session):
    session.query(models.User).filter(models.User.role == 'custodian').update({'enabled': False})


@transact
def identity_fixture(session, itip_id, receiver_id, authorized):
    existing = session.query(models.InternalTipData).filter_by(internaltip_id=itip_id,
                                                              key='whistleblower_identity').first()
    if existing is None:
        existing = models.InternalTipData()
        existing.internaltip_id = itip_id
        existing.key = 'whistleblower_identity'
        session.add(existing)
    existing.value = {'name': [{'value': 'Private identity'}]}
    existing.hash_sha256 = 'private-fingerprint'
    existing.hash_sha512 = 'private-fingerprint'

    if authorized:
        iar = models.IdentityAccessRequest()
        iar.internaltip_id = itip_id
        iar.request_user_id = receiver_id
        iar.reply = 'authorized'
        session.add(iar)

    archived = session.query(models.ArchivedSchema).join(
        models.InternalTipAnswers, models.InternalTipAnswers.questionnaire_hash == models.ArchivedSchema.hash
    ).filter(models.InternalTipAnswers.internaltip_id == itip_id).first()
    field_id = uuid4()
    schema = copy.deepcopy(archived.schema)
    schema[0]['children'].append({'id': uuid4(), 'type': 'fieldgroup',
                                  'template_id': 'whistleblower_identity',
                                  'children': [{'id': field_id, 'type': 'fileupload', 'children': []}]})
    archived.schema = schema
    receiver_tip = session.query(models.ReceiverTip).filter_by(internaltip_id=itip_id, receiver_id=receiver_id).one()
    file = models.InternalFile()
    file.internaltip_id = itip_id
    file.name = 'Identity attachment'
    file.content_type = 'text/plain'
    file.size = 1
    file.reference_id = field_id
    session.add(file)
    session.flush()
    wbfile = models.WhistleblowerFile()
    wbfile.internalfile_id = file.id
    wbfile.receivertip_id = receiver_tip.id
    session.add(wbfile)
    session.flush()
    return wbfile.id


class TestIdentityPermissions(helpers.TestHandlerWithPopulatedDB):
    _handler = rtip.IdentityAccessRequestsCollection

    @inlineCallbacks
    def setUp(self):
        yield super().setUp()
        yield self.perform_minimal_submission_actions()
        reports = yield self.get_rtips()
        self.report_id = reports[0]['id']
        self.receiver_id = self.dummy_receiver_1['id']

    def identity_request(self):
        handler = self.request({'request_motivation': 'Reason'}, role='receiver', user_id=self.receiver_id)
        return handler.post(self.report_id)

    @inlineCallbacks
    def test_request_requires_request_permission_with_custodian(self):
        yield set_identity_permissions(self.receiver_id, True, False)
        yield self.assertFailure(self.identity_request(), errors.ForbiddenOperation)

    @inlineCallbacks
    def test_request_requires_view_permission(self):
        yield set_identity_permissions(self.receiver_id, False, False)
        yield self.assertFailure(self.identity_request(), errors.ForbiddenOperation)

    @inlineCallbacks
    def test_invalid_permission_combination_is_rejected(self):
        yield self.assertFailure(set_identity_permissions(self.receiver_id, False, True), errors.InputValidationError)

    @inlineCallbacks
    def test_allowed_request_remains_pending_with_custodian(self):
        request = yield self.identity_request()
        self.assertEqual(request['reply'], 'pending')

    @inlineCallbacks
    def test_view_only_recipient_can_show_identity_without_custodian(self):
        yield disable_custodians()
        yield set_identity_permissions(self.receiver_id, True, False)
        request = yield self.identity_request()
        self.assertEqual(request['reply'], 'authorized')

    @inlineCallbacks
    def test_hidden_identity_and_hashes_are_withheld_after_report_authorization(self):
        file_id = yield identity_fixture(self.report_id, self.receiver_id, True)
        yield set_identity_permissions(self.receiver_id, False, False)
        report, _ = yield rtip.get_rtip(1, self.receiver_id, self.report_id, 'en')
        self.assertNotIn('whistleblower_identity', report['data'])
        self.assertNotIn('whistleblower_identity_hash_sha256', report['data'])
        self.assertNotIn('whistleblower_identity_hash_sha512', report['data'])
        self.assertFalse(report['can_view_whistleblower_identity'])
        self.assertFalse(report['can_request_whistleblower_identity'])
        self.assertNotIn(file_id, [file['id'] for file in report['wbfiles']])

    @inlineCallbacks
    def test_authorization_is_shared_only_with_permitted_recipients(self):
        yield identity_fixture(self.report_id, self.receiver_id, True)
        yield set_identity_permissions(self.receiver_id, False, False)
        other = self.dummy_receiver_2['id']
        report, _ = yield rtip.get_rtip(1, other, self.report_id, 'en')
        self.assertIn('whistleblower_identity', report['data'])
        self.assertTrue(report['can_view_whistleblower_identity'])

    @inlineCallbacks
    def test_view_permission_does_not_bypass_custodian_approval(self):
        file_id = yield identity_fixture(self.report_id, self.receiver_id, False)
        report, _ = yield rtip.get_rtip(1, self.receiver_id, self.report_id, 'en')
        self.assertNotIn('whistleblower_identity', report['data'])
        self.assertNotIn(file_id, [file['id'] for file in report['wbfiles']])

    @inlineCallbacks
    def test_direct_identity_file_download_is_blocked_without_view_permission(self):
        file_id = yield identity_fixture(self.report_id, self.receiver_id, True)
        yield set_identity_permissions(self.receiver_id, False, False)
        handler = self.request(role='receiver', user_id=self.receiver_id,
                               handler_cls=rtip.WhistleblowerFileDownload)
        yield self.assertFailure(handler.download_wbfile(1, self.receiver_id, file_id), errors.ForbiddenOperation)

    @inlineCallbacks
    def test_direct_identity_file_download_requires_approval(self):
        file_id = yield identity_fixture(self.report_id, self.receiver_id, False)
        handler = self.request(role='receiver', user_id=self.receiver_id,
                               handler_cls=rtip.WhistleblowerFileDownload)
        yield self.assertFailure(handler.download_wbfile(1, self.receiver_id, file_id), errors.ForbiddenOperation)

    @inlineCallbacks
    def test_direct_identity_file_download_is_allowed_with_permission_and_approval(self):
        file_id = yield identity_fixture(self.report_id, self.receiver_id, True)
        handler = self.request(role='receiver', user_id=self.receiver_id,
                               handler_cls=rtip.WhistleblowerFileDownload)
        response = yield handler.download_wbfile(1, self.receiver_id, file_id)
        self.assertEqual(response[0], 'Identity attachment')
