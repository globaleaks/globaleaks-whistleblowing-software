# Handlers dealing with the reports a recipient enters on its own site
import os

from nacl.encoding import Base64Encoder

from globaleaks import models
from globaleaks.handlers.admin.questionnaire import db_get_questionnaire
from globaleaks.handlers.auth import db_receipt_auth_is_legacy
from globaleaks.handlers.base import BaseHandler
from globaleaks.handlers.whistleblower.submission import db_create_submission
from globaleaks.models import get_localized_values
from globaleaks.orm import transact
from globaleaks.rest import errors, requests
from globaleaks.utils.crypto import GCE
from globaleaks.utils.objectdict import ObjectDict


def db_insertion_channels(session, tid):
    """
    Return the channels of a site a report can be entered on

    A report is entered on the channels the site declares available to the
    users that file on it themselves: a channel of the exchanges receives what
    the other sites file and is never one of them.

    :param session: An ORM session
    :param tid: The tenant ID
    :return: The channels the site enters its reports on
    """
    return session.query(models.Context) \
                  .filter(models.Context.tid == tid,
                          models.Context.exchange == False,
                          models.Context.internally_available == True) \
                  .order_by(models.Context.order) \
                  .all()


def db_get_insertion_options(session, tid, channel_id, language):
    """
    Return the channels a report may be entered on and the way it is composed

    The channel is chosen among the ones of the site and composes the report
    with its own questionnaire: a single channel is the one chosen, and there
    is nothing to choose.

    :param session: An ORM session
    :param tid: The tenant ID
    :param channel_id: The channel chosen by the recipient
    :param language: The language the channels are named in
    :return: The channels offered and the questionnaire of the chosen one
    """
    channels = db_insertion_channels(session, tid)

    ret = {
        'channels': [{'id': channel.id,
                      'name': get_localized_values({}, channel, ['name'], language)['name'],
                      'provide_access_code': channel.provide_access_code}
                     for channel in channels],
        'channel_id': '',
        'questionnaire': None
    }

    chosen = None
    for channel in channels:
        if channel.id == channel_id:
            chosen = channel

    if chosen is None and len(channels) == 1:
        chosen = channels[0]

    if chosen is None:
        return ret

    ret['channel_id'] = chosen.id
    ret['questionnaire'] = db_get_questionnaire(session, tid,
                                                chosen.questionnaire_id,
                                                language, True)

    return ret


def db_discarded_receipt(session, tid):
    """
    Return a receipt drawn by the server and handed to no one

    :param session: An ORM session
    :param tid: The tenant ID
    :return: A receipt in the form the tenant keys its reports by
    """
    if db_receipt_auth_is_legacy(session, tid):
        return GCE.generate_receipt()

    return Base64Encoder.encode(os.urandom(32)).decode()


def db_channel_receivers(session, channel):
    """
    Return the recipients a report entered on a channel is handed to

    They are the ones the channel hands its reports to, as the reporting
    people would reach them: the recipients selection is not offered here, and
    the selection is the one the channel makes by default.

    :param session: An ORM session
    :param channel: The channel the report is entered on
    :return: The recipients of the report
    """
    receivers = []
    mandatory = []

    for receiver_id, forcefully_selected in \
            session.query(models.ReceiverContext.receiver_id,
                          models.User.forcefully_selected) \
                   .filter(models.ReceiverContext.context_id == channel.id,
                           models.User.id == models.ReceiverContext.receiver_id,
                           models.User.role == 'receiver',
                           models.User.enabled.is_(True)):
        receivers.append(receiver_id)
        if forcefully_selected:
            mandatory.append(receiver_id)

    return receivers if channel.select_all_receivers else mandatory


@transact
def get_insertion_options(session, tid, user_session, channel_id, language):
    """
    Return what entering a report on the site is composed of
    """
    # The attachments are held on the session until the report is entered:
    # opening a new composition drops the ones left over by a previous one
    user_session.files = []

    return db_get_insertion_options(session, tid, channel_id, language)


@transact
def create_inserted_report(session, tid, user_session, request, language):
    """
    Enter on the site the report composed by one of its recipients

    What is entered is a report of the site as any other: it lives on the
    channel it is entered on and reaches the recipients of it, and the
    recipient that entered it is recorded as the operator of it, as it is
    when a report is filed on behalf of a reporting person.
    """
    channel = None
    for entry in db_insertion_channels(session, tid):
        if entry.id == request['context_id']:
            channel = entry

    if channel is None:
        raise errors.InputValidationError("Invalid channel")

    # The report is entered as the reporting people enter theirs: it is given
    # a key of its own, and the receipt composed by the recipient is what
    # opens it afterwards
    prv_key, _ = GCE.generate_keypair()

    submission_session = ObjectDict({
        'user_id': '',
        'cc': prv_key,
        'files': user_session.files,
        'properties': ObjectDict({'operator_session': user_session.user_id})
    })

    # Keyed by the code the recipient composed only where the channel hands it over; otherwise by
    # one the server draws
    receipt = request['receipt'] if channel.provide_access_code \
              else db_discarded_receipt(session, tid)

    db_create_submission(session, tid, {
        'context_id': channel.id,
        'receivers': db_channel_receivers(session, channel),
        'identity_provided': False,
        'answers': request['answers'],
        'receipt': receipt
    }, submission_session, False, False)

    user_session.files = []

    return {'id': submission_session.user_id,
            'provide_access_code': channel.provide_access_code}


class RTipsInsertion(BaseHandler):
    """
    Handler entering on the site a report composed by one of its recipients

    Entering a report is left to the recipients of the site, as acting on
    behalf of a reporting person was.
    """
    check_roles = 'receiver'
    invalidate_cache = True

    def get(self):
        try:
            channel_id = self.request.args.get(b'channel_id', [b''])[0].decode()
        except (IndexError, TypeError, ValueError, UnicodeDecodeError):
            channel_id = ''

        return get_insertion_options(self.request.tid, self.session,
                                     channel_id, self.request.language)

    def post(self):
        request = self.validate_request(self.request.content.read(),
                                        requests.InsertedReportDesc)

        return create_inserted_report(self.request.tid, self.session, request,
                                      self.request.language)


class InsertionAttachment(BaseHandler):
    """
    Interface used to upload the attachments of a report being entered

    The files are held on the session of the recipient and registered on the
    report as soon as it is entered.
    """
    check_roles = 'receiver'
    upload_handler = True

    def post(self):
        self.uploaded_file['submission'] = True
        self.session.files.append(self.uploaded_file)
