# pylint: disable=unused-import
import json

from sqlalchemy import Column, CheckConstraint, ForeignKeyConstraint, UniqueConstraint, types
from sqlalchemy.schema import ForeignKey
from sqlalchemy.types import Boolean, DateTime, Integer, LargeBinary, UnicodeText

try:
    from sqlalchemy.orm import declarative_base, declared_attr
except ImportError:
    from sqlalchemy.ext.declarative import declarative_base, declared_attr

from globaleaks.utils.utility import uuid4
# pylint: enable=unused-import


class JSON(types.TypeDecorator):
    """Stores and retrieves JSON as TEXT."""
    cache_ok = True
    impl = types.UnicodeText

    def process_bind_param(self, value, dialect):
        if value is not None:
            return json.dumps(value)

        return value

    def process_result_value(self, value, dialect):
        if value is not None:
            return json.loads(value)

        return value


class Enum(types.TypeDecorator):
    """Stores and retrieves ENUM as INTEGER."""
    cache_ok = True
    impl = types.Integer

    def __init__(self, enumtype, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._enumtype = enumtype

    def process_bind_param(self, value, dialect):
        if isinstance(value, str):
            return getattr(self._enumtype, value).value

        return value

    def process_result_value(self, value, dialect):
        return self._enumtype(value).name
