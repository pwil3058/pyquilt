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
    'rename',
    description='Rename the topmost or named patch.',
)

parser.add_argument(
    '-P',
    help='Patch to rename',
    metavar='patch',
    dest='opt_patch',
)

parser.add_argument(
    'new_name',
    help='new name for the patch'
)

def move_file(old_name, new_name):
    newdir = os.path.dirname(new_name)
    if not os.path.isdir(newdir):
        try:
            os.makedirs(newdir)
        except OSError:
            return False
    os.rename(old_name, new_name)
    try:
        os.removedirs(os.path.dirname(old_name))
    except OSError:
        pass
    return True

def run_rename(args):
    patchfns.chdir_to_base_dir()
    patch = patchfns.find_patch_in_series(args.opt_patch)
    if not patch:
        return cmd_result.ERROR
    new_patch = patchfns.patch_name_base(args.new_name)
    new_patch_exists = patchfns.patch_in_series(new_patch)
    new_patch_exists = True if new_patch_exists else os.path.isdir(os.path.join(patchfns.QUILT_PC, new_patch))
    new_patch_exists = True if new_patch_exists else os.path.exists(patchfns.patch_file_name(new_patch))
    if new_patch_exists:
        output.error('Patch %s exists already, please choose a different name\n' % patchfns.print_patch(new_patch))
        return cmd_result.ERROR
    is_ok = True
    if patchfns.is_applied(patch):
        is_ok = patchfns.rename_in_db(patch, new_patch)
        if is_ok:
            is_ok = move_file(os.path.join(patchfns.QUILT_PC, patch), os.path.join(patchfns.QUILT_PC, new_patch))
    if is_ok:
        is_ok = patchfns.rename_in_series(patch, new_patch)
        if is_ok and os.path.exists(patchfns.patch_file_name(patch)):
            is_ok = move_file(patchfns.patch_file_name(patch), patchfns.patch_file_name(new_patch))
    if is_ok:
        output.write('Patch %s renamed to %s\n' % (patchfns.print_patch(patch), patchfns.print_patch(new_patch)))
        return cmd_result.OK
    else:
        output.error('Renaming of patch %s to %s failed\n' % (patchfns.print_patch(patch), patchfns.print_patch(new_patch)))
        return cmd_result.ERROR

parser.set_defaults(run_cmd=run_rename)
