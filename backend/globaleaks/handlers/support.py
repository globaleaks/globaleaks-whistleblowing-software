from collections import defaultdict

from nacl.encoding import Base64Encoder
from nacl.public import PrivateKey
from twisted.internet.defer import inlineCallbacks, returnValue

from globaleaks import models
from globaleaks.handlers.base import BaseHandler
from globaleaks.models.config import ConfigFactory
from globaleaks.orm import db_log, transact
from globaleaks.rest import errors, requests
from globaleaks.utils.crypto import GCE
from globaleaks.utils.defang import defang
from globaleaks.utils.log import log
from globaleaks.utils.utility import datetime_now


MAX_SUPPORT_MESSAGE_LENGTH = 4096
SUPPORT_STATUSES = set(models.EnumSupportRequestStatus.keys())


def generate_support_email(mail_address, hostname, request):
    email = "From: %s\n\n" % defang(mail_address) # untrusted
    email += "Site: %s\n\n" % hostname            # trusted
    email += "Request:\n%s" % defang(request)     # untrusted
    return email


def _encode_ciphertext(value):
    return Base64Encoder.encode(value).decode()


def _decrypt_ciphertext(private_key, value):
    return GCE.asymmetric_decrypt(private_key, Base64Encoder.decode(value)).decode()


def _validate_message_content(content):
    if not content or not content.strip():
        raise errors.InputValidationError("Support message cannot be empty")

    if len(content) > MAX_SUPPORT_MESSAGE_LENGTH:
        raise errors.InputValidationError("Support message is too long")


def _get_support_request(session, tid, support_request_id):
    support_request = session.query(models.SupportRequest) \
                             .filter(models.SupportRequest.tid == tid,
                                     models.SupportRequest.id == support_request_id) \
                             .one_or_none()
    if support_request is None:
        raise errors.ResourceNotFound

    return support_request


def _private_key_matches_public(private_key, expected_public_key):
    if not private_key or not expected_public_key:
        return False

    try:
        derived_public_key = PrivateKey(private_key, Base64Encoder).public_key.encode(Base64Encoder).decode()
        return GCE.check_equality(expected_public_key, derived_public_key)
    except Exception:
        return False


def _support_private_key_matches(session, tid, support_private_key):
    expected_public_key = ConfigFactory(session, tid).get_val('crypto_support_pub_key')
    return _private_key_matches_public(support_private_key, expected_public_key)


def is_support_admin(user):
    """Return whether a user profile permits operating in the admin role."""
    return user.role == 'admin' or (user.profile is not None and 'admin' in user.profile.roles_list)


def decrypt_support_private_key(user_session, tid, session=None):
    """Return the tenant support private key available to an admin session.

    A support key is tenant-scoped. Root administrators operating a secondary
    tenant therefore intentionally receive metadata-only results: the current
    schema has one wrapped support-key slot per user and cannot represent a
    different key for every managed tenant.
    """
    if not user_session or user_session.user_tid != tid:
        return None

    wrapped_keys = []
    if user_session.sk:
        wrapped_keys.append(user_session.sk)

    # The encrypted Session stored in memory may still contain an empty or
    # stale wrapper after support initialization or a user keypair reset. Read
    # the authoritative user row as a second candidate on every transaction.
    if session is not None:
        database_wrapped_key = session.query(models.User.crypto_support_prv_key) \
                                      .filter(models.User.tid == tid,
                                              models.User.id == user_session.user_id) \
                                      .scalar()
        if database_wrapped_key and database_wrapped_key not in wrapped_keys:
            wrapped_keys.append(database_wrapped_key)

    for wrapped_key in wrapped_keys:
        try:
            support_private_key = GCE.asymmetric_decrypt(
                user_session.cc,
                Base64Encoder.decode(wrapped_key)
            )
        except Exception:
            continue

        if session is not None and not _support_private_key_matches(
                session, tid, support_private_key):
            continue

        return support_private_key

    return None


def db_grant_support_key(session, tid, support_private_key):
    """Wrap the shared tenant support key to every eligible administrator.

    Existing wrappers are deliberately replaced: a non-empty wrapper can have
    been sealed to an administrator's previous public key after password/key
    recovery and is otherwise indistinguishable from a current one.
    """
    users = session.query(models.User) \
                   .filter(models.User.tid == tid,
                           models.User.crypto_pub_key != '')

    for user in users:
        if is_support_admin(user):
            user.crypto_support_prv_key = _encode_ciphertext(GCE.asymmetric_encrypt(user.crypto_pub_key, support_private_key))


