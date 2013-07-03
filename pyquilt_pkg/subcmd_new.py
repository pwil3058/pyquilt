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
### Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA

import os

from pyquilt_pkg import cmd_line
from pyquilt_pkg import cmd_result
from pyquilt_pkg import patchfns
from pyquilt_pkg import output

parser = cmd_line.SUB_CMD_PARSER.add_parser(
    'new',
    description='Create a new patch with the specified file name, and insert it after the topmost patch',
    epilog='''"%(prog)s" can be used in sub-directories of a source tree.
    It determines the root of a source tree by searching directories above the
    current working directory until it finds a valid root.
    If a valid root is not found "pyquilt setup" will be run in the
    current working directory.'''
)

parser.add_argument(
    'patchname',
    help='name to be used for the new patch'
)

def run_new(args):
    patchfns.chdir_to_base_dir()
    patch = patchfns.patch_name_base(args.patchname)
    if patchfns.patch_in_series(patch):
        output.error('Patch "%s" exists already\n' % patchfns.print_patch(patch))
        return cmd_result.ERROR | cmd_result.SUGGEST_RENAME
    patchfns.create_db()
    if not patchfns.insert_in_series(patch) or not patchfns.add_to_db(patch):
        output.error('Failed to create patch %s\n' % patchfns.print_patch(patch))
        return cmd_result.ERROR
    else:
        output.write('Patch %s is now on top\n' % patchfns.print_patch(patch))
        return cmd_result.OK

parser.set_defaults(run_cmd=run_new)
