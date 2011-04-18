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
### Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA

'''Classes and functions for operations on patch files'''

import collections
import re
import os

# Useful named tuples to make code clearer
_HUNK = collections.namedtuple('_HUNK', ['offset', 'start', 'length',])
_PAIR = collections.namedtuple('_PAIR', ['before', 'after',])
_FILE_AND_TS = collections.namedtuple('_FILE_AND_TS', ['path', 'timestamp',])
_FILE_AND_TWS_LINES = collections.namedtuple('_FILE_AND_TWS_LINES', ['path', 'tws_lines',])
_DIFF_DATA = collections.namedtuple('_DIFF_DATA', ['file_data', 'hunks',])
FILE_DIFF_STATS = collections.namedtuple('FILE_DIFF_STATS', ['path', 'diff_stats'])

class ParseError(Exception):
    def __init__(self, message, lineno=None):
        self.message = message
        self.lineno = lineno

class Bug(Exception): pass

def gen_strip_level_function(level):
    '''Return a function for stripping the specified levels off a file path'''
    return lambda string: string if string.startswith(os.sep) else string.split(os.sep, level)[level]

def get_common_path(filelist):
    '''Return the longest common path componet for the files in the list'''
    # Extra wrapper required because os.path.commonprefix() is string oriented
    # rather than file path oriented (which is strange)
    return os.path.dirname(os.path.commonprefix(filelist))

def _trim_trailing_ws(line):
    '''Return the given line with any trailing white space removed'''
    return re.sub('[ \t]+$', '', line)

_ORDERED_DIFFSTAT_KEYS = ['inserted', 'deleted', 'modified', 'unchanged']
_DIFFSTAT_FMT_DATA = {
    'inserted' : '{0} insertion{1}(+)',
    'deleted' : '{0} deletion{1}(-)',
    'modified' : '{0} modification{1}(!)',
    'unchanged' : '{0} unchanges line{1}(+)'
}
class _DiffStats:
    '''Class to hold diffstat statistics.'''
    def __init__(self):
        self._counts = {}
        for key in _ORDERED_DIFFSTAT_KEYS:
            self._counts[key] = 0
        assert len(self._counts) == len(_ORDERED_DIFFSTAT_KEYS)
    def __add__(self, other):
        result = _DiffStats()
        for key in _ORDERED_DIFFSTAT_KEYS:
            result._counts[key] = self._counts[key] + other._counts[key]
        return result
    def __len__(self):
        return len(self._counts)
    def __getitem__(self, key):
        if isinstance(key, int):
            key = _ORDERED_DIFFSTAT_KEYS[key]
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
        for key in _ORDERED_DIFFSTAT_KEYS:
            num = self._counts[key]
            if num:
                strings.append(_DIFFSTAT_FMT_DATA[key].format(num, '' if num == 1 else 's'))
        if strings:
            return prefix + joiner.join(strings)
        else:
            return ''
    def as_bar(self, scale=lambda x: x):
        string = ''
        for key in _ORDERED_DIFFSTAT_KEYS:
            count = scale(self._counts[key])
            char = _DIFFSTAT_FMT_DATA[key][-2]
            string += char * count
        return string

def list_format_diff_stats(stats_list, quiet=False, comment=False, trim_names=False, max_width=80):
    if len(stats_list) == 0 and quiet:
        return ''
    string = ''
    if trim_names:
        common_path = get_common_path([x.path for x in stats_list])
        offset = len(common_path)
    else:
        offset = 0
    len_longest_name = max([len(x.path) for x in stats_list]) - offset
    fstr = '%s {0}{1} |{2:5} {3}\n' % ('#' if comment else '')
    largest_total = max(max([x.diff_stats.get_total() for x in stats_list]), 1)
    avail_width = max(0, max_width - (len_longest_name + 9))
    if comment:
        avail_width -= 1
    scale = lambda x: (x * avail_width) / largest_total
    summation = _DiffStats()
    for stats in stats_list:
        summation += stats.diff_stats
        total = stats.diff_stats.get_total()
        name = stats.path[offset:]
        spaces = ' ' * (len_longest_name - len(name))
        string += fstr.format(name, spaces, total, stats.diff_stats.as_bar(scale))
    num_files = len(stats_list)
    if num_files > 0 or not quiet:
        if comment:
            string += '#'
        string += ' {0} file{1} changed'.format(num_files, '' if num_files == 1 else 's')
        string += summation.as_string()
        string += '\n'
    return string

