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
    oe = 3


class EnumStateFile(_Enum):
    pending = 0
    verified = 1
    infected = 2