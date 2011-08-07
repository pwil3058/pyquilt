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

from pyquilt_pkg import cmd_line
from pyquilt_pkg import cmd_result
from pyquilt_pkg import patchfns
from pyquilt_pkg import customization
from pyquilt_pkg import output

parser = cmd_line.SUB_CMD_PARSER.add_parser(
    'unapplied',
    description='''Print a list of patches that are not applied, or
        all patches that follow the specified patch in the series
        file.''',
)

parser.add_argument(
    'arg_patch',
    help='the (optional) specified patch.',
    metavar='patch',
    nargs='?',
)

def run_unapplied(args):
    patchfns.chdir_to_base_dir()
    if args.arg_patch:
        start = patchfns.find_patch_in_series(args.arg_patch)
        if not start:
            return cmd_result.ERROR
        patch = patchfns.patch_after(start)
    else:
        patch = patchfns.find_unapplied_patch()
    if not patch:
        return cmd_result.OK
    output.start_pager()
    patches = [patch] + patchfns.patches_after(patch)
    for patch in patches:
        output.write('%s\n' % patchfns.print_patch(patch))
    output.wait_for_pager()
    return cmd_result.OK

parser.set_defaults(run_cmd=run_unapplied)