class _Header:
    def __init__(self, text=''):
        self.lines = text.splitlines(True)
    def get_as_string(self):
        return ''.join(self.lines)

class _Preamble:
    def __init__(self, preamble_type, lines, file_data, extras=None):
        self.preamble_type = preamble_type
        self.lines = lines
        self.file_data = file_data
        self.extras = extras
    def get_file_name(self):
        if isinstance(self.file_data, str):
            return self.file_data
        elif isinstance(self.file_data, _PAIR):
            if self.file_data.after and self.file_data.after != '/dev/null':
                return self.file_data.after
            elif self.file_data.before and self.file_data.before != '/dev/null':
                return self.file_data.before
            else:
                return None

def _determine_file_name(paths, preambles):
    if paths.after and paths.after != '/dev/null':
        return paths.after
    elif paths.before and paths.before != '/dev/null':
        return paths.before
    else:
        names = {}
        for preamble in preambles:
            name = preamble.get_file_name()
            if name:
                names[preamble.preamble_type] = name
        for key in ['index', 'git', 'diff']:
            if key in names:
                return names[key]
    return None

class _DiffData:
    def __init__(self, diff_type, lines, file_data, hunks):
        self.diff_type = diff_type
        self.lines = lines
        self.file_data = file_data
        self.hunks = hunks
    def _process_hunk_tws(self, hunk, fix=False):
        return list()
    def _get_hunk_diffstat_stats(self, hunk):
        return _DiffStats()
    def fix_trailing_whitespace(self):
        bad_lines = list()
        for hunk in self.hunks:
            bad_lines += self._process_hunk_tws(hunk, fix=True)
        return bad_lines
    def report_trailing_whitespace(self):
        bad_lines = list()
        for hunk in self.hunks:
            bad_lines += self._process_hunk_tws(hunk, fix=False)
        return bad_lines
    def get_diffstat_stats(self):
        stats = _DiffStats()
        for hunk in self.hunks:
            stats += self._get_hunk_diffstat_stats(hunk)
        return stats
    def get_file_paths(self):
        return _PAIR(self.file_data.before.path, self.file_data.after.path)

class FilePatch:
    '''Class to hold patch (headerless) information relavent to a single file.'''
    def __init__(self):
        self.preambles = list()
        self.diff = None
        self.trailing_junk = list()
    def get_as_string(self):
        string = ''
        for pream in self.preambles:
            string += ''.join(pream.lines)
        string += ''.join(self.diff.lines)
        string += ''.join(self.trailing_junk)
        return string
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
            return _DiffStats()
        return self.diff.get_diffstat_stats()
    def get_file_path(self):
        if not self.diff:
            return _determine_file_name(_PAIR(None, None), self.preambles)
        return _determine_file_name(self.diff.get_file_paths(), self.preambles)

class Patch:
    '''Class to hold patch information relavent to multiple files with
    an optional header (or a single file with a header).'''
    def __init__(self, num_strip_levels):
        self.num_strip_levels = num_strip_levels
        self.header = None
        self.file_patches = list()
    def get_header(self):
        return '' if self.header is None else self.header.get_as_string()
    def set_header(self, text):
        self.header = _Header(text)
    def get_as_string(self):
        string = self.get_header()
        for file_patch in self.file_patches:
            string += file_patch.get_as_string()
        return string
    def get_file_paths(self):
        return [file_patch.get_file_path() for file_patch in self.file_patches]
    def get_diffstat_stats(self):
        return [FILE_DIFF_STATS(file_patch.get_file_path(), file_patch.get_diffstat_stats()) for file_patch in self.file_patches]
    def fix_trailing_whitespace(self):
        reports = []
        for file_patch in self.file_patches:
            bad_lines = file_patch.fix_trailing_whitespace()
            if bad_lines:
                path = file_patch.get_file_path()
                reports.append(_FILE_AND_TWS_LINES(path, bad_lines))
        return reports
    def report_trailing_whitespace(self):
        reports = []
        for file_patch in self.file_patches:
            bad_lines = file_patch.report_trailing_whitespace()
            if bad_lines:
                path = file_patch.get_file_path()
                reports.append(_FILE_AND_TWS_LINES(path, bad_lines))
        return reports

