### Copyright (C) 2010 Peter Williams <peter_ono@users.sourceforge.net>
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

'''
Manage the patch directory and patch series file
'''

import os
import re
import sys
import tempfile

from pyquilt_pkg import customization
from pyquilt_pkg import cmd_result
from pyquilt_pkg import shell
from pyquilt_pkg import putils
from pyquilt_pkg import fsutils
from pyquilt_pkg import backup
from pyquilt_pkg import output

DB_VERSION = 2

QUILT_PATCHES = None

QUILT_SERIES = None

QUILT_PC = None

ORIGINAL_LANG = os.getenv('LANG', '')

SUBDIR = ''
SUBDIR_DOWN = 0

SERIES = None
DB = None

def gen_tempfile(template=None, asdir=False):
    if template is None:
        indir = os.getenv('TMPDIR', '/tmp')
        prefix = 'quilt'
    else:
        indir, prefix = os.path.split(template)
    if asdir:
        return tempfile.mkdtemp(prefix=prefix, dir=indir)
    else:
        fdesc, name = tempfile.mkstemp(prefix=prefix, dir=indir)
        os.close(fdesc)
        return name

def version_check():
    if not os.path.isdir(QUILT_PC):
        return True
    ver_file = os.path.join(QUILT_PC, '.version')
    if os.path.isfile(ver_file):
        version = int(open(ver_file).read().strip())
        if version > DB_VERSION:
            output.error('The quilt meta-data in this tree has version %s, but this version of quilt can only handle meta-data formats up to and including version %s. Please pop all the patches using the version of quilt used to push them before downgrading.\n' % (version, DB_VERSION))
            sys.exit(cmd_result.ERROR)
        return version == DB_VERSION
    return False

def _find_base_dir(dirpath=None):
    if dirpath is None:
        dirpath = os.getcwd()
    subdir = None
    subdir_down = 0
    while True:
        if os.path.isdir(os.path.join(dirpath, QUILT_PATCHES)):
            return dirpath, subdir, subdir_down
        elif os.path.isdir(os.path.join(dirpath, QUILT_PC)):
            return dirpath, subdir, subdir_down
        else:
            dirpath, basename = os.path.split(dirpath)
            if not basename:
                break
            subdir = basename if subdir is None else os.path.join(basename, subdir)
            subdir_down += 1
    return None, None, None

def _get_db_quilt_patches():
    fname = os.path.join(QUILT_PC, '.quilt_patches')
    if os.path.isfile(fname):
        return open(fname).read().strip()
    return None

def _get_db_quilt_series():
    fname = os.path.join(QUILT_PC, '.quilt_series')
    if os.path.isfile(fname):
        return open(fname).read().strip()
    return None

def chdir_to_base_dir(skip_version_check=False):
    '''Do the stuff that sourcing patchfns would have done'''
    global SUBDIR, SUBDIR_DOWN, QUILT_PATCHES, QUILT_SERIES, SERIES, DB, QUILT_PC
    QUILT_PATCHES = customization.get_config('QUILT_PATCHES', 'patches')
    QUILT_SERIES = customization.get_config('QUILT_SERIES', 'series')
    QUILT_PC = customization.get_config('QUILT_PC', '.pc')
    basedir, subdir, subdir_down = _find_base_dir()
    if basedir is None:
        SERIES = os.path.join(QUILT_PC, QUILT_SERIES)
        DB = os.path.join(QUILT_PC, 'applied-patches')
        return
    if subdir is not None:
        try:
            os.chdir(basedir)
        except OSError:
            output.error('Cannot change into parent directory %s' % basedir)
            sys.exit(cmd_result.ERROR)
        SUBDIR = subdir
        SUBDIR_DOWN = subdir_down
    quilt_patches = _get_db_quilt_patches()
    if quilt_patches is not None:
        QUILT_PATCHES = quilt_patches
    quilt_series = _get_db_quilt_series()
    if quilt_series is not None:
        QUILT_SERIES = quilt_series
    if os.path.isabs(QUILT_SERIES):
        SERIES = QUILT_SERIES
    elif os.path.isfile(os.path.join(QUILT_PC, QUILT_SERIES)):
        SERIES = os.path.join(QUILT_PC, QUILT_SERIES)
    elif os.path.isfile(QUILT_SERIES):
        SERIES = QUILT_SERIES
    else:
        SERIES = os.path.join(QUILT_PATCHES, QUILT_SERIES)
    DB = os.path.join(QUILT_PC, 'applied-patches')
    if not skip_version_check and not version_check():
        output.error('The working tree was created by an older version of quilt. Please run "quilt upgrade".\n')
        sys.exit(cmd_result.ERROR)

