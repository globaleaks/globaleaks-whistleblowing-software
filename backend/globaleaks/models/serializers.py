import copy
import os


from sqlalchemy import and_, func, or_, not_
from sqlalchemy.orm import aliased

from globaleaks.models import EnumStateFile
from globaleaks import models
from globaleaks.models.config import ConfigFactory
from globaleaks.orm import transact
from globaleaks.state import State
from globaleaks.utils.utility import datetime_never, datetime_null


def get_identity_files(data):
    ids = []

    def extract_from_children(children):
        for child in children:
            if child.get('type') in ['fileupload', 'voice']:
                ids.append(child.get('id'))
            elif child.get('type') == 'fieldgroup':
                extract_from_children(child.get('children', []))

    for questionnaire in data:
        for step in questionnaire.get('steps', []):
            for child in step.get('children', []):
                if child.get('template_id') == 'whistleblower_identity':
                    extract_from_children(child.get('children', []))
                    return ids

    return ids


def serialize_archived_field_recursively(field, language):
    for key, _ in field.get('attrs', {}).items():
        if key not in field['attrs']:
            continue

        if 'type' not in field['attrs'][key]:
            continue

        if field['attrs'][key]['type'] == 'localized':
            if language in field['attrs'][key].get('value', []):
                field['attrs'][key]['value'] = field['attrs'][key]['value'][language]
            else:
                field['attrs'][key]['value'] = ""

    for o in field.get('options', []):
        models.get_localized_values(o, o, models.FieldOption.localized_keys, language)

    for c in field.get('children', []):
        serialize_archived_field_recursively(c, language)

    return models.get_localized_values(field, field, models.Field.localized_keys, language)


def serialize_archived_questionnaire_schema(questionnaire_schema, language):
    questionnaire = copy.deepcopy(questionnaire_schema)

    for step in questionnaire:
        for field in step['children']:
            serialize_archived_field_recursively(field, language)

        models.get_localized_values(step, step, models.Step.localized_keys, language)

    return questionnaire


def serialize_identityaccessrequest(session, identityaccessrequest):
    return {
        'id': identityaccessrequest.id,
        'internaltip_id': identityaccessrequest.internaltip_id,
        'request_date': identityaccessrequest.request_date,
        'request_user_id': identityaccessrequest.request_user_id,
        'request_motivation': identityaccessrequest.request_motivation,
        'reply_date': identityaccessrequest.reply_date,
        'reply_user_id': identityaccessrequest.reply_user_id,
        'reply': identityaccessrequest.reply,
        'reply_motivation': identityaccessrequest.reply_motivation
    }


def serialize_comment(session, comment):
    """
    Transaction returning a serialized descriptor of a comment

    :param session: An ORM session
    :param comment: A model to be serialized
    :return: A serialized description of the model specified
    """
    return {
        'id': comment.id,
        'creation_date': comment.creation_date,
        'content': comment.content,
        'author_id': comment.author_id,
        'visibility': comment.visibility,
        'hash_sha256': comment.hash_sha256,
        'hash_sha512': comment.hash_sha512
    }


def serialize_redaction(session, redaction):
    """
    Transaction returning a serialized descriptor of a redaction

    :param session: An ORM session
    :param redaction: A model to be serialized
    :return: A serialized description of the model specified
    """
    return {
        'id': redaction.id,
        'reference_id': redaction.reference_id,
        'entry': redaction.entry,
        'internaltip_id': redaction.internaltip_id,
        'update_date': redaction.update_date,
        'temporary_redaction': redaction.temporary_redaction,
        'permanent_redaction': redaction.permanent_redaction
    }


def compute_status(file_obj):
    state = file_obj.state

    if not state:
        return EnumStateFile.pending.name.upper()

    if isinstance(state, str):
        for e in EnumStateFile:
            if e.name.lower() == state.lower():
                return e.name.upper()
        return EnumStateFile.pending.name.upper()

    return EnumStateFile(state).name.upper()


