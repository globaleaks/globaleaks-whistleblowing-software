# -*- coding: utf-8 -*-
"""
ORM Models definitions.
"""
import copy

from datetime import datetime
from email.policy import default

from globaleaks.models import config_desc
from globaleaks.models.enums import *
from globaleaks.models.properties import *
from globaleaks.utils.utility import datetime_now, datetime_never, datetime_null


class LocalizationEngine(object):
    """
    This Class can manage all the localized strings inside one ORM object
    """

    def __init__(self, keys):
        self._localized_strings = {}
        self._localized_keys = keys

    def acquire_orm_object(self, obj):
        self._localized_strings = {key: getattr(obj, key) for key in self._localized_keys}

    def acquire_multilang_dict(self, obj):
        self._localized_strings = {}
        self._localized_strings = {key: obj.get(key, '') for key in self._localized_keys}

    def singlelang_to_multilang_dict(self, obj, language):
        return {key: {language: obj.get(key, '')} for key in self._localized_keys}

    def dump_localized_key(self, key, language):
        translated_dict = self._localized_strings.get(key, "")

        if not isinstance(translated_dict, dict):
            return ""

        if language is None:
            # When language is None we export the full language dictionary
            return translated_dict
        elif language in translated_dict:
            return translated_dict[language]
        elif 'en' in translated_dict:
            return translated_dict['en']
        else:
            return ""


def fill_localized_keys(dictionary, keys, language):
    if language is not None:
        mo = LocalizationEngine(keys)
        multilang_dict = mo.singlelang_to_multilang_dict(dictionary, language)
        dictionary.update({key: multilang_dict[key] for key in keys})

    return dictionary


def get_localized_values(dictionary, obj, keys, language):
    mo = LocalizationEngine(keys)

    if isinstance(obj, dict):
        mo.acquire_multilang_dict(obj)
    elif isinstance(obj, Model):
        mo.acquire_orm_object(obj)

    if language is not None:
        dictionary.update({key: mo.dump_localized_key(key, language) for key in keys})
    else:
        dictionary.update({key: mo._localized_strings.get(key, '') for key in keys})

    return dictionary


Base = declarative_base()


class Model(object):
    """
    Base ORM model
    """
    # initialize empty list for the base classes
    properties = []
    unicode_keys = []
    localized_keys = []
    int_keys = []
    bool_keys = []
    datetime_keys = []
    json_keys = []
    date_keys = []
    optional_references = []
    list_keys = []

    def __init__(self, values=None):
        self.update(values)

        self.properties = self.__mapper__.column_attrs.keys()

    def update(self, values=None):
        """
        Updated Models attributes from dict.
        """
        if values is None:
            return

        if 'id' in values and values['id']:
            setattr(self, 'id', values['id'])

        if 'tid' in values and values['tid']:
            setattr(self, 'tid', values['tid'])

        for k in getattr(self, 'unicode_keys'):
            if k in values and values[k] is not None:
                setattr(self, k, values[k])

        for k in getattr(self, 'int_keys'):
            if k in values and values[k] is not None:
                setattr(self, k, int(values[k]))

        for k in getattr(self, 'datetime_keys'):
            if k in values and values[k] is not None:
                setattr(self, k, values[k])

        for k in getattr(self, 'bool_keys'):
            if k in values and values[k] is not None:
                if values[k] == 'true':
                    value = True
                elif values[k] == 'false':
                    value = False
                else:
                    value = bool(values[k])
                setattr(self, k, value)

        for k in getattr(self, 'localized_keys'):
            if k in values and values[k] is not None:
                value = values[k]
                previous = copy.deepcopy(getattr(self, k))

                if previous and isinstance(previous, dict):
                    previous.update(value)
                    value = previous

                setattr(self, k, value)

        for k in getattr(self, 'json_keys'):
            if k in values and values[k] is not None:
                setattr(self, k, values[k])

        for k in getattr(self, 'optional_references'):
            if k in values:
                if values[k]:
                    setattr(self, k, values[k])
                else:
                    setattr(self, k, None)

    def __setattr__(self, name, value):
        if isinstance(value, bytes):
            value = value.decode()

        return super(Model, self).__setattr__(name, value)

    def dict(self, language=None):
        """
        Return a dictionary serialization of the current model.
        """
        ret = {}

        for k in self.properties:
            value = getattr(self, k)

            if value is not None:
                if k in self.localized_keys:
                    if language is not None:
                        ret[k] = value.get(language, '')
                    else:
                        ret[k] = value

                elif k in self.date_keys:
                    ret[k] = value
            else:
                if self.__table__.columns[k].default and not callable(self.__table__.columns[k].default.arg):
                    ret[k] = self.__table__.columns[k].default.arg
                else:
                    ret[k] = ''

        for k in self.list_keys:
            ret[k] = []

        return ret


class _ArchivedSchema(Model):
    __tablename__ = 'archivedschema'

    hash = Column(UnicodeText(64), primary_key=True)
    schema = Column(JSON, default=dict, nullable=False)

    unicode_keys = ['hash']


class _AuditLog(Model):
    """
    This model contains audit logs
    """
    __tablename__ = 'auditlog'
    __table_args__ = {'sqlite_autoincrement': True}

    id = Column(Integer, primary_key=True)
    tid = Column(Integer, default=1)
    date = Column(DateTime, default=datetime_now, nullable=False)
    type = Column(UnicodeText(24), default='', nullable=False)
    user_id = Column(UnicodeText(36))
    object_id = Column(UnicodeText(36))
    data = Column(JSON)