def db_reconcile_support_user_access(session, tid, user, support_private_key, admin_capable=None):
    """Grant or revoke one user's tenant support-key wrapper."""
    if admin_capable is None:
        admin_capable = is_support_admin(user)

    support_public_key = ConfigFactory(session, tid).get_val('crypto_support_pub_key')
    if not support_public_key or not admin_capable:
        user.crypto_support_prv_key = ''
        return

    if not user.crypto_pub_key:
        user.crypto_support_prv_key = ''
        user.password_change_needed = True
        return

    if support_private_key is not None and _support_private_key_matches(session, tid, support_private_key):
        user.crypto_support_prv_key = _encode_ciphertext(GCE.asymmetric_encrypt(user.crypto_pub_key, support_private_key))


def db_reconcile_support_key(session, tid, user, user_private_key):
    """Use a logging-in key holder to refresh every administrator wrapper."""
    if not user_private_key or not user.crypto_support_prv_key:
        return

    try:
        support_private_key = GCE.asymmetric_decrypt(user_private_key, Base64Encoder.decode(user.crypto_support_prv_key))
    except Exception:
        return

    if not _support_private_key_matches(session, tid, support_private_key):
        return

    db_grant_support_key(session, tid, support_private_key)


@transact
def initialize_support(session, tid, user_session):
    """Create a tenant support key once and distribute it to current admins."""
    if not user_session or user_session.user_tid != tid or not user_session.cc:
        raise errors.ForbiddenOperation

    config = ConfigFactory(session, tid)
    support_public_key = config.get_val('crypto_support_pub_key')
    current_user = session.query(models.User) \
                          .filter(models.User.tid == tid,
                                  models.User.id == user_session.user_id) \
                          .one_or_none()

    if current_user is None or user_session.role != 'admin' or \
       not is_support_admin(current_user) or \
       not _private_key_matches_public(user_session.cc, current_user.crypto_pub_key):
        raise errors.ForbiddenOperation

    if support_public_key:
        # Initialization is deliberately idempotent. Rotating this key without
        # rewrapping every thread key would make all existing requests unreadable.
        if decrypt_support_private_key(user_session, tid, session) is None:
            raise errors.ForbiddenOperation
        user_session.sk = current_user.crypto_support_prv_key
        return {'support': True}

    support_private_key, support_public_key = GCE.generate_keypair()
    config.set_val('crypto_support_pub_key', support_public_key)
    db_grant_support_key(session, tid, support_private_key)

    # Admins provisioned without an encryption keypair cannot receive the key
    # yet. Their next password/key setup will make them eligible for a later
    # reconciliation by any existing key holder.
    users_without_keys = session.query(models.User) \
                                .filter(models.User.tid == tid,
                                        models.User.crypto_pub_key == '')
    for user in users_without_keys:
        if is_support_admin(user):
            user.password_change_needed = True

    session.flush()
    user_session.sk = current_user.crypto_support_prv_key
    db_log(session, tid=tid, type='initialize_support', user_id=user_session.user_id)

    return {'support': True}


def _authenticated_author(session, tid, user_session):
    if not user_session or user_session.user_tid != tid or user_session.role == 'whistleblower':
        return None

    author = session.query(models.User) \
                    .filter(models.User.tid == tid,
                            models.User.id == user_session.user_id,
                            models.User.crypto_pub_key != '') \
                    .one_or_none()
    if author is None or not _private_key_matches_public(
            user_session.cc, author.crypto_pub_key):
        return None

    return author


@transact
def create_support_request(session, tid, user_session, mail_address, content):
    config = ConfigFactory(session, tid)
    support_public_key = config.get_val('crypto_support_pub_key')
    if not support_public_key:
        # Never fall back to the legacy plaintext email path. The administrator
        # must initialize encrypted support before this endpoint becomes active.
        raise errors.ForbiddenOperation

    thread_private_key, thread_public_key = GCE.generate_keypair()
    author = _authenticated_author(session, tid, user_session)
    if user_session is not None and user_session.role != 'whistleblower' and \
       author is None:
        # Do not silently downgrade an authenticated conversation to an
        # anonymous one when its requester key is missing or stale.
        raise errors.ForbiddenOperation

    support_request = models.SupportRequest()
    support_request.tid = tid
    support_request.author_id = author.id if author is not None else None
    support_request.crypto_pub_key = thread_public_key
    support_request.crypto_prv_key = _encode_ciphertext(GCE.asymmetric_encrypt(support_public_key, thread_private_key))

    if author is not None:
        support_request.crypto_author_prv_key = _encode_ciphertext(GCE.asymmetric_encrypt(author.crypto_pub_key, thread_private_key))
        support_request.mail_address = ''
    else:
        support_request.crypto_author_prv_key = ''
        support_request.mail_address = _encode_ciphertext(GCE.asymmetric_encrypt(thread_public_key, mail_address))

    session.add(support_request)
    session.flush()

    message = models.SupportMessage()
    message.support_request_id = support_request.id
    message.author_id = None
    message.content = _encode_ciphertext(GCE.asymmetric_encrypt(thread_public_key, content))
    session.add(message)

    db_log(session, tid=tid, type='create_support_request', user_id=support_request.author_id, object_id=support_request.id)

    return {'id': support_request.id, 'status': support_request.status}