def serialize_ifile(session, ifile):
    error = not os.path.exists(os.path.join(State.settings.attachments_path, ifile.id))
    status = compute_status(ifile)

    # A whistleblower's file is considered downloaded as soon as at least one
    # recipient has accessed it (any WhistleblowerFile copy with a set access_date).
    downloaded = session.query(models.WhistleblowerFile) \
                        .filter(models.WhistleblowerFile.internalfile_id == ifile.id,
                                models.WhistleblowerFile.access_date != datetime_null()) \
                        .first() is not None

    return {
        'id': ifile.id,
        'creation_date': ifile.creation_date,
        'name': ifile.name,
        'size': ifile.size,
        'type': ifile.content_type,
        'reference_id': ifile.reference_id,
        'masked': False,
        'status': status,
        'verification_date': ifile.verification_date,
        'error': error,
        'downloaded': downloaded,
        'hash_sha256': ifile.hash_sha256,
        'hash_sha512': ifile.hash_sha512
    }


def serialize_wbfile(session, ifile, wbfile):
    error = not os.path.exists(os.path.join(State.settings.attachments_path, ifile.id)) and \
        not os.path.exists(os.path.join(State.settings.attachments_path, wbfile.id))

    status = compute_status(ifile)

    return {
        'id': wbfile.id,
        'ifile_id': ifile.id,
        'creation_date': ifile.creation_date,
        'name': ifile.name,
        'size': ifile.size,
        'type': ifile.content_type,
        'reference_id': ifile.reference_id,
        'masked': False,
        'status': status,
        'verification_date': ifile.verification_date,
        'error': error,
        'downloaded': wbfile.access_date != datetime_null(),
        'hash_sha256': ifile.hash_sha256,
        'hash_sha512': ifile.hash_sha512
    }

def serialize_rfile(session, rfile):
    error = not os.path.exists(os.path.join(State.settings.attachments_path, rfile.id))
    status = compute_status(rfile)

    return {
        'id': rfile.id,
        'creation_date': rfile.creation_date,
        'author_id': rfile.author_id,
        'name': rfile.name,
        'size': rfile.size,
        'type': rfile.content_type,
        'description': rfile.description,
        'visibility': rfile.visibility,
        'masked': False,
        'status': status,
        'verification_date': rfile.verification_date,
        'error': error,
        'downloaded': rfile.access_date != datetime_null(),
        'hash_sha256': rfile.hash_sha256,
        'hash_sha512': rfile.hash_sha512
    }

def serialize_itip(session, internaltip, language):
    x = session.query(models.InternalTipAnswers, models.ArchivedSchema) \
               .filter(models.ArchivedSchema.hash == models.InternalTipAnswers.questionnaire_hash,
                       models.InternalTipAnswers.internaltip_id == internaltip.id) \
               .order_by(models.InternalTipAnswers.creation_date.asc())

    questionnaires = []
    for ita, aqs in x:
        questionnaires.append({
            'steps': serialize_archived_questionnaire_schema(aqs.schema, language),
            'answers': ita.answers,
            'hash_sha256': ita.hash_sha256 or '',
            'hash_sha512': ita.hash_sha512 or ''
        })

    ret = {
        'id': internaltip.id,
        'creation_date': internaltip.creation_date,
        'update_date': internaltip.update_date,
        'expiration_date': internaltip.expiration_date,
        'context_id': internaltip.context_id,
        'type': internaltip.type,
        'allow_forward': internaltip.allow_forward,
        'questionnaires': questionnaires,
        'tor': internaltip.tor,
        'mobile': internaltip.mobile,
        'reminder_date' : internaltip.reminder_date,
        'identity_provided': internaltip.enable_whistleblower_identity,
        'enable_whistleblower_download': not internaltip.deprecated_crypto_files_pub_key,
        'last_access': internaltip.last_access,
        'score': internaltip.score,
        'status': internaltip.status,
        'substatus': internaltip.substatus,
        'receivers': [],
        'comments': [],
        'wbfiles': [],
        'rfiles': [],
        'redactions': [],
        'data': {},
        "receipt_change_needed": internaltip.receipt_change_needed
    }

    for itd in session.query(models.InternalTipData).filter(models.InternalTipData.internaltip_id == internaltip.id):
        ret['data'][itd.key] = itd.value
        ret['data'][itd.key + "_date"] = itd.creation_date
        ret['data'][itd.key + "_hash_sha256"] = itd.hash_sha256 or ''
        ret['data'][itd.key + "_hash_sha512"] = itd.hash_sha512 or ''

    return ret



