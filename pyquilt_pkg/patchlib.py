### Copyright (C) 2011 Peter Williams <peter@users.sourceforge.net>
###
### This program is free software; you can redistribute it and/or modify
### it under the terms of the GNU General Public License as published by
### the Free Software Foundation; version 2 of the License only.
###
### This program is distributed in the hope that it will be useful,
### but WITHOUT ANY WARRANTY; without even the implied warranty of
### MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
### GNU General Public License for more details.
###
### You should have received a copy of the GNU General Public License
### along with this program; if not, write to the Free Software
### Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA

'''Classes and functions for operations on patch files'''

import collections
import re
import os

# Useful named tuples to make code clearer
_CHUNK = collections.namedtuple('_CHUNK', ['start', 'length'])
_HUNK = collections.namedtuple('_HUNK', ['offset', 'start', 'length', 'numlines'])
_PAIR = collections.namedtuple('_PAIR', ['before', 'after',])
_FILE_AND_TS = collections.namedtuple('_FILE_AND_TS', ['path', 'timestamp',])
_FILE_AND_TWS_LINES = collections.namedtuple('_FILE_AND_TWS_LINES', ['path', 'tws_lines',])
_DIFF_DATA = collections.namedtuple('_DIFF_DATA', ['file_data', 'hunks',])

# Useful strings for including in regular expressions
_PATH_RE_STR = '"([^"]+)"|(\S+)'
_TIMESTAMP_RE_STR = '\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}(\.\d{9})? [-+]{1}\d{4}'
_ALT_TIMESTAMP_RE_STR = '[A-Z][a-z]{2} [A-Z][a-z]{2} \d{2} \d{2}:\d{2}:\d{2} \d{4} [-+]{1}\d{4}'
_EITHER_TS_RE_STR = '(%s|%s)' % (_TIMESTAMP_RE_STR, _ALT_TIMESTAMP_RE_STR)

class ParseError(Exception):
    def __init__(self, message, lineno=None):
        self.message = message
        self.lineno = lineno

class TooMayStripLevels(Exception):
    def __init__(self, message, path, levels):
        self.message = message
        self.path = path
        self.levels = levels

DEBUG = False
class Bug(Exception): pass

def gen_strip_level_function(level):
    '''Return a function for stripping the specified levels off a file path'''
    def strip_n(path, level):
        try:
            return path.split(os.sep, level)[level]
        except IndexError:
            raise TooMayStripLevels('Strip level too large', path, level)
    level = int(level)
    if level == 0:
        return lambda path: path
    return lambda path: path if path.startswith(os.sep) else strip_n(path, level)

def get_common_path(filelist):
    '''Return the longest common path componet for the files in the list'''
    # Extra wrapper required because os.path.commonprefix() is string oriented
    # rather than file path oriented (which is strange)
    return os.path.dirname(os.path.commonprefix(filelist))

def _trim_trailing_ws(line):
    '''Return the given line with any trailing white space removed'''
    return re.sub('[ \t]+$', '', line)