class _Comment(Model):
    """
    This table handle the comment collection, has an InternalTip referenced
    """
    __tablename__ = 'comment'

    id = Column(UnicodeText(36), primary_key=True, default=uuid4)
    creation_date = Column(DateTime, default=datetime_now, nullable=False)
    internaltip_id = Column(UnicodeText(36), nullable=False, index=True)
    author_id = Column(UnicodeText(36))
    content = Column(UnicodeText, nullable=False)
    visibility = Column(Enum(EnumVisibility), default='public', nullable=False)
    new = Column(Boolean, default=True, nullable=False)

    @declared_attr
    def __table_args__(self):
        return ForeignKeyConstraint(['internaltip_id'], ['internaltip.id'], ondelete='CASCADE', deferrable=True,
                                    initially='DEFERRED'),


class _Config(Model):
    __tablename__ = 'config'
    tid = Column(Integer, primary_key=True, default=1)
    var_name = Column(UnicodeText(64), primary_key=True)
    value = Column(JSON, default=dict, nullable=False)
    update_date = Column(DateTime, default=datetime_null, nullable=False)

    @declared_attr
    def __table_args__(self):
        return ForeignKeyConstraint(['tid'], ['tenant.id'], ondelete='CASCADE', deferrable=True, initially='DEFERRED'),

    def __init__(self, values=None):
        """
        :param values:   This input is passed directly into set_v
        """
        if values is None:
            return

        self.tid = values['tid']
        self.var_name = values['var_name']
        self.set_v(values['value'])

    def set_v(self, val):
        desc = config_desc.ConfigDescriptor[self.var_name]
        if val is None:
            val = desc._type()

        if isinstance(val, bytes):
            val = val.decode()

        if isinstance(val, datetime):
            val = int(datetime.timestamp(val))

        if not isinstance(val, desc._type):
            raise ValueError("Cannot assign %s with %s" % (self, type(val)))

        if self.value != val:
            if self.value is not None:
                self.update_date = datetime_now()

            self.value = val


class _ConfigL10N(Model):
    __tablename__ = 'config_l10n'

    tid = Column(Integer, primary_key=True, default=1)
    lang = Column(UnicodeText(12), primary_key=True)
    var_name = Column(UnicodeText(64), primary_key=True)
    value = Column(UnicodeText, nullable=False)
    update_date = Column(DateTime, default=datetime_null, nullable=False)

    @declared_attr
    def __table_args__(self):
        return ForeignKeyConstraint(['tid', 'lang'], ['enabledlanguage.tid', 'enabledlanguage.name'], ondelete='CASCADE', deferrable=True, initially='DEFERRED'),

    def __init__(self, values=None):
        if values is None:
            return

        self.tid = values['tid']
        self.lang = values['lang']
        self.var_name = values['var_name']
        self.value = values['value']

    def set_v(self, value):
        if self.value != value:
            if self.value is not None:
                self.update_date = datetime_now()

            self.value = value


class _Context(Model):
    """
    This model keeps track of contexts settings.
    """
    __tablename__ = 'context'

    id = Column(UnicodeText(36), primary_key=True, default=uuid4)
    tid = Column(Integer, default=1, nullable=False)
    show_steps_navigation_interface = Column(Boolean, default=True, nullable=False)
    allow_recipients_selection = Column(Boolean, default=False, nullable=False)
    maximum_selectable_receivers = Column(Integer, default=0, nullable=False)
    select_all_receivers = Column(Boolean, default=True, nullable=False)
    tip_timetolive = Column(Integer, default=90, nullable=False)
    tip_reminder = Column(Integer, default=0, nullable=False)
    name = Column(JSON, default=dict, nullable=False)
    description = Column(JSON, default=dict, nullable=False)
    show_receivers_in_alphabetical_order = Column(Boolean, default=True, nullable=False)
    score_threshold_high = Column(Integer, default=0, nullable=False)
    score_threshold_medium = Column(Integer, default=0, nullable=False)
    questionnaire_id = Column(UnicodeText(36), default='default', nullable=False, index=True)
    additional_questionnaire_id = Column(UnicodeText(36), index=True)
    hidden = Column(Boolean, default=False, nullable=False)
    order = Column(Integer, default=0, nullable=False)

    unicode_keys = [
        'questionnaire_id',
        'additional_questionnaire_id'
    ]

    localized_keys = [
        'name',
        'description'
    ]

    int_keys = [
        'tip_timetolive',
        'tip_reminder',
        'maximum_selectable_receivers',
        'order',
        'score_threshold_high',
        'score_threshold_medium'
    ]

    bool_keys = [
        'hidden',
        'select_all_receivers',
        'show_context',
        'show_receivers_in_alphabetical_order',
        'show_steps_navigation_interface',
        'allow_recipients_selection'
    ]

    list_keys = ['receivers']

    @declared_attr
    def __table_args__(self):
        return (ForeignKeyConstraint(['tid'], ['tenant.id'], ondelete='CASCADE', deferrable=True, initially='DEFERRED'),
                ForeignKeyConstraint(['questionnaire_id'], ['questionnaire.id'], deferrable=True, initially='DEFERRED'))


class _CustomTexts(Model):
    """
    Class used to implement custom texts
    """
    __tablename__ = 'customtexts'

    tid = Column(Integer, default=1, primary_key=True)
    lang = Column(UnicodeText(12), primary_key=True)
    texts = Column(JSON, default=dict, nullable=False)

    unicode_keys = ['lang']
    json_keys = ['texts']

    @declared_attr
    def __table_args__(self):
        return ForeignKeyConstraint(['tid'], ['tenant.id'], ondelete='CASCADE', deferrable=True, initially='DEFERRED'),


class _EnabledLanguage(Model):
    __tablename__ = 'enabledlanguage'

    tid = Column(Integer, primary_key=True, default=1)
    name = Column(UnicodeText(12), primary_key=True)

    unicode_keys = ['name']

    @declared_attr
    def __table_args__(self):
        return ForeignKeyConstraint(['tid'], ['tenant.id'], ondelete='CASCADE', deferrable=True, initially='DEFERRED'),