def serialize_rtip(session, itip, rtip, language):
    """
    Transaction returning a serialized descriptor of a tip

    :param session: An ORM session
    :param rtip: A model to be serialized
    :param itip: A itip object referenced by the model to be serialized
    :param language: A language of the serialization
    :return: A serialized description of the model specified
    """
    user_id = rtip.receiver_id
    viewer = session.query(models.User).get(user_id)
    viewer_tid = viewer.tid if viewer else itip.tid

    ret = serialize_itip(session, itip, language)

    ret['id'] = itip.id
    ret['rtip_id'] = rtip.id
    ret['progressive'] = itip.progressive
    ret['receiver_id'] = user_id
    ret['custodian'] = State.tenants[itip.tid].cache['custodian']
    ret['important'] = itip.important
    ret['label'] = itip.label
    ret['enable_notifications'] = rtip.enable_notifications
    ret['itip_last_access'] = ret['last_access']
    ret['last_access'] = rtip.last_access
    ret['forwards'] = []

    # The read receipt reports the counterpart of the report: the
    # whistleblower on an ordinary report, the recipients on the other side
    # on the report created by a forward and on a request of forward
    if itip.type in ('forward-request', 'forward'):
        counterpart_last_access = session.query(func.max(models.ReceiverTip.last_access)) \
            .filter(models.ReceiverTip.internaltip_id == itip.id,
                    models.User.id == models.ReceiverTip.receiver_id,
                    models.User.tid != viewer_tid).scalar()
        ret['counterpart_last_access'] = counterpart_last_access or datetime_null()
    else:
        ret['counterpart_last_access'] = itip.last_access

    # Importance, label and reminder belong to the recipients of the tenant the
    # report belongs to: they are not serialized to the recipients reading it
    # from the other side of a forward, that are presented no operation on the
    # report either
    ret['owned'] = itip.is_owned_by(viewer_tid)
    if not ret['owned']:
        ret['important'] = False
        ret['label'] = ''
        ret['reminder_date'] = datetime_never()

    tenant_names = {}

    def get_tenant_name(tid):
        if tid not in tenant_names:
            tenant_names[tid] = ConfigFactory(session, tid).get_val('name')
        return tenant_names[tid]

    forwards = session.query(models.InternalTipForwarding, models.InternalTip) \
                      .filter(models.InternalTipForwarding.internaltip_id == itip.id,
                              models.InternalTip.id == models.InternalTipForwarding.forwarding_internaltip_id) \
                      .order_by(models.InternalTip.creation_date.desc())

    for _, forwarded_itip in forwards:
        ret['forwards'].append({
            'id': forwarded_itip.id,
            'creation_date': forwarded_itip.creation_date,
            'target_tid': forwarded_itip.tid,
            'tenant_name': get_tenant_name(forwarded_itip.tid),
            'progressive': forwarded_itip.progressive,
            'status': forwarded_itip.status,
            'substatus': forwarded_itip.substatus,
            # Whether the viewer follows the report created by the forward: the
            # tenant that receives a forward decides whether the sender keeps
            # accessing it, so the access is told by the tip granted, not inferred
            'accessible': session.query(models.ReceiverTip)
                                 .filter(models.ReceiverTip.internaltip_id == forwarded_itip.id,
                                         models.ReceiverTip.receiver_id == user_id)
                                 .count() > 0
        })

    # The report created by a forward names the two tenants it runs between.
    # The exchange with the whistleblower belongs to the receiving tenant
    # alone: the other recipients are not presented the channel and are handed
    # instead the report the forward originates from, to walk back to it.
    ret['forwarding'] = None
    if itip.type == 'forward':
        forwarding = session.query(models.InternalTipForwarding) \
                            .filter(models.InternalTipForwarding.forwarding_internaltip_id == itip.id) \
                            .one_or_none()
        if forwarding is not None:
            # The tenant of origin is the one recorded when the forward was
            # performed: the tenant of the source report names it only for the
            # direct forwards, a forward performed upon a request originates
            # from the requester while the request lives on the receiving tenant
            forwarded_from = session.query(models.InternalTipData.value) \
                                    .filter(models.InternalTipData.internaltip_id == itip.id,
                                            models.InternalTipData.key == 'forwarded_from') \
                                    .scalar()
            source_tid = forwarded_from.get('source_tid') if forwarded_from else None
            if source_tid is None:
                source_tid = session.query(models.InternalTip.tid) \
                                    .filter(models.InternalTip.id == forwarding.internaltip_id) \
                                    .scalar()
            ret['forwarding'] = {
                'from_tenant_name': get_tenant_name(source_tid) if source_tid else '',
                'to_tenant_name': get_tenant_name(itip.tid),
                'update_date': forwarding.update_date,
                'messages_enabled': viewer_tid == itip.tid and
                                    forwarding.messages_enabled(itip),
                'internaltip_id': forwarding.internaltip_id if viewer_tid != itip.tid else ''
            }
    elif itip.type == 'forward-request':
        # The request of forward names the two tenants it runs between exactly
        # as the report created by a forward does: it originates from the
        # tenant that issued it and is received by the tenant it is filed on
        request_data = session.query(models.InternalTipData.value) \
                              .filter(models.InternalTipData.internaltip_id == itip.id,
                                      models.InternalTipData.key == 'forward_request') \
                              .scalar()

        try:
            source_tid = int(request_data.get('source_tid'))
        except (AttributeError, TypeError, ValueError):
            source_tid = None

        if source_tid is not None:
            ret['forwarding'] = {
                'from_tenant_name': get_tenant_name(source_tid),
                'to_tenant_name': get_tenant_name(itip.tid),
                'update_date': itip.update_date,
                'messages_enabled': False,
                'internaltip_id': ''
            }

    iar = session.query(models.IdentityAccessRequest) \
                 .filter(models.IdentityAccessRequest.internaltip_id == itip.id) \
                 .order_by(models.IdentityAccessRequest.request_date.desc()).first()

    if iar:
        ret['iar'] = serialize_identityaccessrequest(session, iar)

    for redaction in session.query(models.Redaction) \
                            .filter(models.Redaction.internaltip_id == itip.id):
        ret['redactions'].append(serialize_redaction(session, redaction))

    active_receiver_ids = session.query(models.ReceiverTip.receiver_id) \
        .filter(models.ReceiverTip.internaltip_id == itip.id) \
        .distinct()
    active_receiver_ids = set(rid for (rid,) in active_receiver_ids)
    other_receiver_ids = set()

    denied_identity_files = ['1']
    if 'whistleblower_identity' in ret['data']:
        ret['data']['whistleblower_identity_provided'] = True

    if 'iar' not in ret or ret['iar']['reply'] in ('denied', 'pending'):
        if 'data' in ret and 'whistleblower_identity' in ret['data']:
            del ret['data']['whistleblower_identity']

        denied_identity_files = get_identity_files(ret.get('questionnaires', []))

    for ifile, wbfile in session.query(models.InternalFile, models.WhistleblowerFile) \
                               .filter(models.InternalFile.id == models.WhistleblowerFile.internalfile_id,
                                       not_(func.substr(models.InternalFile.reference_id, 1, 36).in_(denied_identity_files)),
                                       models.WhistleblowerFile.receivertip_id == rtip.id):
        ret['wbfiles'].append(serialize_wbfile(session, ifile, wbfile))

    # The public visibility holds the space where the whistleblower is: on the
    # report created by a forward it stays between the whistleblower and the
    # tenant that received it. The forward visibility holds the space the two
    # tenants of a forward share; an internal element is confined to the
    # recipients of the tenant of its author; a personal element to its author.
    sees_public = itip.type != 'forward' or viewer_tid == itip.tid
    author = aliased(models.User)

    rfile_clauses = [models.ReceiverFile.visibility == 3,
                     and_(models.ReceiverFile.visibility == 2,
                          models.ReceiverFile.author_id == user_id),
                     and_(models.ReceiverFile.visibility == 1,
                          or_(models.ReceiverFile.author_id == user_id,
                              author.tid == viewer_tid))]
    comment_clauses = [models.Comment.visibility == 3,
                       and_(models.Comment.visibility == 2,
                            models.Comment.author_id == user_id),
                       and_(models.Comment.visibility == 1,
                            or_(models.Comment.author_id == user_id,
                                author.tid == viewer_tid))]
    if sees_public:
        rfile_clauses.append(models.ReceiverFile.visibility == 0)
        comment_clauses.append(models.Comment.visibility == 0)

    for rfile in session.query(models.ReceiverFile) \
                        .outerjoin(author, author.id == models.ReceiverFile.author_id) \
                        .filter(models.ReceiverFile.internaltip_id == itip.id,
                                or_(*rfile_clauses)):
        ret['rfiles'].append(serialize_rfile(session, rfile))
        if rfile.author_id:
            other_receiver_ids.add(rfile.author_id)

    for comment in session.query(models.Comment) \
                          .outerjoin(author, author.id == models.Comment.author_id) \
                          .filter(models.Comment.internaltip_id == itip.id,
                                  or_(*comment_clauses)):
        ret['comments'].append(serialize_comment(session, comment))
        if comment.author_id:
            other_receiver_ids.add(comment.author_id)

    receiver_ids = active_receiver_ids | other_receiver_ids

    rtips = session.query(models.ReceiverTip).filter(models.ReceiverTip.internaltip_id == itip.id, models.ReceiverTip.receiver_id.in_(receiver_ids)).all()
    rtip_map = {rtip.receiver_id: rtip for rtip in rtips}

    users = session.query(models.User).filter(models.User.id.in_(receiver_ids)).all()
    user_map = {user.id: user for user in users}
    for uid in receiver_ids:
        user = user_map.get(uid)

        # On the report created by a forward each tenant is presented its own
        # recipients alone: the other side of the forward is known only by the
        # name of its tenant
        if itip.type == 'forward' and (user is None or user.tid != viewer_tid):
            continue

        name = user.name if user else 'Recipient'
        if user and user.tid != viewer_tid:
            # The identity of a receiver following the report from the other
            # tenant of a forward is not disclosed: it is presented by the
            # name of its tenant
            name = get_tenant_name(user.tid)

        rtip_obj = rtip_map.get(uid)
        ret['receivers'].append({
            'id': uid,
            'name': name,
            'active': uid in active_receiver_ids,
            'last_access': rtip_obj.last_access if rtip_obj else None
        })

    return ret


