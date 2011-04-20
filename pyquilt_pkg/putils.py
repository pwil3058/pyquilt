# -*- python -*-

### Copyright (C) 2005 Peter Williams <peter_ono@users.sourceforge.net>

### This program is free software; you can redistribute it and/or modify
### it under the terms of the GNU General Public License as published by
### the Free Software Foundation; version 2 of the License only.

### This program is distributed in the hope that it will be useful,
### but WITHOUT ANY WARRANTY; without even the implied warranty of
### MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
### GNU General Public License for more details.

### You should have received a copy of the GNU General Public License
### along with this program; if not, write to the Free Software
### Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA

'''Provide functions for manipulating patch files and/or text buffers'''

import re
import os.path
import shutil
import tempfile
import collections

from pyquilt_pkg import shell
from pyquilt_pkg import fsutils
from pyquilt_pkg import cmd_result
from pyquilt_pkg import patchlib

_DIFFSTAT_EMPTY = re.compile("^#? 0 files changed$")
_DIFFSTAT_END = re.compile("^#? (\d+) files? changed(, (\d+) insertions?\(\+\))?(, (\d+) deletions?\(-\))?(, (\d+) modifications?\(\!\))?$")
_DIFFSTAT_FSTATS = re.compile("^#? (\S+)\s*\|((binary)|(\s*(\d+)(\s+\+*-*\!*)?))$")

_TIMESTAMP_RE_STR = '(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\.\d{9} [-+]{1}\d{4})'
_ALT_TIMESTAMP_RE_STR = '([A-Z][a-z]{2} [A-Z][a-z]{2} \d{2} \d{2}:\d{2}:\d{2} \d{4} [-+]{1}\d{4})'
_EITHER_TS_RE = '(%s|%s)' % (_TIMESTAMP_RE_STR, _ALT_TIMESTAMP_RE_STR)

_UDIFF_H1 = re.compile('^--- (.*?)(\s+%s)?$' % _EITHER_TS_RE)
_UDIFF_H2 = re.compile('^\+\+\+ (.*?)(\s+%s)?$' % _EITHER_TS_RE)
_UDIFF_PD = re.compile("^@@\s+-(\d+)(,(\d+))?\s+\+(\d+)(,(\d+))?\s+@@\s*(.*)$")

_GIT_HDR_DIFF = re.compile("^diff --git (.*)$")
_GIT_OLD_MODE = re.compile('^old mode (\d*)$')
_GIT_NEW_MODE = re.compile('^new mode (\d*)$')
_GIT_DELETED_FILE_MODE = re.compile('^deleted file mode (\d*)$')
_GIT_NEW_FILE_MODE = re.compile('^new file mode (\d*)$')
_GIT_COPY_FROM = re.compile('^copy from (.*)$')
_GIT_COPY_TO = re.compile('^copy to (.*)$')
_GIT_RENAME_FROM = re.compile('^rename from (.*)$')
_GIT_RENAME_TO = re.compile('^rename to (.*)$')
_GIT_SIMILARITY_INDEX = re.compile('^similarity index (\d*)%$')
_GIT_DISSIMILARITY_INDEX = re.compile('^dissimilarity index (\d*)%$')
_GIT_INDEX = re.compile('^index ([a-fA-F0-9]+)..([a-fA-F0-9]+) (\d*)%$')

_GIT_EXTRAS = \
[
    _GIT_OLD_MODE, _GIT_NEW_MODE, _GIT_DELETED_FILE_MODE, _GIT_NEW_FILE_MODE,
    _GIT_COPY_FROM, _GIT_COPY_TO, _GIT_RENAME_FROM, _GIT_RENAME_TO,
    _GIT_SIMILARITY_INDEX, _GIT_DISSIMILARITY_INDEX, _GIT_INDEX
]

_CDIFF_H1 = re.compile("^\*\*\* (\S+)\s*(.*)$")
_CDIFF_H2 = re.compile("^--- (\S+)\s*(.*)$")
_CDIFF_H3 = re.compile("^\*+$")
_CDIFF_CHG = re.compile("^\*+\s+(\d+)(,(\d+))?\s+\*+\s*(.*)$")
_CDIFF_DEL = re.compile("^-+\s+(\d+)(,(\d+))?\s+-+\s*(.*)$")

