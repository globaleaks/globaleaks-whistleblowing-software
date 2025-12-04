from globaleaks.utils.utility import uuid4
from globaleaks.rest import errors
from globaleaks.models.config import ConfigFactory


def check_etag(session, tid, request, key, config=None):
    if config is None:
        config = ConfigFactory(session, tid)
    etags = config.get_val("etags")

    req_key = f"etag_{key}"

    if req_key in request and request[req_key] != etags[key]:
        err = errors.ForbiddenOperation()
        err.reason = "CONCURRENT_UPDATE"
        raise err


def update_etag(session, tid, key, config=None):
    if config is None:
        config = ConfigFactory(session, tid)
    etags = config.get_val("etags")

    etags[key] = str(uuid4())
    config.set_val("etags", etags)