class DiffStat(object):
    '''Class to encapsulate diffstat related code'''
    _ORDERED_KEYS = ['inserted', 'deleted', 'modified', 'unchanged']
    _FMT_DATA = {
        'inserted' : '{0} insertion{1}(+)',
        'deleted' : '{0} deletion{1}(-)',
        'modified' : '{0} modification{1}(!)',
        'unchanged' : '{0} unchanges line{1}(+)'
    }
    EMPTY_CRE = re.compile("^#? 0 files changed$")
    END_CRE = re.compile("^#? (\d+) files? changed(, (\d+) insertions?\(\+\))?(, (\d+) deletions?\(-\))?(, (\d+) modifications?\(\!\))?$")
    FSTATS_CRE = re.compile("^#? (\S+)\s*\|((binary)|(\s*(\d+)(\s+\+*-*\!*)?))$")
    BLANK_LINE_CRE = re.compile("^\s*$")
    DIVIDER_LINE_CRE = re.compile("^---$")
    @staticmethod
    def list_summary_starts_at(lines, index):
        '''Return True if lines[index] is the start of a valid "list" diffstat summary'''
        if DiffStat.DIVIDER_LINE_CRE.match(lines[index]):
            index += 1
        while index < len(lines) and DiffStat.BLANK_LINE_CRE.match(lines[index]):
            index += 1
        if index >= len(lines):
            return False
        if DiffStat.EMPTY_CRE.match(lines[index]):
            return True
        while index < len(lines) and DiffStat.FSTATS_CRE.match(lines[index]):
            index += 1
            if (index < len(lines) and DiffStat.END_CRE.match(lines[index])):
                return True
        return False
    class Stats(object):
        '''Class to hold diffstat statistics.'''
        def __init__(self):
            self._counts = {}
            for key in DiffStat._ORDERED_KEYS:
                self._counts[key] = 0
            assert len(self._counts) == len(DiffStat._ORDERED_KEYS)
        def __add__(self, other):
            result = DiffStat.Stats()
            for key in DiffStat._ORDERED_KEYS:
                result._counts[key] = self._counts[key] + other._counts[key]
            return result
        def __len__(self):
            return len(self._counts)
        def __getitem__(self, key):
            if isinstance(key, int):
                key = DiffStat._ORDERED_KEYS[key]
            return self._counts[key]
        def get_total(self):
            return sum(list(self))
        def get_total_changes(self):
            return sum([self._counts[key] for key in ['inserted', 'deleted', 'modified']])
        def incr(self, key):
            self._counts[key] += 1
            return self._counts[key]
        def as_string(self, joiner=', ', prefix=', '):
            strings = []
            for key in DiffStat._ORDERED_KEYS:
                num = self._counts[key]
                if num:
                    strings.append(DiffStat._FMT_DATA[key].format(num, '' if num == 1 else 's'))
            if strings:
                return prefix + joiner.join(strings)
            else:
                return ''
        def as_bar(self, scale=lambda x: x):
            string = ''
            for key in DiffStat._ORDERED_KEYS:
                count = scale(self._counts[key])
                char = DiffStat._FMT_DATA[key][-2]
                string += char * count
            return string
    class PathStats(object):
        def __init__(self, path, diff_stats):
            self.path = path
            self.diff_stats = diff_stats
        def __eq__(self, other): return self.path == other.path
        def __ne__(self, other): return self.path != other.path
        def __lt__(self, other): return self.path < other.path
        def __gt__(self, other): return self.path > other.path
        def __le__(self, other): return self.path <= other.path
        def __ge__(self, other): return self.path >= other.path
        def __iadd__(self, other):
            if isinstance(other, DiffStat.PathStats):
                if other.path != self.path:
                    raise
                else:
                    self.diff_stats += other.diff_stats
            else:
                self.diff_stats += other
            return self
    class PathStatsList(list):
        def __contains__(self, item):
            if isinstance(item, DiffStat.PathStats):
                return list.__contains__(self, item)
            for pstat in self:
                if pstat.path == item:
                    return True
            return False
        def list_format_string(self, quiet=False, comment=False, trim_names=False, max_width=80):
            if len(self) == 0 and quiet:
                return ''
            string = ''
            if trim_names:
                common_path = get_common_path([x.path for x in self])
                offset = len(common_path)
            else:
                offset = 0
            len_longest_name = max([len(x.path) for x in self]) - offset
            fstr = '%s {0}{1} |{2:5} {3}\n' % ('#' if comment else '')
            largest_total = max(max([x.diff_stats.get_total() for x in self]), 1)
            avail_width = max(0, max_width - (len_longest_name + 9))
            if comment:
                avail_width -= 1
            scale = lambda x: (x * avail_width) / largest_total
            summation = DiffStat.Stats()
            for stats in self:
                summation += stats.diff_stats
                total = stats.diff_stats.get_total()
                name = stats.path[offset:]
                spaces = ' ' * (len_longest_name - len(name))
                string += fstr.format(name, spaces, total, stats.diff_stats.as_bar(scale))
            num_files = len(self)
            if num_files > 0 or not quiet:
                if comment:
                    string += '#'
                string += ' {0} file{1} changed'.format(num_files, '' if num_files == 1 else 's')
                string += summation.as_string()
                string += '\n'
            return string

class _Lines(object):
    def __init__(self, contents=None):
        if contents is None:
            self.lines = list()
        elif isinstance(contents, str):
            self.lines = contents.splitlines(True)
        else:
            self.lines = list(contents)
    def __str__(self):
        return ''.join(self.lines)
    def append(self, data):
        if isinstance(data, str):
            self.lines += data.splitlines(True)
        else:
            self.lines += list(data)

class Header(object):
    def __init__(self, text=''):
        lines = text.splitlines(True)
        descr_starts_at = 0
        for line in lines:
            if not line.startswith('#'):
                break
            descr_starts_at += 1
        self.comment_lines = _Lines(lines[:descr_starts_at])
        diffstat_starts_at = None
        index = descr_starts_at
        while index < len(lines):
            if DiffStat.list_summary_starts_at(lines, index):
                diffstat_starts_at = index
                break
            index += 1
        if diffstat_starts_at is not None:
            self.description_lines = _Lines(lines[descr_starts_at:diffstat_starts_at])
            self.diffstat_lines = _Lines(lines[diffstat_starts_at:])
        else:
            self.description_lines = _Lines(lines[descr_starts_at:])
            self.diffstat_lines = _Lines()
    def __str__(self):
        return self.get_comments() + self.get_description() + self.get_diffstat()
    def get_comments(self):
        return str(self.comment_lines)
    def get_description(self):
        return str(self.description_lines)
    def get_diffstat(self):
        return str(self.diffstat_lines)
    def set_comments(self, text):
        self.comment_lines = _Lines(text)
    def set_description(self, text):
        self.description_lines = _Lines(text)
    def set_diffstat(self, text):
        self.diffstat_lines = _Lines(text)

def _is_non_null(path):
    return path and path != '/dev/null'

