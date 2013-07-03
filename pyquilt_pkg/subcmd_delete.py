### Copyright (C) 2011 Peter Williams <peter_ono@users.sourceforge.net>
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
    'delete',
    description='Remove the specified or topmost patch from the series file.',
    epilog='''If thepatch is applied, quilt will attempt to remove it
           first. (Only the topmost patch can be removed right now.)'''
)

parser.add_argument(
    '-n',
    help='Delete the next patch after topmost, rather than the specified or topmost patch.',
    dest='opt_next',
    action='store_true',
)

parser.add_argument(
    '-r',
    help='Remove the deleted patch file from the patches directory as well.',
    dest='opt_remove',
    action='store_true',
)

parser.add_argument(
    '--backup',
    help='Rename the patch file to patch~ rather than deleting it. Ignored if not used with `-r\'.',
    dest='opt_backup',
    action='store_true',
)

parser.add_argument(
    'patch',
    help='name of the patch to delete',
    nargs='?',
)

def run_delete(args):
    patchfns.chdir_to_base_dir()
    if args.patch:
        patch = patchfns.find_patch(args.patch)
        if not patch:
            return cmd_result.ERROR
    else:
        patch = patchfns.top_patch()
    if args.opt_next:
        patch =patchfns.patch_after(patch)
        if not patch:
            output.error('No next patch\n')
            return cmd_result.ERROR
    if not patch:
        patchfns.find_top_patch()
        return cmd_result.ERROR
    if patchfns.is_applied(patch):
        if patch != patchfns.top_patch():
            output.error('Patch %s is currently applied\n' % patchfns.print_patch(patch))
            return cmd_result.ERROR
        if patchfns.pyquilt_command('pop -qf') != cmd_result.OK:
            return cmd_result.ERROR
    if patchfns.remove_from_series(patch):
        output.write('Removed patch %s\n' % patchfns.print_patch(patch))
    else:
        output.error('Failed to remove patch %s\n' % patchfns.print_patch(patch))
        return cmd_result.ERROR
    patch_file = patchfns.patch_file_name(patch)
    if args.opt_remove and os.path.exists(patch_file):
        if args.opt_backup:
            try:
                os.rename(patch_file, patch_file + '~')
            except IOError:
                output.error('Failed to backup patch file %s\n' % patch_file)
                return cmd_result.ERROR
        else:
            try:
                os.remove(patch_file)
            except IOError:
                output.error('Failed to remove patch file %s\n' % patch_file)
                return cmd_result.ERROR
    return cmd_result.OK

parser.set_defaults(run_cmd=run_delete)
