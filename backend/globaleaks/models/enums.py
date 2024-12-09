# -*- coding: utf-8 -*-
import enum


class _Enum(enum.Enum):
    @classmethod
    def keys(cls):
        return [e.name for e in cls]


class EnumUserRole(_Enum):
    admin = 0
    receiver = 1
    custodian = 2
    analyst = 3
    accreditor = 4


class EnumUserStatus(_Enum):
    active = 0
    suspend = 1


class EnumFieldInstance(_Enum):
    instance = 0
    template = 1
    reference = 2


class EnumFieldAttrType(_Enum):
    int = 0
    bool = 1
    unicode = 2
    localized = 3


class EnumFieldOptionScoreType(_Enum):
    none = 0
    addition = 1
    multiplier = 2


class EnumVisibility(_Enum):
    public = 0
    internal = 1
    personal = 2
    eo = 3
    whistleblower = 4


class EnumStateFile(_Enum):
    pending = 0
    verified = 1
    infected = 2


class EnumSubscriberStatus(_Enum):
    requested = 0
    accredited = 1
    rejected = 2
    instructor_request = 3
    invited = 4
    suspended = 5
    approved = 6

class EnumContentForwarding(_Enum):
    internal_file = 0
    receiver_file = 1
    comment = 2

class EnumForwardingState(_Enum):
    open = 0
    closed = 1
    
class EnumAuthorType(_Enum):
    main = 0
    eo = 1