def _file_path_fm_pair(pair, strip=lambda x: x):
    get_path = lambda x: x if isinstance(x, str) else x.path
    after = get_path(pair.after)
    if _is_non_null(after):
        return strip(after)
    before = get_path(pair.before)
    if _is_non_null(before):
        return strip(before)
    return None

class FilePathPlus(object):
    ADDED = '+'
    EXTANT = ' '
    DELETED = '-'
    def __init__(self, path, status, expath=None):
        self.path = path
        self.status = status
        self.expath = expath
    @staticmethod
    def fm_pair(pair, strip=lambda x: x):
        get_path = lambda x: x if isinstance(x, str) else x.path
        path = None
        status = None
        after = get_path(pair.after)
        before = get_path(pair.before)
        if _is_non_null(after):
            path = strip(after)
            status = FilePathPlus.EXTANT if _is_non_null(before) else FilePathPlus.ADDED
        elif _is_non_null(before):
            path = strip(before)
            status = FilePathPlus.DELETED
        else:
            return None
        return FilePathPlus(path=path, status=status, expath=None)

class Preamble(_Lines):
    subtypes = list()
    @staticmethod
    def get_preamble_at(lines, index, raise_if_malformed):
        for subtype in Preamble.subtypes:
            preamble, next_index = subtype.get_preamble_at(lines, index, raise_if_malformed)
            if preamble is not None:
                return (preamble, next_index)
        return (None, index)
    @staticmethod
    def parse_lines(lines):
        '''Parse list of lines and return a valid Preamble or raise exception'''
        preamble, index = Preamble.get_preamble_at(lines, 0, raise_if_malformed=True)
        if not preamble or index < len(lines):
            raise ParseError('Not a valid preamble.')
        return preamble
    @staticmethod
    def parse_text(text):
        '''Parse text and return a valid Preamble or raise exception'''
        return DiffPlus.parse_lines(text.splitlines(True))
    def __init__(self, preamble_type, lines, file_data, extras=None):
        _Lines.__init__(self, lines)
        self.preamble_type = preamble_type
        self.file_data = file_data
        self.extras = extras
    def get_file_path(self, strip_level=0):
        strip = gen_strip_level_function(strip_level)
        if isinstance(self.file_data, str):
            return strip(self.file_data)
        elif isinstance(self.file_data, _PAIR):
            return _file_path_fm_pair(self.file_data, strip)
        else:
            return None
    def get_file_path_plus(self, strip_level=0):
        if isinstance(self.file_data, str):
            return FilePathPlus(path=self.get_file_path(strip_level), status=None, expath=None)
        elif isinstance(self.file_data, _PAIR):
            return FilePathPlus.fm_pair(self.file_data, gen_strip_level_function(strip_level))
        else:
            return None
    def get_file_expath(self, strip_level=0):
        return None

class GitPreamble(Preamble):
    DIFF_CRE = re.compile("^diff\s+--git\s+({0})\s+({1})$".format(_PATH_RE_STR, _PATH_RE_STR))
    EXTRAS_CRES = {
        'old mode' : re.compile('^(old mode)\s+(\d*)$'),
        'new mode' : re.compile('^(new mode)\s+(\d*)$'),
        'deleted file mode' : re.compile('^(deleted file mode)\s+(\d*)$'),
        'new file mode' :  re.compile('^(new file mode)\s+(\d*)$'),
        'copy from' : re.compile('^(copy from)\s+({0})$'.format(_PATH_RE_STR)),
        'copy to' : re.compile('^(copy to)\s+({0})$'.format(_PATH_RE_STR)),
        'rename from' : re.compile('^(rename from)\s+({0})$'.format(_PATH_RE_STR)),
        'rename to' : re.compile('^(rename to)\s+({0})$'.format(_PATH_RE_STR)),
        'similarity index' : re.compile('^(similarity index)\s+((\d*)%)$'),
        'dissimilarity index' : re.compile('^(dissimilarity index)\s+((\d*)%)$'),
        'index' : re.compile('^(index)\s+(([a-fA-F0-9]+)..([a-fA-F0-9]+) (\d*))$'),
    }
    @staticmethod
    def get_preamble_at(lines, index, raise_if_malformed):
        match = GitPreamble.DIFF_CRE.match(lines[index])
        if not match:
            return (None, index)
        file1 = match.group(3) if match.group(3) else match.group(4)
        file2 = match.group(6) if match.group(6) else match.group(7)
        extras = {}
        next_index = index + 1
        while next_index < len(lines):
            found = False
            for cre in GitPreamble.EXTRAS_CRES:
                match = GitPreamble.EXTRAS_CRES[cre].match(lines[next_index])
                if match:
                    extras[match.group(1)] = match.group(2)
                    next_index += 1
                    found = True
            if not found:
                break
        return (GitPreamble(lines[index:next_index], _PAIR(file1, file2), extras), next_index)
    def __init__(self, lines, file_data, extras=None):
        if extras is None:
            etxras = {}
        Preamble.__init__(self, 'git', lines=lines, file_data=file_data,extras=extras)
    def get_file_path(self, strip_level=0):
        strip = gen_strip_level_function(strip_level)
        return _file_path_fm_pair(self.file_data, strip)
    def get_file_path_plus(self, strip_level=0):
        path_plus = Preamble.get_file_path_plus(self, strip_level=strip_level)
        if path_plus and path_plus.status == FilePathPlus.ADDED:
            path_plus.expath = self.get_file_expath(strip_level=strip_level)
        return path_plus
    def get_file_expath(self, strip_level=0):
        for key in ['copy from', 'rename from']:
            if key in self.extras:
                strip = gen_strip_level_function(strip_level)
                return strip(self.extras[key])
        return None

