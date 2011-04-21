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

import os.path
import tempfile

from pyquilt_pkg import shell
from pyquilt_pkg import fsutils
from pyquilt_pkg import cmd_result
from pyquilt_pkg import patchlib

def get_patch_descr_fm_text(text):
    obj = patchlib.parse_text(text)
    return obj.get_description()

def get_patch_descr(path):
    try:
        buf = fsutils.get_file_contents(path)
    except IOError:
        return ''
    return get_patch_descr_fm_text(buf)

def get_patch_hdr_fm_text(text, omit_diffstat=False):
    obj = patchlib.parse_text(text)
    if omit_diffstat:
        obj.set_diffstat('')
    return obj.get_header()

def get_patch_hdr(path, omit_diffstat=False):
    try:
        buf = fsutils.get_file_contents(path)
    except IOError:
        return ''
    return get_patch_hdr_fm_text(buf, omit_diffstat)

def get_patch_diff_fm_text(text, file_list=None, strip_level=0):
    obj = patchlib.parse_text(text)
    if not file_list:
        return ''.join([x.get_as_string() for x in obj.file_patches])
    else:
        num_strip_level = int(strip_level)
        return ''.join([x.get_as_string() for x in obj.file_patches if x.get_file_path(num_strip_level) in file_list])

def get_patch_diff(path, file_list=None, strip_level=0):
    return get_patch_diff_fm_text(fsutils.get_file_contents(path), file_list, strip_level)

def _write_via_temp(path, text):
    tmpdir = os.path.dirname(path)
    _dummy, suffix = os.path.splitext(path)
    try:
        fd, tmpf_name = tempfile.mkstemp(dir=tmpdir,suffix=suffix)
        os.close(fd)
        fsutils.set_file_contents(tmpf_name, text)
    except IOError:
        if tmpf_name is not None and os.path.exists(tmpf_name):
            os.remove(tmpf_name)
        return False
    try:
        os.rename(tmpf_name, path)
        return True
    except IOError:
        if os.path.exists(tmpf_name):
            os.remove(tmpf_name)
        return False

def set_patch_descr(path, text):
    if os.path.exists(path):
        patch_obj = patchlib.parse_text(fsutils.get_file_contents(path))
    else:
        patch_obj = patchlib.Patch()
    patch_obj.set_description(text)
    return _write_via_temp(path, patch_obj.get_as_string())

def set_patch_hdr(path, text, omit_diffstat=False):
    if os.path.exists(path):
        patch_obj = patchlib.parse_text(fsutils.get_file_contents(path))
    else:
        patch_obj = patchlib.Patch()
    if omit_diffstat:
        dummy = patchlib.parse_text(text)
        dummy.set_diffstat('')
        text = dummy.get_header()
    patch_obj.set_header(text)
    return _write_via_temp(path, patch_obj.get_as_string())

def get_patch_files(path, strip_level=1):
    try:
        buf = fsutils.get_file_contents(path)
    except IOError:
        return (False, 'Problem(s) open file "%s" not found' % path)
    obj = patchlib.parse_text(buf)
    return obj.get_file_paths(int(strip_level))

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
    obj = patchlib.parse_text(text)
    report = obj.fix_trailing_whitespace(int(strip_level))
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