# Useful strings for including in regular expressions
_PATH_RE_STR = '"([^"]+)"|(\S+)'
_TIMESTAMP_RE_STR = '\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}(\.\d{9})? [-+]{1}\d{4}'
_ALT_TIMESTAMP_RE_STR = '[A-Z][a-z]{2} [A-Z][a-z]{2} \d{2} \d{2}:\d{2}:\d{2} \d{4} [-+]{1}\d{4}'
_EITHER_TS_RE_STR = '(%s|%s)' % (_TIMESTAMP_RE_STR, _ALT_TIMESTAMP_RE_STR)

# START: preamble extraction code
# START: git preamble extraction code
GIT_PREAMBLE_DIFF_CRE = re.compile("^diff\s+--git\s+({0})\s+({1})$".format(_PATH_RE_STR, _PATH_RE_STR))
GIT_PREAMBLE_EXTRAS_CRES = {
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
    'index' : re.compile('^(index)\s+(([a-fA-F0-9]+)..([a-fA-F0-9]+) (\d*)%)$'),
}

def _get_git_preamble_at(lines, index, raise_if_malformed):
    match = GIT_PREAMBLE_DIFF_CRE.match(lines[index])
    if not match:
        return (None, index)
    file1 = match.group(3) if match.group(3) else match.group(4)
    file2 = match.group(6) if match.group(6) else match.group(7)
    extras = {}
    next_index = index + 1
    while next_index < len(lines):
        found = False
        for cre in GIT_PREAMBLE_EXTRAS_CRES:
            match = GIT_PREAMBLE_EXTRAS_CRES[cre].match(lines[next_index])
            if match:
                extras[match.group(1)] = match.group(2)
                next_index += 1
                found = True
        if not found:
            break
    return (_Preamble('git', lines[index:next_index], _PAIR(file1, file2), extras), next_index)
# END: git preamble extraction code

# START: diff preamble extraction code
DIFF_PREAMBLE_CRE = re.compile('^diff(\s.+)\s+({0})\s+({1})$'.format(_PATH_RE_STR, _PATH_RE_STR))

def _get_diff_preamble_at(lines, index, raise_if_malformed):
    match = DIFF_PREAMBLE_CRE.match(lines[index])
    if not match:
        return (None, index)
    file1 = match.group(3) if match.group(3) else match.group(4)
    file2 = match.group(6) if match.group(6) else match.group(7)
    next_index = index + 1
    return (_Preamble('diff', lines[index:next_index], _PAIR(file1, file2), match.group(1)), next_index)
# END: diff preamble extraction code

# START: Index: preamble extraction code
INDEX_PREAMBLE_FILE_RCE = re.compile("^Index:\s+({0})$".format(_PATH_RE_STR))
INDEX_PREAMBLE_SEP_RCE = re.compile("^==*$")

def _get_index_preamble_at(lines, index, raise_if_malformed):
    match = INDEX_PREAMBLE_FILE_RCE.match(lines[index])
    if not match:
        return (None, index)
    filename = match.group(2) if match.group(2) else match.group(3)
    next_index = index + (2 if INDEX_PREAMBLE_SEP_RCE.match(lines[index + 1]) else 1)
    return (_Preamble('index', lines[index:next_index], filename), next_index)
# END: Index: preamble extraction code

# An array to hold functions for extracting diff preludes from a list of lines
# Order is important (e.g. git before diff)
_GET_PREAMBLE_FUNCS = [_get_git_preamble_at, _get_diff_preamble_at, _get_index_preamble_at]
# END: preamble extraction code

