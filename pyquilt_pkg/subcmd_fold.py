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
import sys
import shutil

from pyquilt_pkg import cmd_line
from pyquilt_pkg import cmd_result
from pyquilt_pkg import patchfns
from pyquilt_pkg import customization
from pyquilt_pkg import output
from pyquilt_pkg import putils
from pyquilt_pkg import fsutils

parser = cmd_line.SUB_CMD_PARSER.add_parser(
    'fold',
    description='''Integrate the patch read from standard input into
        the topmost patch: After making sure that all files modified
        are part of the topmost patch, the patch is applied with the
        specified strip level (which defaults to 1).''',
)

parser.add_argument(
    '-R',
    help='Apply patch in reverse.',
    dest='opt_reverse',
    action='store_true',
)

parser.add_argument(
    '-q',
    help='Quiet operation.',
    dest='opt_quiet',
    action='store_true',
)

parser.add_argument(
    '-f',
    help='''Force apply, even if the patch has rejects. Unless in quiet
        mode, apply the patch interactively: the patch utility may ask
        questions.''',
    dest='opt_force',
    action='store_true',
)

parser.add_argument(
    '-p',
    help='''The number of pathname components to strip from file names
        when applying patchfile.''',
    dest='opt_strip_level',
    metavar='strip-level',
    choices=('0', '1',),
    default='1'
)

def run_fold(args):
    patchfns.chdir_to_base_dir()
    if not args.opt_strip_level:
        args.opt_strip_level = '1'
    opt_patch_args = '' if not args.opt_quiet else ' -s'
    if not args.opt_force or args.opt_quiet:
        opt_patch_args += ' -f'
    if args.opt_reverse:
        opt_patch_args += ' -R'
    top = patchfns.find_top_patch()
    if not top:
        return cmd_result.ERROR
    failed = suggest_force = False
    try:
        workdir = patchfns.gen_tempfile(template=os.getcwd(), asdir=True)
        if patchfns.SUBDIR:
            subdir = patchfns.SUBDIR
            prefix = os.path.join(workdir, patchfns.SUBDIR) + os.sep
        else:
            subdir = '.'
            prefix = workdir + os.sep
        patch_args = '-p%s --backup --prefix="%s" -E %s' % (args.opt_strip_level, prefix, opt_patch_args)
        patch_text = sys.stdin.read()
        result = putils.apply_patch_text(patch_text, indir=subdir, patch_args=patch_args)
        output.write(result.stdout)
        output.error(result.stderr)
        if result.eflags != 0 and not args.opt_force:
            suggest_force = True
            failed = True
        if not failed:
            for filename in fsutils.files_in_dir(workdir):
                backup_file = patchfns.backup_file_name(top, filename)
                if not os.path.exists(backup_file):
                    try:
                        backup_file_dir = os.path.dirname(backup_file)
                        if backup_file_dir and not os.path.exists(backup_file_dir):
                            os.makedirs(backup_file_dir)
                        os.link(os.path.join(workdir, filename), backup_file)
                    except OSError as edata:
                        failed = True
                        break
    except KeyboardInterrupt:
        failed = True
    if failed:
        for filename in fsutils.files_in_dir(workdir):
            try:
                shutil.move(os.path.join(workdir, filename), filename)
            except OSError:
                output.error('File %s may be corrupted\n' % filename)
    if os.path.exists(workdir):
        shutil.rmtree(workdir)
    return cmd_result.OK if not failed else cmd_result.ERROR_SUGGEST_FORCE if suggest_force else cmd_result.ERROR

parser.set_defaults(run_cmd=run_fold)