def create_db():
    if not os.path.isdir(QUILT_PC):
        if os.path.exists(QUILT_PC):
            output.error('%s is not a directory.\n' % QUILT_PC)
            sys.exit(cmd_result.ERROR)
        try:
            os.mkdir(QUILT_PC)
        except OSError:
            output.error('Could not create directory %s.\n' % QUILT_PC)
            sys.exit(cmd_result.ERROR)
        open(os.path.join(QUILT_PC, '.version'), 'w').write('%s\n' % DB_VERSION)
    if not os.path.isfile(os.path.join(QUILT_PC, '.quilt_patches')):
        open(os.path.join(QUILT_PC, '.quilt_patches'), 'w').write(QUILT_PATCHES + '\n')
    if not os.path.isfile(os.path.join(QUILT_PC, '.quilt_series')):
        open(os.path.join(QUILT_PC, '.quilt_series'), 'w').write(QUILT_SERIES + '\n')

def quote_bre(string):
    'Quote a string for use in a basic regular expression.'
    result = shell.sed(['-e', 's:\([][^$/.*\\]\):\\\1:g'], string)
    assert result.eflags == 0
    return result.stdout

def quote_bre(string):
    'Quote a string for use in anextended regular expression.'
    result = shell.sed(['-e', 's:\([][?{(|)}^$/.+*\\]\):\\\1:g'], string)
    assert result.eflags == 0
    return result.stdout

def print_patch(patchname):
    if customization.get_config('QUILT_PATCHES_PREFIX', False):
        parts = ['..'] * SUBDIR_DOWN + [QUILT_PATCHES, patchname]
        return os.path.join(*parts)
    else:
        return patchname

def pyquilt_command(cmd):
    from pyquilt_pkg import cmd_line
    args = cmd_line.PARSER.parse_args(cmd.split())
    return args.run_cmd(args)

def patch_name_base(patchname):
    if patchname[:len(QUILT_PATCHES)+1] == QUILT_PATCHES + os.sep:
        return patchname[len(QUILT_PATCHES)+1:]
    return patchname

def patch_file_name(patch):
    return os.path.join(QUILT_PATCHES, patch)

def find_first_patch():
    patches = _get_series()
    if len(patches) > 0:
        return patches[0]
    if os.path.isfile(SERIES):
        output.error('No patches in series\n')
    else:
        output.error('No series file found\n')
    return False

# Also remove -R if present.
def change_db_strip_level(level, patch):
    level = '' if level == '-p1' else level
    if os.path.exists(SERIES):
        rec = re.compile(r'^(' + re.escape(patch) + r')(\s+.*)?\n$')
        lines = open(SERIES).readlines()
        for index in range(len(lines)):
            match = rec.match(lines[index])
            if match:
                if not match.group(2):
                    if level:
                        lines[index] = '%s %s\n' % (match.group(1), level)
                    open(SERIES, 'w').writelines(lines)
                    break
                parts = match.group(2).split('#', 1)
                patch_args = parts[0].split()
                if '-R' in patch_args:
                    patch_args.remove('-R')
                changed = False
                for aindex in range(len(patch_args)):
                    if patch_args[aindex].startswith('-p'):
                        patch_args[aindex] = level
                        changed = True
                if not changed and level:
                    patch_args.append(level)
                if len(parts) == 2:
                    patch_args.append('#' + parts[1])
                pa_str = ' '.join(patch_args).strip()
                if pa_str:
                    lines[index] = '%s %s\n' % (match.group(1), pa_str)
                else:
                    lines[index] = '%s\n' % match.group(1)
                open(SERIES, 'w').writelines(lines)
                break
    else:
        return False

def patch_in_series(patch):
    if os.path.isfile(SERIES):
        rec = re.compile(r'^' + re.escape(patch) + r'(\s.*)?$')
        for line in open(SERIES).readlines():
            if rec.match(line):
                return True
    return False

