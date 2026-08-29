from globaleaks.handlers.base import BaseHandler
from globaleaks.rest import errors, requests


class OperationHandler(BaseHandler):
    """
    Base handler for implementing handlers for executing platform configuration
    """
    require_confirmation = []

    # Optional per-operation permission map: when non-empty every operation must be listed and the
    # session must hold the mapped permission
    operation_permissions = {}

    def operation_descriptors(self):
        raise NotImplementedError

    def put(self, *args, **kwargs):
        request = self.validate_request(self.request.content.read(), requests.OpsDesc)

        if self.operation_permissions:
            permission = self.operation_permissions.get(request['operation'])
            if not permission or not (self.session and self.session.has_permission(permission)):
                raise errors.ForbiddenOperation

        if request['operation'] in self.require_confirmation:
            self.check_confirmation()

        func = self.operation_descriptors().get(request['operation'], None)
        if func:
            return func(self, request['args'], *args, **kwargs)
