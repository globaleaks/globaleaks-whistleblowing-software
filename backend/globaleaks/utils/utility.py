# -*- coding: utf-8
#   utility
#   *******
#
# Utility Functions
import re
import uuid

from datetime import datetime, timedelta

from twisted.internet import reactor
from twisted.internet.defer import Deferred


def get_distribution_codename():
    try:
        with open("/etc/os-release", "r") as fd:
            for line in fd:
                key, value = line.split("=")
                if key == "VERSION_CODENAME":
                    return value.strip().strip("\"")
    except:
        pass

    return ""


def uuid4():
    """
    This function returns a uuid4.
    """
    return str(uuid.uuid4())


def deferred_sleep(timeout):
    d = Deferred()

    reactor.callLater(timeout, d.callback, True)

    return d


def msdos_encode(s):
    """
    This functions returns a new string with all occurrences of newlines
    prepended with a carriage return.
    """
    return re.sub(r'(\r\n)|(\n)', '\r\n', s)


def iso_strf_time(d):
    return d.strftime("%Y-%m-%d %H:%M:%S.%f")


def datetime_null():
    """
    :return: a utc datetime object representing a null date
    """
    return datetime(1970, 1, 1, 0, 0)

def datetime_now():
    """
    :return: a utc datetime object representing a null date
    """
    return datetime.utcnow()


def datetime_never():
    """
    :return: a utc datetime object representing the 1st January 3000
    """
    return datetime(3000, 1, 1, 0, 0)


def get_expiration(days):
    """
    :return: a utc datetime object representing an expiration time calculated as the current date + N days
    """
    date = datetime.utcnow()
    return datetime(year=date.year, month=date.month, day=date.day, hour=23, minute=59, second=59) + timedelta(days)


def is_expired(check_date, seconds=0, minutes=0, hours=0, days=0):
    """
    """
    total_hours = (days * 24) + hours
    check = check_date + timedelta(seconds=seconds, minutes=minutes, hours=total_hours)

    return datetime_now() > check


def datetime_to_ISO8601(date):
    """
    Convert a datetime into ISO8601 date
    """
    if date is None:
        date = datetime_null()

    return date.isoformat() + "Z"  # Z means that the date is in UTC

def iso8601_to_datetime(string_date):
    """
    Convert a ISO8601 string into datetime date
    """
    if string_date is None:
        return datetime_null()

    return datetime.fromisoformat(string_date)


def datetime_to_pretty_str(date):
    """
    Print a datetime in pretty formatted str format
    """
    return date.strftime("%A %d %B %Y %H:%M (UTC)")


def datetime_to_day_str(date, tz=0):
    """
    Print a datetime in DD/MM/YYYY formatted str
    """
    if tz != 0:
        tz_i, tz_d = divmod(tz, 1)
        tz_d, _ = divmod(tz_d * 100, 1)
        date += timedelta(hours=tz_i, minutes=tz_d)

    return date.strftime("%d/%m/%Y")


def ISO8601_to_pretty_str(isodate, tz=0):
    """
    convert a ISO8601 in pretty formatted str format
    """
    if isodate is None:
        isodate = datetime_null().isoformat()

    date = datetime(year=int(isodate[0:4]),
                    month=int(isodate[5:7]),
                    day=int(isodate[8:10]),
                    hour=int(isodate[11:13]),
                    minute=int(isodate[14:16]),
                    second=int(isodate[17:19]))

    if tz != 0:
        tz_i, tz_d = divmod(tz, 1)
        tz_d, _ = divmod(tz_d * 100, 1)
        date += timedelta(hours=tz_i, minutes=tz_d)
        return date.strftime("%A %d %B %Y %H:%M")

    return datetime_to_pretty_str(date)


def ISO8601_to_day_str(isodate, tz=0):
    """
    convert a ISO8601 in DD/MM/YYYY formatted str
    """
    if isodate is None:
        isodate = datetime_null().isoformat()

    date = datetime(year=int(isodate[0:4]),
                    month=int(isodate[5:7]),
                    day=int(isodate[8:10]),
                    hour=int(isodate[11:13]),
                    minute=int(isodate[14:16]),
                    second=int(isodate[17:19]))

    return datetime_to_day_str(date, tz)

def iso_year_start(iso_year):
    """Returns the gregorian calendar date of the first day of the given ISO year"""
    fourth_jan = datetime.strptime('{0}-01-04'.format(iso_year), '%Y-%m-%d')
    delta = timedelta(fourth_jan.isoweekday() - 1)
    return fourth_jan - delta


def iso_to_gregorian(iso_year, iso_week, iso_day):
    """Returns gregorian calendar date for the given ISO year, week and day"""
    year_start = iso_year_start(iso_year)
    return year_start + timedelta(days=iso_day - 1, weeks=iso_week - 1)


def bytes_to_pretty_str(b):
    if isinstance(b, str):
        b = int(b)

    if b >= 1000000000:
        return "%dGB" % int(b / 1000000000)

    if b >= 1000000:
        return "%dMB" % int(b / 1000000)

    return "%dKB" % int(b / 1000)
