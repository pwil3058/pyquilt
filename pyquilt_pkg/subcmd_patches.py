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
from pyquilt_pkg import colour
from pyquilt_pkg import putils

parser = cmd_line.SUB_CMD_PARSER.add_parser(
    'patches',
    description='''Print the list of patches that modify the specified
        file. (Uses a heuristic to determine which files are modified
        by unapplied patches.  Note that this heuristic is much slower
        than scanning applied patches.)''',
)

parser.add_argument(
    '-v',
    help='Verbose, more user friendly output.',
    dest='opt_verbose',
    action='store_true',
)

parser.add_argument(
    '--color',
    help='''Use coloring.''',
    dest='opt_color',
    nargs='?',
    choices=['always', 'auto', 'tty', 'never',],
    const='always'
)

parser.add_argument(
    'filelist',
    help='The file(s) to be analysed.',
    nargs='+',
    metavar='file',
)

def scan_applied(category, prefix, file_paths, patches):
    for patch in patches:
        for file_path in file_paths:
            if os.path.isfile(patchfns.backup_file_name(patch, file_path)):
                output.write(colour.wrap('%s%s\n' % (prefix, patchfns.print_patch(patch)), category))

def scan_unapplied(category, prefix, file_paths, patches):
    for patch in patches:
        strip = patchfns.patch_strip_level(patch)
        pfn = patchfns.patch_file_name(patch)
        patch_files = putils.get_patch_files(pfn, strip_level=strip)
        for file_path in file_paths:
            if file_path in patch_files:
                output.write(colour.wrap('%s%s\n' % (prefix, patchfns.print_patch(patch)), category))

def run_patches(args):
    patchfns.chdir_to_base_dir()
    if args.opt_verbose:
        applied = '+ '
        current = '= '
        unapplied = '  '
    else:
        applied = current = unapplied = ''
    do_colorize = args.opt_color == 'always' or (args.opt_color in ['auto', 'tty'] and sys.stderr.isatty())
    if do_colorize:
        colour.set_up()
    file_paths = [os.path.join(patchfns.SUBDIR, file_path) if patchfns.SUBDIR else file_path for file_path in args.filelist]
    top = patchfns.top_patch()
    output.start_pager()
    if top:
        scan_applied('series_app', applied, file_paths, patchfns.patches_before(top))
        scan_applied('series_top', current, file_paths, (top,))
    scan_unapplied('series_una', unapplied, file_paths, patchfns.patches_after(top))
    output.wait_for_pager()
    return cmd_result.OK

parser.set_defaults(run_cmd=run_patches)
