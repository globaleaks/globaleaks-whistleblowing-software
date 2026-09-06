from collections import Counter

from twisted.internet.defer import inlineCallbacks
from twisted.trial import unittest

from globaleaks.handlers import auditlog, auditor
from globaleaks.handlers.admin import auditlog as admin_auditlog
from globaleaks.handlers.recipient import rtip
from globaleaks.jobs.delivery import Delivery
from globaleaks.rest import errors
from globaleaks.tests import helpers

# The implementation of the audit log is shared and exported on two areas: the
# behaviour is exercised on both, so that the two exports cannot drift apart
EXPORTED_HANDLERS = [
    ('AuditLog', auditlog.AuditLogHandler),
    ('AccessLog', auditlog.AccessLogHandler),
    ('DebugLog', auditlog.DebugLogHandler),
    ('JobsTiming', auditlog.JobsTimingHandler),
    ('TipsCollection', auditlog.TipsCollectionHandler),
    ('UsersAudit', auditlog.UsersAuditHandler)
]


class TestExports(unittest.TestCase):
    def test_each_area_binds_the_shared_implementation_to_its_own_role(self):
        for module, role in [(admin_auditlog, 'admin'), (auditor, 'auditor')]:
            for name, implementation in EXPORTED_HANDLERS:
                handler = getattr(module, name)

                # The export adds the role and nothing else: what is served
                # comes from the shared implementation
                self.assertTrue(issubclass(handler, implementation))
                self.assertEqual(handler.check_roles, role)

                # The administrative area scopes who reads the log; the auditor
                # reads it by the role it holds
                expected = 'can_manage_auditlog' if role == 'admin' else None
                self.assertEqual(handler.require_permission, expected)


class AuditLogBehaviour:
    """
    The checks the audit log satisfies on whichever area it is exported; the
    """
    role = None

    def audit_request(self):
        user_id = None if self.role == 'admin' else self.dummy_analyst['id']
        return self.request({}, user_id=user_id, role=self.role)

    @inlineCallbacks
    def test_get(self):
        yield self.perform_full_submission_actions()

        response = yield self.audit_request().get()

        self.assertTrue(isinstance(response, list))

        # A full submission run records, for each of the two reports, its
        # creation, the files attached to it and the comments exchanged on it
        types = Counter(entry['type'] for entry in response)

        self.assertEqual(types['whistleblower_new_report'], 2)
        self.assertEqual(types['whistleblower_add_answers'], 2)
        self.assertEqual(types['whistleblower_upload_file'], 4)
        self.assertEqual(types['whistleblower_add_comment'], 2)
        self.assertEqual(types['add_comment'], 2)
        self.assertEqual(len(response), sum(types.values()))

    @inlineCallbacks
    def test_the_entries_name_who_acted(self):
        yield self.perform_full_submission_actions()

        response = yield self.audit_request().get()

        # The reader reaches no other API: the entries carry the username
        self.assertTrue(all('username' in entry for entry in response))

    def test_get_as_recipient_is_refused(self):
        # The log is read by the two areas that export it and by no other role
        handler = self.request({}, role='receiver')

        return self.assertRaises(errors.NotAuthenticated, handler.get)


class TestAdminAuditLog(AuditLogBehaviour, helpers.TestHandlerWithPopulatedDB):
    _handler = admin_auditlog.AuditLog
    role = 'admin'

    def test_get_without_the_permission_is_refused(self):
        # The log records what everyone did, so the reading is the privilege:
        # an administrator scoped out of the area does not read it
        handler = self.request({}, role='admin', permissions={'can_manage_auditlog': False})

        return self.assertRaises(errors.ForbiddenOperation, handler.get)


class TestAuditorAuditLog(AuditLogBehaviour, helpers.TestHandlerWithPopulatedDB):
    _handler = auditor.AuditLog
    role = 'auditor'

    @inlineCallbacks
    def test_get_holds_no_administrative_permission(self):
        # The auditor reads the log by the role it holds: the permission
        # scoping the administrators says nothing about it
        handler = self.request({},
                               user_id=self.dummy_analyst['id'],
                               role='auditor',
                               permissions={'can_manage_auditlog': False})

        response = yield handler.get()

        self.assertTrue(isinstance(response, list))


class AccessLogBehaviour:
    role = None

    def test_get(self):
        user_id = None if self.role == 'admin' else self.dummy_analyst['id']
        handler = self.request({}, user_id=user_id, role=self.role)

        # During tests the file does not exists but this is enought to test
        return self.assertRaises(errors.ResourceNotFound, handler.get)


class TestAdminAccessLog(AccessLogBehaviour, helpers.TestHandlerWithPopulatedDB):
    _handler = admin_auditlog.AccessLog
    role = 'admin'