Preamble.subtypes.append(GitPreamble)

class DiffPreamble(Preamble):
    CRE = re.compile('^diff(\s.+)\s+({0})\s+({1})$'.format(_PATH_RE_STR, _PATH_RE_STR))
    @staticmethod
    def get_preamble_at(lines, index, raise_if_malformed):
        match = DiffPreamble.CRE.match(lines[index])
        if not match:
            return (None, index)
        file1 = match.group(3) if match.group(3) else match.group(4)
        file2 = match.group(6) if match.group(6) else match.group(7)
        next_index = index + 1
        return (DiffPreamble(lines[index:next_index], _PAIR(file1, file2), match.group(1)), next_index)
    def __init__(self, lines, file_data, extras=None):
        Preamble.__init__(self, 'diff', lines=lines, file_data=file_data, extras=extras)
    def get_file_path(self, strip_level=0):
        strip = gen_strip_level_function(strip_level)
        return _file_path_fm_pair(self.file_data, strip)

Preamble.subtypes.append(DiffPreamble)

class IndexPreamble(Preamble):
    FILE_RCE = re.compile("^Index:\s+({0})(.*)$".format(_PATH_RE_STR))
    SEP_RCE = re.compile("^==*$")
    @staticmethod
    def get_preamble_at(lines, index, raise_if_malformed):
        match = IndexPreamble.FILE_RCE.match(lines[index])
        if not match:
            return (None, index)
        filename = match.group(2) if match.group(2) else match.group(3)
        next_index = index + (2 if (index + 1) < len(lines) and IndexPreamble.SEP_RCE.match(lines[index + 1]) else 1)
        return (IndexPreamble(lines[index:next_index], filename), next_index)
    def __init__(self, lines, file_data, extras=None):
        Preamble.__init__(self, 'index', lines=lines, file_data=file_data, extras=extras)
    def get_file_path(self, strip_level=0):
        strip = gen_strip_level_function(strip_level)
        return strip(self.file_data)

Preamble.subtypes.append(IndexPreamble)

class Preambles(list):
    path_precedence = ['index', 'git', 'diff']
    expath_precedence = ['git', 'index', 'diff']
    @staticmethod
    def get_preambles_at(lines, index, raise_if_malformed):
        preambles = Preambles()
        while index < len(lines):
            preamble, index = Preamble.get_preamble_at(lines, index, raise_if_malformed)
            if preamble:
                preambles.append(preamble)
            else:
                break
        return (preambles, index)
    @staticmethod
    def parse_lines(lines):
        '''Parse list of lines and return a valid Preambles list or raise exception'''
        preambles, index = Preambles.get_preambles_at(lines, 0, raise_if_malformed=True)
        if not preambles or index < len(lines):
            raise ParseError('Not a valid preamble list.')
        return preambles
    @staticmethod
    def parse_text(text):
        '''Parse text and return a valid Preambles list or raise exception'''
        return DiffPlus.parse_lines(text.splitlines(True))
    def __str__(self):
        return ''.join([str(preamble) for preamble in self])
    def get_types(self):
        return [item.preamble_type for item in self]
    def get_index_for_type(self, preamble_type):
        for index in range(len(self)):
            if self[index].preamble_type == preamble_type:
                return index
        return None
    def get_file_path(self, strip_level=0):
        paths = {}
        for preamble in self:
            path = preamble.get_file_path(strip_level=strip_level)
            if path:
                paths[preamble.preamble_type] = path
        for key in Preambles.path_precedence:
            if key in paths:
                return paths[key]
        return None
    def get_file_path_plus(self, strip_level=0):
        paths_plus = {}
        for preamble in self:
            path_plus = preamble.get_file_path_plus(strip_level=strip_level)
            if path_plus:
                paths_plus[preamble.preamble_type] = path_plus
        for key in Preambles.expath_precedence:
            if key in paths_plus:
                return paths_plus[key]
        return None
    def get_file_expath(self, strip_level=0):
        expaths = {}
        for preamble in self:
            expath = preamble.get_file_expath(strip_level=strip_level)
            if expath:
                expaths[preamble.preamble_type] = expath
        for key in Preambles.expath_precedence:
            if key in expaths:
                return expaths[key]
        return None

