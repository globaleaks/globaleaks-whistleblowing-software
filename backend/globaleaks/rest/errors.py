# -*- coding: utf-8
#
#   errors
#   ******
#
# Here shall go all the error messages that a GLBackend can generate.
# GLException is the class inherit by the other Errors, and define the
# class variables expected in the Error handler routine


class GLException(Exception):
    reason = "GLTypesError not set"
    log_message = "GLException"
    error_code = 0
    status_code = 500  # generic Server error

    def __str__(self):
        return self.__repr__()

    def __repr__(self):
        return "%s: <<%s>> (%d) HTTP:%d" % (
            self.__class__.__name__, self.reason,
            self.error_code, self.status_code
        )


class InternalServerError(GLException):
    """
    Internal server error
    """
    error_code = 1
    status_code = 500  # Internal Server Error

    def __init__(self, error_str):
        self.reason = "InternalServerError [%s]" % error_str
        self.arguments = [error_str]


class MethodNotImplemented(GLException):
    """
    The expected format described in the REST specification is not
    respected by the data body in the HTTP request.
    """
    error_code = 2
    status_code = 501  # Not implemented

    def __init__(self):
        self.reason = "Method not implemented"


class InputValidationError(GLException):
    """
    Error on input validation
    """
    error_code = 3
    status_code = 406  # Not Acceptable

    def __init__(self, error=''):
        self.reason = "Invalid Input [%s]" % error
        self.arguments = [error]


class TwoFactorAuthCodeRequired(GLException):
    """
    Error signaling need for two factor auth token
    """
    reason = "Two Factor authentication required"
    error_code = 4
    status_code = 300


class SessionExpired(GLException):
    reason = "Session expired"
    error_code = 5
    status_code = 401


class ResourceNotFound(GLException):
    """
    Resource not found
    """
    reason = "Resource not found"
    error_code = 6
    status_code = 404  # Not Found


class ForbiddenOperation(GLException):
    """
    A user has tried one operation not permitted by their privileges
    """
    reason = "Operation Forbidden"
    error_code = 8
    status_code = 403  # Forbidden


class InvalidAuthentication(GLException):
    """
    An invalid request was presented
    """
    reason = "Authentication Failed"
    error_code = 9
    status_code = 401  # Unauthorized


class NotAuthenticated(GLException):
    """
    The user attempted to access a not-authorized request. The output messages
    may contain reasons about the Authentication failure, but they are specify
    only if users has show knowledge of good credentials.
    """
    error_code = 10
    status_code = 412  # Precondition Failed
    reason = "Not Authenticated"


class PasswordReuseError(GLException):
    """
    Error signaling that the choosen new password is already used
    """
    reason = "The new password must differ from the previous."
    error_code = 11
    status_code = 406


class InvalidOldPassword(GLException):
    """
    Error signaling that the provided old password is wrong
    """
    reason = "The specified old password is not valid"
    error_code = 12
    status_code = 406


class InvalidTwoFactorAuthCode(GLException):
    """
    Error signaling that the inserted two factor auth token is wrong
    """
    reason = "Two Factor authentication required"
    error_code = 13
    status_code = 406


class TorNetworkRequired(GLException):
    """
    A connection receiver not via Tor network is required to
    be enforced with anonymity
    """
    reason = "Resource can be accessed only within Tor network"
    error_code = 13
    status_code = 403  # Forbidden


class FileTooBig(GLException):
    """
    Raised when the uploaded file is bigger than acceptable
    """
    error_code = 13
    status_code = 413  # Bad Request

    def __init__(self, size_limit):
        self.reason = ("Provided file upload overcomes size limits (%d Mb)" %
                       size_limit)
        self.arguments = [size_limit]


class DirectoryTraversalError(GLException):
    """
    Blocked file operation out of the expected path
    """
    reason = "Blocked file operation out of the expected path"
    error_code = 14
    status_code = 403


class SubmissionDisabled(GLException):
    reason = "Submissions are disabled"
    error_code = 15
    status_code = 503  # Service not available


class AccessLocationInvalid(GLException):
    reason = "IP Address not allows to login from this location"
    error_code = 16
    status_code = 401


class DuplicateUserError(GLException):
    reason = "A user with this username already exists"
    error_code = 17
    status_code = 422


class FileInfectedDownloadPermissionDenied(GLException):
    """
    User lacks download permissions.
    """
    reason = "User lacks download permissions."
    error_code = 18
    status_code = 403


class FilePendingDownloadPermissionDenied(GLException):
    """
    Files in pending cannot be downloaded.
    """
    reason = "Files in pending cannot be downloaded."
    error_code = 19
    status_code = 403
