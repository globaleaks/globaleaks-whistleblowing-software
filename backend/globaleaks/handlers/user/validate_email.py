# Validates the token for email changes


from twisted.internet.defer import inlineCallbacks

from globaleaks import models
from globaleaks.handlers.base import BaseHandler
from globaleaks.orm import tw
from globaleaks.utils.utility import datetime_null


def db_validate_address_change(session, validation_token):
    """Retrieves a user given a mail change validation token"""
    user = session.query(models.User).filter(
        models.User.change_email_token == validation_token
    ).one_or_none()

    if user is None:
        return False

    user.mail_address = user.change_email_address
    user.change_email_token = None
    user.change_email_address = ''
    user.change_email_date = datetime_null()

    return True


class EmailValidation(BaseHandler):
    check_roles = 'any'
    redirect_url = "/#/email/validation/success"

    @inlineCallbacks
    def get(self, validation_token):
        check = yield tw(db_validate_address_change, validation_token)
        if not check:
            self.redirect_url = "/#/email/validation/failure"

        self.redirect(self.redirect_url)
