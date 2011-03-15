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
Run diff program
'''

import os.path
import time
import shell

from pyquilt_pkg import customization

DTFMT = r'%Y-%m-%d %H:%M:%S %z'

def file_mtime_as_string(filnm):
    mtime = time.localtime(os.path.getmtime(filnm))
    return time.strftime(DTFMT, mtime)

def _get_diff_opts(args):
    diff_opts = customization.get_default_opts('diff')
    if args.opt_format is not None:
        return diff_opts + args.opt_format
    return diff_opts + ' -u'

def _get_no_diff_index(args):
    if args.opt_no_index:
        return True
    return customization.get_config('QUILT_NO_DIFF_INDEX', False)

def _get_no_diff_timestamps(args):
    if args.opt_no_timestamps:
        return True
    return customization.get_config('QUILT_NO_DIFF_TIMESTAMPS', False)

def diff_file(filnm, old_file, new_file, args):
    # protect against referencing unset variables
    index = old_hdr = new_hdr = line = None
    new_date = old_date = ''
    opt_strip_level = '1' if args.opt_strip_level is None else args.opt_strip_level
    if opt_strip_level == 'ab':
        old_hdr = os.path.join('a', filnm)
        new_hdr = os.path.join('b', filnm)
    elif opt_strip_level == '0':
        old_hdr = filnm + '.orig'
        new_hdr = filnm
    else:
        dirnm = os.path.basename(os.getcwd())
        old_hdr = os.path.join(dirnm + '.orig', filnm)
        new_hdr = os.path.join(dirnm, filnm)
    index = new_hdr
    use_timestamps = not _get_no_diff_timestamps(args)
    if not os.path.exists(old_file) or os.path.getsize(old_file) == 0:
        old_file = '/dev/null'
        old_hdr = '/dev/null'
        if use_timestamps:
            old_date = '\t1970-01-01 00:00:00.000000000 +0000'
    elif use_timestamps:
        old_date = '\t%s' % file_mtime_as_string(old_file)
    if not os.path.exists(new_file) or os.path.getsize(new_file) == 0:
        if opt_strip_level == '0':
            old_hdr = new_hdr
        new_file = '/dev/null'
        new_hdr = '/dev/null'
        if use_timestamps:
            new_date = '\t1970-01-01 00:00:00.000000000 +0000'
    elif use_timestamps:
        new_date = '\t%s' % file_mtime_as_string(new_file)
    diff_opts = _get_diff_opts(args)
    cmd = 'diff %s --label "%s" --label "%s" "%s" "%s"' % \
        (diff_opts, old_hdr + old_date, new_hdr + new_date, old_file, new_file)
    result = shell.run_cmd(cmd)
    if result.eflags == 1:
        if not _get_no_diff_index(args):
            index_str = 'Index: %s\n%s\n' % (index, '=' * 67)
            result = result._replace(stdout=index_str + result.stdout)
    return result

def same_contents(file1, file2):
    result = shell.run_cmd('diff -q "%s" "%s"' % (file1, file2))
    return result.eflags == 0
