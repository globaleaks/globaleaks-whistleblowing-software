import json

from collections import defaultdict

from nacl.encoding import Base64Encoder
from nacl.public import PrivateKey
from twisted.internet.defer import inlineCallbacks, returnValue

from globaleaks import models
from globaleaks.handlers.base import BaseHandler
from globaleaks.models.config import ConfigFactory
from globaleaks.orm import db_log, transact
from globaleaks.rest import errors, requests
from globaleaks.state import State
from globaleaks.utils.crypto import GCE
from globaleaks.utils.defang import defang
from globaleaks.utils.log import log
from globaleaks.utils.utility import datetime_now


MAX_SUPPORT_MESSAGE_LENGTH = 4096
SUPPORT_STATUSES = set(models.EnumSupportRequestStatus.keys())


def encode_ciphertext(value):
    return Base64Encoder.encode(value).decode()


def decrypt_ciphertext(private_key, value):
    return GCE.asymmetric_decrypt(private_key, Base64Encoder.decode(value)).decode()


def decrypt_private_key(private_key, wrapped_key, public_key):
    if not private_key or not wrapped_key:
        return None

    try:
        decrypted_key = GCE.asymmetric_decrypt( private_key, Base64Encoder.decode(wrapped_key))
    except Exception:
        return None

    if not private_key_matches_public(decrypted_key, public_key):
        return None

    return decrypted_key


def validate_message_content(content):
    if not content or not content.strip():
        raise errors.InputValidationError("Support message cannot be empty")

    if len(content) > MAX_SUPPORT_MESSAGE_LENGTH:
        raise errors.InputValidationError("Support message is too long")


def get_support_request(session, tid, user_session, support_request_id):
    support_request = session.query(models.SupportRequest) \
                             .filter(models.SupportRequest.id == support_request_id) \
                             .one_or_none()
    if support_request is None or (support_request.tid != tid and not is_root_management_session(user_session, support_request.tid)):
        raise errors.ResourceNotFound

    # A request the tenant keeps for itself does not exist for the root tenant,
    # neither to read nor to act upon
    if not db_filter_escalated(session, user_session, [support_request]):
        raise errors.ResourceNotFound

    return support_request


def get_user_support_request(session, tid, user_session,
                              support_request_id):
    support_request = session.query(models.SupportRequest) \
                             .filter(models.SupportRequest.tid == tid,
                                     models.SupportRequest.id == support_request_id,
                                     models.SupportRequest.author_id == user_session.user_id) \
                             .one_or_none()
    if support_request is None:
        raise errors.ResourceNotFound

    return support_request


def db_assign_support_progressive(session, tid):
    """
    Assign the progressive number identifying a support request within its tenant.

    The counter is monotonic: numbers of deleted requests are never reassigned.
    """
    config = ConfigFactory(session, tid)
    progressive = config.get_val('counter_support_requests') + 1
    config.set_val('counter_support_requests', progressive)
    return progressive


def get_support_messages(session, support_request_id):
    return session.query(models.SupportMessage) \
                  .filter(models.SupportMessage.support_request_id == support_request_id) \
                  .order_by(models.SupportMessage.creation_date.asc()) \
                  .all()


def private_key_matches_public(private_key, expected_public_key):
    if not private_key or not expected_public_key:
        return False

    try:
        derived_public_key = PrivateKey(private_key, Base64Encoder).public_key.encode(Base64Encoder).decode()
        return GCE.check_equality(expected_public_key, derived_public_key)
    except Exception:
        return False


def get_support_config(session, tid, var_name):
    value = session.query(models.Config.value) \
                   .filter(models.Config.tid == tid,
                           models.Config.var_name == var_name) \
                   .scalar()
    return value or ''


def support_private_key_matches(session, tid, support_private_key):
    expected_public_key = get_support_config(session, tid, 'crypto_support_pub_key')
    return private_key_matches_public(support_private_key, expected_public_key)


def is_root_admin_session(user_session):
    return user_session is not None and \
        user_session.user_tid == 1 and \
        user_session.role == 'admin'


def is_root_management_session(user_session, tid):
    return is_root_admin_session(user_session) and tid != 1


def is_support_admin(user):
    return user.role == 'admin' or \
        user.profile is not None and 'admin' in user.profile.roles_list


