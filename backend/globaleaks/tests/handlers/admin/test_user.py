# -*- coding: utf-8 -*-
from globaleaks import models
from globaleaks.handlers.admin import user
from globaleaks.tests import helpers


class TestAdminCollection(helpers.TestCollectionHandler):
    _handler = user.UsersCollection
    _test_desc = {
        'model': models.User,
        'create': user.create_user,
        'data': {
            'role': 'admin',
            'name': 'Mario Rossi',
            'mail_address': 'admin@theguardian.com',
            'language': 'en',
            'wizard': True
        }
    }

    def get_dummy_request(self):
        data = helpers.TestCollectionHandler.get_dummy_request(self)
        data['pgp_key_remove'] = False
        return data


class TestAdminInstance(helpers.TestInstanceHandler):
    _handler = user.UserInstance
    _test_desc = {
        'model': models.User,
        'create': user.create_user,
        'data': {
            'role': 'admin',
            'mail_address': 'admin@theguardian.com',
            'language': 'en'
        }
    }

    def get_dummy_request(self):
        data = helpers.TestInstanceHandler.get_dummy_request(self)
        data['pgp_key_remove'] = False
        return data


class TestReceiverCollection(TestAdminCollection):
    _test_desc = {
        'model': models.User,
        'create': user.create_user,
        'data': {
            'role': 'receiver',
            'name': 'Mario Rossi',
            'mail_address': 'receiver@theguardian.com',
            'language': 'en'
        }
    }


class TestReceiverInstance(TestAdminInstance):
    _test_desc = {
        'model': models.User,
        'create': user.create_user,
        'data': {
            'role': 'receiver',
            'name': 'Mario Rossi',
            'mail_address': 'receiver@theguardian.com',
            'language': 'en',
            'forcefully_selected': True
        }
    }


class TestCustodianCollection(TestAdminCollection):
    _test_desc = {
        'model': models.User,
        'create': user.create_user,
        'data': {
            'role': 'custodian',
            'name': 'Mario Rossi',
            'mail_address': 'custodian@theguardian.com',
            'language': 'en'
        }
    }


class TestCustodianInstance(TestAdminInstance):
    _test_desc = {
        'model': models.User,
        'create': user.create_user,
        'data': {
            'role': 'custodian',
            'mail_address': 'custodian@theguardian.com',
            'language': 'en'
        }
    }
