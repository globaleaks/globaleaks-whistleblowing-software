# -*- coding: utf-8
import datetime
import json

try:
    from sqlalchemy.engine import row
except:
    row = None

from globaleaks.utils.utility import datetime_to_ISO8601


class JSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if row and isinstance(obj, row.Row):
            return dict(obj)
        elif isinstance(obj, bytes):
            return obj.decode()
        elif isinstance(obj, datetime.datetime):
            return datetime_to_ISO8601(obj)
        else:
            return super().default(obj)