def db_support_escalation(session, tid):
    """
    Which of the support requests received by a tenant the root tenant is
    entitled to handle: 'all', 'admins' (only the ones written by the
    administrators of that tenant) or 'none'. The root tenant always handles
    its own, so the scope is meaningless there.

    :param session: An ORM session
    :param tid: The tenant the request was received by
    :return: The configured scope
    """
    if tid == 1:
        return 'all'

    # Resolved through the profile of the tenant, so that a scope set on a
    # profile applies to every tenant that inherits from it
    escalation = ConfigFactory(session, tid).get_val('support_escalation')

    return escalation if escalation in ('none', 'admins', 'all') else 'all'


def db_admin_author_ids(session, author_ids):
    """
    Of the given authors, the ones that are administrators of their tenant

    :param session: An ORM session
    :param author_ids: The ids of the authors to resolve
    :return: The subset of ids belonging to an administrator
    """
    author_ids = {author_id for author_id in author_ids if author_id}
    if not author_ids:
        return set()

    return {user.id
            for user in session.query(models.User).filter(models.User.id.in_(author_ids))
            if is_support_admin(user)}


def db_escalates_to_root(session, tid, author_id):
    """
    Whether a support request received by a tenant is handled by the root
    tenant too. An anonymous request identifies no author, so it is not one of
    an administrator and stays with the tenant when the scope is 'admins'.

    :param session: An ORM session
    :param tid: The tenant the request was received by
    :param author_id: The id of the author of the request, if identified
    :return: True when the root tenant handles the request as well
    """
    if tid == 1:
        return False

    escalation = db_support_escalation(session, tid)

    if escalation == 'all':
        return True

    if escalation == 'none':
        return False

    return bool(db_admin_author_ids(session, [author_id]))


def db_filter_escalated(session, user_session, support_requests):
    """
    Drop from a listing the requests a root tenant session is not entitled to
    handle. A session of the tenant that received the request always keeps it:
    the scope confines the root tenant, never the tenant itself.

    :param session: An ORM session
    :param user_session: The session of the reader
    :param support_requests: The requests to filter
    :return: The requests the reader is entitled to handle
    """
    if user_session is None or user_session.user_tid != 1:
        return support_requests

    escalation = {}
    for support_request in support_requests:
        if support_request.tid not in escalation:
            escalation[support_request.tid] = db_support_escalation(session, support_request.tid)

    admin_author_ids = db_admin_author_ids(
        session,
        [support_request.author_id for support_request in support_requests
         if escalation[support_request.tid] == 'admins']
    )

    return [support_request for support_request in support_requests
            if support_request.tid == 1 or
            escalation[support_request.tid] == 'all' or
            (escalation[support_request.tid] == 'admins' and
             support_request.author_id in admin_author_ids)]


def decrypt_support_private_key(user_session, tid, session=None):
    if not user_session or session is None:
        return None

    key_tid = 1 if is_root_management_session(user_session, tid) else tid
    if user_session.user_tid != key_tid:
        return None

    wrapped_keys = []
    if user_session.sk:
        wrapped_keys.append(user_session.sk)

    database_wrapped_key = session.query(models.User.crypto_support_prv_key) \
                                  .filter(models.User.tid == key_tid,
                                          models.User.id == user_session.user_id) \
                                  .scalar()
    if database_wrapped_key and database_wrapped_key not in wrapped_keys:
        wrapped_keys.append(database_wrapped_key)

    support_public_key = get_support_config(session, key_tid, 'crypto_support_pub_key')

    for wrapped_key in wrapped_keys:
        support_private_key = decrypt_private_key(user_session.cc, wrapped_key, support_public_key)
        if support_private_key is not None:
            return support_private_key

    return None


def decrypt_tenant_support_private_key(user_session, tid, session=None):
    """
    Resolve the support private key of the tenant tid.

    A root tenant administrator resolves it by descending the key hierarchy:
    the tenant key is unwrapped with the root support key. The key material is
    never regenerated here: a tenant key that does not open is an anomaly to be
    reported, not to be silently rotated.
    """
    support_private_key = decrypt_support_private_key(user_session, tid, session)

    if support_private_key is None or not is_root_management_session(user_session, tid):
        return support_private_key

    return decrypt_private_key(support_private_key,
                               get_support_config(session, tid, 'crypto_support_prv_key'),
                               get_support_config(session, tid, 'crypto_support_pub_key'))


