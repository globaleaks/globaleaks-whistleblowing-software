from globaleaks.handlers.base import BaseHandler
from globaleaks.rest import requests


class OperationHandler(BaseHandler):
    """
    Base handler for implementing handlers for executing platform configuration
    """
    require_confirmation = []

    def operation_descriptors(self):
        raise NotImplementedError

    def put(self, *args, **kwargs):
        request = self.validate_request(self.request.content.read(), requests.OpsDesc)

        if request['operation'] in self.require_confirmation:
            self.check_confirmation()

        func = self.operation_descriptors().get(request['operation'], None)
        if func:
            return func(self, request['args'], *args, **kwargs)