def _canonical_patchname(patchname):
    subdir_part = ('..' + os.sep) * SUBDIR_DOWN
    if subdir_part == patchname[:len(subdir_part)]:
        patchname = patchname[len(subdir_part):]
    qpatches_part = QUILT_PATCHES + os.sep
    if qpatches_part == patchname[:len(qpatches_part)]:
        patchname = patchname[len(qpatches_part):]
    return patchname

def _re_for_finding_patch_in_series(patchname):
    pname_part = re.escape(patchname)
    opextpat = r'((\.(patch|diff?))*(\.(gz|bz2|xz|lzma))*)*'
    return re.compile(r'^(' + re.escape(patchname) + opextpat + r')(\s.*)?$')

def find_patch(patchname):
    if os.path.exists(SERIES):
        if not os.path.isfile(SERIES):
            output.error('%s is not a regular file\n' % SERIES)
            return False
        can_pacthname = _canonical_patchname(patchname)
        matcher = _re_for_finding_patch_in_series(can_pacthname)
        candidates = []
        for line in open(SERIES).readlines():
            reres = matcher.match(line)
            if reres:
                candidates.append(reres.group(1))
        if len(candidates) == 1:
            return candidates[0]
        elif len(candidates) > 1:
            for candidate in candidates:
                # We may have an exact match, which overrides
                # extension expansion.  Otherwise we're confused
                if candidate == can_pacthname:
                    return candidate
            output.error('%s has too many matches in series:\n' % patchname)
            for candidate in candidates:
                 output.error('\t%s\n' % candidate)
            return False
    if find_first_patch():
        output.error('Patch %s is not in series\n' % patchname)
    return False

def cat_series():
    if not os.path.exists(SERIES):
       return []
    ignore_line_cre = re.compile('(^#.*)|(^\s*$)')
    upto_white_space_cre = re.compile('^\s*(\S+).*')
    result = []
    for line in open(SERIES).readlines():
        if ignore_line_cre.match(line):
            continue
        result.append(upto_white_space_cre.match(line).group(1))
    return result

def top_patch():
    if not os.path.isfile(DB):
        return ''
    applied_lines = open(DB).readlines()
    if len(applied_lines):
        return applied_lines[-1].strip()
    return False

def find_top_patch():
    result = top_patch()
    if not result and find_first_patch():
        output.error('No patches applied\n')
    return result

def is_applied(patchname):
    if os.path.isfile(DB):
        for line in open(DB).readlines():
            if line.strip() == patchname:
                return True
    return False

def applied_patches():
    if not os.path.exists(DB):
        return []
    return [line.strip() for line in open(DB).readlines()]

def applied_before(patch):
    patches = applied_patches()
    if not patches:
        return []
    if not patch in patches:
        return patches
    return patches[:patches.index(patch)]

def find_patch_in_series(name=None):
    if name:
        return find_patch(name)
    else:
        return find_top_patch()


def find_applied_patch(patchname=None):
    if patchname:
        patch = find_patch(patchname)
        if patch:
            if not is_applied(patch):
                output.error('Patch %s is not applied\n' % print_patch(patch))
                return False
            return patch
        else:
            return False
    else:
        return find_top_patch()

def _extract_patch_name(line):
    if line[0] == '#':
        return ''
    return line.strip()

def _rename_in_xxxx(from_name, to_name, xxxx):
    tmpfile = os.tmpfile()
    if not tempfile:
        return False
    rec = re.compile(r'^(' + re.escape(from_name) + ').*')
    change_made = False
    for line in open(xxxx).readlines():
        if not change_made and rec.match(line):
            tmpfile.write(re.sub(re.escape(from_name), to_name, line))
            change_made = True
        else:
            tmpfile.write(line)
    if not change_made:
        return False
    try:
        tmpfile.seek(0)
        open(xxxx, 'w').write(tmpfile.read())
        return True
    except IOError:
        return False

def rename_in_series(from_name, to_name):
    return _rename_in_xxxx(from_name, to_name, xxxx=SERIES)

def rename_in_db(from_name, to_name):
    return _rename_in_xxxx(from_name, to_name, xxxx=DB)

def backup_dir_name(patch):
    return os.path.join(QUILT_PC, patch)

def backup_file_name(patch, *args):
    if len(args) == 1:
        return os.path.join(QUILT_PC, patch, args[0])
    return [os.path.join(QUILT_PC, patch, filn) for filn in args]

def _get_series():
    result = []
    if os.path.isfile(SERIES):
        for line in open(SERIES).readlines():
            patch_name = _extract_patch_name(line)
            if patch_name:
                result.append(patch_name)
    return result