class Diff(object):
    subtypes = list()
    @staticmethod
    def _get_file_data_at(cre, lines, index):
        match = cre.match(lines[index])
        if not match:
            return (None, index)
        filename = match.group(2) if match.group(2) else match.group(3)
        return (_FILE_AND_TS(filename, match.group(4)), index + 1)
    @staticmethod
    def _get_diff_at(subtype, lines, start_index, raise_if_malformed=False):
        '''generic function that works for unified and context diffs'''
        if len(lines) - start_index < 2:
            return (None, start_index)
        hunks = list()
        index = start_index
        before_file_data, index = subtype.get_before_file_data_at(lines, index)
        if not before_file_data:
            return (None, start_index)
        after_file_data, index = subtype.get_after_file_data_at(lines, index)
        if not after_file_data:
            if raise_if_malformed:
                raise ParseError('Missing unified diff after file data.', index)
            else:
                return (None, start_index)
        while index < len(lines):
            hunk, index = subtype.get_hunk_at(lines, index)
            if hunk is None:
                break
            hunks.append(hunk)
        if len(hunks) == 0:
            if raise_if_malformed:
                raise ParseError('Expected unified diff hunks not found.', index)
            else:
                return (None, start_index)
        return (subtype(lines[start_index:start_index + 2], _PAIR(before_file_data, after_file_data), hunks), index)
    @staticmethod
    def get_diff_at(lines, index, raise_if_malformed):
        for subtype in Diff.subtypes:
            diff, next_index = subtype.get_diff_at(lines, index, raise_if_malformed)
            if diff is not None:
                return (diff, next_index)
        return (None, index)
    @staticmethod
    def parse_lines(lines):
        '''Parse list of lines and return a valid Diff or raise exception'''
        diff, index = Diff.get_diff_at(lines, 0, raise_if_malformed=True)
        if not diff or index < len(lines):
            raise ParseError('Not a valid diff.')
        return plus
    @staticmethod
    def parse_text(text):
        '''Parse text and return a valid DiffPlus or raise exception'''
        return Diff.parse_lines(text.splitlines(True))
    def __init__(self, diff_type, lines, file_data, hunks):
        self.header = _Lines(lines)
        self.diff_type = diff_type
        self.file_data = file_data
        self.hunks = list() if hunks is None else hunks
    class Hunk(_Lines):
        def __init__(self, lines, before, after):
            _Lines.__init__(self, lines)
            self.before = before
            self.after = after
        def get_diffstat_stats(self):
            return DiffStat.Stats()
        def fix_trailing_whitespace(self):
            return list()
        def report_trailing_whitespace(self):
            return list()
    def __str__(self):
        return str(self.header) + ''.join([str(hunk) for hunk in self.hunks])
    def fix_trailing_whitespace(self):
        bad_lines = list()
        for hunk in self.hunks:
            bad_lines += hunk.fix_trailing_whitespace()
        return bad_lines
    def report_trailing_whitespace(self):
        bad_lines = list()
        for hunk in self.hunks:
            bad_lines += hunk.report_trailing_whitespace()
        return bad_lines
    def get_diffstat_stats(self):
        stats = DiffStat.Stats()
        for hunk in self.hunks:
            stats += hunk.get_diffstat_stats()
        return stats
    def get_file_path(self, strip_level=0):
        strip = gen_strip_level_function(strip_level)
        if isinstance(self.file_data, str):
            return strip(self.file_data)
        elif isinstance(self.file_data, _PAIR):
            return _file_path_fm_pair(self.file_data, strip)
        else:
            return None
    def get_file_path_plus(self, strip_level=0):
        strip = gen_strip_level_function(strip_level)
        if isinstance(self.file_data, str):
            return FilePathPlus(path=strip(self.file_data), status=None, expath=None)
        elif isinstance(self.file_data, _PAIR):
            return FilePathPlus.fm_pair(self.file_data, strip)
        else:
            return None