# START: diff extraction code
# START: Unified Diff Format specific code
# Compiled regular expressions for unified diff format
UDIFF_BEFORE_FILE_CRE = re.compile('^--- ({0})(\s+{1})?$'.format(_PATH_RE_STR, _EITHER_TS_RE_STR))
UDIFF_AFTER_FILE_CRE = re.compile('^\+\+\+ ({0})(\s+{1})?$'.format(_PATH_RE_STR, _EITHER_TS_RE_STR))
UDIFF_HUNK_DATA_CRE = re.compile("^@@\s+-(\d+)(,(\d+))?\s+\+(\d+)(,(\d+))?\s+@@\s*(.*)$")

def _get_udiff_before_file_data_at(lines, index, strip_level):
    match = UDIFF_BEFORE_FILE_CRE.match(lines[index])
    if not match:
        return (None, index)
    filename = match.group(2) if match.group(2) else match.group(3)
    return (_FILE_AND_TS(strip_level(filename), match.group(4)), index + 1)

def _get_udiff_after_file_data_at(lines, index, strip_level):
    match = UDIFF_AFTER_FILE_CRE.match(lines[index])
    if not match:
        return (None, index)
    filename = match.group(2) if match.group(2) else match.group(3)
    return (_FILE_AND_TS(strip_level(filename), match.group(4)), index + 1)

def _get_udiff_hunk_at(lines, index, udiff_start_index):
    match = UDIFF_HUNK_DATA_CRE.match(lines[index])
    if not match:
        return (None, index)
    offset = index - udiff_start_index
    before_hunk = _HUNK(offset, int(match.group(1)), int(match.group(3)) if match.group(3) is not None else 1)
    after_hunk = _HUNK(offset, int(match.group(4)), int(match.group(6)) if match.group(6) is not None else 1)
    index += 1
    before_count = after_count = 0
    try:
        while before_count < before_hunk.length or after_count < after_hunk.length:
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
    return (_PAIR(before_hunk, after_hunk), index)

class _UDiffData(_DiffData):
    def __init__(self, lines, file_data, hunks):
        _DiffData.__init__(self, 'u', lines, file_data, hunks)
    def _process_hunk_tws(self, hunk, fix=False):
        bad_lines = list()
        before_count = after_count = 0
        index = hunk.before.offset + 1
        while before_count < hunk.before.length or after_count < hunk.after.length:
            if self.lines[index].startswith('-'):
                before_count += 1
            elif self.lines[index].startswith(' '):
                before_count += 1
                after_count += 1
            elif self.lines[index].startswith('+'):
                repl_line = _trim_trailing_ws(self.lines[index])
                if len(repl_line) != len(self.lines[index]):
                    bad_lines.append(str(hunk.after.start + after_count))
                    if fix:
                        self.lines[index] = repl_line
                after_count += 1
            else:
                raise Bug('Unexpected end of unified diff hunk.')
            index += 1
        return bad_lines
    def _get_hunk_diffstat_stats(self, hunk):
        stats = _DiffStats()
        before_count = after_count = 0
        index = hunk.before.offset + 1
        while before_count < hunk.before.length or after_count < hunk.after.length:
            if self.lines[index].startswith('-'):
                before_count += 1
                stats.incr('deleted')
            elif self.lines[index].startswith(' '):
                before_count += 1
                after_count += 1
            elif self.lines[index].startswith('+'):
                after_count += 1
                stats.incr('inserted')
            else:
                raise Bug('Unexpected end of unified diff hunk.')
            index += 1
        return stats

def _get_file_udiff_at(lines, start_index, strip_level, raise_if_malformed=False):
    hunks = list()
    index = start_index
    before_file_data, index = _get_udiff_before_file_data_at(lines, index, strip_level)
    if not before_file_data:
        return (None, start_index)
    after_file_data, index = _get_udiff_after_file_data_at(lines, index, strip_level)
    if not after_file_data:
        if raise_if_malformed:
            raise ParseError('Missing unified diff after file data.', index)
        else:
            return (None, start_index)
    while index < len(lines):
        hunk, index = _get_udiff_hunk_at(lines, index, start_index)
        if hunk is None:
            break
        hunks.append(hunk)
    if len(hunks) == 0:
        if raise_if_malformed:
            raise ParseError('Expected unified diff hunks not found.', index)
        else:
            return (None, start_index)
    return (_UDiffData(lines[start_index:index], _PAIR(before_file_data, after_file_data), hunks), index)

