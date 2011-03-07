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
### Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA

import os
import shutil

from pyquilt_pkg import cmd_line
from pyquilt_pkg import cmd_result
from pyquilt_pkg import patchfns
from pyquilt_pkg import customization
from pyquilt_pkg import diff
from pyquilt_pkg import putils
from pyquilt_pkg import fsutils
from pyquilt_pkg import shell
from pyquilt_pkg import output

parser = cmd_line.SUB_CMD_PARSER.add_parser(
    'refresh',
    description='''
        Refreshes the specified patch, or the topmost patch by default.
        Documentation that comes before the actual patch in the patch file is
        retained.''',
    epilog='''
        It is possible to refresh patches that are not on top.  If any patches
        on top of the patch to refresh modify the same files, the script aborts
        by default.  Patches can still be refreshed with -f.  In that case this
        script will print a warning for each shadowed file, changes by more
        recent patches will be ignored, and only changes in files that have not
        been modified by any more recent patches will end up in the specified
        patch.''',
)

parser.add_argument(
    'patchname',
    help='(optional) name of the patch to be refreshed',
    default=None,
    nargs='?',
    metavar='patch'
)

parser.add_argument(
    '-p',
    help='''Create a -p n style patch if 0 or 1. Else,
    create a -p1 style patch, but use a/file and b/file as the
    original and new filenames instead of the default
    dir.orig/file and dir/file names.''',
    choices=('0', '1', 'ab'),
    dest='opt_strip_level',
)

import argparse
class FormatAction(argparse.Action):
    def __call__(self, parser, namespace, values, option_string=None):
        setattr(namespace, self.dest, ' %s %d' % (option_string, values))

format_group = parser.add_mutually_exclusive_group()
format_group.add_argument(
    '-U',
    help='Create a unified diff with num lines of context.',
    dest='opt_format',
    type=int,
    metavar='num',
    action=FormatAction,
)

format_group.add_argument(
    '-u',
    help='Create a unified diff with the default number of context lines.',
    dest='opt_format',
    const=' -u',
    action='store_const',
)

format_group.add_argument(
    '-C',
    help='Create a context diff with num lines of context.',
    dest='opt_format',
    type=int,
    metavar='num',
    action=FormatAction,
)

format_group.add_argument(
    '-c',
    help='Create a context diff with the default number of context lines.',
    dest='opt_format',
    const=' -c',
    action='store_const',
)

parser.add_argument(
    '-z',
    help='''
    Create a new patch containing the changes instead of refreshing the
    topmost patch. If no new name is specified, \`-2' is added to the
    original patch name, etc. (See the fork command.)
    ''',
    nargs='?',
    dest='opt_new_name',
    const=True,
)

parser.add_argument(
    '--no-timestamps',
    help='Do not include file timestamps in patch headers.',
    dest='opt_no_timestamps',
    action='store_true',
)

parser.add_argument(
    '--no-index',
    help='Do not output Index: lines.',
    dest='opt_no_index',
    action='store_true',
)

parser.add_argument(
    '--diffstat',
    help='''Add a diffstat section to the patch header, or replace the
    existing diffstat section.''',
    dest='opt_diffstat',
    action='store_true',
)

parser.add_argument(
    '-f',
    help='Enforce refreshing of a patch that is not on top.',
    dest='opt_force',
    action='store_true',
)

parser.add_argument(
    '--backup',
    help='Create a backup copy of the old version of a patch as patch~.',
    dest='opt_backup',
    action='store_true',
)

parser.add_argument(
    '--sort',
    help='Sort files by their name instead of preserving the original order.',
    dest='opt_sort',
    action='store_true',
)

parser.add_argument(
    '--strip-trailing-whitespace',
    help='Strip trailing whitespace at the end of lines.',
    dest='opt_strip_trailing_whitespace',
    action='store_true',
)