def db_grant_support_key(session, tid, support_private_key):
    users = session.query(models.User).filter(models.User.tid == tid, models.User.crypto_pub_key != '')

    for user in users:
        if is_support_admin(user):
            user.crypto_support_prv_key = encode_ciphertext(GCE.asymmetric_encrypt(user.crypto_pub_key, support_private_key))


def db_reconcile_support_user_access(session, tid, user, support_private_key, admin_capable=None):
    if admin_capable is None:
        admin_capable = is_support_admin(user)

    support_public_key = get_support_config(session, tid, 'crypto_support_pub_key')
    if not support_public_key or not admin_capable:
        user.crypto_support_prv_key = ''
        return

    if not user.crypto_pub_key:
        user.crypto_support_prv_key = ''
        user.password_change_needed = True
        return

    if support_private_key is None or not support_private_key_matches(session, tid, support_private_key):
        # Every administrator must hold the support key: failing to resolve it
        # would silently produce an administrator without access.
        raise errors.InternalServerError("Unable to resolve the support key of tenant %d" % tid)

    user.crypto_support_prv_key = encode_ciphertext(GCE.asymmetric_encrypt(user.crypto_pub_key, support_private_key))


def db_reconcile_support_key(session, tid, user, user_private_key):
    if not user_private_key or not user.crypto_support_prv_key:
        return

    support_private_key = decrypt_private_key(user_private_key, user.crypto_support_prv_key, get_support_config(session, tid, 'crypto_support_pub_key'))
    if support_private_key is None:
        return

    db_grant_support_key(session, tid, support_private_key)


def db_initialize_support(session, tid):
    config = ConfigFactory(session, tid)
    support_public_key = get_support_config(session, tid, 'crypto_support_pub_key')
    if support_public_key:
        return

    root_support_public_key = get_support_config(session, 1, 'crypto_support_pub_key')

    if tid != 1 and not root_support_public_key:
        db_initialize_support(session, 1)
        root_support_public_key = get_support_config(session, 1, 'crypto_support_pub_key')

    support_private_key, support_public_key = GCE.generate_keypair()
    config.set_val('crypto_support_pub_key', support_public_key)

    if tid != 1:
        config.set_val('crypto_support_prv_key',encode_ciphertext(GCE.asymmetric_encrypt(root_support_public_key, support_private_key)))

    db_grant_support_key(session, tid, support_private_key)

    users_without_keys = session.query(models.User) \
                                .filter(models.User.tid == tid,
                                        models.User.crypto_pub_key == '')
    for user in users_without_keys:
        if is_support_admin(user):
            user.password_change_needed = True

    session.flush()


def authenticated_author(session, tid, user_session):
    if not user_session or user_session.user_tid != tid or user_session.role == 'whistleblower':
        return None

    return session.query(models.User) \
                  .filter(models.User.tid == tid,
                          models.User.id == user_session.user_id) \
                  .one_or_none()


def idp_authenticated_author(session, tid, idp_claims):
    """
    Resolve the account bound to the identity authenticated on the identity provider.

    An user that has authenticated on the identity provider and is being asked
    for the password that decrypts its keys holds no session yet, but the token
    it presents has already been verified against the identity provider
    configured on the tenant (rest/api.py) and the identity it carries is bound
    to an account (handlers/auth: db_bind_idp_identity). That binding is what
    identifies the requester, exactly as it identifies it at the login, so a
    request opened from that step is recorded as the one of that account.
    """
    subject = idp_claims.get('sub') if idp_claims else None
    if not subject:
        return None

    return session.query(models.User) \
                  .filter(models.User.tid == tid,
                          models.User.idp_id == subject,
                          models.User.enabled.is_(True)) \
                  .one_or_none()


def session_public_key(user_session):
    """
    The public key a thread is sealed to for the user that holds the session.

    It is derived from the session key rather than read from the account,
    because the two coincide for an account that has completed its access and
    the session one is the right key for an account that has not. An user that
    has authenticated on the identity provider and has still to set its
    password holds a session keyed on a keypair that its account adopts when
    the password is set (db_change_password); sealing the thread to it is what
    makes the request it opens from that step readable by its author as soon as
    the access is completed.
    """
    if not user_session.cc:
        return ''

    try:
        return PrivateKey(user_session.cc, Base64Encoder).public_key.encode(Base64Encoder).decode()
    except Exception:
        return ''


