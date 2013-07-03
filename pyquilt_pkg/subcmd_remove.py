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

import os

from pyquilt_pkg import cmd_line
from pyquilt_pkg import cmd_result
from pyquilt_pkg import patchfns
from pyquilt_pkg import customization
from pyquilt_pkg import output
from pyquilt_pkg import backup
from pyquilt_pkg import fsutils

parser = cmd_line.SUB_CMD_PARSER.add_parser(
    'remove',
    description='''Remove one or more files from the topmost or named
        patch.  Files that  are modified by patches on top of the
        specified patch cannot be removed.''',
)

parser.add_argument(
    '-P',
    help='Remove named files from the named patch.',
    dest='opt_patch',
    metavar='patch',
)

parser.add_argument(
    'file_list',
    help='File(s) to be removed.',
    metavar='file',
    nargs='+',
)

def run_remove(args):
    patchfns.chdir_to_base_dir()
    patch = patchfns.find_applied_patch(args.opt_patch)
    if not patch:
        return cmd_result.ERROR
    prpatch = patchfns.print_patch(patch)
    patchfn = patchfns.patch_file_name(patch)
    patchrefrfile = os.path.join(patchfns.QUILT_PC, patch + '~refresh')
    patchrefrdir = os.path.dirname(patchrefrfile)
    budir = patchfns.backup_dir_name(patch)
    is_ok = True
    for filename in args.file_list:
        if patchfns.SUBDIR:
            filename = os.path.join(patchfns.SUBDIR, filename)
        if not patchfns.file_in_patch(filename, patch):
            output.error('File %s is not in patch %s\n' % (filename, prpatch))
            is_ok = False
            continue
        next_patch = patchfns.next_patch_for_file(patch, filename)
        if next_patch:
            output.error('File %s modified by patch %s\n' % (filename, patchfns.print_patch(next_patch)))
            is_ok = False
            continue
        # Restore file from backup
        if not backup.restore(budir, filelist=[filename], touch=True):
            output.error('Failed to remove file %s from patch %s\n' % (filename, prpatch))
            is_ok = False
            continue
        if os.path.exists(patchrefrdir) and os.path.exists(patchfn):
            fsutils.touch(patchrefrfile)
        output.write('File %s removed from patch %s\n' % (filename, prpatch))
    return cmd_result.OK if is_ok else cmd_result.ERROR

parser.set_defaults(run_cmd=run_remove)
