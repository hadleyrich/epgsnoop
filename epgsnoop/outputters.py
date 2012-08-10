# By hads <hads@nice.net.nz>
# Released under the MIT license

import os
import logging
import ConfigParser

from datetime import datetime, timedelta
from cgi import escape

from base import *

log = logging.getLogger(NAME)

class BaseOutputter(object):
    def __init__(self, config):
        self.config = config
    
    def __call__(self, channels, programs):
        self.channels = channels
        channels_seen = []
        output = []
        
        for program in programs:
            if program.isValid() and program['channel'].pid not in channels_seen:
                channels_seen.append(program['channel'].pid)
        
        output.append(self.header())
        for channel in channels.values():
            if channel.pid in channels_seen:
                output.append(self.channel(channel))
        for program in programs:
            if program.isValid():
                output.append(self.program(program))
        output.append(self.footer())

        output = [o for o in output if o]
        return '\n'.join(output)

    def header(self):
        pass

    def footer(self):
        pass

    def channel(self, channel):
        pass
    
    def program(self, program):
        pass

class Test(BaseOutputter):
    def channel(self, channel):
        return '%s - %s' % (channel.pid, channel.xmltvid)
    
    def program(self, program):
        return '%(title)s - %(start)s (%(duration)s)' % program

class XMLTV(BaseOutputter):
    def __init__(self, config, old_channel_ids=False):
        BaseOutputter.__init__(self, config)
        self.old_channel_ids = old_channel_ids
    
    def header(self):
        gendate = datetime.now().strftime("%Y%m%d%H%M%S %z")
        return '<?xml version="1.0" encoding="ISO-8859-1"?>\n'\
            '<!DOCTYPE tv SYSTEM "xmltv.dtd">\n'\
            '<tv generator-info-name="%s/%s" generator-info-url="%s" date="%s">' % (NAME, VERSION, URL, gendate)
    
    def footer(self):
        return '</tv>\n'
    
    def channel(self, channel):
        output = []
        try:
            show_icons = self.config.getboolean('XMLTV', 'show_icons')
        except (ConfigParser.NoSectionError, ConfigParser.NoOptionError, ValueError):
            show_icons = True
        try:
            icon_url_base = self.config.get('XMLTV', 'icon_url_base')
        except (ConfigParser.NoSectionError, ConfigParser.NoOptionError):
            show_icons = False
        if self.old_channel_ids:
            output.append('<channel id="%s.dvb.guide">' % channel.pid)
        else:
            output.append('<channel id="%s">' % channel.xmltvid)
        output.append('\t<display-name>%s</display-name>' % channel.name)
        if channel.icon and show_icons:
            output.append('\t<icon src="%s%s" />' % (icon_url_base, channel.icon))
        if channel.url:
            output.append('\t<url>%s</url>' % channel.url)
        output.append('</channel>')
        return '\n'.join(output)
    
    def program(self, program):
        output = []
        start = program['start'].astimezone(local)
        end = program['end'].astimezone(local)
        
        if self.old_channel_ids:
            output.append(
                '<programme channel="%s.dvb.guide" start="%s" stop="%s">' \
                % (program['channel'].pid, start.strftime("%Y%m%d%H%M%S %z"), end.strftime("%Y%m%d%H%M%S %z"))
            )
        else:
            output.append(
                '<programme channel="%s" start="%s" stop="%s">' \
                % (program['channel'].xmltvid, start.strftime("%Y%m%d%H%M%S %z"), end.strftime("%Y%m%d%H%M%S %z"))
            )
        if 'language' in program:
            output.append('\t<title lang="%s">%s</title>' % (program['language'], escape(program['title'])))
        else:
            output.append('\t<title>%s</title>' % escape(program['title']))

        if 'subtitle' in program:
            output.append('\t<sub-title>%s</sub-title>' % escape(program['subtitle']))

        if 'description' in program and program['description']:
            output.append('\t<desc>%s</desc>' % escape(program['description']))

        if 'actors' in program or 'director' in program:
            output.append('\t<credits>')
            if 'director' in program:
                output.append('\t\t<director>%s</director>' % escape(program['director']))
            if 'actors' in program:
                for actor in program['actors']:
                    output.append('\t\t<actor>%s</actor>' % escape(actor))
            output.append('\t</credits>')

        if 'year' in program:
            output.append('\t<date>%s</date>' % program['year'])
        
        if 'category_type' in program:
            output.append('\t<category>%s</category>' % program['category_type'])

        if 'category_name' in program:
            output.append('\t<category>%s</category>' % program['category_name'])

        if 'runtime' in program:
            output.append('\t<length units="minutes">%s</length>' % program['runtime'])

        if 'imdb_id' in program:
            output.append('\t<url>http://imdb.com/title/tt%s/</url>' % program['imdb_id'])
        
        if 'series'  in program and 'episode' in program:
            output.append('\t<episode-num system="xmltv_ns">%s.%s.0/1</episode-num>' % (program['series'] - 1, program['episode'] -1))

        if 'video' in program and program['video']:
            output.append('\t<video>')
            output.append('\t\t<present>yes</present>')
            if 'aspect' in program:
                output.append('\t\t<aspect>%s</aspect>' % program['aspect'])
            if 'hd' in program:
                output.append('\t\t<quality>HDTV</quality>')
            output.append('\t</video>')

        # Rating
        if 'rating' in program:
            if 'rating_advisory' in program:
                output.append('\t<rating system="%s">\n\t\t<value>%s %s</value>\n\t</rating>' \
                        % (program['rating_system'], program['rating'], program['rating_advisory']))
            else:
                output.append('\t<rating system="%s">\n\t\t<value>%s</value>\n\t</rating>' 
                        % (program['rating_system'], program['rating']))

        if 'star_rating' in program:
            output.append('\t<star-rating>\n\t\t<value>%s/10</value>\n\t</star-rating>' % program['star_rating'])

        # Close tag
        output.append('</programme>')

        output = [o.encode('latin-1','replace') for o in output]
        return '\n'.join(output)

class OldXMLTV(XMLTV):
    def __init__(self, config):
        XMLTV.__init__(self, config, old_channel_ids=True)