class _Field(Model):
    __tablename__ = 'field'

    id = Column(UnicodeText(36), primary_key=True, default=uuid4)
    tid = Column(Integer, default=1, nullable=False)
    x = Column(Integer, default=0, nullable=False)
    y = Column(Integer, default=0, nullable=False)
    width = Column(Integer, default=0, nullable=False)
    label = Column(JSON, default=dict, nullable=False)
    description = Column(JSON, default=dict, nullable=False)
    hint = Column(JSON, default=dict, nullable=False)
    placeholder = Column(JSON, default=dict, nullable=False)
    required = Column(Boolean, default=False, nullable=False)
    multi_entry = Column(Boolean, default=False, nullable=False)
    triggered_by_score = Column(Integer, default=0, nullable=False)
    step_id = Column(UnicodeText(36), index=True)
    fieldgroup_id = Column(UnicodeText(36), index=True)
    type = Column(UnicodeText, default='inputbox', nullable=False)
    instance = Column(Enum(EnumFieldInstance), default='instance', nullable=False)
    template_id = Column(UnicodeText(36), index=True)
    template_override_id = Column(UnicodeText(36), index=True)
    statistical = Column(Boolean, default=False, nullable=False)

    @declared_attr
    def __table_args__(self):
        return (ForeignKeyConstraint(['tid'], ['tenant.id'], ondelete='CASCADE', deferrable=True, initially='DEFERRED'),
                ForeignKeyConstraint(['step_id'], ['step.id'], ondelete='CASCADE', deferrable=True,
                                     initially='DEFERRED'),
                ForeignKeyConstraint(['fieldgroup_id'], ['field.id'], ondelete='CASCADE', deferrable=True,
                                     initially='DEFERRED'),
                ForeignKeyConstraint(['template_id'], ['field.id'], deferrable=True, initially='DEFERRED'),
                ForeignKeyConstraint(['template_override_id'], ['field.id'], ondelete='SET NULL', deferrable=True,
                                     initially='DEFERRED'),
                CheckConstraint(self.instance.in_(EnumFieldInstance.keys())))

    unicode_keys = ['type', 'instance', 'key']
    int_keys = ['x', 'y', 'width', 'triggered_by_score']
    localized_keys = ['label', 'description', 'hint', 'placeholder']
    bool_keys = ['multi_entry', 'required', 'statistical']
    optional_references = ['template_id', 'step_id', 'fieldgroup_id', 'template_override_id']


class _FieldAttr(Model):
    __tablename__ = 'fieldattr'

    field_id = Column(UnicodeText(36), primary_key=True)
    name = Column(UnicodeText, primary_key=True)
    type = Column(Enum(EnumFieldAttrType), nullable=False)
    value = Column(JSON, default=dict, nullable=False)

    unicode_keys = ['field_id', 'name', 'type']

    @declared_attr
    def __table_args__(self):
        return (UniqueConstraint('field_id', 'name'),
                ForeignKeyConstraint(['field_id'], ['field.id'], ondelete='CASCADE', deferrable=True,
                                     initially='DEFERRED'),
                CheckConstraint(self.type.in_(EnumFieldAttrType.keys())))

    def update(self, values=None):
        super(_FieldAttr, self).update(values)

        if values is None:
            return

        value = values['value']

        if self.type == 'localized':
            previous = getattr(self, 'value')
            if previous and isinstance(previous, dict):
                previous = copy.deepcopy(previous)
                previous.update(value)
                value = previous

        self.value = value


class _FieldOption(Model):
    __tablename__ = 'fieldoption'

    id = Column(UnicodeText(36), primary_key=True, default=uuid4)
    field_id = Column(UnicodeText(36), nullable=False, index=True)
    order = Column(Integer, default=0, nullable=False)
    label = Column(JSON, default=dict, nullable=False)
    hint1 = Column(JSON, default=dict, nullable=False)
    hint2 = Column(JSON, default=dict, nullable=False)
    score_points = Column(Integer, default=0, nullable=False)
    score_type = Column(Enum(EnumFieldOptionScoreType), default='addition', nullable=False)
    block_submission = Column(Boolean, default=False, nullable=False)
    trigger_receiver = Column(JSON, default=list, nullable=False)

    unicode_keys = ['field_id']
    bool_keys = ['block_submission']
    int_keys = ['order', 'score_points']
    json_keys = ['trigger_receiver']
    localized_keys = ['hint1', 'hint2', 'label']

    @declared_attr
    def __table_args__(self):
        return ForeignKeyConstraint(['field_id'], ['field.id'], ondelete='CASCADE', deferrable=True,
                                    initially='DEFERRED'),


class _FieldOptionTriggerField(Model):
    __tablename__ = 'fieldoptiontriggerfield'

    option_id = Column(UnicodeText(36), primary_key=True)
    object_id = Column(UnicodeText(36), primary_key=True)
    sufficient = Column(Boolean, default=True, nullable=False)

    @declared_attr
    def __table_args__(self):
        return (ForeignKeyConstraint(['option_id'], ['fieldoption.id'], ondelete='CASCADE', deferrable=True,
                                     initially='DEFERRED'),
                ForeignKeyConstraint(['object_id'], ['field.id'], ondelete='CASCADE', deferrable=True,
                                     initially='DEFERRED'))


class _FieldOptionTriggerStep(Model):
    __tablename__ = 'fieldoptiontriggerstep'

    option_id = Column(UnicodeText(36), primary_key=True)
    object_id = Column(UnicodeText(36), primary_key=True)
    sufficient = Column(Boolean, default=True, nullable=False)

    @declared_attr
    def __table_args__(self):
        return (ForeignKeyConstraint(['option_id'], ['fieldoption.id'], ondelete='CASCADE', deferrable=True,
                                     initially='DEFERRED'),
                ForeignKeyConstraint(['object_id'], ['step.id'], ondelete='CASCADE', deferrable=True,
                                     initially='DEFERRED'))