_HDR_INDEX = re.compile("^Index:\s+(.*)$")
_HDR_DIFF = re.compile("^diff\s+(.*)$")
_HDR_SEP = re.compile("^==*$")
_HDR_RCS1 = re.compile("^RCS file:\s+(.*)$")
_HDR_RCS2 = re.compile("^retrieving revision\s+(\d+(\.\d+)*)$")

_BLANK_LINE = re.compile("^\s*$")
_DIVIDER_LINE = re.compile("^---$")

def _udiff_starts_at(lines, i):
    """
    Return whether the ith line in lines is the start of a unified diff

    Arguments:
    lines -- the list of lines to be examined
    i     -- the line number to be examined
    """
    if (i + 2) >= len(lines):
        return False
    if not _UDIFF_H1.match(lines[i]):
        return False
    if not _UDIFF_H2.match(lines[i + 1]):
        return False
    return _UDIFF_PD.match(lines[i + 2])

def _is_git_extra_line(line):
    """
    Return whether the line is a git diff "extra" line

    Argument:
    line -- theline to be examined
    """
    for regex in _GIT_EXTRAS:
        match = regex.match(line)
        if match:
            return (regex, match)
    return False

def _git_diff_starts_at(lines, i):
    """
    Return whether the ith line in lines is the start of a git diff

    Arguments:
    lines -- the list of lines to be examined
    i     -- the line number to be examined
    """
    if i < len(lines) and _GIT_HDR_DIFF.match(lines[i]):
        i += 1
    else:
        return False
    extra_count = 0
    while i < len(lines) and _is_git_extra_line(lines[i]):
        i += 1
        extra_count += 1
    if extra_count == 0:
        return _udiff_starts_at(lines, i)
    elif i < len(lines):
        return _GIT_HDR_DIFF.match(lines[i]) or _udiff_starts_at(lines, i)
    else:
        return True

def _cdiff_starts_at(lines, i):
    """
    Return whether the ith line in lines is the start of a combined diff

    Arguments:
    lines -- the list of lines to be examined
    i     -- the line number to be examined
    """
    if (i + 3) >= len(lines):
        return False
    if not _CDIFF_H1.match(lines[i]):
        return False
    if not _CDIFF_H2.match(lines[i + 1]):
        return False
    if not _CDIFF_H3.match(lines[i + 2]):
        return False
    return _CDIFF_CHG.match(lines[i + 3]) or  _CDIFF_DEL.match(lines[i + 3])

def _trisect_patch_lines(lines):
    """
    Return indices splitting lines into comments, stats and diff parts

    Arguments:
    lines -- the list of lines to be trisected

    Return a two tuple indicating start of stats and diff parts.
    For stats part provide integer index of first stats line or None if
    the stats part is not present.
    For diff part provide a two tuple (index of first diff line, diff type)
    or None if the diff part is not present.
    """
    n = len(lines)
    patch_type = None
    patch_si = None
    diffstat_si = None
    i = 0
    while i < n:
        if _DIFFSTAT_EMPTY.match(lines[i]):
            diffstat_si = i
        elif _DIFFSTAT_FSTATS.match(lines[i]):
            k = 1
            while (i + k) < n and _DIFFSTAT_FSTATS.match(lines[i + k]):
                k += 1
            if (i + k) < n and _DIFFSTAT_END.match(lines[i + k]):
                diffstat_si = i
                i += k
            else:
                diffstat_si = None
                i += k - 1
        elif _git_diff_starts_at(lines, i):
            patch_si = i
            patch_type = 'git'
            break
        elif _HDR_INDEX.match(lines[i]) or _HDR_DIFF.match(lines[i]):
            k = i + 1
            if k < n and _HDR_SEP.match(lines[k]):
                k += 1
            if _udiff_starts_at(lines, k):
                patch_si = i
                patch_type = "u"
                break
            elif _cdiff_starts_at(lines, k):
                patch_si = i
                patch_type = "c"
                break
            else:
                i = k
                diffstat_si = None
        elif _HDR_RCS1.match(lines[i]):
            if (i + 1) < n and _HDR_RCS2.match(lines[i]):
                k = i + 1
                if k < n and _HDR_SEP.match(lines[k]):
                    k += 1
                if _udiff_starts_at(lines, k):
                    patch_si = i
                    patch_type = "u"
                    break
                elif _cdiff_starts_at(lines, k):
                    patch_si = i
                    patch_type = "c"
                    break
                else:
                    i = k
                    diffstat_si = None
            else:
                diffstat_si = None
        elif _udiff_starts_at(lines, i):
            patch_si = i
            patch_type = "u"
            break
        elif _cdiff_starts_at(lines, i):
            patch_si = i
            patch_type = "c"
            break
        elif not (_BLANK_LINE.match(lines[i]) or _DIVIDER_LINE.match(lines[i])):
            diffstat_si = None
        i += 1
    if patch_si is None:
        return (diffstat_si, None)
    else:
        return (diffstat_si, (patch_si, patch_type))

