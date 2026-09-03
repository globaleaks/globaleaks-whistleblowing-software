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
from globaleaks.handlers.public import serialize_questionnaire


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

    internaltip_data = session.query(models.InternalTipData) \
                              .filter(models.InternalTipData.internaltip_id == internaltip.id).all()

    # A report accumulates its questionnaire and the additional ones asked over its life, each named
    # by the questionnaire it answers
    answered = list(x)

    names = dict(session.query(models.Questionnaire.id, models.Questionnaire.name)
                        .filter(models.Questionnaire.id.in_({ita.questionnaire_id for ita, _ in answered})))

    questionnaires = []
    for ita, aqs in answered:
        questionnaires.append({
            'questionnaire_id': ita.questionnaire_id,
            'name': names.get(ita.questionnaire_id, ''),
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
        'additional_questionnaire_id': internaltip.additional_questionnaire_id,
        'type': internaltip.type,
        'allow_transmission': internaltip.allow_transmission,
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

    for itd in internaltip_data:
        ret['data'][itd.key] = itd.value
        ret['data'][itd.key + "_date"] = itd.creation_date
        ret['data'][itd.key + "_hash_sha256"] = itd.hash_sha256 or ''
        ret['data'][itd.key + "_hash_sha512"] = itd.hash_sha512 or ''

    return ret



def db_exchange_sides(session, itip):
    """
    Return the two sites what an exchange created runs between

    :param session: An ORM session
    :param itip: The internaltip of what an exchange created
    :return: The tenant ID of the site that filed and of the one that received
    """
    recorded = session.query(models.InternalTipData.value) \
                      .filter(models.InternalTipData.internaltip_id == itip.id,
                              models.InternalTipData.key.in_(['request', 'transmitted_from'])) \
                      .first()
    recorded = recorded[0] if recorded else {}

    try:
        source_tid = int(recorded.get('source_tid'))
    except (AttributeError, TypeError, ValueError):
        source_tid = None

    try:
        target_tid = int(recorded.get('target_tid'))
    except (AttributeError, TypeError, ValueError):
        target_tid = itip.tid if source_tid != itip.tid else None

    return source_tid, target_tid


def db_runs_between_sites(session, itip):
    """
    Check whether what an exchange created runs between two different sites

    :param session: An ORM session
    :param itip: The internaltip of what an exchange created
    :return: True when two sites read it, False when a single one does
    """
    if itip.type not in ('request', 'exchange'):
        return False

    source_tid, target_tid = db_exchange_sides(session, itip)

    return source_tid != target_tid


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
    ret['exchanges'] = []

    # The read receipt is the counterpart's, any of whom reads for all: the recipients of the other
    # site on a request or a communication, the whistleblower otherwise, on a transmitted report
    # through the messages handed to them
    from globaleaks.handlers.exchange import db_get_report_exchange  # noqa: PLC0415

    exchange = db_get_report_exchange(session, itip)
    if db_runs_between_sites(session, itip) and \
            (itip.type == 'request' or (exchange is not None and exchange.type == 'communication')):
        counterpart_last_access = session.query(func.max(models.ReceiverTip.last_access)) \
            .filter(models.ReceiverTip.internaltip_id == itip.id,
                    models.User.id == models.ReceiverTip.receiver_id,
                    models.User.tid != viewer_tid).scalar()
        ret['counterpart_last_access'] = counterpart_last_access or datetime_null()
    else:
        ret['counterpart_last_access'] = itip.last_access

    # The channel lives on the owning site: its name travels with the report
    channel = session.query(models.Context).get(itip.context_id)
    ret['context_name'] = models.get_localized_values({}, channel, ['name'], language)['name'] \
        if channel is not None else ''

    # Importance, label and reminder belong to the owning tenant: not serialized to the other side
    # of an exchange
    ret['owned'] = itip.is_owned_by(viewer_tid)
    if not ret['owned']:
        ret['important'] = False
        ret['label'] = ''
        ret['reminder_date'] = datetime_never()

    # Local import to avoid a circular import with handlers.recipient.rtip.
    from globaleaks.handlers.recipient.rtip import db_get_requestable_questionnaires  # noqa: PLC0415

    # Requestable while the report is owned and open, and there is something to ask or already asked
    ret['additional_questionnaire_requestable'] = \
        ret['owned'] and \
        itip.status != 'closed' and \
        (bool(itip.additional_questionnaire_id) or
         db_get_requestable_questionnaires(session, itip).count() > 0)

    tenant_names = {}

    def get_tenant_name(tid):
        if tid not in tenant_names:
            tenant_names[tid] = ConfigFactory(session, tid).get_val('name')
        return tenant_names[tid]

    # Listed under the report: what was handed over to other sites and what was entered upon a
    # granted request
    filed = session.query(models.InternalTipTransmission, models.InternalTip) \
                   .filter(models.InternalTipTransmission.internaltip_id == itip.id,
                           models.InternalTip.id == models.InternalTipTransmission.transmitting_internaltip_id) \
                   .order_by(models.InternalTip.creation_date.desc())

    for _, filed_itip in filed:
        source_tid, target_tid = db_exchange_sides(session, filed_itip)
        counterpart_tid = source_tid if viewer_tid == target_tid else target_tid
        if counterpart_tid is None:
            counterpart_tid = filed_itip.tid

        # named by the receiving site, or by the channel when it stayed on this one
        destination = get_tenant_name(counterpart_tid)
        if source_tid == target_tid:
            from globaleaks.handlers.exchange import db_get_report_exchange  # noqa: PLC0415
            from globaleaks.models.exchanges import db_get_exchange_channel  # noqa: PLC0415

            exchange = db_get_report_exchange(session, filed_itip)
            channel = db_get_exchange_channel(session, exchange, viewer_tid) \
                if exchange is not None else None

            if channel is not None:
                destination = models.get_localized_values({}, channel, ['name'],
                                                          language)['name']

        ret['exchanges'].append({
            'id': filed_itip.id,
            'creation_date': filed_itip.creation_date,
            'target_tid': counterpart_tid,
            'tenant_name': destination,
            'progressive': filed_itip.progressive,
            'status': filed_itip.status,
            'substatus': filed_itip.substatus,
            # followed by the recipients of the origin that held it when it was filed
            'accessible': session.query(models.ReceiverTip)
                                 .filter(models.ReceiverTip.internaltip_id == filed_itip.id,
                                         models.ReceiverTip.receiver_id == user_id)
                                 .count() > 0
        })

    # The exchange with the whistleblower belongs to the owning site alone
    ret['exchange'] = None

    def origin_held(transmission):
        return session.query(models.ReceiverTip) \
                      .filter(models.ReceiverTip.internaltip_id == transmission.internaltip_id,
                              models.ReceiverTip.receiver_id == user_id) \
                      .count() > 0

    if db_runs_between_sites(session, itip):
        source_tid, target_tid = db_exchange_sides(session, itip)

        transmission = session.query(models.InternalTipTransmission) \
                            .filter(models.InternalTipTransmission.transmitting_internaltip_id == itip.id) \
                            .one_or_none()

        ret['exchange'] = {
            # typed by what created it: a transmission or a communication
            'type': exchange.type if exchange is not None else '',
            'from_tenant_name': get_tenant_name(source_tid) if source_tid else '',
            'to_tenant_name': get_tenant_name(target_tid) if target_tid else '',
            'update_date': itip.update_date,
            # walked back to the report of origin, or to the request that granted it
            'internaltip_id': transmission.internaltip_id
                              if transmission is not None and origin_held(transmission) else ''
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

    # 'public' is shared with the counterpart, 'internal' with the recipients of the viewer's site
    author = aliased(models.User)

    rfile_clauses = [models.ReceiverFile.visibility == 0,
                     and_(models.ReceiverFile.visibility == 2,
                          models.ReceiverFile.author_id == user_id),
                     and_(models.ReceiverFile.visibility == 1,
                          or_(models.ReceiverFile.author_id == user_id,
                              author.tid == viewer_tid))]
    comment_clauses = [models.Comment.visibility == 0,
                       and_(models.Comment.visibility == 2,
                            models.Comment.author_id == user_id),
                       and_(models.Comment.visibility == 1,
                            or_(models.Comment.author_id == user_id,
                                author.tid == viewer_tid))]

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

        # each tenant is presented its own recipients; the other side is known by the name of its
        # tenant
        if itip.type == 'exchange' and (user is None or user.tid != viewer_tid):
            continue

        name = user.name if user else 'Recipient'
        if user and user.tid != viewer_tid:
            # the identity of a receiver of the other tenant is not disclosed
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
    # Local import to avoid a circular import with handlers.public.

    ret = serialize_itip(session, itip, language)

    # The questionnaire asked of this report is not among the published ones: it travels with the
    # report
    if itip.additional_questionnaire_id:
        questionnaire = session.query(models.Questionnaire) \
                               .filter(models.Questionnaire.id == itip.additional_questionnaire_id) \
                               .one_or_none()

        if questionnaire is not None:
            ret['additional_questionnaire'] = serialize_questionnaire(session, itip.tid, questionnaire, language,
                                                                      serialize_templates=True, include_scoring=False)

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