@transact
def create_support_request(session, tid, user_session, mail_address, content, idp_claims=None):
    support_public_key = get_support_config(session, tid, 'crypto_support_pub_key')

    if not support_public_key:
        raise errors.ForbiddenOperation

    thread_private_key, thread_public_key = GCE.generate_keypair()
    author = authenticated_author(session, tid, user_session)
    if user_session is not None and user_session.role != 'whistleblower' and \
       author is None:
        raise errors.ForbiddenOperation

    if author is None:
        author = idp_authenticated_author(session, tid, idp_claims)

    # An identity bound to no account identifies no requester: the request is
    # recorded as any other anonymous one and an address to answer to is needed
    if author is None and not mail_address:
        raise errors.ForbiddenOperation

    support_request = models.SupportRequest()
    support_request.tid = tid
    support_request.progressive = db_assign_support_progressive(session, tid)
    support_request.author_id = author.id if author is not None else None
    support_request.crypto_pub_key = thread_public_key
    support_request.crypto_prv_key = encode_ciphertext(GCE.asymmetric_encrypt(support_public_key, thread_private_key))
    root_support_public_key = get_support_config(session, 1, 'crypto_support_pub_key')
    support_request.root_crypto_prv_key = encode_ciphertext(GCE.asymmetric_encrypt(root_support_public_key, thread_private_key)) if root_support_public_key else ''

    if author is not None:
        # The thread is sealed to the key of the session when there is one, and
        # to the key of the account when the requester is identified by the
        # identity it presents alone. An account whose access is not complete
        # holds no key at all: the request is recorded as its own all the same
        # and is answered by e-mail, and becomes readable in platform once the
        # account holds its keypair
        author_public_key = session_public_key(user_session) if user_session is not None else author.crypto_pub_key
        support_request.crypto_author_prv_key = encode_ciphertext(GCE.asymmetric_encrypt(author_public_key, thread_private_key)) if author_public_key else ''
        support_request.mail_address = ''
    else:
        support_request.crypto_author_prv_key = ''
        support_request.mail_address = encode_ciphertext(GCE.asymmetric_encrypt(thread_public_key, mail_address))

    session.add(support_request)
    session.flush()

    message = models.SupportMessage()
    message.support_request_id = support_request.id
    message.author_id = None
    message.content = encode_ciphertext(GCE.asymmetric_encrypt(thread_public_key, content))
    session.add(message)

    db_log(session, tid=tid, type='create_support_request', user_id=support_request.author_id, object_id=support_request.id)

    # The thread is sealed to the root tenant key in any case: what the scope
    # configured by the tenant decides is who handles the request, and is
    # therefore evaluated when the request is listed and when it is notified
    return ({'id': support_request.id, 'status': support_request.status},
            db_escalates_to_root(session, tid, support_request.author_id))


def load_messages(session, support_request_ids):
    messages = defaultdict(list)
    if not support_request_ids:
        return messages

    rows = session.query(models.SupportMessage) \
                  .filter(models.SupportMessage.support_request_id.in_(support_request_ids)) \
                  .order_by(models.SupportMessage.creation_date.asc())
    for message in rows:
        messages[message.support_request_id].append(message)

    return messages


def serialize_message(message, thread_private_key=None):
    content = ''
    if thread_private_key is not None:
        try:
            content = decrypt_ciphertext(thread_private_key, message.content)
        except Exception:
            content = ''

    return {'id': message.id, 'creation_date': message.creation_date, 'author_id': message.author_id, 'content': content, 'new': message.new}


def tenant_name(tid):
    """
    Resolve the name of the tenant from the cache already held in memory: the
    lists are serialized one row at a time and a query per row would be a N+1.
    """
    tenant = State.tenants.get(tid)
    return tenant.cache.name if tenant is not None else ''


