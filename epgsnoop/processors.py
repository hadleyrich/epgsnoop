# By hads <hads@nice.net.nz>
# Released under the MIT license

import os
import re
import copy
import logging
import ConfigParser
from urllib import urlopen

from base import *

log = logging.getLogger(NAME)

class BaseProcessor(object):
    valid = True

    def __init__(self, config):
        self.config = config

    def __call__(self, programs):
        self.programs = programs
        if self.valid:
            log.info('Processing programs with %s processor' % self.__class__.__name__)
            for program in self.programs:
                if program.isValid():
                    self.process(program)
                else:
                    if 'title' in program:
                        log.debug(
                            'Ignoring invalid program (PID:%s) (Title:%s)', program['pid'], program['title']
                        )
                        if 'start' not in program:
                            log.debug('No start')
                        if 'end' not in program:
                            log.debug('No end')
                        if 'channel' not in program:
                            log.debug('No channel')
                    else:
                        log.debug('Ignoring invalid program (no title)')
            self.postProcess()
        return self.programs

    def process(self, program):
        raise NotImplementedError

    def postProcess(self):
        pass

class StripHtml(BaseProcessor):
    def process(self, program):
        program['title'] = re.sub('<.*?>', '', program['title'])

class HD(BaseProcessor):
    regex = re.compile(r'HD$')
    
    def process(self, program):
        matched = self.regex.search(program['description'])
        if matched:
            log.debug("Found HD program: '%s'", program['title'])
            program['video'] = True
            program['hd'] = True
            # I imagine all HD programs will be widescreen
            program['aspect'] = '16:9'
            program['description'] = self.regex.sub('', program['description'])

class Widescreen(BaseProcessor):
    regex = re.compile(r' \(WS\)')
    
    def process(self, program):
        matched = self.regex.search(program['description'])
        if matched:
            log.debug("Found widescreen program: '%s'", program['title'])
            program['video'] = True
            program['aspect'] = '16:9'
            program['description'] = self.regex.sub('', program['description'])

class Credits(BaseProcessor):
    actor_regex = re.compile(r'\. Starring: (.*?)\.')
    director_regex = re.compile(r"Directed by (([A-Za-z'\-]+(\s|.))+)")
    
    def process(self, program):
        matched = self.actor_regex.search(program['description'])
        if matched:
            log.debug("Found actor in program: '%s'", program['title'])
            program['actors'] = matched.group(1).split(', ')
            #program['description'] = self.regex.sub('', program['description'])
        matched = self.director_regex.search(program['description'])
        if matched:
            log.debug("Found director in program: '%s'", program['title'])
            program['director'] = matched.group(1).strip(' .')
            #program['description'] = self.regex.sub('', program['description'])

class Year(BaseProcessor):
    regex = re.compile(r' \((\d{4})\)\.$')
    
    def process(self, program):
        matched = self.regex.search(program['description'])
        if matched:
            log.debug("Found year %s for program: '%s'", matched.groups()[0], program['title'])
            program['year'] = matched.groups(1)[0]
            #program['description'] = self.regex.sub('', program['description'])

class MovieTitle(BaseProcessor):
    regex = re.compile(
        r'''(
            Movie|
            Saturday\sBlockbuster|
            Blockbuster\sTuesday|
            Sunday\sPremiere\sMovie|
            Sunday\sBlockbuster\sPremiere|
            Sunday\sPremier\sMovie|
            Mid-Week\sMovi?e|
            The\sSol\sSunday\sNight\sMovie|
            Saturday\sComedy\sBlockbuster
            ):\s?''',
        re.VERBOSE
    )
    
    def process(self, program):
        matched = self.regex.match(program['title'])
        if matched:
            log.debug("Found movie from title: '%s'", program['title'])
            program['category_type'] = 'movie'
            program['title'] = self.regex.sub('', program['title'])

