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

import sys

from pyquilt_pkg import cmd_line
from pyquilt_pkg import cmd_result
from pyquilt_pkg import patchfns
from pyquilt_pkg import customization
from pyquilt_pkg import output

parser = cmd_line.SUB_CMD_PARSER.add_parser(
    'applied',
    description='''Print a list of applied patches, or all patches
        up to and including the specified patch in the file series.''',
)

parser.add_argument(
    'patch',
    help='end patch.',
    nargs='?'
)

def run_applied(args):
    patchfns.chdir_to_base_dir()
    patch = patchfns.find_applied_patch(args.patch)
    if not patch:
        return cmd_result.ERROR
    output.start_pager()
    for patch in patchfns.applied_before(patch) + [patch]:
        output.write('%s\n' % patchfns.print_patch(patch))
    output.wait_for_pager()
    return cmd_result.OK

parser.set_defaults(run_cmd=run_applied)
