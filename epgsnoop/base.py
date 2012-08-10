# By hads <hads@nice.net.nz>
# Released under the MIT license

# Timezone classes taken and modified from
# http://docs.python.org/lib/datetime-tzinfo.html

import os
import sys
import time
import logging
import re

from datetime import tzinfo, datetime, timedelta

NAME = 'epgsnoop'
VERSION = '0.84'
URL = 'http://launchpad.net/epgsnoop'

log = logging.getLogger(NAME)
logging.basicConfig(level=logging.INFO, format='%(message)s')

class StatusDisplay(object):
    def __init__(self):
        self.length = 0

    def out(self, text):
        i = 0
        pre = ''
        while i < self.length:
            pre = pre + '\b'
            i = i + 1
        self.length = len(text)
        sys.stderr.write(pre + text)

class Channel(object):
    xmltvid = None
    name = None
    icon = None
    url = None
    
    def __init__(self, pid):
        self.pid = pid

class Program(dict):
    def __str__(self):
        if 'title' in self and self['title']:
            return 'Program: %s' % self['title']
        else:
            return 'Program instance'

    def __repr__(self):
        if 'title' in self:
            return 'Program: %s' % self['title']
        else:
            return 'Program instance'

    def __setitem__(self, name, value):
        if name in ('start', 'duration') and not (isinstance(value, datetime) or isinstance(value, timedelta)):
            # Convert the raw value to datetime or timedelta
            try:
                value = self.mjdToDate(value)
            except Exception, e:
                log.debug('\nError converting %s value: %s', name, e)
                return
            else:
                if name == 'duration' and 'start' in self:
                    # If we have a start and we just got duration
                    # calculate the end time
                    self['end'] = self['start'] + value
                if name == 'start' and 'duration' in self:
                    # If we have a duration and we just got start
                    # calculate the end time
                    self['end'] = value + self['duration']
            
        dict.__setitem__(self, name, value)

    def isValid(self):
        if 'title' in self and self['title'] and 'start' in self and 'end' in self and 'channel' in self:
            return True
        else:
            return False

    # Convert DVB dates, ETSI EN 300 468 (DVB SI), Annex C
    def mjdToDate(self, dvb):
        # bcd hour/min/sec
        hour = int(dvb[-6:-4])
        minute = int(dvb[-4:-2])
        second = int(dvb[-2:])

        # Date or duration
        mjd = int(dvb[:-6], 16)
        if mjd == 0:
            return timedelta(hours=hour, minutes=minute, seconds=second)

        # Intermediate calcs
        y = int((mjd - 15078.2) / 365.25)
        m = int((mjd - 14956.1 - int(y * 365.25)) / 30.6001)
        if m == 14 or m == 15:
            k = 1
        else:
            k = 0

        # Date
        m_year = y + k + 1900
        m_month = m - 1 - k * 12
        m_day = mjd - 14956 - int(y * 365.25) - int(m * 30.6001)

        return datetime(m_year, m_month, m_day, hour, minute, second, tzinfo=utc)

class UTC(tzinfo):
    """
    Represents the UTC timezone
    """

    def utcoffset(self, dt):
        return timedelta(0)

    def tzname(self, dt):
        return "UTC"

    def dst(self, dt):
        return timedelta(0)

class LocalTimezone(tzinfo):
    """
    Represents the computers local timezone
    """

    def __init__(self):
        self.STDOFFSET = timedelta(seconds = -time.timezone)
        if time.daylight:
            self.DSTOFFSET = timedelta(seconds = -time.altzone)
        else:
            self.DSTOFFSET = self.STDOFFSET

        self.DSTDIFF = self.DSTOFFSET - self.STDOFFSET
        tzinfo.__init__(self)

    def utcoffset(self, dt):
        if self._isdst(dt):
            return self.DSTOFFSET
        else:
            return self.STDOFFSET

    def dst(self, dt):
        if self._isdst(dt):
            return self.DSTDIFF
        else:
            return timedelta(0)

    def tzname(self, dt):
        return time.tzname[self._isdst(dt)]

    def _isdst(self, dt):
        tt = (dt.year, dt.month, dt.day, dt.hour, dt.minute, dt.second, dt.weekday(), 0, -1)
        stamp = time.mktime(tt)
        tt = time.localtime(stamp)
        return tt.tm_isdst > 0

local = LocalTimezone()
utc = UTC()