class Subtitle(BaseProcessor):
    regexes = (
        re.compile(r"(Today|Tonight)?:? ?'(?P<subtitle>.*?)'\.\s?"),
        re.compile(r"'(?P<subtitle>.{2,60}?)'\s"),
        re.compile(r"(?P<subtitle>.{2,60}?):\s"),
    )

    def process(self, program):
        if 'description' in program:
            for regex in self.regexes:
                matched = regex.match(program['description'])
                if matched:
                    program['category_type'] = 'series'
                    log.debug('Found subtitle in %s', program['description'])
                    program['subtitle'] = matched.group('subtitle')
                    program['description'] = regex.sub('', program['description'])

class MovieDesc(BaseProcessor):
    regex = re.compile(
        r'''(
            Action|
            Adventure|
            Animated|
            Comedy|
            Crime|
            Documentary|
            Drama|
            Family|
            Horror|
            Magazine|
            Musical|
            Romantic\sComedy|
            Rom\sCom|
            Thriller|
            Biography/Drama
        )(?:, (\d{4}))?:\s?''',
        re.VERBOSE
    )
    
    def process(self, program):
        if 'description' in program:
            matched = self.regex.match(program['description'])
            if matched:
                log.debug("Found movie from description in '%s'", program['title'])
                program['category_name'] = matched.groups()[0]
                if matched.groups()[1]:
                    program['year'] = matched.groups()[1]
                program['category_type'] = 'movie'
                program['description'] = self.regex.sub('', program['description'])