def _load_messages(session, support_request_ids):
    messages = defaultdict(list)
    if not support_request_ids:
        return messages

    rows = session.query(models.SupportMessage) \
                  .filter(models.SupportMessage.support_request_id.in_(support_request_ids)) \
                  .order_by(models.SupportMessage.creation_date.asc())
    for message in rows:
        messages[message.support_request_id].append(message)

    return messages


def _serialize_message(message, thread_private_key=None):
    content = ''
    if thread_private_key is not None:
        try:
            content = _decrypt_ciphertext(thread_private_key, message.content)
        except Exception:
            # A damaged message must not prevent administrators from triaging
            # the rest of the thread.
            content = ''

    return {'id': message.id, 'creation_date': message.creation_date, 'author_id': message.author_id, 'content': content, 'new': message.new}


def _serialize_support_request(session, support_request, messages, wrapping_private_key=None, author_wrapped=False):
    thread_private_key = None
    wrapped_thread_key = support_request.crypto_author_prv_key if author_wrapped \
        else support_request.crypto_prv_key

    if wrapping_private_key is not None and wrapped_thread_key:
        try:
            thread_private_key = GCE.asymmetric_decrypt(wrapping_private_key, Base64Encoder.decode(wrapped_thread_key))
            if not _private_key_matches_public(thread_private_key, support_request.crypto_pub_key):
                thread_private_key = None
        except Exception:
            thread_private_key = None

    key_available = thread_private_key is not None
    serialized_messages = [_serialize_message(message, thread_private_key) for message in messages]

    mail_address = ''
    if key_available:
        if support_request.mail_address:
            try:
                mail_address = _decrypt_ciphertext(thread_private_key, support_request.mail_address)
            except Exception:
                mail_address = ''
        elif support_request.author_id:
            author = session.query(models.User.mail_address) \
                            .filter(models.User.tid == support_request.tid,
                                    models.User.id == support_request.author_id) \
                            .one_or_none()
            mail_address = author[0] if author is not None else ''

    preview = next((message['content'][:160] for message in reversed(serialized_messages) if message['content']), '')

    return {
        'id': support_request.id,
        'creation_date': support_request.creation_date,
        'update_date': support_request.update_date,
        'author_id': support_request.author_id,
        'mail_address': mail_address,
        'status': support_request.status,
        'preview': preview,
        'messages': serialized_messages,
        'message_count': len(serialized_messages),
        'key_available': key_available,
        # Kept as an alias for compatibility with the first client prototype.
        'decryptable': key_available
    }


@transact
def get_admin_support_requests(session, tid, user_session, status=None):
    query = session.query(models.SupportRequest) \
                   .filter(models.SupportRequest.tid == tid)
    if status is not None:
        query = query.filter(models.SupportRequest.status == status)

    support_requests = query.order_by(models.SupportRequest.update_date.desc()).all()
    messages = _load_messages(session, [request.id for request in support_requests])
    support_private_key = decrypt_support_private_key(user_session, tid, session)

    return [_serialize_support_request(session, support_request, messages[support_request.id], support_private_key) for support_request in support_requests]


@transact
def update_support_request_status(session, tid, user_session, support_request_id, status):
    support_request = _get_support_request(session, tid, support_request_id)
    support_request.status = status
    support_request.update_date = datetime_now()

    if status == 'read':
        session.query(models.SupportMessage) \
               .filter(models.SupportMessage.support_request_id == support_request.id,
                       models.SupportMessage.author_id.is_(None)) \
               .update({'new': False}, synchronize_session=False)

    db_log(session, tid=tid, type='support_status_update', user_id=user_session.user_id, object_id=support_request.id, data={'status': status})

    messages = session.query(models.SupportMessage) \
                      .filter(models.SupportMessage.support_request_id == support_request.id) \
                      .order_by(models.SupportMessage.creation_date.asc()).all()
    return _serialize_support_request(session, support_request, messages, decrypt_support_private_key(user_session, tid, session))


