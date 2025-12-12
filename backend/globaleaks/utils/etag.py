from globaleaks.rest import errors

def check_etag(current_etag, previous_etag):

    if current_etag != previous_etag:
        err = errors.ForbiddenOperation()
        err.reason = "CONCURRENT_UPDATE"
        raise err