def serialize_support_request(session, support_request, messages, wrapping_private_key=None, wrapped_thread_key=None):

    thread_private_key = decrypt_private_key(wrapping_private_key, wrapped_thread_key, support_request.crypto_pub_key)

    key_available = thread_private_key is not None

    serialized_messages = [serialize_message(message, thread_private_key) for message in messages]

    author = None
    if support_request.author_id:
        author = session.query(models.User.username, models.User.mail_address) \
                        .filter(models.User.tid == support_request.tid,
                                models.User.id == support_request.author_id) \
                        .one_or_none()

    mail_address = ''
    if key_available:
        if support_request.mail_address:
            try:
                mail_address = decrypt_ciphertext(thread_private_key, support_request.mail_address)
            except Exception:
                mail_address = ''
        elif author is not None:
            mail_address = author[1]

    preview = next((message['content'][:160] for message in reversed(serialized_messages) if message['content']), '')

    return {
        'id': support_request.id,
        'tid': support_request.tid,
        'tenant_name': tenant_name(support_request.tid),
        'progressive': support_request.progressive,
        'creation_date': support_request.creation_date,
        'update_date': support_request.update_date,
        'author_id': support_request.author_id,
        'author_username': author[0] if author is not None else '',
        'mail_address': mail_address,
        'status': support_request.status,
        'preview': preview,
        'messages': serialized_messages,
        'key_available': key_available
    }


@transact
def get_admin_support_requests(session, tid, user_session, status=None, tenant_id=None):
    root_access = tid == 1 and is_root_admin_session(user_session)
    query = session.query(models.SupportRequest)
    if root_access:
        if tenant_id is not None:
            query = query.filter(models.SupportRequest.tid == tenant_id)
    else:
        if tenant_id is not None and tenant_id != tid:
            raise errors.ForbiddenOperation
        query = query.filter(models.SupportRequest.tid == tid)

    if status is not None:
        query = query.filter(models.SupportRequest.status == status)

    support_requests = db_filter_escalated(
        session,
        user_session,
        query.order_by(models.SupportRequest.update_date.desc()).all()
    )

    messages = load_messages(session, [request.id for request in support_requests])

    return [
        serialize_support_request(
            session,
            support_request,
            messages[support_request.id],
            decrypt_support_private_key(user_session, support_request.tid, session),
            support_request.root_crypto_prv_key
            if is_root_management_session(user_session, support_request.tid) else support_request.crypto_prv_key
        )
        for support_request in support_requests
    ]


@transact
def update_support_request_status(session, tid, user_session, support_request_id, status):
    support_request = get_support_request(session, tid, user_session, support_request_id)
    request_tid = support_request.tid

    # A request once opened never returns new: new marks only the requests
    # never yet handled
    if status == 'new' and support_request.status != 'new':
        raise errors.ForbiddenOperation

    support_request.status = status
    support_request.update_date = datetime_now()

    if status == 'opened':
        session.query(models.SupportMessage) \
               .filter(models.SupportMessage.support_request_id == support_request.id,
                       models.SupportMessage.author_id.is_(None)) \
               .update({'new': False}, synchronize_session=False)

    db_log(session, tid=request_tid, type='support_status_update', user_id=user_session.user_id, object_id=support_request.id, data={'status': status})

    messages = get_support_messages(session, support_request.id)
    return serialize_support_request(
        session,
        support_request,
        messages,
        decrypt_support_private_key(user_session, request_tid, session),
        support_request.root_crypto_prv_key
        if is_root_management_session(user_session, request_tid)
        else support_request.crypto_prv_key
    )


@transact
def delete_support_request(session, tid, user_session, support_request_id):
    support_request = get_support_request(session, tid, user_session, support_request_id)
    request_tid = support_request.tid
    session.delete(support_request)

    db_log(session, tid=request_tid, type='delete_support_request', user_id=user_session.user_id, object_id=support_request_id)


