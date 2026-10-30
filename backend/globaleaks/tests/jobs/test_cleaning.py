import os
from datetime import timedelta

from twisted.internet.defer import inlineCallbacks

from globaleaks import models
from globaleaks.handlers.admin import invite
from globaleaks.jobs import cleaning, delivery
from globaleaks.orm import transact
from globaleaks.sessions import Sessions
from globaleaks.settings import Settings
from globaleaks.tests import helpers
from globaleaks.utils.fs import get_storage_path
from globaleaks.utils.utility import datetime_now


class TestCleaning(helpers.TestGLWithPopulatedDB):
    @transact
    def check0(self, session):
        self.assertEqual(len(os.listdir(get_storage_path(1, 'attachments', create=True))), 0)
        self.assertEqual(len(os.listdir(Settings.tmp_path)), 0)

        self.db_test_model_count(session, models.InternalTip, 0)
        self.db_test_model_count(session, models.ReceiverTip, 0)
        self.db_test_model_count(session, models.InternalFile, 0)
        self.db_test_model_count(session, models.WhistleblowerFile, 0)
        self.db_test_model_count(session, models.Comment, 0)
        self.db_test_model_count(session, models.Mail, 0)

    @transact
    def check1(self, session):
        self.assertEqual(len(os.listdir(get_storage_path(1, 'attachments', create=True))), self.population_of_submissions * self.population_of_attachments)

        self.db_test_model_count(session, models.InternalTip, self.population_of_submissions)
        self.db_test_model_count(session, models.ReceiverTip, self.population_of_recipients * self.population_of_submissions)
        self.db_test_model_count(session, models.InternalFile, self.population_of_submissions * self.population_of_attachments)
        self.db_test_model_count(session, models.WhistleblowerFile, self.population_of_submissions * self.population_of_attachments * self.population_of_recipients)
        self.db_test_model_count(session, models.Comment, 4)
        self.db_test_model_count(session, models.Mail, 0)

    @transact
    def check2(self, session):
        self.assertEqual(len(os.listdir(get_storage_path(1, 'attachments', create=True))), 0)

        self.db_test_model_count(session, models.InternalTip, 0)
        self.db_test_model_count(session, models.ReceiverTip, 0)
        self.db_test_model_count(session, models.InternalFile, 0)
        self.db_test_model_count(session, models.WhistleblowerFile, 0)
        self.db_test_model_count(session, models.Comment, 0)
        self.db_test_model_count(session, models.Mail, 0)

    @inlineCallbacks
    def test_job(self):
        # verify that the system starts clean
        yield self.check0()

        yield self.perform_full_submission_actions()

        yield delivery.Delivery().run()

        # verify tip creation
        yield self.check1()

        # mark files as uploaded on timestamp 0
        for f in os.listdir(get_storage_path(1, 'attachments', create=True)):
            path = os.path.join(get_storage_path(1, 'attachments', create=True), f)
            os.utime(path, (0, 0))

        yield cleaning.Cleaning().run()

        # verify tips survive the scheduler if they are not expired
        yield self.check1()

        yield self.set_itips_expiration_as_expired()

        yield cleaning.Cleaning().run()

        # verify cascade deletion when tips expire
        yield self.check2()

    @inlineCallbacks
    def test_job_removes_storage_of_missing_tenant(self):
        path = get_storage_path(999, 'attachments', 'untracked', create=True)
        with open(path, 'wb') as f:
            f.write(b'untracked')

        yield cleaning.Cleaning().run()

        self.assertFalse(os.path.exists(os.path.join(Settings.tenants_path, '999')))

    @inlineCallbacks
    def test_job_ignores_non_numeric_storage_entries(self):
        path = os.path.join(Settings.tenants_path, 'unexpected')
        os.mkdir(path)
        with open(os.path.join(path, 'file'), 'wb') as f:
            f.write(b'keep')

        yield cleaning.Cleaning().run()

        with open(os.path.join(path, 'file'), 'rb') as f:
            self.assertEqual(f.read(), b'keep')

    @inlineCallbacks
    def test_job_keeps_tracked_file_under_wrong_tenant(self):
        yield self.perform_full_submission_actions()
        yield delivery.Delivery().run()

        file_id = os.listdir(get_storage_path(1, 'attachments'))[0]
        path = get_storage_path(2, 'attachments', file_id, create=True)
        with open(path, 'wb') as f:
            f.write(b'misplaced')
        os.utime(path, (0, 0))

        yield cleaning.Cleaning().run()

        with open(path, 'rb') as f:
            self.assertEqual(f.read(), b'misplaced')

    @inlineCallbacks
    def test_job_unlinks_storage_symlinks_without_following_them(self):
        target = os.path.join(Settings.working_path, 'target')
        os.mkdir(target)
        with open(os.path.join(target, 'file'), 'wb') as f:
            f.write(b'keep')
        link = get_storage_path(1, 'attachments', 'link', create=True)
        os.symlink(target, link)
        os.symlink(target, os.path.join(Settings.tenants_path, '999'))

        yield cleaning.Cleaning().run()

        self.assertFalse(os.path.lexists(link))
        self.assertFalse(os.path.lexists(os.path.join(Settings.tenants_path, '999')))
        with open(os.path.join(target, 'file'), 'rb') as f:
            self.assertEqual(f.read(), b'keep')

    @transact
    def age_invites(self, session, days):
        session.query(models.Subscriber) \
               .update({'registration_date': datetime_now() - timedelta(days=days)})

    @transact
    def count_invites(self, session):
        return session.query(models.Subscriber).count()

    @inlineCallbacks
    def test_an_invitation_lasts_a_week(self):
        session = Sessions.new(1, self.dummy_admin['id'], 1, 'admin', 'admin')

        yield invite.create_invite(1, session, {'organization_name': 'Invited Organization',
                                                'email': 'invited@example.org',
                                                'mail_template': ''}, 'en')

        yield self.age_invites(6)
        yield cleaning.Cleaning().run()

        self.assertEqual((yield self.count_invites()), 1)

        yield self.age_invites(8)
        yield cleaning.Cleaning().run()

        self.assertEqual((yield self.count_invites()), 0)


    @inlineCallbacks
    def test_job_unlinks_storage_directory_symlinks(self):
        target = get_storage_path(1, 'files', 'keep', create=True)
        with open(target, 'wb') as stream:
            stream.write(b'keep')
        path = get_storage_path(1, 'attachments', create=True)
        os.rename(path, os.path.join(Settings.tmp_path, 'saved-attachments'))
        os.symlink(get_storage_path(1, 'files'), path)
        orphan = get_storage_path(999, 'attachments', 'untracked', create=True)
        with open(orphan, 'wb') as stream:
            stream.write(b'remove')
        yield cleaning.Cleaning().run()
        self.assertFalse(os.path.lexists(path))
        self.assertFalse(os.path.exists(os.path.dirname(os.path.dirname(orphan))))
        with open(target, 'rb') as stream:
            self.assertEqual(stream.read(), b'keep')