class UnifiedDiff(Diff):
    BEFORE_FILE_CRE = re.compile('^--- ({0})(\s+{1})?(.*)$'.format(_PATH_RE_STR, _EITHER_TS_RE_STR))
    AFTER_FILE_CRE = re.compile('^\+\+\+ ({0})(\s+{1})?(.*)$'.format(_PATH_RE_STR, _EITHER_TS_RE_STR))
    HUNK_DATA_CRE = re.compile("^@@\s+-(\d+)(,(\d+))?\s+\+(\d+)(,(\d+))?\s+@@\s*(.*)$")
    @staticmethod
    def get_before_file_data_at(lines, index):
        return Diff._get_file_data_at(UnifiedDiff.BEFORE_FILE_CRE, lines, index)
    @staticmethod
    def get_after_file_data_at(lines, index):
        return Diff._get_file_data_at(UnifiedDiff.AFTER_FILE_CRE, lines, index)
    @staticmethod
    def get_hunk_at(lines, index):
        match = UnifiedDiff.HUNK_DATA_CRE.match(lines[index])
        if not match:
            return (None, index)
        start_index = index
        before_length = int(match.group(3)) if match.group(3) is not None else 1
        after_length = int(match.group(6)) if match.group(6) is not None else 1
        index += 1
        before_count = after_count = 0
        try:
            while before_count < before_length or after_count < after_length:
                if lines[index].startswith('-'):
                    before_count += 1
                elif lines[index].startswith('+'):
                    after_count += 1
                elif lines[index].startswith(' '):
                    before_count += 1
                    after_count += 1
                else:
                    raise ParseError('Unexpected end of unified diff hunk.', index)
                index += 1
        except IndexError:
            raise ParseError('Unexpected end of patch text.')
        before_chunk = _CHUNK(int(match.group(1)), before_length)
        after_chunk = _CHUNK(int(match.group(4)), after_length)
        return (UnifiedDiff.Hunk(lines[start_index:index], before_chunk, after_chunk), index)
    @staticmethod
    def get_diff_at(lines, start_index, raise_if_malformed=False):
        return Diff._get_diff_at(UnifiedDiff, lines, start_index, raise_if_malformed)
    def __init__(self, lines, file_data, hunks):
        Diff.__init__(self, 'unified', lines, file_data, hunks)
    class Hunk(Diff.Hunk):
        def __init__(self, lines, before, after):
            Diff.Hunk.__init__(self, lines, before, after)
        def _process_tws(self, fix=False):
            bad_lines = list()
            after_count = 0
            for index in range(len(self.lines)):
                if self.lines[index].startswith('+'):
                    after_count += 1
                    repl_line = _trim_trailing_ws(self.lines[index])
                    if len(repl_line) != len(self.lines[index]):
                        bad_lines.append(str(self.after.start + after_count - 1))
                        if fix:
                            self.lines[index] = repl_line
                elif self.lines[index].startswith(' '):
                    after_count += 1
                elif DEBUG and not self.lines[index].startswith('-'):
                    raise Bug('Unexpected end of unified diff hunk.')
            return bad_lines
        def get_diffstat_stats(self):
            stats = DiffStat.Stats()
            for index in range(len(self.lines)):
                if self.lines[index].startswith('-'):
                    stats.incr('deleted')
                elif self.lines[index].startswith('+'):
                    stats.incr('inserted')
                elif DEBUG and not self.lines[index].startswith(' '):
                    raise Bug('Unexpected end of unified diff hunk.')
            return stats
        def fix_trailing_whitespace(self):
            return self._process_tws(fix=True)
        def report_trailing_whitespace(self):
            return self._process_tws(fix=False)

Diff.subtypes.append(UnifiedDiff)