@transact
def create_admin_support_message(session, tid, user_session, support_request_id, content):

    support_request = get_support_request(session, tid, user_session, support_request_id)
    request_tid = support_request.tid
    if support_request.status == 'closed':
        raise errors.ForbiddenOperation

    support_private_key = decrypt_support_private_key(user_session, request_tid, session)
    if support_private_key is None:
        raise errors.ForbiddenOperation

    wrapped_thread_key = support_request.root_crypto_prv_key if \
        is_root_management_session(user_session, request_tid) else \
        support_request.crypto_prv_key

    thread_private_key = decrypt_private_key(support_private_key, wrapped_thread_key, support_request.crypto_pub_key)
    if thread_private_key is None:
        raise errors.ForbiddenOperation

    message = models.SupportMessage()
    message.support_request_id = support_request.id
    message.author_id = user_session.user_id
    session.query(models.SupportMessage) \
           .filter(models.SupportMessage.support_request_id == support_request.id,
                   models.SupportMessage.author_id.is_(None)) \
           .update({'new': False}, synchronize_session=False)
    message.new = support_request.author_id is not None
    message.content = encode_ciphertext(GCE.asymmetric_encrypt(support_request.crypto_pub_key, content))
    session.add(message)

    # A reply implies the request has been handled
    support_request.status = 'opened'
    support_request.update_date = datetime_now()
    session.flush()

    notification = None
    if support_request.author_id:
        author = session.query(models.User) \
                        .filter(models.User.tid == request_tid,
                                models.User.id == support_request.author_id) \
                        .one_or_none()
        if author is not None and author.notification and author.mail_address:
            notification = {'address': author.mail_address, 'pgp_key_public': author.pgp_key_public, 'content_free': True, 'body': ''}
    else:
        try:
            address = decrypt_ciphertext(thread_private_key, support_request.mail_address)
        except Exception:
            raise errors.ForbiddenOperation

        notification = {'address': address, 'pgp_key_public': '', 'content_free': False, 'body': defang(content)}

    db_log(session, tid=request_tid, type='reply_support_request', user_id=user_session.user_id, object_id=support_request.id, data={'message_id': message.id})

    return serialize_message(message, thread_private_key), notification


@transact
def get_user_support_requests(session, tid, user_session):
    support_requests = session.query(models.SupportRequest) \
                              .filter(models.SupportRequest.tid == tid,
                                      models.SupportRequest.author_id == user_session.user_id) \
                              .order_by(models.SupportRequest.update_date.desc()) \
                              .all()
    messages = load_messages(session, [request.id for request in support_requests])

    return [
        serialize_support_request(session, support_request, messages[support_request.id], user_session.cc, support_request.crypto_author_prv_key)
        for support_request in support_requests
    ]


@transact
def mark_admin_support_request_read(session, tid, user_session, support_request_id):
    """
    Mark as read, for the administrators, the messages the requester wrote

    It mirrors what the requester does on the replies it receives, and does not
    move the update date: looking at a request is not an update of it.

    :param session: An ORM session
    :param tid: The tenant of the session
    :param user_session: The session of the administrator
    :param support_request_id: The id of the request being read
    """
    support_request = get_support_request(session, tid, user_session, support_request_id)
    request_tid = support_request.tid

    unread_messages = session.query(models.SupportMessage) \
                             .filter(models.SupportMessage.support_request_id == support_request.id,
                                     models.SupportMessage.author_id.is_(None),
                                     models.SupportMessage.new.is_(True)) \
                             .update({'new': False}, synchronize_session=False)

    if unread_messages:
        db_log(session, tid=request_tid, type='read_support_request', user_id=user_session.user_id, object_id=support_request.id)


@transact
def mark_user_support_request_read(session, tid, user_session, support_request_id):

    support_request = get_user_support_request(session, tid, user_session, support_request_id)
    thread_private_key = decrypt_private_key(user_session.cc, support_request.crypto_author_prv_key, support_request.crypto_pub_key)
    if thread_private_key is None:
        raise errors.ForbiddenOperation

    unread_messages = session.query(models.SupportMessage) \
                             .filter(models.SupportMessage.support_request_id == support_request.id,
                                     models.SupportMessage.author_id.isnot(None),
                                     models.SupportMessage.new.is_(True)) \
                             .update({'new': False}, synchronize_session=False)

    if unread_messages:
        db_log(session, tid=tid, type='read_support_request', user_id=user_session.user_id, object_id=support_request.id)

    messages = get_support_messages(session, support_request.id)

    return serialize_support_request(session, support_request, messages, user_session.cc, support_request.crypto_author_prv_key)


