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
    'top',
    description='''Print the name of the topmost patch on the current
        stack of applied patches.''',
)

def run_top(args):
    patchfns.chdir_to_base_dir()
    top = patchfns.find_top_patch()
    if not top:
        return cmd_result.ERROR
    output.write('%s\n' % patchfns.print_patch(top))
    return cmd_result.OK

parser.set_defaults(run_cmd=run_top)