class ContextDiff(Diff):
    BEFORE_FILE_CRE = re.compile('^\*\*\* ({0})(\s+{1})?$'.format(_PATH_RE_STR, _EITHER_TS_RE_STR))
    AFTER_FILE_CRE = re.compile('^--- ({0})(\s+{1})?$'.format(_PATH_RE_STR, _EITHER_TS_RE_STR))
    HUNK_START_CRE = re.compile('^\*{15}\s*(.*)$')
    HUNK_BEFORE_CRE = re.compile('^\*\*\*\s+(\d+)(,(\d+))?\s+\*\*\*\*\s*(.*)$')
    HUNK_AFTER_CRE = re.compile('^---\s+(\d+)(,(\d+))?\s+----(.*)$')
    @staticmethod
    def get_before_file_data_at(lines, index):
        return Diff._get_file_data_at(ContextDiff.BEFORE_FILE_CRE, lines, index)
    @staticmethod
    def get_after_file_data_at(lines, index):
        return Diff._get_file_data_at(ContextDiff.AFTER_FILE_CRE, lines, index)
    @staticmethod
    def _chunk(match):
        start = int(match.group(1))
        finish = int(match.group(3)) if match.group(3) is not None else start
        if start == 0 and finish == 0:
            length = 0
        else:
            length = finish - start + 1
        return _CHUNK(start, length)
    @staticmethod
    def _get_before_chunk_at(lines, index):
        match = ContextDiff.HUNK_BEFORE_CRE.match(lines[index])
        if not match:
            return (None, index)
        return (ContextDiff._chunk(match), index + 1)
    @staticmethod
    def _get_after_chunk_at(lines, index):
        match = ContextDiff.HUNK_AFTER_CRE.match(lines[index])
        if not match:
            return (None, index)
        return (ContextDiff._chunk(match), index + 1)
    @staticmethod
    def get_hunk_at(lines, index):
        if not ContextDiff.HUNK_START_CRE.match(lines[index]):
            return (None, index)
        start_index = index
        before_start_index = index + 1
        before_chunk, index = ContextDiff._get_before_chunk_at(lines, before_start_index)
        if not before_chunk:
            return (None, index)
        before_count = after_count = 0
        try:
            after_chunk = None
            while before_count < before_chunk.length:
                after_start_index = index
                after_chunk, index = ContextDiff._get_after_chunk_at(lines, index)
                if after_chunk is not None:
                    break
                before_count += 1
                index += 1
            if after_chunk is None:
                after_start_index = index
                after_chunk, index = ContextDiff._get_after_chunk_at(lines, index)
                if after_chunk is None:
                    raise ParseError('Failed to find context diff "after" hunk.', index)
            while after_count < after_chunk.length:
                if not (lines[index].startswith('! ') or lines[index].startswith('+ ') or lines[index].startswith('  ')):
                    if after_count == 0:
                        break
                    raise ParseError('Unexpected end of context diff hunk.', index)
                after_count += 1
                index += 1
        except IndexError:
            raise ParseError('Unexpected end of patch text.')
        before_hunk = _HUNK(before_start_index - start_index, before_chunk.start, before_chunk.length, after_start_index - before_start_index)
        after_hunk = _HUNK(after_start_index - start_index, after_chunk.start, after_chunk.length, index - after_start_index)
        return (ContextDiff.Hunk(lines[start_index:index], before_hunk, after_hunk), index)
    @staticmethod
    def get_diff_at(lines, start_index, raise_if_malformed=False):
        return Diff._get_diff_at(ContextDiff, lines, start_index, raise_if_malformed)
    def __init__(self, lines, file_data, hunks):
        Diff.__init__(self, 'context', lines, file_data, hunks)
    class Hunk(Diff.Hunk):
        def __init__(self, lines, before, after):
            Diff.Hunk.__init__(self, lines, before, after)
        def _process_tws(self, fix=False):
            bad_lines = list()
            for index in range(self.after.offset + 1, self.after.offset + self.after.numlines):
                if self.lines[index].startswith('+ ') or self.lines[index].startswith('! '):
                    repl_line = self.lines[index][:2] + _trim_trailing_ws(self.lines[index][2:])
                    after_count = index - (self.after.offset + 1)
                    if len(repl_line) != len(self.lines[index]):
                        bad_lines.append(str(self.after.start + after_count))
                        if fix:
                            self.lines[index] = repl_line
                elif DEBUG and not self.lines[index].startswith('  '):
                    raise Bug('Unexpected end of context diff hunk.')
            return bad_lines
        def get_diffstat_stats(self):
            stats = DiffStat.Stats()
            for index in range(self.before.offset + 1, self.before.offset + self.before.numlines):
                if self.lines[index].startswith('- '):
                    stats.incr('deleted')
                elif self.lines[index].startswith('! '):
                    stats.incr('modified')
                elif DEBUG and not self.lines[index].startswith('  '):
                    raise Bug('Unexpected end of context diff "before" hunk.')
            for index in range(self.after.offset + 1, self.after.offset + self.after.numlines):
                if self.lines[index].startswith('+ '):
                    stats.incr('inserted')
                elif self.lines[index].startswith('! '):
                    stats.incr('modified')
                elif DEBUG and not self.lines[index].startswith('  '):
                    raise Bug('Unexpected end of context diff "after" hunk.')
            return stats
        def fix_trailing_whitespace(self):
            return self._process_tws(fix=True)
        def report_trailing_whitespace(self):
            return self._process_tws(fix=False)

Diff.subtypes.append(ContextDiff)

class DiffPlus(object):
    '''Class to hold diff (headerless) information relavent to a single file.
    Includes (optional) preambles and trailing junk such as quilt's separators.'''
    @staticmethod
    def get_diff_plus_at(lines, start_index, raise_if_malformed=False):
        preambles, index = Preambles.get_preambles_at(lines, start_index, raise_if_malformed)
        if index >= len(lines):
            if preambles:
                return (DiffPlus(preambles, None), index)
            else:
                return (None, start_index)
        diff_data, index = Diff.get_diff_at(lines, index, raise_if_malformed)
        if not diff_data:
            if preambles:
                return (DiffPlus(preambles, None), index)
            else:
                return (None, start_index)
        return (DiffPlus(preambles, diff_data), index)
    @staticmethod
    def parse_lines(lines):
        '''Parse list of lines and return a valid DiffPlus or raise exception'''
        diff_plus, index = DiffPlus.get_diff_plus_at(lines, 0, raise_if_malformed=True)
        if not diff_plus or index < len(lines):
            raise ParseError('Not a valid (optionally preambled) diff.')
        return diff_plus
    @staticmethod
    def parse_text(text):
        '''Parse text and return a valid DiffPlus or raise exception'''
        return DiffPlus.parse_lines(text.splitlines(True))
    def __init__(self, preambles=None, diff=None):
        self.preambles = Preambles() if preambles is None else preambles
        self.diff = diff
        self.trailing_junk = _Lines()
        if DEBUG:
            assert isinstance(self.preambles, Preambles) and (self.diff is None or isinstance(self.diff, Diff))
    def __str__(self):
        return str(self.preambles) + str(self.diff) + str(self.trailing_junk)
    def fix_trailing_whitespace(self):
        if self.diff is None:
            return []
        return self.diff.fix_trailing_whitespace()
    def report_trailing_whitespace(self):
        if self.diff is None:
            return []
        return self.diff.report_trailing_whitespace()
    def get_diffstat_stats(self):
        if self.diff is None:
            return DiffStat.Stats()
        return self.diff.get_diffstat_stats()
    def get_file_path(self, strip_level):
        path = self.diff.get_file_path(strip_level) if self.diff else None
        if not path:
            path = self.preambles.get_file_path(strip_level=strip_level)
        return path
    def get_file_path_plus(self, strip_level):
        path_plus = self.diff.get_file_path_plus(strip_level) if self.diff else None
        if not path_plus:
            path_plus = self.preambles.get_file_path_plus(strip_level=strip_level)
        elif path_plus.status == FilePathPlus.ADDED and path_plus.expath is None:
            path_plus.expath = self.preambles.get_file_expath(strip_level=strip_level)
        return path_plus