class _File(Model):
    """
    Class used for storing files
    """
    __tablename__ = 'file'

    tid = Column(Integer, default=1)
    id = Column(UnicodeText(36), primary_key=True, default=uuid4)
    name = Column(UnicodeText, default='', nullable=False)

    unicode_keys = ['name']

    @declared_attr
    def __table_args__(self):
        return (ForeignKeyConstraint(['tid'], ['tenant.id'], ondelete='CASCADE', deferrable=True, initially='DEFERRED'),
                UniqueConstraint('tid', 'name'))


class _IdentityAccessRequest(Model):
    """
    This model keeps track of identity access requests by receivers and
    of the answers by custodians.
    """
    __tablename__ = 'identityaccessrequest'

    id = Column(UnicodeText(36), primary_key=True, default=uuid4)
    internaltip_id = Column(UnicodeText(36), nullable=False, index=True)
    request_date = Column(DateTime, default=datetime_now, nullable=False)
    request_user_id = Column(UnicodeText(36), nullable=False)
    request_motivation = Column(UnicodeText, default='')
    reply_date = Column(DateTime, default=datetime_null, nullable=False)
    reply_user_id = Column(UnicodeText(36))
    reply_motivation = Column(UnicodeText, default='', nullable=False)
    reply = Column(UnicodeText, default='pending', nullable=False)

    @declared_attr
    def __table_args__(self):
        return ForeignKeyConstraint(['internaltip_id'], ['internaltip.id'], ondelete='CASCADE', deferrable=True,
                                    initially='DEFERRED'),


class _IdentityAccessRequestCustodian(Model):
    """
    Class used to implement references between Receivers and Contexts
    """
    __tablename__ = 'identityaccessrequest_custodian'

    identityaccessrequest_id = Column(UnicodeText(36), primary_key=True)
    custodian_id = Column(UnicodeText(36), primary_key=True)
    crypto_tip_prv_key = Column(UnicodeText(84), default='', nullable=False)

    @declared_attr
    def __table_args__(self):
        return (ForeignKeyConstraint(['identityaccessrequest_id'], ['identityaccessrequest.id'], ondelete='CASCADE',
                                     deferrable=True, initially='DEFERRED'),
                ForeignKeyConstraint(['custodian_id'], ['user.id'], ondelete='CASCADE', deferrable=True,
                                     initially='DEFERRED'))


class _ContentForwarding(Model):
    """
    This model keeps track of submission files for the eo
    """
    __tablename__ = 'content_forwarding'

    id = Column(UnicodeText(36), primary_key=True, default=uuid4)
    internaltip_forwarding_id = Column(UnicodeText(36), nullable=False, index=True)
    content_id = Column(UnicodeText(36), nullable=False, index=True)
    forwarding_content_id = Column(UnicodeText(36), nullable=False, index=True)
    content_origin = Column(Enum(EnumContentForwarding), default='receiver_file', nullable=False)
    author_type = Column(Enum(EnumAuthorType), default='main', nullable=False)

    @declared_attr
    def __table_args__(self):
        return (
            ForeignKeyConstraint(
                ['internaltip_forwarding_id'],
                ['internaltip_forwarding.id'],
                ondelete='CASCADE',
                deferrable=True,
                initially='DEFERRED'
            ),
        )


class _InternalFile(Model):
    """
    This model keeps track of submission files
    """
    __tablename__ = 'internalfile'

    id = Column(UnicodeText(36), primary_key=True, default=uuid4)
    creation_date = Column(DateTime, default=datetime_now, nullable=False)
    internaltip_id = Column(UnicodeText(36), nullable=False, index=True)
    name = Column(UnicodeText, nullable=False)
    content_type = Column(JSON, default='', nullable=False)
    size = Column(JSON, default='', nullable=False)
    new = Column(Boolean, default=True, nullable=False)
    reference_id = Column(UnicodeText(36), default='', nullable=False)
    verification_date = Column(DateTime, nullable=True)
    state = Column(Enum(EnumStateFile), default='pending', nullable=False)

    @declared_attr
    def __table_args__(self):
        return ForeignKeyConstraint(['internaltip_id'], ['internaltip.id'], ondelete='CASCADE', deferrable=True,
                                    initially='DEFERRED'),


class _InternalTip(Model):
    """
    This is the internal representation of a Tip that has been submitted
    """
    __tablename__ = 'internaltip'

    id = Column(UnicodeText(36), primary_key=True, default=uuid4)
    tid = Column(Integer, default=1, nullable=False)
    creation_date = Column(DateTime, default=datetime_now, nullable=False)
    update_date = Column(DateTime, default=datetime_now, nullable=False)
    context_id = Column(UnicodeText(36), nullable=False)
    operator_id = Column(UnicodeText(33), default='', nullable=False)
    progressive = Column(Integer, default=0, nullable=False)
    access_count = Column(Integer, default=0, nullable=False)
    tor = Column(Boolean, default=False, nullable=False)
    mobile = Column(Boolean, default=False, nullable=False)
    score = Column(Integer, default=0, nullable=False)
    expiration_date = Column(DateTime, default=datetime_never, nullable=False)
    reminder_date = Column(DateTime, default=datetime_never, nullable=False)
    enable_whistleblower_identity = Column(Boolean, default=False, nullable=False)
    important = Column(Boolean, default=False, nullable=False)
    label = Column(UnicodeText, default='', nullable=False)
    last_access = Column(DateTime, default=datetime_now, nullable=False)
    status = Column(UnicodeText(36))
    substatus = Column(UnicodeText(36))
    receipt_change_needed = Column(Boolean, default=False, nullable=False)
    receipt_hash = Column(UnicodeText(44), nullable=False)
    crypto_prv_key = Column(UnicodeText(84), default='', nullable=False)
    crypto_pub_key = Column(UnicodeText(56), default='', nullable=False)
    crypto_tip_pub_key = Column(UnicodeText(56), default='', nullable=False)
    crypto_tip_prv_key = Column(UnicodeText(84), default='', nullable=False)
    deprecated_crypto_files_pub_key = Column(UnicodeText(56), default='', nullable=False)

    @declared_attr
    def __table_args__(self):
        return (UniqueConstraint('tid', 'progressive'),
                UniqueConstraint('tid', 'receipt_hash'),
                ForeignKeyConstraint(['tid'], ['tenant.id'], ondelete='CASCADE', deferrable=True, initially='DEFERRED'),
                ForeignKeyConstraint(['context_id'], ['context.id'], ondelete='CASCADE', deferrable=True,
                                     initially='DEFERRED'))