def _trisect_patch_file(path):
    try:
        buf = fsutils.get_file_contents(path)
    except IOError:
        return (False, (None, None, None))
    lines = buf.splitlines(True)
    diffstat_si, patch = _trisect_patch_lines(lines)
    if patch is None:
        if diffstat_si is None:
            res = (lines, [], [])
        else:
            res = (lines[0:diffstat_si], lines[diffstat_si:], [])
    else:
        plines = lines[patch[0]:]
        if diffstat_si is None:
            res = (lines[:patch[0]], [], plines)
        else:
            res = (lines[0:diffstat_si], lines[diffstat_si:patch[0]], plines)
    return (True,  res)

def _count_comment_lines(lines):
    count = 0
    for line in lines:
        if not line.startswith('#'):
            break
        count += 1
    return count

def get_patch_descr_lines(path):
    try:
        buf = fsutils.get_file_contents(path)
    except IOError:
        return (False, None)
    lines = buf.splitlines(True)
    diffstat_si, patch = _trisect_patch_lines(lines)
    if diffstat_si is None:
        if patch is None:
            res = lines
        else:
            res = lines[0:patch[0]]
    else:
        res = lines[0:diffstat_si]
    if len(res):
        comment_count = _count_comment_lines(res)
        res = res[comment_count:]
    return (True, res)

def get_patch_descr(path):
    ok, lines = get_patch_descr_lines(path)
    if not ok:
        return ''
    else:
        return ''.join(lines)

def extract_header(text):
    lines = text.splitlines(True)
    diffstat_si, patch = _trisect_patch_lines(lines)
    if patch is None:
        return text
    else:
        return ''.join(lines[0:patch[0]])

def get_patch_hdr_lines(path):
    try:
        buf = fsutils.get_file_contents(path)
    except IOError:
        return (False, None)
    lines = buf.splitlines(True)
    diffstat_si, patch = _trisect_patch_lines(lines)
    if patch is None:
        res = lines
    else:
        res = lines[0:patch[0]]
    if len(res):
        comment_count = _count_comment_lines(res)
        res = res[comment_count:]
    return (True,  res)

def get_patch_hdr(path):
    ok, lines = get_patch_hdr_lines(path)
    if not ok:
        return ''
    else:
        return ''.join(lines)

def get_patch_diff_fm_text(textbuf):
    lines = textbuf.splitlines(True)
    _, patch = _trisect_patch_lines(lines)
    if patch is None:
        return ''
    return ''.join(lines[patch[0]:])

def get_patch_diff(path, file_list=None):
    if not file_list:
        return get_patch_diff_fm_text(fsutils.get_file_contents(path))
    if not shell.which("filterdiff"):
        return (False, "This functionality requires \"filterdiff\" from \"patchutils\"")
    cmd = "filterdiff -p 1"
    for filename in file_list:
        cmd += " -i %s" % filename
    res, sout, serr = shell.run_cmd("%s %s" % (cmd, path))
    if res == 0:
        return (True, sout)
    else:
        return (False, sout + serr)

def _lines_to_temp_file(lines, dummyfor=None):
    if dummyfor:
        tmpdir = os.path.dirname(dummyfor)
        _dummy, suffix = os.path.splitext(dummyfor)
    else:
        tmpdir = os.getcwd()
        suffix = ''
    try:
        fd, tmpf_name = tempfile.mkstemp(dir=tmpdir,suffix=suffix)
        os.close(fd)
        fsutils.set_file_contents(tmpf_name, ''.join(lines))
    except IOError:
        if tmpf_name is not None and os.path.exists(tmpf_name):
            os.remove(tmpf_name)
        return None
    return tmpf_name