class Patch(object):
    '''Class to hold patch information relavent to multiple files with
    an optional header (or a single file with a header).'''
    @staticmethod
    def parse_lines(lines, num_strip_levels=0):
        '''Parse list of lines and return a Patch instance'''
        diff_starts_at = None
        diff_pluses = list()
        index = 0
        last_diff_plus = None
        while index < len(lines):
            raise_if_malformed = diff_starts_at is not None
            starts_at = index
            diff_plus, index = DiffPlus.get_diff_plus_at(lines, index, raise_if_malformed)
            if diff_plus:
                if diff_starts_at is None:
                    diff_starts_at = starts_at
                diff_pluses.append(diff_plus)
                last_diff_plus = diff_plus
                continue
            elif last_diff_plus:
                last_diff_plus.trailing_junk.append(lines[index])
            index += 1
        patch = Patch(num_strip_levels=num_strip_levels)
        patch.diff_pluses = diff_pluses
        patch.set_header(''.join(lines[0:diff_starts_at]))
        return patch
    @staticmethod
    def parse_text(text, num_strip_levels=0):
        '''Parse text and return a Patch instance'''
        return Patch.parse_lines(text.splitlines(True), num_strip_levels=num_strip_levels)
    def __init__(self, num_strip_levels=0):
        self.num_strip_levels = int(num_strip_levels)
        self.header = Header()
        self.diff_pluses = list()
    def _adjusted_strip_level(self, strip_level):
        return int(strip_level) if strip_level is not None else self.num_strip_levels
    def set_strip_level(self, strip_level):
        self.num_strip_levels = int(strip_level)
    def get_header(self):
        return self.header
    def set_header(self, text):
        self.header = Header(text)
    def get_comments(self):
        return '' if self.header is None else self.header.get_comments()
    def set_comments(self, text):
        if not self.header:
            self.header = Header(text)
        else:
            self.header.set_comments(text)
    def get_description(self):
        return '' if self.header is None else self.header.get_description()
    def set_description(self, text):
        if not self.header:
            self.header = Header(text)
        else:
            self.header.set_description(text)
    def get_header_diffstat(self):
        return '' if self.header is None else self.header.get_diffstat()
    def set_header_diffstat(self, text=None, strip_level=None):
        if not self.header:
            self.header = Header()
        if text is None:
            stats = self.get_diffstat_stats(strip_level)
            text = '-\n\n%s\n' % stats.list_format_string()
        self.header.set_diffstat(text)
    def __str__(self):
        string = '' if self.header is None else str(self.header)
        for diff_plus in self.diff_pluses:
            string += str(diff_plus)
        return string
    def get_file_paths(self, strip_level=None):
        strip_level = self._adjusted_strip_level(strip_level)
        return [diff_plus.get_file_path(strip_level=strip_level) for diff_plus in self.diff_pluses]
    def get_file_paths_plus(self, strip_level=None):
        strip_level = self._adjusted_strip_level(strip_level)
        return [diff_plus.get_file_path_plus(strip_level=strip_level) for diff_plus in self.diff_pluses]
    def get_diffstat_stats(self, strip_level=None):
        strip_level = self._adjusted_strip_level(strip_level)
        return DiffStat.PathStatsList([DiffStat.PathStats(diff_plus.get_file_path(strip_level=strip_level), diff_plus.get_diffstat_stats()) for diff_plus in self.diff_pluses])
    def fix_trailing_whitespace(self, strip_level=None):
        strip_level = self._adjusted_strip_level(strip_level)
        reports = []
        for diff_plus in self.diff_pluses:
            bad_lines = diff_plus.fix_trailing_whitespace()
            if bad_lines:
                path = diff_plus.get_file_path(strip_level=strip_level)
                reports.append(_FILE_AND_TWS_LINES(path, bad_lines))
        return reports
    def report_trailing_whitespace(self, strip_level=None):
        strip_level = self._adjusted_strip_level(strip_level)
        reports = []
        for diff_plus in self.diff_pluses:
            bad_lines = diff_plus.report_trailing_whitespace()
            if bad_lines:
                path = diff_plus.get_file_path(strip_level=strip_level)
                reports.append(_FILE_AND_TWS_LINES(path, bad_lines))
        return reports