class _InternalTipAnswers(Model):
    """
    This is the internal representation of Tip Questionnaire Answers
    """
    __tablename__ = 'internaltipanswers'

    internaltip_id = Column(UnicodeText(36), primary_key=True)
    questionnaire_hash = Column(UnicodeText(64), primary_key=True)
    creation_date = Column(DateTime, default=datetime_now, nullable=False)
    answers = Column(UnicodeText, default='{}', nullable=False)
    stat_answers = Column(UnicodeText, default='{}', nullable=False)

    @declared_attr
    def __table_args__(self):
        return ForeignKeyConstraint(['internaltip_id'], ['internaltip.id'], ondelete='CASCADE', deferrable=True,
                                    initially='DEFERRED'),


class _InternalTipData(Model):
    __tablename__ = 'internaltipdata'

    internaltip_id = Column(UnicodeText(36), primary_key=True)
    key = Column(UnicodeText, primary_key=True)
    creation_date = Column(DateTime, default=datetime_now, nullable=False)
    value = Column(JSON, default=dict, nullable=False)

    @declared_attr
    def __table_args__(self):
        return (UniqueConstraint('internaltip_id', 'key'),
                ForeignKeyConstraint(['internaltip_id'], ['internaltip.id'], ondelete='CASCADE', deferrable=True,
                                     initially='DEFERRED'))


class _Mail(Model):
    """
    This model keeps track of emails to be spooled by the system
    """
    __tablename__ = 'mail'

    id = Column(UnicodeText(36), primary_key=True, default=uuid4)
    tid = Column(Integer, default=1, nullable=False)
    creation_date = Column(DateTime, default=datetime_now, nullable=False)
    address = Column(UnicodeText, nullable=False)
    subject = Column(UnicodeText, nullable=False)
    body = Column(UnicodeText, nullable=False)
    secondary_smtp = Column(Boolean, nullable=False, default=False)

    unicode_keys = ['address', 'subject', 'body']
    bool_keys = ['secondary_smtp']

    @declared_attr
    def __table_args__(self):
        return ForeignKeyConstraint(['tid'], ['tenant.id'], ondelete='CASCADE', deferrable=True, initially='DEFERRED'),


class _Questionnaire(Model):
    __tablename__ = 'questionnaire'

    id = Column(UnicodeText(36), primary_key=True, default=uuid4)
    tid = Column(Integer, default=1, nullable=False)
    name = Column(UnicodeText, default='', nullable=False)

    unicode_keys = ['name']
    list_keys = ['steps']

    @declared_attr
    def __table_args__(self):
        return ForeignKeyConstraint(['tid'], ['tenant.id'], ondelete='CASCADE', deferrable=True, initially='DEFERRED'),


class _ReceiverContext(Model):
    """
    Class used to implement references between Receivers and Contexts
    """
    __tablename__ = 'receiver_context'

    context_id = Column(UnicodeText(36), primary_key=True)
    receiver_id = Column(UnicodeText(36), primary_key=True)
    order = Column(Integer, default=0, nullable=False)

    unicode_keys = ['context_id', 'receiver_id']
    int_keys = ['order']

    @declared_attr
    def __table_args__(self):
        return (
            ForeignKeyConstraint(['context_id'], ['context.id'], ondelete='CASCADE', deferrable=True,
                                 initially='DEFERRED'),
            ForeignKeyConstraint(['receiver_id'], ['user.id'], ondelete='CASCADE', deferrable=True,
                                 initially='DEFERRED'))


class _WhistleblowerFile(Model):
    """
    This model keeps track of files destinated to a specific receiver
    """
    __tablename__ = 'whistleblowerfile'

    id = Column(UnicodeText(36), primary_key=True, default=uuid4)
    internalfile_id = Column(UnicodeText(36), nullable=False, index=True)
    receivertip_id = Column(UnicodeText(36), nullable=False, index=True)
    access_date = Column(DateTime, default=datetime_null, nullable=False)
    new = Column(Boolean, default=True, nullable=False)

    @declared_attr
    def __table_args__(self):
        return (ForeignKeyConstraint(['internalfile_id'], ['internalfile.id'], ondelete='CASCADE', deferrable=True,
                                     initially='DEFERRED'),
                ForeignKeyConstraint(['receivertip_id'], ['receivertip.id'], ondelete='CASCADE', deferrable=True,
                                     initially='DEFERRED'))


class _ReceiverTip(Model):
    """
    This is the table keeping track of all the receivers activities and
    date in a Tip, Tip core data are stored in StoredTip. The data here
    provide accountability of Receiver accesses, operations, options.
    """
    __tablename__ = 'receivertip'

    id = Column(UnicodeText(36), primary_key=True, default=uuid4)
    internaltip_id = Column(UnicodeText(36), nullable=False, index=True)
    receiver_id = Column(UnicodeText(36), nullable=False, index=True)
    access_date = Column(DateTime, default=datetime_null, nullable=False)
    last_access = Column(DateTime, default=datetime_null, nullable=False)
    last_notification = Column(DateTime, default=datetime_null, nullable=False)
    new = Column(Boolean, default=True, nullable=False)
    enable_notifications = Column(Boolean, default=True, nullable=False)
    crypto_tip_prv_key = Column(UnicodeText(84), default='', nullable=False)
    deprecated_crypto_files_prv_key = Column(UnicodeText(84), default='', nullable=False)

    @declared_attr
    def __table_args__(self):
        return (
            ForeignKeyConstraint(['receiver_id'], ['user.id'], ondelete='CASCADE', deferrable=True,
                                 initially='DEFERRED'),
            ForeignKeyConstraint(['internaltip_id'], ['internaltip.id'], ondelete='CASCADE', deferrable=True,
                                 initially='DEFERRED'))