# END: Unified Diff Format specific code

# START: Context Diff Format specific code
# Compiled regular expressions for context diff format
CDIFF_BEFORE_FILE_CRE = re.compile('^\*\*\* ({0})(\s+{1})?$'.format(_PATH_RE_STR, _EITHER_TS_RE_STR))
CDIFF_AFTER_FILE_CRE = re.compile('^--- ({0})(\s+{1})?$'.format(_PATH_RE_STR, _EITHER_TS_RE_STR))
CDIFF_HUNK_START_CRE = re.compile('^\*{15}\s*(.*)$')
CDIFF_HUNK_BEFORE_CRE = re.compile('^\*\*\*\s+(\d+)(,(\d+))?\s+\*\*\*\*\s*(.*)$')
CDIFF_HUNK_AFTER_CRE = re.compile('^---\s+(\d+)(,(\d+))?\s+----(.*)$')

def _get_cdiff_before_file_data_at(lines, index, strip_level):
    match = CDIFF_BEFORE_FILE_CRE.match(lines[index])
    if not match:
        return (None, index)
    filename = match.group(2) if match.group(2) else match.group(3)
    return (_FILE_AND_TS(strip_level(filename), match.group(4)), index + 1)

def _get_cdiff_after_file_data_at(lines, index, strip_level):
    match = CDIFF_AFTER_FILE_CRE.match(lines[index])
    if not match:
        return (None, index)
    filename = match.group(2) if match.group(2) else match.group(3)
    return (_FILE_AND_TS(strip_level(filename), match.group(4)), index + 1)

def _cdiff_hunk(offset, match):
    start = int(match.group(1))
    finish = int(match.group(3)) if match.group(3) is not None else start
    if start == 0 and finish == 0:
        length = 0
    else:
        length = finish - start + 1
    return _HUNK(offset, start, length)

def _get_cdiff_before_hunk_at(lines, index, cdiff_start_index):
    match = CDIFF_HUNK_BEFORE_CRE.match(lines[index])
    if not match:
        return (None, index)
    offset = index - cdiff_start_index
    return (_cdiff_hunk(offset, match), index + 1)

def _get_cdiff_after_hunk_at(lines, index, cdiff_start_index):
    match = CDIFF_HUNK_AFTER_CRE.match(lines[index])
    if not match:
        return (None, index)
    offset = index - cdiff_start_index
    return (_cdiff_hunk(offset, match), index + 1)

def _get_cdiff_hunk_at(lines, index, cdiff_start_index):
    if not CDIFF_HUNK_START_CRE.match(lines[index]):
        return (None, index)
    before_hunk, index = _get_cdiff_before_hunk_at(lines, index + 1, cdiff_start_index)
    if not before_hunk:
        return (None, index)
    before_count = after_count = 0
    try:
        after_hunk = None
        while before_count < before_hunk.length:
            after_hunk, index = _get_cdiff_after_hunk_at(lines, index, cdiff_start_index)
            if after_hunk is not None:
                break
            before_count += 1
            index += 1
        if after_hunk is None:
            after_hunk, index = _get_cdiff_after_hunk_at(lines, index, cdiff_start_index)
            if after_hunk is None:
                raise ParseError('Failed to find context diff "after" hunk.', index)
        while after_count < after_hunk.length:
            if not (lines[index].startswith('! ') or lines[index].startswith('+ ') or lines[index].startswith('  ')):
                if after_count == 0:
                    break
                raise ParseError('Unexpected end of context diff hunk.', index)
            after_count += 1
            index += 1
    except IndexError:
        raise ParseError('Unexpected end of patch text.')
    return (_PAIR(before_hunk, after_hunk), index)