class TestAuditorAccessLog(AccessLogBehaviour, helpers.TestHandlerWithPopulatedDB):
    _handler = auditor.AccessLog
    role = 'auditor'


class TestAdminDebugLog(AccessLogBehaviour, helpers.TestHandlerWithPopulatedDB):
    _handler = admin_auditlog.DebugLog
    role = 'admin'


class TestAuditorDebugLog(AccessLogBehaviour, helpers.TestHandlerWithPopulatedDB):
    _handler = auditor.DebugLog
    role = 'auditor'


class TipsCollectionBehaviour:
    role = None

    @inlineCallbacks
    def test_get(self):
        yield self.perform_full_submission_actions()

        user_id = None if self.role == 'admin' else self.dummy_analyst['id']
        handler = self.request({}, user_id=user_id, role=self.role)
        response = yield handler.get()

        self.assertTrue(isinstance(response, list))
        self.assertEqual(len(response), 2)


class TestAdminTipsCollection(TipsCollectionBehaviour, helpers.TestHandlerWithPopulatedDB):
    _handler = admin_auditlog.TipsCollection
    role = 'admin'


class TestAuditorTipsCollection(TipsCollectionBehaviour, helpers.TestHandlerWithPopulatedDB):
    _handler = auditor.TipsCollection
    role = 'auditor'


class UsersAuditBehaviour:
    role = None

    @inlineCallbacks
    def test_get(self):
        user_id = None if self.role == 'admin' else self.dummy_analyst['id']
        handler = self.request({}, user_id=user_id, role=self.role)
        response = yield handler.get()

        self.assertTrue(isinstance(response, list))

        # The audit view of an account carries what the oversight looks at and
        # nothing of the configuration of the account itself
        for user in response:
            self.assertEqual(sorted(user.keys()),
                             ['creation_date', 'id', 'last_login', 'name', 'role', 'two_factor', 'username'])


class TestAdminUsersAudit(UsersAuditBehaviour, helpers.TestHandlerWithPopulatedDB):
    _handler = admin_auditlog.UsersAudit
    role = 'admin'


class TestAuditorUsersAudit(UsersAuditBehaviour, helpers.TestHandlerWithPopulatedDB):
    _handler = auditor.UsersAudit
    role = 'auditor'


class JobsTimingBehaviour:
    role = None

    @inlineCallbacks
    def test_get(self):
        user_id = None if self.role == 'admin' else self.dummy_analyst['id']
        handler = self.request({}, user_id=user_id, role=self.role)

        yield handler.get()


class TestAdminJobsTiming(JobsTimingBehaviour, helpers.TestHandler):
    _handler = admin_auditlog.JobsTiming
    role = 'admin'


class TestAuditorJobsTiming(JobsTimingBehaviour, helpers.TestHandler):
    _handler = auditor.JobsTiming
    role = 'auditor'


class TestReportAuditLog(helpers.TestHandlerWithPopulatedDB):
    """
    The audit log of a single report, read by whoever the report belongs to.
    """
    _handler = rtip.ReportAuditLog

    # what a recipient deletes from a report leaves on the log of the
    # report the fingerprints of what has been taken away, so that what is no
    # longer there stays verifiable.
    @inlineCallbacks
    def test_a_deleted_file_leaves_its_fingerprints_on_the_log_of_the_report(self):
        yield self.perform_full_submission_actions()
        yield Delivery().run()

        rtips_desc = yield self.get_rtips()
        rtip_desc = rtips_desc[0]

        # the recipient attaches a file of its own and then takes it away
        self._handler = rtip.ReceiverFileUpload
        handler = self.request(role='receiver',
                               user_id=rtip_desc['receiver_id'],
                               attachment=self.get_dummy_attachment(content=b'Hello World'))
        yield handler.post(rtip_desc['id'])

        rtips_desc = yield self.get_rtips()
        rfile_id = rtips_desc[0]['rfiles'][0]['id']

        self._handler = rtip.ReceiverFileDownload
        handler = self.request(role='receiver', user_id=rtip_desc['receiver_id'])
        yield handler.delete(rfile_id)

        self._handler = rtip.ReportAuditLog
        handler = self.request(role='receiver', user_id=rtip_desc['receiver_id'])
        logs = yield handler.get(rtip_desc['id'])

        deletions = [entry for entry in logs if entry['type'] == 'delete_file']
        self.assertEqual(len(deletions), 1)

        # the entry stays in the log of the report although the row it attests
        # is gone: what it names is the report, and the file inside itself
        self.assertEqual(deletions[0]['object_id'], rtip_desc['id'])
        self.assertEqual(deletions[0]['data']['file_id'], rfile_id)

        # and the fingerprints reach the reader opened, as the digests they are
        self.assertEqual(len(deletions[0]['data']['hash_sha256']), 64)
        self.assertEqual(len(deletions[0]['data']['hash_sha512']), 128)