@transact
def delete_support_request(session, tid, user_session, support_request_id):
    support_request = _get_support_request(session, tid, support_request_id)
    session.delete(support_request)
    db_log(session, tid=tid, type='delete_support_request', user_id=user_session.user_id, object_id=support_request_id)


@transact
def create_admin_support_message(session, tid, user_session, support_request_id, content):
    support_request = _get_support_request(session, tid, support_request_id)
    if support_request.status == 'closed':
        raise errors.ForbiddenOperation

    support_private_key = decrypt_support_private_key(user_session, tid, session)
    if support_private_key is None:
        raise errors.ForbiddenOperation

    try:
        thread_private_key = GCE.asymmetric_decrypt(support_private_key, Base64Encoder.decode(support_request.crypto_prv_key))
    except Exception:
        raise errors.ForbiddenOperation

    if not _private_key_matches_public(thread_private_key, support_request.crypto_pub_key):
        raise errors.ForbiddenOperation

    message = models.SupportMessage()
    message.support_request_id = support_request.id
    message.author_id = user_session.user_id
    # Replying necessarily consumes all requester-authored unread messages.
    session.query(models.SupportMessage) \
           .filter(models.SupportMessage.support_request_id == support_request.id,
                   models.SupportMessage.author_id.is_(None)) \
           .update({'new': False}, synchronize_session=False)
    # Anonymous requesters have no in-system recipient inbox; their reply is
    # delivered by email below and is not left perpetually unread in the DB.
    message.new = support_request.author_id is not None
    message.content = _encode_ciphertext(GCE.asymmetric_encrypt(support_request.crypto_pub_key, content))
    session.add(message)

    support_request.status = 'answered'
    support_request.update_date = datetime_now()
    session.flush()

    notification = None
    if support_request.author_id:
        author = session.query(models.User) \
                        .filter(models.User.tid == tid,
                                models.User.id == support_request.author_id) \
                        .one_or_none()
        if author is not None and author.notification and author.mail_address:
            notification = {'address': author.mail_address, 'pgp_key_public': author.pgp_key_public, 'content_free': True, 'body': ''}
    else:
        try:
            address = _decrypt_ciphertext(thread_private_key, support_request.mail_address)
        except Exception:
            raise errors.ForbiddenOperation

        # Explicit trust-boundary crossing: anonymous requesters have no account
        # in which to read replies, so an administrator-triggered reply is queued
        # as cleartext email. The UI warns the administrator before this action.
        notification = {'address': address, 'pgp_key_public': '', 'content_free': False, 'body': defang(content)}

    db_log(session, tid=tid, type='reply_support_request', user_id=user_session.user_id, object_id=support_request.id, data={'message_id': message.id})

    return _serialize_message(message, thread_private_key), notification


@transact
def get_user_support_requests(session, tid, user_session):
    support_requests = session.query(models.SupportRequest) \
                              .filter(models.SupportRequest.tid == tid,
                                      models.SupportRequest.author_id == user_session.user_id) \
                              .order_by(models.SupportRequest.update_date.desc()).all()
    messages = _load_messages(session, [request.id for request in support_requests])

    return [_serialize_support_request(session, support_request, messages[support_request.id], user_session.cc, author_wrapped=True) for support_request in support_requests]


@transact
def mark_user_support_request_read(session, tid, user_session,
                                   support_request_id):
    support_request = session.query(models.SupportRequest) \
                             .filter(models.SupportRequest.tid == tid,
                                     models.SupportRequest.id == support_request_id,
                                     models.SupportRequest.author_id == user_session.user_id) \
                             .one_or_none()
    if support_request is None:
        raise errors.ResourceNotFound

    try:
        thread_private_key = GCE.asymmetric_decrypt(user_session.cc, Base64Encoder.decode(support_request.crypto_author_prv_key))
    except Exception:
        raise errors.ForbiddenOperation

    if not _private_key_matches_public(
            thread_private_key, support_request.crypto_pub_key):
        raise errors.ForbiddenOperation

    unread_messages = session.query(models.SupportMessage) \
                             .filter(models.SupportMessage.support_request_id == support_request.id,
                                     models.SupportMessage.author_id.isnot(None),
                                     models.SupportMessage.new.is_(True)) \
                             .update({'new': False}, synchronize_session=False)

    if unread_messages:
        db_log(session, tid=tid, type='read_support_request', user_id=user_session.user_id, object_id=support_request.id)

    messages = session.query(models.SupportMessage) \
                      .filter(models.SupportMessage.support_request_id == support_request.id) \
                      .order_by(models.SupportMessage.creation_date.asc()).all()
    return _serialize_support_request(session, support_request, messages, user_session.cc, author_wrapped=True)


