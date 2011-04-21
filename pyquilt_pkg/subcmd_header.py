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

import os
import re
import sys
import shutil

from pyquilt_pkg import cmd_line
from pyquilt_pkg import cmd_result
from pyquilt_pkg import patchfns
from pyquilt_pkg import customization
from pyquilt_pkg import output
from pyquilt_pkg import putils

parser = cmd_line.SUB_CMD_PARSER.add_parser(
    'header',
    description='''Print or change the header of the topmost or specified patch.''',
    epilog='''If none of the options -a, -r or -e is given, print the patch header.''',
)

action_group = parser.add_mutually_exclusive_group()

action_group.add_argument(
    '-a',
    help='Append standard input to the header.',
    dest='opt_append',
    action='store_true',
)

action_group.add_argument(
    '-r',
    help='Replace the header with standard input.',
    dest='opt_replace',
    action='store_true',
)

action_group.add_argument(
    '-e',
    help='Edit the header in $EDITOR (%s).' % os.getenv('EDITOR'),
    dest='opt_edit',
    action='store_true',
)

parser.add_argument(
    '--strip-diffstat',
    help='Strip diffstat output from the header.',
    dest='opt_strip_diffstat',
    action='store_true',
)

parser.add_argument(
    '--strip-trailing-whitespace',
    help='Strip trailing whitespace at the end of lines of the header.',
    dest='opt_strip_trailing_whitespace',
    action='store_true',
)

parser.add_argument(
    '--backup',
    help='Create a backup copy of the old version of a patch as patch~.',
    dest='opt_backup',
    action='store_true',
)

parser.add_argument(
    'arg_patch',
    help='patch whose header is to be processed.',
    metavar='patch',
    nargs='?',
)

def run_header(args):
    def read_input():
        text = sys.stdin.read()
        if args.opt_strip_trailing_whitespace:
            return re.sub('[ \t]+\n]', '\n', text)
        return text
    def get_text(pfile):
        text = putils.get_patch_hdr(pfile, omit_diffstat=args.opt_strip_diffstat)
        if args.opt_strip_trailing_whitespace:
            return re.sub('[ \t]+\n]', '\n', text)
        return text
    def set_text(pfile, text):
        if args.opt_backup:
            try:
                shutil.copy2(pfile, pfile + '~')
            except Exception as edata:
                output.perror(edata)
        putils.set_patch_hdr(pfile, text, omit_diffstat=args.opt_strip_diffstat)
    patchfns.chdir_to_base_dir()
    if not args.opt_backup:
        args.opt_backup = customization.get_config('QUILT_BACKUP')
    patch = patchfns.find_patch_in_series(args.arg_patch)
    if not patch:
        return cmd_result.ERROR
    patch_file = patchfns.patch_file_name(patch)
    if args.opt_replace:
        set_text(patch_file, read_input())
        output.write('Replaced header of patch %s\n' % patchfns.print_patch(patch))
    elif args.opt_append:
        set_text(patch_file, get_text(patch_file) + read_input())
        output.write('Appended text to header of patch %s\n' % patchfns.print_patch(patch))
    elif args.opt_edit:
        savelang = os.getenv('LANG', None)
        os.environ['LANG'] = patchfns.ORIGINAL_LANG
        tempfile = patchfns.gen_tempfile()
        result = shell.run_cmd('%s %s' % (os.getenv('EDITOR'), tempfile))
        if savelang:
            os.environ['LANG'] = savelang
        output.error(result.stderr)
        output.write(result.stdout)
        text = open(tempfile).read()
        os.remove(tempfile)
        if result.eflags != 0:
            return cmd_result.ERROR
        set_text(patch_file, text)
        output.write('Replaced header of patch %s\n' % patchfns.print_patch(patch))
    else:
        if not os.path.exists(patch_file):
            return cmd_result.OK
        output.start_pager()
        output.write(get_text(patch_file))
        output.wait_for_pager()
    return cmd_result.OK

parser.set_defaults(run_cmd=run_header)