def serialize_wbtip(session, itip, language):
    ret = serialize_itip(session, itip, language)

    # The whistleblower is presented the forwards of its report, each carrying
    # the exchange with the recipients of the tenant that received it; the
    # tenant is the only identity disclosed
    ret['forwards'] = []
    forwards = session.query(models.InternalTipForwarding, models.InternalTip) \
                      .filter(models.InternalTipForwarding.internaltip_id == itip.id,
                              models.InternalTip.id == models.InternalTipForwarding.forwarding_internaltip_id) \
                      .order_by(models.InternalTip.creation_date.desc())

    for forwarding, forwarded_itip in forwards:
        ret['forwards'].append({
            'id': forwarded_itip.id,
            'creation_date': forwarded_itip.creation_date,
            'update_date': forwarding.update_date,
            'tenant_name': ConfigFactory(session, forwarded_itip.tid).get_val('name'),
            'status': forwarded_itip.status,
            'substatus': forwarded_itip.substatus,
            'messages_enabled': forwarding.messages_enabled(forwarded_itip)
        })

    active_receiver_ids = session.query(models.ReceiverTip.receiver_id) \
        .filter(models.ReceiverTip.internaltip_id == itip.id) \
        .distinct()
    active_receiver_ids = set(rid for (rid,) in active_receiver_ids)
    other_receiver_ids = set()

    for ifile in session.query(models.InternalFile) \
                        .filter(models.InternalFile.internaltip_id == itip.id):
        ret['wbfiles'].append(serialize_ifile(session, ifile))

    for rfile in session.query(models.ReceiverFile) \
                         .filter(models.ReceiverFile.internaltip_id == itip.id,
                                 models.ReceiverFile.visibility == 0):
        ret['rfiles'].append(serialize_rfile(session, rfile))
        if rfile.author_id:
            other_receiver_ids.add(rfile.author_id)

    for comment in session.query(models.Comment) \
                          .filter(models.Comment.internaltip_id == itip.id,
                                  models.Comment.visibility == 0):
        ret['comments'].append(serialize_comment(session, comment))
        if comment.author_id:
            other_receiver_ids.add(comment.author_id)

    receiver_ids = active_receiver_ids | other_receiver_ids

    rtips = session.query(models.ReceiverTip).filter(models.ReceiverTip.internaltip_id == itip.id, models.ReceiverTip.receiver_id.in_(receiver_ids)).all()
    rtip_map = {rtip.receiver_id: rtip for rtip in rtips}

    users = session.query(models.User).filter(models.User.id.in_(receiver_ids)).all()
    user_map = {user.id: user for user in users}
    for uid in receiver_ids:
        user = user_map.get(uid)
        rtip_obj = rtip_map.get(uid)
        ret['receivers'].append({
            'id': uid,
            'name': user.public_name if user else 'Recipient',
            'active': uid in active_receiver_ids,
            'last_access': rtip_obj.last_access if rtip_obj else None
        })

    return ret