def set_patch_descr_lines(path, lines):
    if os.path.exists(path):
        res, parts = _trisect_patch_file(path)
        if not res:
            return False
    else:
        parts = ([], [], [])
    if len(parts[0]):
        comment_count = _count_comment_lines(parts[0])
        comments = parts[0][:comment_count]
    else:
        comments = []
    tmpf_name = _lines_to_temp_file(comments + lines + parts[1] + parts[2], path)
    if not tmpf_name:
        return False
    try:
        os.rename(tmpf_name, path)
        ret = True
    except IOError:
        ret = False
        if os.path.exists(tmpf_name):
            os.remove(tmpf_name)
    return ret

def set_patch_descr(path, text):
    return set_patch_descr_lines(path, text.splitlines(True))

def set_patch_hdr_lines(path, lines):
    if os.path.exists(path):
        res, parts = _trisect_patch_file(path)
        if not res:
            return False
    else:
        parts = ([], [], [])
    if len(parts[0]):
        comment_count = _count_comment_lines(parts[0])
        comments = parts[0][:comment_count]
    else:
        comments = []
    tmpf_name = _lines_to_temp_file(comments + lines + parts[2], path)
    if not tmpf_name:
        return False
    try:
        os.rename(tmpf_name, path)
        ret = True
    except IOError:
        ret = False
        if os.path.exists(tmpf_name):
            os.remove(tmpf_name)
    return ret

def set_patch_hdr(path, text):
    return set_patch_hdr_lines(path, text.splitlines(True))

ADDED = "A"
EXTANT = "M"
DELETED = "R"

def strip_zero_levels(path):
    return path

def strip_one_level(path):
    return path.split('/', 1)[1]

def _file_name_in_diffline(diffline):
    match = re.match('diff --git \w+/(.*) \w+/(.*)', diffline)
    if match:
        return match.group(1)
    else:
        return None

def _get_git_diff_file_data(lines, i):
    assert _GIT_HDR_DIFF.match(lines[i])
    diffline = lines[i]
    i += 1
    new_file = False
    deleted_file = False
    copy_from = None
    copy_to = None
    rename_from = None
    rename_to = None
    while i < len(lines):
        match_data = _is_git_extra_line(lines[i])
        if not match_data:
            break
        else:
            i += 1
            regex, match = match_data
        if regex is _GIT_COPY_FROM:
            copy_from = match.group(1)
        elif regex is _GIT_COPY_TO:
            copy_to = match.group(1)
        elif regex is _GIT_RENAME_FROM:
            rename_from = match.group(1)
        elif regex is _GIT_RENAME_TO:
            rename_from = match.group(1)
        elif regex is _GIT_NEW_FILE_MODE:
            new_file = True
        elif regex is _GIT_DELETED_FILE_MODE:
            deleted_file = True
    if copy_to:
        return [i, [(copy_to, ADDED, copy_from)]]
    if rename_to:
        return [i, [(rename_to, ADDED, rename_from), (rename_from, DELETED, None)]]
    if deleted_file:
        while i < len(lines):
            match = _UDIFF_H1.match(lines[i])
            i += 1
            if match:
                filename = match.group(1)[2:]
                return [i, [(filename, DELETED, None)]]
    while i < len(lines) and not _GIT_HDR_DIFF.match(lines[i]):
        match = _UDIFF_H2.match(lines[i])
        i += 1
        if match:
            filename = match.group(1)[2:]
            if new_file:
                return [i, [(filename, ADDED, None)]]
            else:
                return [i, [(filename, EXTANT, None)]]
    filename = _file_name_in_diffline(diffline)
    if new_file:
        return (i, [[filename, ADDED, None]])
    else:
        return (i, [[filename, EXTANT, None]])

def _get_git_diff_files(lines, i):
    files = []
    while i < len(lines):
        i, files_data = _get_git_diff_file_data(lines, i)
        files += files_data
        while i < len(lines) and not _git_diff_starts_at(lines, i):
            i += 1
    return files