@transact
def create_user_support_message(session, tid, user_session, support_request_id, content):

    support_request = get_user_support_request(session, tid, user_session, support_request_id)
    if support_request.status == 'closed':
        raise errors.ForbiddenOperation

    thread_private_key = decrypt_private_key(user_session.cc, support_request.crypto_author_prv_key, support_request.crypto_pub_key)
    if thread_private_key is None:
        raise errors.ForbiddenOperation

    message = models.SupportMessage()
    message.support_request_id = support_request.id
    message.author_id = None
    message.content = encode_ciphertext(GCE.asymmetric_encrypt(support_request.crypto_pub_key, content))
    session.add(message)

    # The message does not move the status: a request once opened never
    # returns new, the attention being signaled by the unread messages
    support_request.update_date = datetime_now()
    session.flush()

    db_log(session, tid=tid, type='update_support_request', user_id=user_session.user_id, object_id=support_request.id, data={'message_id': message.id})

    return (serialize_message(message, thread_private_key),
            db_escalates_to_root(session, tid, support_request.author_id))


class SupportHandler(BaseHandler):
    check_roles = 'any'

    @inlineCallbacks
    def post(self):
        authenticated = self.session is not None and self.session.role != 'whistleblower'

        # An user that has authenticated on the identity provider and is being
        # asked for its password holds no session yet, but the identity it
        # presents is bound to an account and identifies it. It writes as that
        # account and provides no address, exactly as an user that holds a
        # session; an identity bound to no account identifies nobody and its
        # user provides an address as any other anonymous requester, which is
        # what tells the two apart.
        idp_claims = self.request.oidc_token if self.session is None else None

        try:
            payload = json.loads(self.request.content.read())
        except Exception:
            raise errors.InputValidationError

        if not isinstance(payload, dict):
            raise errors.InputValidationError

        if idp_claims and not payload.get('mail_address'):
            authenticated = True

        request_desc = requests.AuthenticatedSupportDesc if authenticated else requests.SupportDesc
        request = self.validate_request(payload, request_desc)
        validate_message_content(request['text'])

        result, escalate = yield create_support_request(self.request.tid, self.session, request.get('mail_address', ''), request['text'], idp_claims)
        yield self.state.schedule_support_email(self.request.tid, result['id'], escalate)
        log.debug("Received and encrypted support request", tid=self.request.tid)
        returnValue(result)


class AdminSupportRequests(BaseHandler):
    check_roles = 'admin'
    require_permission = 'can_manage_support'

    def get(self):
        status = self.request.args.get(b'status', [None])[0]
        tenant_id = self.request.args.get(b'tenant_id', [None])[0]
        if isinstance(status, bytes):
            status = status.decode()
        if status is not None and status not in SUPPORT_STATUSES:
            raise errors.InputValidationError("Invalid support status")
        if tenant_id is not None:
            try:
                tenant_id = int(tenant_id)
            except (TypeError, ValueError):
                raise errors.InputValidationError("Invalid tenant ID")

        return get_admin_support_requests(self.request.tid, self.session, status, tenant_id)


class AdminSupportRequest(BaseHandler):
    check_roles = 'admin'
    require_permission = 'can_manage_support'

    def put(self, support_request_id):
        request = self.validate_request(self.request.content.read(), requests.AdminSupportRequestDesc)
        return update_support_request_status(self.request.tid, self.session, support_request_id, request['status'])

    def delete(self, support_request_id):
        return delete_support_request(self.request.tid, self.session, support_request_id)


class AdminSupportRequestRead(BaseHandler):
    check_roles = 'admin'
    require_permission = 'can_manage_support'

    def put(self, support_request_id):
        return mark_admin_support_request_read(self.request.tid, self.session, support_request_id)


class AdminSupportMessage(BaseHandler):
    check_roles = 'admin'
    require_permission = 'can_manage_support'

    @inlineCallbacks
    def post(self, support_request_id):
        request = self.validate_request(self.request.content.read(), requests.SupportMessageDesc)
        validate_message_content(request['content'])

        message, notification = yield create_admin_support_message(self.request.tid, self.session, support_request_id, request['content'])
        if notification is not None:
            try:
                yield self.state.schedule_support_reply_email(self.request.tid, notification['address'], notification['body'], notification['pgp_key_public'], notification['content_free'])
            except Exception:
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
        validate_message_content(request['content'])

        message, escalate = yield create_user_support_message(self.request.tid, self.session, support_request_id, request['content'])
        yield self.state.schedule_support_email(self.request.tid, support_request_id, escalate)
        returnValue(message)
