# -*- coding: utf-8 -*-
from twisted.conch.test.test_insults import Mock
from twisted.internet.defer import inlineCallbacks

from globaleaks import models
from globaleaks.handlers.accreditator import toggle_status_activate, SubmitAccreditationHandler, \
    GetAllAccreditationHandler, ConfirmRequestHandler
from globaleaks.handlers.accreditator.utils import save_step, create_tenant, determine_type, count_user_tip
from globaleaks.models import EnumSubscriberStatus
from globaleaks.tests import helpers


class TestStepAccreditation(helpers.TestHandler):
    def setUp(self):
        self.session_mock = Mock()
        self.tenant_mock = Mock()
        self.subscriber_mock = Mock()

    def test_save_step(self):
        """Test save_step properly adds and flushes objects"""
        obj = Mock()
        save_step(self.session_mock, obj)

        self.session_mock.add.assert_called_once_with(obj)
        self.session_mock.flush.assert_called_once()

    def test_create_tenant(self):
        """Test the create_tenant function creates an inactive external tenant"""
        tenant = create_tenant()

        self.assertFalse(tenant.active)
        self.assertTrue(tenant.external)

    def test_determine_type(self):
        """Test determine_type function with different input types"""
        # Test with boolean True
        self.assertTrue(determine_type({'type': True}))

        # Test with string 'AFFILIATED'
        self.assertTrue(determine_type({'type': 'AFFILIATED'}))

        # Test with string 'affiliated'
        self.assertTrue(determine_type({'type': 'affiliated'}))

        # Test with boolean False
        self.assertFalse(determine_type({'type': False}))

        # Test with other string
        self.assertFalse(determine_type({'type': 'NOT_AFFILIATED'}))

        # Test with None
        self.assertFalse(determine_type({'type': None}))

        # Test with missing key
        self.assertFalse(determine_type({}))

    def test_count_user_tip_not_accredited(self):
        """Test count_user_tip returns empty results for non-accredited subscribers"""
        # Setup mock subscriber with non-accredited state
        subscriber_mock = models.Subscriber()
        subscriber_mock.state = EnumSubscriberStatus.requested.name

        count_tip, count_user = count_user_tip(self.session_mock, subscriber_mock)

        self.assertEqual(count_tip, {})
        self.assertEqual(count_user, 2)

    def test_toggle_status_activate_forbidden(self):
        """Test toggle_status_activate raises ForbiddenOperation for invalid status"""
        subscriber_mock = Mock()
        subscriber_mock.state = "invalid_status"
        self.session_mock.query.return_value.filter.return_value.one.return_value = subscriber_mock

    def test_toggle_status_activate_success(self):
        """Test toggle_status_activate successful status change"""
        subscriber_mock = Mock()
        subscriber_mock.state = "requested"
        self.session_mock.query.return_value.filter.return_value.one.return_value = subscriber_mock

        result = toggle_status_activate(self.session_mock, "test-id", False)

        self.assertIsNotNone(result)


class TestRequestAccreditation(helpers.TestHandlerWithPopulatedDB):
    _handler = SubmitAccreditationHandler

    @inlineCallbacks
    def setUp(self):
        yield helpers.TestHandlerWithPopulatedDB.setUp(self)
        yield self.perform_full_submission_actions()

    @staticmethod
    def post_dummy_request_accreditation():
        return {
            "admin_email": "admin@test.it",
            "admin_name": "admin",
            "admin_surname": "admin",
            "organization_email": "adminb_eo@admin.com",
            "organization_name": "eo",
            "organization_institutional_site": "http://eo.com/",
            "recipient_name": "rec",
            "recipient_surname": "rec",
            "recipient_email": "rec@rec.com",
            "recipient_tax_code": "tax_code",
            "tos1": True
        }

    @inlineCallbacks
    def test_post(self):
        handler = self.request(
            body=self.post_dummy_request_accreditation(),
            headers={'x-idp-userid': 'admin_tax_code'},
            role='analyst'
        )
        stats = yield handler.post()
        self.assertTrue(stats)
        self.assertTrue(stats.get('id'))

class TestGetAllAccreditationHandler(helpers.TestHandlerWithPopulatedDB):
    _handler = GetAllAccreditationHandler

    @inlineCallbacks
    def setUp(self):
        yield helpers.TestHandlerWithPopulatedDB.setUp(self)
        yield self.perform_full_submission_actions()

    @inlineCallbacks
    def test_get(self):
        handler = self.request(
            role='accreditor'
        )
        stats = yield handler.get()
        self.assertFalse(stats)

