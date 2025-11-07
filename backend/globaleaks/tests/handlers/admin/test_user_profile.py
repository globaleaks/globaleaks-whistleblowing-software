from globaleaks import models
from globaleaks.handlers.admin import user
from globaleaks.handlers.admin import user_profile
from globaleaks.tests import helpers


class TestUserProfilesCollection(helpers.TestCollectionHandler):
    _handler = user_profile.UserProfilesCollection
    _test_desc = {
        'model': models.UserProfile,
        'create': user_profile.create_user_profile,
        'data': {}
    }

    def get_dummy_request(self):
        data = helpers.TestCollectionHandler.get_dummy_request(self)
        data['roles'] = ['admin']
        data['permissions'] = user.user_permissions
        return data


class TestUserProfileInstance(helpers.TestInstanceHandler):
    _handler = user_profile.UserProfileInstance
    _test_desc = {
        'model': models.UserProfile,
        'create': user_profile.create_user_profile,
        'data': {}
    }

    def get_dummy_request(self):
        data = helpers.TestInstanceHandler.get_dummy_request(self)
        data['role'] = 'admin'
        data['roles'] = ['admin']
        data['permissions'] = user.user_permissions
        return data