def _get_unified_diff_files(lines, i, strip_req_level=strip_one_level):
    files = []
    while i < len(lines):
        match1 = _UDIFF_H1.match(lines[i])
        i += 1
        if match1:
            match2 = _UDIFF_H2.match(lines[i])
            i += 1
            file1 = match1.group(1)
            if file1 == '/dev/null':
                files.append((strip_req_level(match2.group(1)), ADDED, None))
            else:
                file2 = match2.group(1)
                if file2 == '/dev/null' :
                    files.append((strip_req_level(file1), DELETED, None))
                else:
                    files.append((strip_req_level(file2), EXTANT, None))
    return files

def _get_combined_diff_files(lines, i, strip_req_level=strip_one_level):
    files = []
    while i < len(lines):
        match1 = _CDIFF_H1.match(lines[i])
        i += 1
        if not match1:
            continue
        match2 = _CDIFF_H2.match(lines[i])
        if not match2:
            continue
        match3 = _CDIFF_H3.match(lines[i + 1])
        if not match3:
            continue
        if not (_CDIFF_CHG.match(lines[i + 2]) or  _CDIFF_DEL.match(lines[i + 2])):
            continue
        if i >= 3:
            matchIndex = _HDR_INDEX.match(lines[i-3])
            sepIndex = _HDR_SEP.match(lines[i-2])
            if matchIndex and sepIndex:
                files.append(matchIndex.group(1))
                i += 2
                continue
        if match2.group(1) != '/dev/null':
            files.append(strip_req_level(match2.group(1)))
        else:
            files.append(strip_req_level(match1.group(1)))
        i += 2
    return files

def get_patch_files(path, status=True, decorated=False, strip_level=1):
    strip_level = strip_zero_levels if int(strip_level) == 0 else strip_one_level
    try:
        buf = fsutils.get_file_contents(path)
    except IOError:
        return (False, 'Problem(s) open file "%s" not found' % path)
    lines = buf.splitlines(True)
    _, patch = _trisect_patch_lines(lines)
    if patch is None:
        return (True, [])
    if patch[1] == 'git':
        files = _get_git_diff_files(lines, patch[0])
    elif patch[1] == 'u':
        files = _get_unified_diff_files(lines, patch[0], strip_level)
    else:
        files = _get_combined_diff_files(lines, patch[0], strip_level)
    if decorated:
        filelist = []
        for file_data in files:
            filelist.append(' '.join([file_data[1], file_data[0]]))
            if file_data[1] == ADDED and file_data[2]:
                filelist.append('  %s' % file_data[2])
        return (True, filelist)
    elif status:
        return (True, files)
    return (True, [file_data[0] for file_data in files])

def apply_patch_text(text, indir=None, patch_args=''):
    from pyquilt_pkg import customization
    patch_opts = customization.get_default_opts('patch')
    if indir:
        cmd = 'patch -d %s' % indir
    else:
        cmd = 'patch'
    cmd += ' %s %s' % (patch_opts, patch_args)
    return shell.run_cmd(cmd, input_text=text)

def apply_patch(patch_file, indir=None, patch_args=''):
    text = fsutils.get_file_contents(patch_file)
    return apply_patch_text(text, indir=indir, patch_args=patch_args)

def remove_trailing_ws(text, strip_level, dry_run=False):
    obj = patchlib.parse_text(text, int(strip_level))
    if isinstance(obj, patchlib.Patch):
        report = obj.fix_trailing_whitespace()
    elif isinstance(obj, patchlib.FilePatch):
        bad_lines = obj.fix_trailing_whitespace()
        report = [(obj.get_file_path(), bad_lines)] if bad_lines else []
    else:
        return cmd_result.Result(cmd_result.ERROR, text, 'Patch data does not conform to expectations\n')
    errtext = ''
    if dry_run:
        for filename, bad_lines in report:
            if len(bad_lines) > 1:
                errtext += 'Warning: trailing whitespace in lines %s of %s\n' % (','.join(bad_lines), filename)
            else:
                errtext += 'Warning: trailing whitespace in line %s of %s\n' % (bad_lines[0], filename)
        return cmd_result.Result(cmd_result.OK, text, errtext)
    else:
        for filename, bad_lines in report:
            if len(bad_lines) > 1:
                errtext += 'Removing trailing whitespace from lines %s of %s\n' % (','.join(bad_lines), filename)
            else:
                errtext += 'Removing trailing whitespace from line %s of %s\n' % (bad_lines[0], filename)
        return cmd_result.Result(cmd_result.OK, obj.get_as_string(), errtext)