class _CDiffData(_DiffData):
    def __init__(self, lines, file_data, hunks):
        _DiffData.__init__(self, 'u', lines, file_data, hunks)
    def _process_hunk_tws(self, hunk, fix=False):
        bad_lines = list()
        for index in range(hunk.after.offset + 1, hunk.after.offset + hunk.after.length + 1):
            if self.lines[index].startswith('+ ') or self.lines[index].startswith('! '):
                repl_line = _trim_trailing_ws(self.lines[index])
                if len(repl_line) != len(self.lines[index]):
                    bad_lines.append(str(hunk.after.start + after_count))
                    if fix:
                        self.lines[index] = repl_line
            elif not self.lines[index].startswith('  '):
                if index == hunk.after.offset + 1:
                    break
                raise Bug('Unexpected end of context diff hunk.')
        return bad_lines
    def _get_hunk_diffstat_stats(self, hunk):
        stats = _DiffStats()
        finish = min(hunk.after.offset, hunk.before.offset + hunk.before.length + 1)
        for index in range(hunk.before.offset + 1, finish):
            if self.lines[index].startswith('- '):
                stats.incr('deleted')
            elif self.lines[index].startswith('! '):
                stats.incr('modified')
            elif not self.lines[index].startswith('  '):
                raise Bug('Unexpected end of context diff "before" hunk.')
        finish = min(hunk.after.offset + hunk.after.length + 1, len(self.lines))
        for index in range(hunk.after.offset + 1, finish):
            if self.lines[index].startswith('+ '):
                stats.incr('inserted')
            elif self.lines[index].startswith('! '):
                stats.incr('modified')
            elif not self.lines[index].startswith('  '):
                if index == hunk.after.offset + 1:
                    break
                raise Bug('Unexpected end of context diff "after" hunk.')
        return stats

def _get_file_cdiff_at(lines, start_index, strip_level, raise_if_malformed=False):
    hunks = list()
    index = start_index
    before_file_data, index = _get_cdiff_before_file_data_at(lines, index, strip_level)
    if not before_file_data:
        return (None, start_index)
    after_file_data, index = _get_cdiff_after_file_data_at(lines, index, strip_level)
    if not after_file_data:
        if raise_if_malformed:
            raise ParseError('Missing unified diff after file data.', index)
        else:
            return (None, start_index)
    while index < len(lines):
        hunk, index = _get_cdiff_hunk_at(lines, index, start_index)
        if hunk is None:
            break
        hunks.append(hunk)
    if len(hunks) == 0:
        if raise_if_malformed:
            raise ParseError('Expected unified diff hunks not found.', index)
        else:
            return (None, start_index)
    return (_CDiffData(lines[start_index:index], _PAIR(before_file_data, after_file_data), hunks), index)

# END: Context Diff Format specific code

# An array to hold functions for extracting diffs from a list of lines
# In order of likelihood of encounter
_GET_DIFF_FUNCS = [_get_file_udiff_at, _get_file_cdiff_at]
# END: diff extraction code

def parse_lines(lines, num_strip_levels=1):
    '''Parse list of lines and return a FilePatch of Patch instance as appropriate'''
    strip_level = gen_strip_level_function(num_strip_levels)
    diff_starts_at = None
    file_patches = list()
    index = 0
    last_file_patch = None
    while index < len(lines):
        raise_if_malformed = diff_starts_at is not None
        starts_at = index
        preambles = list()
        for get_preamble_at in _GET_PREAMBLE_FUNCS:
            preamble, index = get_preamble_at(lines, index, raise_if_malformed)
            if preamble:
                preambles.append(preamble)
        for get_file_diff_at in _GET_DIFF_FUNCS:
            diff_data, index = get_file_diff_at(lines, index, strip_level, raise_if_malformed)
            if diff_data:
                break
        if diff_data:
            if diff_starts_at is None:
                diff_starts_at = starts_at
            file_patch = FilePatch()
            file_patch.diff = diff_data
            file_patch.preambles = preambles
            file_patches.append(file_patch)
            last_file_patch = file_patch
            continue
        elif last_file_patch:
            last_file_patch.trailing_junk.append(lines[index])
        index += 1
    if diff_starts_at == 0 and len(file_patches) == 1:
        return last_file_patch
    patch = Patch(num_strip_levels)
    patch.file_patches = file_patches
    patch.set_header(''.join(lines[0:diff_starts_at]))
    return patch

def parse_text(text, num_strip_levels=1):
    '''Parse text and return a FilePatch of Patch instance as appropriate'''
    return parse_lines(text.splitlines(True))
