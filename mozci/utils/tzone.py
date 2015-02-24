import datetime
import time

ZERO = datetime.timedelta(0)
HOUR = datetime.timedelta(hours=1)


class USTimeZone(datetime.tzinfo):
    # In the US, DST starts at 2am (standard time) on the first Sunday in April.
    DSTSTART = datetime.datetime(1, 4, 1, 2)
    # and ends at 2am (DST time; 1am standard time) on the last Sunday of Oct.
    # which is the first Sunday on or after Oct 25.
    DSTEND = datetime.datetime(1, 10, 25, 1)

    def __init__(self, hours, reprname, stdname, dstname):
        self.stdoffset = datetime.timedelta(hours=hours)
        self.reprname = reprname
        self.stdname = stdname
        self.dstname = dstname

    def __repr__(self):
        return self.reprname

    def tzname(self, dt):
        if self.dst(dt):
            return self.dstname
        else:
            return self.stdname

    def utcoffset(self, dt):
        return self.stdoffset + self.dst(dt)

    def dst(self, dt):
        if dt is None or dt.tzinfo is None:
            # An exception may be sensible here, in one or both cases.
            # It depends on how you want to treat them.  The default
            # fromutc() implementation (called by the default astimezone()
            # implementation) passes a datetime with dt.tzinfo is self.
            return ZERO
        assert dt.tzinfo is self

        # Find first Sunday in April & the last in October.
        start = self._first_sunday_on_or_after(USTimeZone.DSTSTART.replace(year=dt.year))
        end = self._first_sunday_on_or_after(USTimeZone.DSTEND.replace(year=dt.year))

        # Can't compare naive to aware objects, so strip the timezone from
        # dt first.
        if start <= dt.replace(tzinfo=None) < end:
            return HOUR
        else:
            return ZERO

    def _first_sunday_on_or_after(self, dt):
        days_to_go = 6 - dt.weekday()
        if days_to_go:
            dt += datetime.timedelta(days_to_go)
        return dt


class Pacific(USTimeZone):
    def __init__(self):
        USTimeZone.__init__(self, -8, "Pacific",  "PST", "PDT")


pacific_tz = Pacific()
time_format = '%a, %d %b %Y %H:%M:%S %z (%Z)'
day_format = '%Y-%m-%d'


def pacific_time(timestamp=None):
    """Convert a time expressed in seconds since the epoch to a string representing Pacific time.
    If timestamp is not provided or None, the current time as returned by time() is used.
    """
    if not timestamp:
        timestamp = time.time()
    dt = datetime.datetime.fromtimestamp(timestamp, pacific_tz)

    return dt.strftime(time_format)


def pacific_day(timestamp=None):
    """Convert a time expressed in seconds since the epoch to a string representing a Pacific date.
    If timestamp is not provided or None, the current time as returned by time() is used.
    """
    if not timestamp:
        timestamp = time.time()
    dt = datetime.datetime.fromtimestamp(timestamp, pacific_tz)

    return dt.strftime(day_format)


def utc_dt(timestamp=None):
    if not timestamp:
        return datetime.datetime.utcnow()
    else:
        return datetime.datetime.utcfromtimestamp(timestamp)


def utc_time(timestamp=None):
    """Convert a time expressed in seconds since the epoch to a string representing UTC time.
    If timestamp is not provided or None, the current time as returned by time() is used.
    """
    return utc_dt(timestamp).strftime(time_format)


def utc_day(timestamp=None):
    """Convert a time expressed in seconds since the epoch to a string representing UTC day.
    If timestamp is not provided or None, the current time as returned by time() is used.
    """
    return utc_dt(timestamp).strftime(day_format)