@transact
def create_user_support_message(session, tid, user_session, support_request_id, content):
    support_request = session.query(models.SupportRequest) \
                             .filter(models.SupportRequest.tid == tid,
                                     models.SupportRequest.id == support_request_id,
                                     models.SupportRequest.author_id == user_session.user_id) \
                             .one_or_none()
    if support_request is None:
        raise errors.ResourceNotFound
    if support_request.status == 'closed':
        raise errors.ForbiddenOperation

    try:
        thread_private_key = GCE.asymmetric_decrypt(user_session.cc, Base64Encoder.decode(support_request.crypto_author_prv_key))
    except Exception:
        raise errors.ForbiddenOperation

    if not _private_key_matches_public(thread_private_key, support_request.crypto_pub_key):
        raise errors.ForbiddenOperation

    message = models.SupportMessage()
    message.support_request_id = support_request.id
    # A null author identifies requester-authored messages; the thread's
    # author_id records the authenticated requester identity.
    message.author_id = None
    message.content = _encode_ciphertext(GCE.asymmetric_encrypt(support_request.crypto_pub_key, content))
    session.add(message)

    support_request.status = 'new'
    support_request.update_date = datetime_now()
    session.flush()

    db_log(session, tid=tid, type='update_support_request', user_id=user_session.user_id, object_id=support_request.id, data={'message_id': message.id})

    return _serialize_message(message, thread_private_key)


class SupportHandler(BaseHandler):
    """Create an encrypted support request for the current tenant."""
    check_roles = 'any'

    @inlineCallbacks
    def post(self):
        authenticated = self.session is not None and \
            self.session.role != 'whistleblower'
        request_desc = requests.AuthenticatedSupportDesc if authenticated \
            else requests.SupportDesc
        request = self.validate_request(self.request.content.read(), request_desc)
        _validate_message_content(request['text'])

        result = yield create_support_request(self.request.tid, self.session, request.get('mail_address', ''), request['text'])
        yield self.state.schedule_support_email(self.request.tid)
        log.debug("Received and encrypted support request", tid=self.request.tid)
        returnValue(result)


class AdminSupportRequests(BaseHandler):
    check_roles = 'admin'

    def get(self):
        status = self.request.args.get(b'status', [None])[0]
        if isinstance(status, bytes):
            status = status.decode()
        if status is not None and status not in SUPPORT_STATUSES:
            raise errors.InputValidationError("Invalid support status")

        return get_admin_support_requests(self.request.tid, self.session, status)


class AdminSupportRequest(BaseHandler):
    check_roles = 'admin'

    def put(self, support_request_id):
        request = self.validate_request(self.request.content.read(), requests.AdminSupportRequestDesc)
        return update_support_request_status(self.request.tid, self.session, support_request_id, request['status'])

    def delete(self, support_request_id):
        return delete_support_request(self.request.tid, self.session, support_request_id)


class AdminSupportMessage(BaseHandler):
    check_roles = 'admin'

    @inlineCallbacks
    def post(self, support_request_id):
        request = self.validate_request(self.request.content.read(), requests.SupportMessageDesc)
        _validate_message_content(request['content'])

        message, notification = yield create_admin_support_message(self.request.tid, self.session, support_request_id, request['content'])
        if notification is not None:
            try:
                yield self.state.schedule_support_reply_email(self.request.tid, notification['address'], notification['body'], notification['pgp_key_public'], notification['content_free'])
            except Exception:
                # The encrypted reply is already committed. Notification is
                # ancillary, so surface success and avoid duplicate replies on
                # a client retry.
                log.err("Unable to queue support reply notification", tid=self.request.tid)

        returnValue(message)


class UserSupportRequests(BaseHandler):
    check_roles = 'user'

    def get(self):
        return get_user_support_requests(self.request.tid, self.session)


class UserSupportRequest(BaseHandler):
    check_roles = 'user'

    def put(self, support_request_id):
        return mark_user_support_request_read(self.request.tid, self.session, support_request_id)


class UserSupportMessage(BaseHandler):
    check_roles = 'user'

    @inlineCallbacks
    def post(self, support_request_id):
        request = self.validate_request(self.request.content.read(), requests.SupportMessageDesc)
        _validate_message_content(request['content'])

        message = yield create_user_support_message(self.request.tid, self.session, support_request_id, request['content'])
        yield self.state.schedule_support_email(self.request.tid)
        returnValue(message)
