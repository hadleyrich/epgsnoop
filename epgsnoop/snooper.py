# By hads <hads@nice.net.nz>
# Released under the MIT license

import os
import sys
import subprocess
import signal
import re

from base import *

class Snooper(object):
    # regex's for packet data extraction
    decode_regex = re.compile(r'\[= (.*?)\]$')
    detail_regex = re.compile(r'[char|name]: "(.*?)"  -- Charset')
    
    programs = []
    unique = {}

    # Maximum number of packets with no data before we stop
    nilpkts = 2500
    
    # Key counters
    events = 0
    packets = 0

    def __init__(self, adapter, quiet=False):
        self.quiet = quiet
        self.adapter = adapter

    def processPacket(self, pkt):
        found = 0

        # Process the packet
        self.packets += 1
        event_id = None
        for data in pkt:
            # Channel ID for this packet
            if data[:10] == "Service_ID":
                channel = data.split(': ')[1:][0].split()[0]

            # Are we in en event
            if data[:8] == "Event_ID":
                # Store old event and create a new one
                if event_id:
                    key = channel + "|" + event_id
                    if not self.unique.has_key(key):
                        found += 1
                        self.unique[key] = True
                        self.programs.append(event)
                event_id = data.split(': ')[1:][0].split()[0]
                event = Program()
                event['pid'] = channel
                self.events += 1
                continue

            # End of packet store last event
            if data[:3] == "CRC":
                if event_id:
                    key = channel + "|" + event_id
                    if not self.unique.has_key(key):
                        found += 1
                        self.unique[key] = True
                        self.programs.append(event)

            # Check for event data
            if event_id:
                # Starttime
                if data[:11] == "Start_time:":
                    event['start'] = ' '.join(data.split(': ')[1:]).split()[0]
                    event['startinfo'] = self.decode_regex.findall(data)[0].strip()
                    continue
                # Duration
                if data[:9] == "Duration:":
                    event['duration'] = ' '.join(data.split(': ')[1:]).split()[0]
                    event['durationinfo'] = self.decode_regex.findall(data)[0].strip()
                    continue
                # Name
                if data[:11] == "event_name:":
                    try:
                        event['title'] = self.detail_regex.findall(data)[0].decode('latin-1')
                    except IndexError:
                        event['title'] = ""
                    continue
                # Description
                if data[:10] == "text_char:":
                    try:
                        event['description'] = self.detail_regex.findall(data)[0].decode('latin-1')
                    except:
                        event['description'] = ""
                    continue
                # Rating
                if data[:7] == "Rating:":
                    event['ratingnum'] = ' '.join(data.split(': ')[1:]).split()[0]
                    event['ratinginfo'] = self.decode_regex.findall(data)[0].strip()
                    continue
                # Country
                if data[:13] == "Country_code:":
                    event['country'] = ' '.join(data.split(': ')[1:]).strip()
                    continue
                # Language
                if data.find("language_code:") >= 0:
                    event['language'] = ' '.join(data.split(': ')[1:]).strip()
                    continue
                # Content
                if data[:23] == "Content_nibble_level_1:":
                    event['content_1'] = ' '.join(data.split(': ')[1:]).split()[0]
                    continue
                if data[:23] == "Content_nibble_level_2:":
                    event['content_2'] = ' '.join(data.split(': ')[1:]).split()[0]
                    continue
                if data[:3] == "[= ":
                    event['contentinfo'] = self.decode_regex.findall(data)[0].strip()
                    continue
                # User
                if data[:14] == "User_nibble_1:":
                    event['user_1'] = ' '.join(data.split(': ')[1:]).split()[0]
                    continue
                if data[:14] == "User_nibble_2:":
                    event['user_2'] = ' '.join(data.split(': ')[1:]).split()[0]
                    continue
        # Found how many shows?
        return found

    def snoop(self):
        # Open stream
        command = ('dvbsnoop', '-adapter', self.adapter, '-nph', '0x12')

        self.snoop = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            close_fds=True)

        self.snoop.stderr.close()

        # Loop packets
        check = i = 0
        if not self.quiet:
            s = StatusDisplay()
            sys.stderr.write('\n')
        while check < self.nilpkts:
            i = i + 1
            if not self.quiet:
                s.out('Processing packets: %05d' % i)
        
            # Get packet start
            out = self.snoop.stdout.readline()
            while out and out[:11] != "SECT-Packet":
                out = self.snoop.stdout.readline()
        
            # Packetize
            pkt = []
            pkt.append(out.strip())
            while out and out[:3] != "CRC":
                out = self.snoop.stdout.readline()
                pkt.append(out.strip())
        
            # Process the packet
            found = self.processPacket(pkt)
            if found > 0:
                check = 0
            else:
                check += 1
        
            # Had enoungh
            if check >= self.nilpkts:
                break
        
        # Natural completion ... kill snoop
        self.kill()
        return self.programs

    def kill(self):
        os.kill(self.snoop.pid, signal.SIGTERM)