class _Redaction(Model):
    """
    This models keep track of data redactions applied on internaltips and related objects
    """
    __tablename__ = 'redaction'

    id = Column(UnicodeText(36), primary_key=True, default=uuid4)
    reference_id = Column(UnicodeText(36), nullable=False)
    entry = Column(UnicodeText, default='0', nullable=False)
    internaltip_id = Column(UnicodeText(36), nullable=False, index=True)
    temporary_redaction = Column(JSON, default=dict, nullable=False)
    permanent_redaction = Column(JSON, default=dict, nullable=False)
    update_date = Column(DateTime, default=datetime_now, nullable=False)

    @declared_attr
    def __table_args__(self):
        return ForeignKeyConstraint(['internaltip_id'], ['internaltip.id'], ondelete='CASCADE', deferrable=True,
                                    initially='DEFERRED'),


class _Redirect(Model):
    """
    Class used to implement url redirects
    """
    __tablename__ = 'redirect'

    id = Column(UnicodeText(36), primary_key=True, default=uuid4)
    tid = Column(Integer, default=1, nullable=False)
    path1 = Column(UnicodeText, nullable=False)
    path2 = Column(UnicodeText, nullable=False)

    unicode_keys = ['path1', 'path2']

    @declared_attr
    def __table_args__(self):
        return ForeignKeyConstraint(['tid'], ['tenant.id'], ondelete='CASCADE', deferrable=True, initially='DEFERRED'),


class _Step(Model):
    __tablename__ = 'step'

    id = Column(UnicodeText(36), primary_key=True, default=uuid4)
    questionnaire_id = Column(UnicodeText(36), nullable=False, index=True)
    label = Column(JSON, default=dict, nullable=False)
    description = Column(JSON, default=dict, nullable=False)
    triggered_by_score = Column(Integer, default=0, nullable=False)
    order = Column(Integer, default=0, nullable=False)

    unicode_keys = ['questionnaire_id']
    int_keys = ['order', 'triggered_by_score']
    localized_keys = ['label', 'description']

    @declared_attr
    def __table_args__(self):
        return ForeignKeyConstraint(['questionnaire_id'], ['questionnaire.id'], ondelete='CASCADE', deferrable=True,
                                    initially='DEFERRED'),


class _SubmissionStatus(Model):
    """
    Contains the statuses a submission may be in
    """
    __tablename__ = 'submissionstatus'

    id = Column(UnicodeText(36), primary_key=True, default=uuid4)
    tid = Column(Integer, primary_key=True, default=1)
    label = Column(JSON, default=dict, nullable=False)
    order = Column(Integer, default=0, nullable=False)

    # TODO: to be removed at next migration
    tip_timetolive = Column(Integer, default=0, nullable=False)

    localized_keys = ['label']
    int_keys = ['order', 'tip_timetolive']
    json_keys = ['receivers']

    @declared_attr
    def __table_args__(self):
        return ForeignKeyConstraint(['tid'], ['tenant.id'], ondelete='CASCADE', deferrable=True, initially='DEFERRED'),


class _SubmissionSubStatus(Model):
    """
    Contains the substatuses that a submission may be in
    """
    __tablename__ = 'submissionsubstatus'

    id = Column(UnicodeText(36), primary_key=True, default=uuid4)
    tid = Column(Integer, primary_key=True, default=1)
    submissionstatus_id = Column(UnicodeText(36), nullable=False)
    label = Column(JSON, default=dict, nullable=False)
    order = Column(Integer, default=0, nullable=False)
    tip_timetolive = Column(Integer, default=0, nullable=False)

    localized_keys = ['label']
    int_keys = ['order', 'tip_timetolive']

    @declared_attr
    def __table_args__(self):
        return ForeignKeyConstraint(['tid', 'submissionstatus_id'], ['submissionstatus.tid', 'submissionstatus.id'],
                                    ondelete='CASCADE', deferrable=True, initially='DEFERRED'),


class _Subscriber(Model):
    __tablename__ = 'subscriber'

    id = Column(UnicodeText(36), nullable=False, default=uuid4, primary_key=True)
    tid = Column(Integer, primary_key=True)
    subdomain = Column(UnicodeText, unique=True, nullable=False)
    language = Column(UnicodeText(12), nullable=False)
    user_id = Column(UnicodeText, default='', nullable=False)
    name = Column(UnicodeText, nullable=False)
    surname = Column(UnicodeText, nullable=False)
    phone = Column(UnicodeText, default='', nullable=False)
    email = Column(UnicodeText, nullable=False)
    tax_code = Column(UnicodeText, nullable=True)
    organization_name = Column(UnicodeText, default='', nullable=False, unique=True)
    organization_tax_code = Column(UnicodeText, unique=True, nullable=True)
    organization_vat_code = Column(UnicodeText, unique=True, nullable=True)
    organization_location = Column(UnicodeText, default='', nullable=False)
    activation_token = Column(UnicodeText, unique=True)
    client_ip_address = Column(UnicodeText, nullable=False)
    client_user_agent = Column(UnicodeText, nullable=False)
    registration_date = Column(DateTime, default=datetime_now, nullable=False)
    tos1 = Column(UnicodeText, default='', nullable=False)
    tos2 = Column(UnicodeText, default='', nullable=False)
    creation_date = Column(DateTime, default=datetime_now, nullable=False)
    state = Column(Integer, default=None, nullable=True)
    organization_email = Column(UnicodeText, nullable=True)
    organization_institutional_site = Column(UnicodeText, default='', nullable=False)
    accreditation_date = Column(DateTime, nullable=True)
    recipient_user_id = Column(UnicodeText, default='', nullable=False)
    recipient_name = Column(UnicodeText, nullable=True)
    recipient_surname = Column(UnicodeText, nullable=True)
    recipient_email = Column(UnicodeText, nullable=True)
    recipient_tax_code = Column(UnicodeText, nullable=True)
    requestor_id = Column(UnicodeText, nullable=True)

    unicode_keys = ['subdomain', 'language', 'name', 'surname', 'phone', 'email', 'tax_code',
                    'organization_name', 'organization_tax_code',
                    'organization_vat_code', 'organization_location',
                    'client_ip_address', 'client_user_agent', 'state', 'organization_email',
                    'organization_institutional_site', 'recipient_name', 'recipient_surname', 'recipient_email',
                    'recipient_tax_code', 'requestor_id']

    bool_keys = ['tos1', 'tos2']

    optional_references = ['activation_token']

    @declared_attr
    def __table_args__(self):
        return ForeignKeyConstraint(['tid'], ['tenant.id'], ondelete='CASCADE', deferrable=True, initially='DEFERRED'),