def serialize_redirect(redirect):
    """
    Transact for serializing a redirect

    :param redirect: The redirect to be serialized
    :return: The serialized redirect
    """
    return {
        'id': redirect.id,
        'path1': redirect.path1,
        'path2': redirect.path2
    }


def serialize_signup(signup):
    """
    Transaction serializing the signup descriptor

    :param signup: A signup model
    :return: A serialization of the provided model
    """
    return {
        'name': signup.name,
        'surname': signup.surname,
        'email': signup.email,
        'phone': signup.phone,
        'subdomain': signup.subdomain,
        'language': signup.language,
        'activation_token': signup.activation_token,
        'registration_date': signup.registration_date,
        'organization_name': signup.organization_name,
        'organization.tax_code': signup.organization_tax_code,
        'organization_vat_code': signup.organization_vat_code,
        'organization_location': signup.organization_location,
        'tos1': signup.tos1,
        'tos2': signup.tos2
    }


def serialize_tenant(session, tenant, config=None):
    ret = {
      'id': tenant.id,
      'creation_date': tenant.creation_date,
      'active': tenant.active
    }

    if config:
        ret.update(config)
    else:
        ret.update(ConfigFactory(session, tenant.id).serialize('tenant'))

    return ret


def serialize_auditlog_as_comment(log):
    """
    Serialize an audit log entry for external use.
    """
    return {
        'id': log.id,
        'creation_date': log.date,
        'content': '',
        'data': log.data,
        'author_id': log.user_id,
        'visibility': 'public',
        'type': 'auditlog_' + log.type
    }


def get_label(session, label_id, table):
    """
    Fetch the label for a given UUID from the specified table.
    """
    result = session.query(table).filter_by(id=label_id).first()
    return result.label['en'] if result else f"Unknown {table.__tablename__}"


def format_date(date):
    """
    Format the date to the desired string format.
    """
    return date.strftime("%B %d, %Y")


@transact
def process_logs(session, tip, tip_id):
    """
    Process a list of logs to append their details to a tip dictionary.
    """
    logs = session.query(models.AuditLog).filter(
        models.AuditLog.object_id == tip_id,
        models.AuditLog.type.in_(['update_report_status', 'update_report_expiration'])
    )

    for log in logs:
        tip['comments'].append(serialize_auditlog_as_comment(log))

    return tip