def patches_before(patch):
    """Return list of patches in series before the nominated patch"""
    full_series = _get_series()
    if not patch or patch not in full_series:
        return []
    patch_index = full_series.index(patch)
    return full_series[:patch_index]

def patches_after(patch):
    full_series = _get_series()
    if not patch or patch not in full_series:
        return full_series
    patch_index = full_series.index(patch)
    return full_series[patch_index+1:]

def patch_after(patch):
    patches_after_patch = patches_after(patch)
    if patches_after_patch:
        return patches_after_patch[0]
    else:
        return ''

def insert_in_series(patch, patch_args=None, before=None):
    if os.path.exists(SERIES) and not os.path.isfile(SERIES):
        output.error('%s is not a regular file\n' % SERIES)
        sys.exit(cmd_result.ERROR)
    if before is None:
        before = patch_after(top_patch())
    try:
        tmpfile = os.tmpfile()
    except OSError:
        output.error('Unable to create temporary file\n')
        sys.exit(cmd_result.ERROR)
    series_dir = os.path.dirname(SERIES)
    if not os.path.isdir(series_dir):
        try:
            os.mkdir(series_dir)
        except OSError:
            output.error('Could not create directory %s\n' % series_dir)
            sys.exit(cmd_result.ERROR)
    if isinstance(patch_args, str):
        new_line = patch if not patch_args else ' '.join([patch, patch_args])
    else:
        new_line = patch if not patch_args else ' '.join([patch] + patch_args)
    if before:
        rec = re.compile(r'^' + re.escape(before) + r'(\s.*)?$')
        series_lines = open(SERIES).readlines()
        num_lines = len(series_lines)
        index = 0
        while index < num_lines:
            if rec.match(series_lines[index]):
                tmpfile.write('%s\n' % new_line)
                break
            else:
                tmpfile.write(series_lines[index])
                index += 1
        while index < num_lines:
            tmpfile.write(series_lines[index])
            index += 1
    else:
        if os.path.exists(SERIES):
            for line in open(SERIES).readlines():
                tmpfile.write(line)
        tmpfile.write('%s\n' % new_line)
    try:
        tmpfile.seek(0)
        open(SERIES, 'w').write(tmpfile.read())
        return True
    except IOError:
        return False

def remove_from_series(patch):
    rec = re.compile(r'^(' + re.escape(patch) + ').*')
    lines = []
    for line in open(SERIES).readlines():
        if not rec.match(line):
            lines.append(line)
    try:
        open(SERIES, 'w').writelines(lines)
        return True
    except IOError:
        return False

def patches_on_top_of(patch):
    seen = False
    patches = []
    for entry in open(DB).readlines():
        if seen:
            patches.append(entry.strip())
        elif entry.strip() == patch:
            seen = True
    return patches

def next_patch_for_file(patch, filnm):
    patches_on_top = patches_on_top_of(patch)
    for patch in patches_on_top:
        if os.path.isfile(backup_file_name(patch, filnm)):
            return patch
    return None

def add_to_db(patch):
    try:
        open(DB, 'a').write('%s\n' % patch)
        return True
    except IOError:
        return False

def remove_from_db(patch):
    rec = re.compile(r'^(' + re.escape(patch) + ').*')
    lines = []
    for line in open(DB).readlines():
        if not rec.match(line):
            lines.append(line)
    try:
        if not lines:
            os.remove(DB)
        else:
            open(DB, 'w').writelines(lines)
        return True
    except IOError:
        return False

def find_patch_file(name):
    """Find the patch file with the given name"""
    if os.path.exists(name) and os.access(name, os.R_OK):
        return name
    output.set_swallow_errors(True)
    patch = find_patch_in_series(name)
    output.set_swallow_errors(False)
    if not patch:
        output.error('Patch %s does not exist\n' % name)
        return False
    return patch_file_name(patch)

def files_in_patch(patch):
    path = os.path.join(QUILT_PC, patch)
    if os.path.isdir(path):
        return sorted(fsutils.files_in_dir(path, exclude_timestamp=True))
    return [] 

def file_in_patch(filename, patch):
    return os.path.isfile(os.path.join(QUILT_PC, patch, filename))