class _Tenant(Model):
    """
    Class used to implement tenants
    """
    __tablename__ = 'tenant'
    __table_args__ = {'sqlite_autoincrement': True}

    id = Column(Integer, primary_key=True)
    creation_date = Column(DateTime, default=datetime_now, nullable=False)
    active = Column(Boolean, default=False, nullable=False)
    affiliated = Column(Boolean, nullable=True)
    external = Column(Boolean, default=False, nullable=False)

    bool_keys = ['active']


class _InternalTipForwarding(Model):
    """
        This model keeps track of forward tip.
        """
    __tablename__ = 'internaltip_forwarding'
    id = Column(UnicodeText(36), primary_key=True, default=uuid4)
    internaltip_id = Column(UnicodeText(36), nullable=False, index=True)
    forwarding_internaltip_id = Column(UnicodeText(36), nullable=False, index=True)
    tid = Column(Integer, default=1, nullable=False)
    creation_date = Column(DateTime, default=datetime_now, nullable=False)
    update_date = Column(DateTime, default=datetime_now, nullable=False)
    data = Column(UnicodeText, default='{}', nullable=False)
    questionnaire_id = Column(UnicodeText(36), nullable=False, index=True)
    state = Column(Enum(EnumForwardingState), default='open', nullable=False)
    stat_data = Column(UnicodeText, default='{}', nullable=False)
    questionnaire_hash = Column(UnicodeText(64), nullable=True)

    @declared_attr
    def __table_args__(self):
        return (
            ForeignKeyConstraint(
                ['internaltip_id'],
                ['internaltip.id'],
                ondelete='CASCADE',
                deferrable=True,
                initially='DEFERRED'
            ),
            ForeignKeyConstraint(
                ['forwarding_internaltip_id'],
                ['internaltip.id'],
                ondelete='CASCADE',
                deferrable=True,
                initially='DEFERRED'
            ),
            ForeignKeyConstraint(
                ['questionnaire_id'],
                ['questionnaire.id'],
                ondelete='CASCADE',
                deferrable=True,
                initially='DEFERRED'
            ),
            ForeignKeyConstraint(
                ['tid'],
                ['tenant.id'],
                ondelete='CASCADE',
                deferrable=True,
                initially='DEFERRED'
            )
        )


class _User(Model):
    """
    This model keeps track of users.
    """
    __tablename__ = 'user'

    id = Column(UnicodeText(36), primary_key=True, default=uuid4)
    tid = Column(Integer, default=1, nullable=False)
    creation_date = Column(DateTime, default=datetime_now, nullable=False)
    username = Column(UnicodeText, default='', nullable=False)
    salt = Column(UnicodeText(24), default='', nullable=False)
    hash = Column(UnicodeText(44), default='', nullable=False)
    name = Column(UnicodeText, default='', nullable=False)
    description = Column(JSON, default=dict, nullable=False)
    public_name = Column(UnicodeText, default='', nullable=False)
    role = Column(Enum(EnumUserRole), default='receiver', nullable=False)
    enabled = Column(Boolean, default=True, nullable=False)
    last_login = Column(DateTime, default=datetime_null, nullable=False)
    mail_address = Column(UnicodeText, default='', nullable=False)
    language = Column(UnicodeText(12), nullable=False)
    password_change_needed = Column(Boolean, default=True, nullable=False)
    password_change_date = Column(DateTime, default=datetime_null, nullable=False)
    crypto_prv_key = Column(UnicodeText(84), default='', nullable=False)
    crypto_pub_key = Column(UnicodeText(56), default='', nullable=False)
    crypto_rec_key = Column(UnicodeText(80), default='', nullable=False)
    crypto_bkp_key = Column(UnicodeText(84), default='', nullable=False)
    crypto_escrow_prv_key = Column(UnicodeText(84), default='', nullable=False)
    crypto_escrow_bkp1_key = Column(UnicodeText(84), default='', nullable=False)
    crypto_escrow_bkp2_key = Column(UnicodeText(84), default='', nullable=False)
    crypto_global_stat_prv_key = Column(UnicodeText(84), default='', nullable=True)
    change_email_address = Column(UnicodeText, default='', nullable=False)
    change_email_token = Column(UnicodeText, unique=True)
    change_email_date = Column(DateTime, default=datetime_null, nullable=False)
    notification = Column(Boolean, default=True, nullable=False)
    forcefully_selected = Column(Boolean, default=False, nullable=False)
    can_delete_submission = Column(Boolean, default=False, nullable=False)
    can_postpone_expiration = Column(Boolean, default=True, nullable=False)
    can_grant_access_to_reports = Column(Boolean, default=False, nullable=False)
    can_transfer_access_to_reports = Column(Boolean, default=False, nullable=False)
    can_download_infected = Column(Boolean, default=False, nullable=False)
    can_redact_information = Column(Boolean, default=False, nullable=False)
    can_mask_information = Column(Boolean, default=True, nullable=False)
    can_reopen_reports = Column(Boolean, default=True, nullable=False)
    can_edit_general_settings = Column(Boolean, default=False, nullable=False)
    readonly = Column(Boolean, default=False, nullable=False)
    two_factor_secret = Column(UnicodeText(32), default='', nullable=False)
    reminder_date = Column(DateTime, default=datetime_null, nullable=False)
    status = Column(Enum(EnumUserStatus), default='active', nullable=False)
    idp_id = Column(UnicodeText(18), default='', nullable=False)

    # BEGIN of PGP key fields
    pgp_key_fingerprint = Column(UnicodeText, default='', nullable=False)
    pgp_key_public = Column(UnicodeText, default='', nullable=False)
    pgp_key_expiration = Column(DateTime, default=datetime_null, nullable=False)
    # END of PGP key fields

    accepted_privacy_policy = Column(DateTime, default=datetime_null, nullable=False)
    clicked_recovery_key = Column(Boolean, default=False, nullable=False)

    unicode_keys = ['username', 'role',
                    'language', 'mail_address',
                    'name', 'public_name',
                    'language', 'change_email_address',
                    'salt',
                    'two_factor_secret', 'status', 'idp_id']

    localized_keys = ['description']

    bool_keys = ['enabled',
                 'password_change_needed',
                 'notification',
                 'can_delete_submission',
                 'can_postpone_expiration',
                 'can_reopen_reports',
                 'can_grant_access_to_reports',
                 'can_redact_information',
                 'can_mask_information',
                 'can_transfer_access_to_reports',
                 'can_edit_general_settings',
                 'forcefully_selected',
                 'readonly',
                 'can_download_infected',
                 'clicked_recovery_key']

    date_keys = ['accepted_privacy_policy',
                 'creation_date',
                 'reminder_date',
                 'last_login',
                 'password_change_date',
                 'pgp_key_expiration']

    @declared_attr
    def __table_args__(self):
        return (ForeignKeyConstraint(['tid'], ['tenant.id'], ondelete='CASCADE', deferrable=True, initially='DEFERRED'),
                UniqueConstraint('tid', 'username'),
                CheckConstraint(self.role.in_(EnumUserRole.keys())))


