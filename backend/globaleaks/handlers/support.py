# Handlers dealing with user support requests
from nacl.encoding import Base64Encoder
from twisted.internet.defer import inlineCallbacks

from globaleaks import models
from globaleaks.handlers.base import BaseHandler
from globaleaks.models.config import ConfigFactory
from globaleaks.orm import transact
from globaleaks.rest import requests
from globaleaks.utils.crypto import GCE
from globaleaks.utils.log import log
from globaleaks.utils.utility import datetime_now


# Roles whose session identifies a real ``User`` row (as opposed to an
# anonymous whistleblower submission session). Only for these do we bind the
# support thread to the requester so they can later read admin replies (v2).
AUTHENTICATED_ROLES = ('admin', 'receiver', 'custodian', 'analyst')


def db_get_support_prv_key(session, tid, user_session):
    """
    Resolve the tenant support private key that an administrator must use to
    read the support requests of tenant ``tid``.

    This mirrors the escrow key hierarchy: an administrator of the root tenant
    can read the support requests of any secondary tenant, because each
    secondary tenant stores its own support private key sealed to the root
    tenant support public key (config ``crypto_support_prv_key``). A root
    administrator therefore descends the hierarchy:

        session.sk  --(session.cc)-->  root support prv
        root support prv  --(secondary config crypto_support_prv_key)-->  secondary support prv

    An administrator of a secondary tenant only ever holds their own tenant
    support key and can read only their own tenant requests.
    """
    support_prv = GCE.asymmetric_decrypt(user_session.cc, Base64Encoder.decode(user_session.sk))

    if user_session.user_tid == 1 and tid != 1:
        wrapped = ConfigFactory(session, tid).get_val('crypto_support_prv_key')
        if wrapped:
            support_prv = GCE.asymmetric_decrypt(support_prv, Base64Encoder.decode(wrapped))

    return support_prv


def db_add_support_message(session, support, text, author_id):
    """
    Append a message to an existing support thread.

    The content is sealed to the thread public key (writing a sealed box needs
    only the public key, so neither the admin support key nor the requester key
    is required here). ``author_id`` is the administrator id for an admin reply,
    or ``None`` for a message posted by the requester. On tenants with
    encryption disabled the content is stored in cleartext.
    """
    if support.crypto_pub_key:
        content = Base64Encoder.encode(
            GCE.asymmetric_encrypt(support.crypto_pub_key, text.encode())).decode()
    else:
        content = text

    message = models.SupportMessage()
    message.support_request_id = support.id
    message.author_id = author_id
    message.content = content
    message.new = True

    session.add(message)

    support.update_date = datetime_now()

    return message


def db_create_support_request(session, tid, user_session, request):
    """
    Persist a support request as an encrypted conversation thread plus its
    first (inbound) message.

    Cryptographic model (see SUPPORT_REQUESTS_DESIGN.md):
      * a per-thread keypair is generated; every message is sealed to the
        thread public key (libsodium sealed box, write requires only the public
        key);
      * the thread private key is sealed to the tenant support public key so
        that every administrator holding the support key can read the thread;
      * if the requester is an authenticated user, the thread private key is
        also sealed to the requester public key (``crypto_author_prv_key``) so
        they can read replies later; otherwise the provided e-mail address is
        sealed to the thread public key so administrators can recover it for a
        reply without it resting in cleartext.

    When tenant encryption is disabled (no support public key), the request is
    stored in cleartext, consistent with how comments behave on unencrypted
    tips.
    """
    crypto_support_pub_key = ConfigFactory(session, tid).get_val('crypto_support_pub_key')

    text = request['text']
    mail_address = request['mail_address']

    author = None
    if user_session and user_session.role in AUTHENTICATED_ROLES:
        author = session.query(models.User).filter(models.User.id == user_session.user_id,
                                                    models.User.tid == tid).one_or_none()

    support = models.SupportRequest()
    support.tid = tid
    support.status = 'new'

    if crypto_support_pub_key:
        crypto_prv_key, crypto_pub_key = GCE.generate_keypair()

        support.crypto_pub_key = crypto_pub_key.decode()
        support.crypto_prv_key = Base64Encoder.encode(
            GCE.asymmetric_encrypt(crypto_support_pub_key, crypto_prv_key)).decode()

        if author and author.crypto_pub_key:
            support.author_id = author.id
            support.crypto_author_prv_key = Base64Encoder.encode(
                GCE.asymmetric_encrypt(author.crypto_pub_key, crypto_prv_key)).decode()
        elif mail_address:
            support.mail_address = Base64Encoder.encode(
                GCE.asymmetric_encrypt(crypto_pub_key, mail_address.encode())).decode()
    else:
        if author:
            support.author_id = author.id
        support.mail_address = mail_address

    session.add(support)
    session.flush()

    # the requester posts the first (inbound) message of the thread
    db_add_support_message(session, support, text, None)

    return support


@transact
def create_support_request(session, tid, user_session, request):
    support = db_create_support_request(session, tid, user_session, request)
    return support.id


class SupportHandler(BaseHandler):
    """
    This handler is responsible of receiving support requests, persisting them
    encrypted at rest and notifying administrators with a content-free e-mail.
    """
    check_roles = 'any'

    @inlineCallbacks
    def post(self):
        request = self.validate_request(self.request.content.read(),
                                        requests.SupportDesc)

        yield create_support_request(self.request.tid, self.session, request)

        # Administrators are notified with a content-free notification only:
        # the request content never leaves the encrypted boundary.
        self.state.schedule_support_email(self.request.tid)

        log.debug("Received support request and notified administrators")
