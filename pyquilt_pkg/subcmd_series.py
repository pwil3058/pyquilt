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
from pyquilt_pkg import colour

parser = cmd_line.SUB_CMD_PARSER.add_parser(
    'series',
    description='''Print the names of all patches in the series file.''',
)

parser.add_argument(
    '-v',
    help='Verbose, more user friendly output.',
    dest='opt_verbose',
    action='store_true',
)

parser.add_argument(
    '--color',
    help='''Use syntax coloring.''',
    dest='opt_color',
    nargs='?',
    choices=['always', 'auto', 'never',],
    const='always'
)

def run_series(args):
    patchfns.chdir_to_base_dir()
    output.start_pager()
    do_colorize = args.opt_color == 'always' or (args.opt_color == 'auto' and sys.stderr.isatty())
    if do_colorize:
        colour.set_up()
    if do_colorize or args.opt_verbose:
        top = patchfns.top_patch()
        for patch in patchfns.patches_before(top):
            string = '+ %s\n' % patchfns.print_patch(patch)
            output.write(colour.wrap(string, 'series_app') if do_colorize else string)
        if top:
            string = '= %s\n' % patchfns.print_patch(top)
            output.write(colour.wrap(string, 'series_top') if do_colorize else string)
        for patch in patchfns.patches_after(top):
            string = '  %s\n' % patchfns.print_patch(patch)
            output.write(colour.wrap(string, 'series_una') if do_colorize else string)
    else:
        for patch in patchfns.cat_series():
            output.write('%s\n' % patchfns.print_patch(patch))
    output.wait_for_pager()
    return cmd_result.OK

parser.set_defaults(run_cmd=run_series)