class _ReceiverFile(Model):
    """
    This models stores metadata of files uploaded by recipients intended to bes
    delivered to the whistleblower. This file is not encrypted and nor is it
    integrity checked in any meaningful way.
    """
    __tablename__ = 'receiverfile'

    id = Column(UnicodeText(36), primary_key=True, default=uuid4)
    internaltip_id = Column(UnicodeText(36), nullable=False, index=True)
    author_id = Column(UnicodeText(36))
    name = Column(UnicodeText, nullable=False)
    size = Column(Integer, nullable=False)
    content_type = Column(UnicodeText, nullable=False)
    creation_date = Column(DateTime, default=datetime_now, nullable=False)
    verification_date = Column(DateTime, nullable=True)
    access_date = Column(DateTime, default=datetime_null, nullable=False)
    description = Column(UnicodeText, default="", nullable=False)
    visibility = Column(Enum(EnumVisibility), default='public', nullable=False)
    state = Column(Enum(EnumStateFile), default='pending', nullable=False)
    new = Column(Boolean, default=True, nullable=False)

    @declared_attr
    def __table_args__(self):
        return (ForeignKeyConstraint(['internaltip_id'], ['internaltip.id'], ondelete='CASCADE', deferrable=True,
                                     initially='DEFERRED'),
                CheckConstraint(self.visibility.in_(EnumVisibility.keys())))


class ArchivedSchema(_ArchivedSchema, Base):
    pass


class AuditLog(_AuditLog, Base):
    pass


class Comment(_Comment, Base):
    pass


class Config(_Config, Base):
    pass


class ConfigL10N(_ConfigL10N, Base):
    pass


class Context(_Context, Base):
    pass


class CustomTexts(_CustomTexts, Base):
    pass


class EnabledLanguage(_EnabledLanguage, Base):
    pass


class Field(_Field, Base):
    pass


class FieldAttr(_FieldAttr, Base):
    pass


class FieldOption(_FieldOption, Base):
    pass


class FieldOptionTriggerField(_FieldOptionTriggerField, Base):
    pass


class FieldOptionTriggerStep(_FieldOptionTriggerStep, Base):
    pass


class File(_File, Base):
    pass


class IdentityAccessRequest(_IdentityAccessRequest, Base):
    pass


class IdentityAccessRequestCustodian(_IdentityAccessRequestCustodian, Base):
    pass


class InternalFile(_InternalFile, Base):
    pass


class InternalTip(_InternalTip, Base):
    pass


class InternalTipAnswers(_InternalTipAnswers, Base):
    pass


class InternalTipData(_InternalTipData, Base):
    pass


class Mail(_Mail, Base):
    pass


class Questionnaire(_Questionnaire, Base):
    pass


class ReceiverContext(_ReceiverContext, Base):
    pass


class ReceiverFile(_ReceiverFile, Base):
    pass


class ReceiverTip(_ReceiverTip, Base):
    pass


class Redaction(_Redaction, Base):
    pass


class Redirect(_Redirect, Base):
    pass


class Subscriber(_Subscriber, Base):
    pass


class SubmissionStatus(_SubmissionStatus, Base):
    pass


class SubmissionSubStatus(_SubmissionSubStatus, Base):
    pass


class Step(_Step, Base):
    pass


class Tenant(_Tenant, Base):
    pass


class User(_User, Base):
    pass


class WhistleblowerFile(_WhistleblowerFile, Base):
    pass


class InternalTipForwarding(_InternalTipForwarding, Base):
    pass


class ContentForwarding(_ContentForwarding, Base):
    pass