def run_refresh(args):
    workdir = None
    def clean_up(status):
        if workdir and os.path.isdir(workdir):
            shutil.rmtree(workdir)
        return status
    patchfns.chdir_to_base_dir()
    patch = patchfns.find_applied_patch(args.patchname)
    if not patch:
        return cmd_result.ERROR
    if args.opt_sort:
        files = patchfns.files_in_patch_ordered(patch)
    else:
        files = patchfns.files_in_patch(patch)
    if args.opt_new_name:
        if args.patchname:
            output.error('Can only refresh the topmost patch with -z currently\n')
            return cmd_result.ERROR
        old_patch = patch
        old_patch_args = patchfns.patch_args(old_patch)
        if args.opt_new_name is True:
            patch = patchfns.next_filename(patch)
        else:
            patch = args.opt_new_name
        if os.path.exists(patchfns.patch_file_name(patch)):
            output.error('Patch %s exists already\n' % patchfns.print_patch(patch))
            return cmd_result.ERROR
    if args.opt_strip_level is None:
        args.opt_strip_level = patchfns.patch_strip_level(patch)
    if args.opt_strip_level in ['0', '1']:
        num_strip_level = args.opt_strip_level
    elif args.opt_strip_level == 'ab':
        num_strip_level = '1'
    else:
        output.error('Cannot refresh patches with -p%s, please specify -p0 or -p1 instead\n' % args.opt_strip_level)
        return cmd_result.ERROR
    if args.opt_new_name:
        workdir = patchfns.gen_tempfile(asdir=True, template=os.path.join(os.getcwd(), 'quilt'))
        if not patchfns.apply_patch_temporarily(workdir, old_patch):
            return clean_up(cmd_result.ERROR)
    patch_content = ''
    files_were_shadowed = False
    for filn in files:
        if args.opt_new_name:
            old_file = os.path.join(workdir, filn)
            new_file = filn
        else:
            old_file = patchfns.backup_file_name(patch, filn)
            next_patch = patchfns.next_patch_for_file(patch, filn)
            if not next_patch:
                new_file = filn
            else:
                new_file = patchfns.backup_file_name(next_patch, filn)
                files_were_shadowed = True
        result = diff.diff_file(filn, old_file, new_file, args)
        if result.eflags > 1:
            output.error('\n'.join(result.stderr, 'Diff failed, aborting\n'))
            return clean_up(cmd_result.ERROR)
        elif result.eflags == 0 or not result.stdout:
            continue
        else:
            patch_content += result.stdout
    if not patch_content:
        output.error('Nothing in patch %s\n' % patchfns.print_patch(patch))
        return clean_up(cmd_result.ERROR)
    if files_were_shadowed:
        if not args.opt_force:
            output.error('More recent patches modify files in patch %s. Enforce refresh with -f.\n' % patchfns.print_patch(patch))
            return clean_up(cmd_result.ERROR_SUGGEST_FORCE)
        if args.opt_strip_trailing_whitespace:
            output.error('Cannot use --strip-trailing-whitespace on a patch that has shadowed files.\n')
    if args.opt_strip_trailing_whitespace and not files_were_shadowed:
        result = putils.remove_trailing_ws(patch_content, num_strip_level)
        if result.eflags == cmd_result.OK:
            patch_content = result.stdout
        if result.stderr:
            output.error(result.stderr)
    else:
        result = putils.remove_trailing_ws(patch_content, num_strip_level, dry_run=True)
        if result.stderr:
            output.error('\n'.join(result[1:]))
    patch_file = patchfns.patch_file_name(patch)
    prev_patch_file = patch_file if os.path.isfile(patch_file) else '/dev/null'
    result_content = patchfns.patch_header(prev_patch_file)
    if args.opt_diffstat:
        diffstat = shell.get_diffstat(patch_content, num_strip_level)
        result_content += diffstat
    result_content += patch_content
    patch_file_dir = os.path.dirname(patch_file)
    if not os.path.exists(patch_file_dir):
        os.makedirs(patch_file_dir)
    is_ok = True
    QUILT_PC = customization.get_config('QUILT_PC')
    if fsutils.file_contents_equal(patch_file, result_content):
        output.write('Patch %s is unchanged\n' % patchfns.print_patch(patch))
    else:
        if args.opt_backup and os.path.isfile(patch_file):
            try:
                os.rename(patch_file, patch_file + '~')
            except OSError:
                output.error('Failed to create backup %s\n' % patch_file + '~')
                is_ok = False
        if is_ok:
            is_ok = fsutils.set_file_contents(patch_file, result_content)
        if is_ok and args.opt_new_name:
            insert_ok = patchfns.insert_in_series(patch, old_patch_args)
            if not insert_ok:
                output.error('Failed to insert patch %s into file series\n' % patchfns.print_patch(patch))
                return clean_up(cmd_result.ERROR)
            try:
                patch_dir = os.path.join(QUILT_PC, patch)
                if os.path.exists(patch_dir):
                    shutil.rmtree(patch_dir)
                os.rename(workdir, patch_dir)
                open(patchfns.DB, 'a').write(patch + '\n')
            except:
                output.error('Failed to create patch %s\n' % patchfns.print_patch(patch))
                return clean_up(cmd_result.ERROR)
            output.write('Fork of patch %s created as %s\n' % (patchfns.print_patch(old_patch), patchfns.print_patch(patch)))
        elif is_ok:
            output.write('Refreshed patch %s\n' % patchfns.print_patch(patch))
        fsutils.touch(os.path.join(QUILT_PC, patch, '.timestamp'))
    if is_ok:
        tagf = os.path.join(QUILT_PC, patch + '~refresh')
        if os.path.exists(tagf):
            os.remove(tagf)
        is_ok = patchfns.change_db_strip_level('-p%s' % num_strip_level, patch)
    return clean_up(cmd_result.OK if is_ok else cmd_result.ERROR)

parser.set_defaults(run_cmd=run_refresh)
