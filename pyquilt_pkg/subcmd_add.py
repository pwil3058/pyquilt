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

import sys
import os

from pyquilt_pkg import cmd_line
from pyquilt_pkg import cmd_result
from pyquilt_pkg import patchfns
from pyquilt_pkg import backup

parser = cmd_line.SUB_CMD_PARSER.add_parser(
    'add',
    description='Add one or more files to the topmost or named patch.',
    epilog='''Files must be
    added to the patch before being modified.  Files that are modified by
    patches already applied on top of the specified patch cannot be added.'''
)

parser.add_argument(
    'filelist',
    help='name(s) of file(s) to be added patch',
    nargs='+',
    metavar='file'
)

parser.add_argument(
    '-P',
    help='Path name prefix for backup files.',
    dest='opt_patch',
    metavar = 'patch',
)

def run_add(args):
    patchfns.chdir_to_base_dir()
    patch = patchfns.find_applied_patch(args.opt_patch)
    if not patch:
        return 1
    patch_dir = os.path.join(patchfns.QUILT_PC, patch)
    status = 0
    for filename in args.filelist:
        filename = patchfns.filename_rel_base(filename)
        if not patchfns.in_valid_dir(filename):
            status = 1
            continue
        if patchfns.file_in_patch(patch, filename):
            sys.stderr.write('File %s is already in patch %s\n' % (filename, patchfns.print_patch(patch)))
            status = 2 if status != 1 else 1
        next_patch = patchfns.next_patch_for_file(patch, filename)
        if next_patch is not None:
            sys.stderr.write('File %s modified by patch %s\n' % (filename, patchfns.print_patch(next_patch)))
            status = 1
            continue
        if os.path.islink(filename):
            sys.stderr.write('Cannot add symbolic link %s\n' % filename)
            status = 1
            continue
        if not backup.backup(patch_dir, [filename]):
            sys.stderr.write('Failed to back up file %s\n' % filename)
            status = 1
            continue
        if os.path.exists(filename):
            # The original tree may be read-only.
            os.chmod(os.stat(filename).st_mode|stat.S_IWUSR)
        sys.stdout.write('File %s added to patch %s\n' % (filename, patchfns.print_patch(patch)))
    return status

parser.set_defaults(run_cmd=run_add)