def file_names_in_patch(patch):
    patch_file = patch_file_name(patch)
    if os.path.isfile(patch_file):
        patch_level = patch_strip_level(patch)
        if patch_level == 'ab':
            patch_level = 1
        is_ok, file_names = putils.get_patch_files(patch_file, status=False, strip_level=patch_level)
        if is_ok:
            return file_names
    return []

def files_in_patch_ordered(patch):
    files = []
    files_in_dir = files_in_patch(patch)
    for filename in file_names_in_patch(patch):
        if filename in files_in_dir:
            files.append(filename)
            files_in_dir.remove(filename)
    return files + sorted(files_in_dir)

def patch_args(patch):
    if os.path.isfile(SERIES):
        rec = re.compile(r'^' + re.escape(patch) + r'(\s+.*)\n$')
        for line in open(SERIES).readlines():
            match = rec.match(line)
            if match:
                p_seen = False
                args = []
                for arg in match.group(1).split('#')[0].split():
                    args.append(arg)
                    if arg[:2] == '-p':
                        p_seen = True
                if not p_seen:
                    args.append('-p1')
                return args
    return ['-p1']

def patch_strip_level(patch):
    for arg in patch_args(patch):
        if arg[:2] == '-p':
            return arg[2:]
    return '1'

def patch_header(patch_filnm):
    return putils.get_patch_descr(patch_filnm)

def first_modified_by(filename, patches):
    if not patches:
        patches = applied_patches()
    for patch in patches:
        if os.path.isfile(os.path.join(QUILT_PC, patch, filename)):
            return patch
    return None

def apply_patch_temporarily(workdir, patch, files=None):
    patch_file = patch_file_name(patch)
    args = patch_args(patch)
    srcdir = os.path.join(QUILT_PC, patch)
    if not backup.restore(srcdir, to_dir=workdir, filelist=files, keep=True):
        output.error('Failed to copy files to temporary directory\n')
        return False
    if os.path.isfile(patch_file) and os.path.getsize(patch_file) > 0:
        text = fsutils.get_file_contents(patch_file)
        result = putils.apply_patch(indir=workdir, patch_args=' '.join(args) + ' --no-backup-if-mismatch -Ef', patch_file=patch_file)
        if result.eflags != 0:
            # Generating a relative diff for a subset of files in
            # the patch will fail. Also, if a patch was force
            # applied, we know that it won't apply cleanly. In
            # all other cases, print a warning.
            if not os.path.isfile(os.path.join(QUILT_PC, patch + '~refresh')) and len(files) == 0:
                output.error('Failed to patch temporary files\n')
                return False
    return True

_SUFFIX_MATCHER = re.compile('.*(\.gz|\.bz2|\.xz|\.lzma|\.diff?|\.patch)$')
_SUFFIX_NUM_MATCHER = re.compile('.*(-\d+)$')

def next_filename(patch):
    match = _SUFFIX_MATCHER.match(patch)
    if match:
        suffix = match.group(1)
        base = patch[:-len(suffix)]
    else:
        suffix = ''
        base = patch
    match = _SUFFIX_NUM_MATCHER.match(base)
    if match:
        num = match.group(1)
        return base[:-len(num)] + str(int(num) - 1) + suffix
    else:
        return base + '-2' + suffix

def find_unapplied_patch(name=None):
    if name is not None:
        patch = find_patch(name)
        if not patch:
            return False
        if is_applied(patch):
            output.write('Patch %s is currently applied\n' % print_patch(patch))
            return False
        return patch
    else:
        start = top_patch()
        if not start:
            return find_first_patch()
        patch = patch_after(start)
        if not patch:
            output.write('File series fully applied, ends at patch %s\n' % print_patch(start))
            return False
        return patch

def top_patch_needs_refresh():
    top = top_patch()
    return top and os.path.exists(os.path.join(QUILT_PC, top + '~refresh'))

def print_top_patch():
    top = top_patch()
    if top:
        return print_patch(top)
    else:
        return ''

def in_valid_dir(filename):
    '''Is (relative) filename in a valid directory?'''
    dirpath = os.path.dirname(filename)
    while dirpath:
        for invalid_dir in [QUILT_PATCHES, QUILT_PC]:
            if os.path.samefile(dirpath, invalid_dir):
                output.error('File %s is located below %s\n' % (filename, invalid_dir + os.sep))
                return False
        dirpath = os.path.dirname(dirpath)
    return True

def filename_rel_base(filename):
    if SUBDIR:
        return os.path.join(SUBDIR, filename)
    return filename