class CategoryList(BaseProcessor):
    CATEGORY_TYPES = {
        '0': 'tvshow',
        '1': 'movie',
        '2': 'tvshow',
        '3': 'tvshow',
        '4': 'sports',
        '5': 'tvshow',
        '6': 'tvshow',
        '7': 'tvshow',
        '8': 'tvshow',
        '9': 'tvshow',
        '10': 'tvshow',
        '11': 'tvshow',
        '15': 'tvshow',
    }
    CATEGORIES = {
        # Special
        #'0-0': '',
        #'0-11': '',

        # Movies
        '1-0': 'Drama',
        '1-1': 'Thriller/Crime',
        '1-2': 'Action/Adventure',
        '1-3': 'Thriller/Crime',
        '1-4': 'Comedy',
        '1-5': 'Drama',
        '1-6': 'Family/Romance',
        '1-7': 'Classical/Religious/Historical',
        '1-8': 'Adult',
        '1-9': 'Religious',
        '1-10': 'Thriller',
        '1-12': 'News/Magazine',
        '1-13': 'War',
        '1-14': 'Western',
        '1-15': 'Making of',

        # News/Documentary
        '2-0': 'News/Current Affairs',
        '2-1': 'News',
        '2-2': 'Magazine',
        '2-3': 'Documentary',
        '2-4': 'Discussion/Interview',
        '2-15': 'Sports',

        # General shows
        '3-0': 'General Show',
        '3-1': 'Game Show/Quiz/Contest',
        '3-2': 'Variety Show',
        '3-3': 'Talk Show',
        '3-4': 'Reality',
        '3-5': 'Reality/Stunt',
        '3-6': 'Drama',
        '3-7': 'Reality',
        '3-8': 'Reality',
        '3-10': 'Science Fiction',
        '3-11': 'Crime',
        '3-12': 'Sports - Wrestling/Fighting',
        '3-13': 'Special Event',
        '3-14': 'Adult',

        # Sports
        '4-0': 'Sports',
        '4-1': 'Sports - Special Event',
        '4-2': 'Sports - Golf', # Magazine?
        '4-3': 'Sports - Soccer',
        '4-4': 'Sports - Tennis/Squash',
        '4-5': 'Team Sports',
        '4-6': 'Sports - Athletics',
        '4-7': 'Motor Sports',
        '4-8': 'Water Sports',
        '4-9': 'Winter Sports',
        '4-10': 'Sports - Equestrian',
        '4-11': 'Sports - Martial Arts',
        '4-13': 'Sports - Cricket',
        '4-14': 'Sports - Cycling',
        '4-15': 'Sports Talk Show',

        # Childrens show
        '5-0': 'Childrens - General',
        '5-1': 'Childrens - Pre-school',
        '5-2': 'Childrens - Ages 6-14',
        '5-3': 'Childrens - Ages 10-16',
        '5-4': 'Childrens - Educational/Informational',
        '5-5': 'Childrens - Cartoon/Puppets',

        # Music
        '6-0': 'Music - General',
        '6-1': 'Music - Rock/Pop',
        '6-2': 'Music - Classical/Opera',
        '6-3': 'Music - Folk/Traditional',
        '6-4': 'Music - Jazz',
        '6-5': 'Music - Musical/Opera',
        '6-6': 'Music - Ballet',
        '6-7': 'Music - Religious',
        '6-8': 'Music - Countdown',
        '6-9': 'Music - Gospel',
        '6-15': 'Music - Special',

        # Arts/Culture
        '7-0': 'Arts/Culture',
        '7-1': 'Performing Arts',
        '7-2': 'Fine Arts',
        '7-3': 'Religion',
        '7-5': 'Literature',
        '7-6': 'Film/Cinema',
        '7-10': 'Magazine',

        # Social/Political/Economics
        '8-0': 'News/Current Affairs',
        '8-1': 'Magazone/Documentary',
        '8-2': 'Social Advisory',
        '8-3': 'Documentary',
        '8-4': 'Social/Political/Economics',

        # Education/Science/Factual
        '9-0': 'Education/Science/Factual',
        '9-1': 'Nature/Animals/Environment',
        '9-2': 'Technology/Natural Science',
        '9-3': 'Medicine/Physiology/Psychology',
        '9-6': 'Further Education',
        '9-8': 'Education/Science/Factual',
        '9-9': 'Education/Science/Factual',
        '9-10': 'Education/Science/Factual',
        '9-11': 'Travel',
        '9-12': 'Education/Science/Factual',
        '9-13': 'Education/Science/Factual',
        '9-14': 'Education/Science/Factual',
        '9-15': 'Education/Science/Factual',

        # Leisure/Hobbies
        '10-0': 'Leisure/Hobbies',
        '10-1': 'Tourisim/Travel',
        '10-2': 'Craft',
        '10-3': 'Fishing/Motoring',
        '10-4': 'Fitness/Health',
        '10-5': 'Cooking',
        '10-6': 'Shopping/Advertisment',
        '10-7': 'Home/Gardening',
        '10-8': 'Leisure/Hobbies',
        '10-10': 'Reality',
        '10-11': 'Home/Design',
        '10-12': 'Property/Reality',

        # Special News/Entertainment
        '11-0': 'Special News/Entertainment',
        '11-1': 'Special News/Entertainment',
        '11-3': 'Live broadcast',
        '11-5': 'Special News/Entertainment',
        '11-6': 'International',
        '11-7': 'Special News/Entertainment',
        '11-8': 'Special News/Entertainment',
        '11-9': 'Special News/Entertainment',
        '11-10': 'Special News/Entertainment',
        '11-11': 'Special News/Entertainment',
        '11-12': 'Special News/Entertainment',
        '11-13': 'Special News/Entertainment',
        '11-14': 'Special News/Entertainment',

        # Adult
        '15-0': 'Adult',
        '15-1': 'Adult',
        '15-5': 'Adult',
        '15-8': 'Adult',
    }

    def process(self, program):
        if 'content_1' in program and 'content_2' in program:
            cat_num = '%s-%s' % (program['content_1'], program['content_2'])
            try:
                program['category_type'] = self.CATEGORY_TYPES[program['content_1']]
            except KeyError:
                pass
            try:
                program['category_name'] = self.CATEGORIES[cat_num]
            except KeyError:
                pass

