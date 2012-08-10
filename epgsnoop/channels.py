# By hads <hads@nice.net.nz>
# Released under the MIT license

import os
import sys

from cgi import escape

from base import *

log = logging.getLogger(NAME)

def get_channels(channel_file):
    channels = {}
    channel_file_ok = False
    channel_info = []
    f = open(channel_file)
    for line in f:
        channel_info.append(line.strip())
    f.close()
    for line in channel_info:
        if line == '# CHANNEL_ID|XMLTVID|NAME|ICON|WEBSITE|CHANNEL_NUMBER':
            channel_file_ok = True
    if not channel_file_ok:
        log.critical("Channel file '%s' appears to be out of date.", channel_file)
        return False

    for chan in channel_info:
        chan = chan.strip()
        if chan and chan[0] != '#':
            fields = chan.split('|')
            channel = Channel(fields[0])
            try:
                channel.xmltvid = fields[1]
            except IndexError:
                pass
            try:
                channel.name = escape(fields[2], quote=True)
            except IndexError:
                pass
            try:
                channel.icon = escape(fields[3], quote=True)
            except IndexError:
                pass
            try:
                channel.url = escape(fields[4], quote=True)
            except IndexError:
                pass
            channels[fields[0]] = channel
    return channels

