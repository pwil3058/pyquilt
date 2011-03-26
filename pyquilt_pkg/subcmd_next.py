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
### Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA

from pyquilt_pkg import cmd_line
from pyquilt_pkg import cmd_result
from pyquilt_pkg import patchfns
from pyquilt_pkg import customization
from pyquilt_pkg import output

parser = cmd_line.SUB_CMD_PARSER.add_parser(
    'next',
    description='''Print the name of the next patch after the
        specified or topmost patch in the series file.''',
)

parser.add_argument(
    'arg_patch',
    help='the (optional) specified patch.',
    metavar='patch',
    nargs='?',
)

def run_next(args):
    patchfns.chdir_to_base_dir()
    nextpatch = patchfns.find_unapplied_patch(args.arg_patch)
    if not nextpatch:
        return cmd_result.ERROR
    output.write('%s\n' % patchfns.print_patch(nextpatch))
    return cmd_result.OK

parser.set_defaults(run_cmd=run_next)