class CategoryDb(BaseProcessor):
    def __init__(self, config):
        BaseProcessor.__init__(self, config)
        try:
            try:
                # Try sqlite from the standard library (> 2.5)
                from sqlite3 import dbapi2 as sqlite
            except ImportError:
                # Try sqlite from the external package (< 2.4)
                from pysqlite2 import dbapi2 as sqlite
        except ImportError:
            self.valid = False
            log.info('Not using CategoryDb processor - sqlite not found.')
        else:
            try:
                database = os.path.expanduser(config.get('CategoryDb', 'database'))
            except (ConfigParser.NoSectionError, ConfigParser.NoOptionError):
                self.valid = False
                log.info('Not using CategoryDb processor - no config found.')
            else:
                self.db = sqlite.connect(database)
                self.c = self.db.cursor()
                self.c.execute("""CREATE TABLE IF NOT EXISTS categories(
                    id INTEGER PRIMARY KEY,
                    title VARCHAR,
                    cat_type VARCHAR,
                    cat VARCHAR
                    )"""
                )
    
    def process(self, program):
        self.c.execute(
            "SELECT cat_type, cat FROM categories WHERE title LIKE ?",
            (program['title'],)
        )
        row = self.c.fetchone()
        if row:
            try:
                (program['category_type'], program['category_name']) = row
                log.debug('Set category %s for %s', program['category_name'], program['title'])
            except Exception, e:
                log.debug('Exception getting category from DB: %s', e)

class SkyRatings(BaseProcessor):
    RATING_SYSTEM = 'SKY-NZ'
    RATINGS = {
        #'1': '?' # Freeview?
        '2': 'G', # Some G
        '4': 'PG', # Some PG
        '6': 'M',
        '8': 'R16',
        '10': '18+',
        '12': 'R18',
        '13': 'R20',
    }
    RATING_ADVISORIES = {
        '1': 'V',
        '2': 'S',
        '3': 'VS',
        '4': 'L',
        '5': 'VL',
        '6': 'LS',
        '7': 'VLS', # Seems to be V in SKY
        '8': 'C',
        #'9': '?', # Unknown
        #'10': '?', # Unknown
        #'13': '?', # Unknown
        #'14': '?', # Unknown
    }
    def process(self, program):
        program['rating_system'] = self.RATING_SYSTEM
        if 'ratingnum' in program:
            try:
                program['rating'] = self.RATINGS[program['ratingnum']]
            except:
                pass
        if 'user_2' in program and program['user_2'] != '0':
            try:
                program['rating_advisory'] = self.RATING_ADVISORIES[program['user_2']]
            except:
                pass

class SearchReplaceTitle(BaseProcessor):
    def __init__(self, config):
        BaseProcessor.__init__(self, config)
        try:
            import simplejson
        except ImportError:
            self.valid = False
            log.info('Not using SearchReplaceTitle processor - simplejson not found.')
        else:
            try:
                data = urlopen(config.get('SearchReplaceTitle', 'url')).read()
            except IOError:
                self.valid = False
                log.info('Not using SearchReplaceTitle - fetching data failed.')
            else:
                try:
                    self.replacements = simplejson.loads(data)
                except ValueError:
                    self.valid = False
                    log.info('Not using SearchReplaceTitle - JSON parse failed.')

    def process(self, program):
        for r in self.replacements:
            old_title = program['title']
            program['title'] = re.sub(r['search'], r['replace'], program['title'])
            if old_title != program['title']:
                log.debug('SearchReplaceTitle: Changed title from "%s" to "%s"', program['title'], r['replace'])

class BBCWorldOnTV1(BaseProcessor):
    programs_to_delete = []
    programs_to_insert = []

    def process(self, program):
        if program['channel'].xmltvid == 'tv1.sky.co.nz' and re.match(r'BBC World( \d{4})?', program['title']):
            for op in self.programs:
                if op.isValid() and op['channel'].xmltvid == 'bbc-world.sky.co.nz'\
                and op['start'] > program['start'] and op['end'] < program['end']:
                    np = copy.deepcopy(op)
                    np['channel'] = program['channel']
                    self.programs_to_insert.append(np)
            self.programs_to_delete.append(program)

    def postProcess(self):
        for program in self.programs_to_delete:
            log.debug('Removing program %s', program)
            self.programs.remove(program)
        for program in self.programs_to_insert:
            log.debug('Inserting program %s', program)
            self.programs.append(program)

