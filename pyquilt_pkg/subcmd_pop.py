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
### Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA

import os
import shutil
import argparse
import re
import errno

from pyquilt_pkg import cmd_line
from pyquilt_pkg import cmd_result
from pyquilt_pkg import patchfns
from pyquilt_pkg import customization
from pyquilt_pkg import diff
from pyquilt_pkg import putils
from pyquilt_pkg import fsutils
from pyquilt_pkg import shell
from pyquilt_pkg import colour
from pyquilt_pkg import backup
from pyquilt_pkg import output

parser = cmd_line.SUB_CMD_PARSER.add_parser(
    'pop',
    description='''
        Remove patch(es) from the stack of applied patches.  Without options,
        the topmost patch is removed.  When a number is specified, remove the
        specified number of patches.  When a patch name is specified, remove
        patches until the specified patch end up on top of the stack.''',
    epilog='''
        Patchnames may include the patches/ prefix, which means that filename
        completion can be used.''',
)

what_parser = parser.add_mutually_exclusive_group()
what_parser.add_argument(
    'patchnamornum',
    help='(optional) name/number of the patch(es) to be popped',
    default=None,
    nargs='?',
    metavar='patch|num'
)

what_parser.add_argument(
    '-a',
    help='''Remove all patches.''',
    dest='opt_all',
    action='store_true',
)

parser.add_argument(
    '-f',
    help='''
    Force remove. The state before the patch(es) were applied will
    be restored from backup files.
    ''',
    dest='opt_force',
    action='store_true',
)

parser.add_argument(
    '-R',
    help='''
    Always verify if the patch removes cleanly; don't rely on
    timestamp checks.
    ''',
    dest='opt_remove',
    action='store_true',
)

parser.add_argument(
    '-q',
    help='''Quiet operation.''',
    dest='opt_quiet',
    action='store_true',
)

parser.add_argument(
    '-v',
    help='''Verbose operation.''',
    dest='opt_verbose',
    action='store_true',
)

def list_patches(number=None, stop_at_patch=None):
    patches = patchfns.applied_patches()
    patches.reverse()
    if stop_at_patch is not None:
        number = patches.index(stop_at_patch) + 1
    if number is not None and number < len(patches):
        return patches[:number]
    return patches

def files_may_have_changed(patch):
    patch_file = patchfns.patch_file_name(patch)
    if not patch_file or not os.path.exists(patch_file):
        return True
    tsf = os.path.join(patchfns.QUILT_PC, patch, '.timestamp')
    if os.path.exists(tsf):
        tsf_mt = os.path.getmtime(tsf)
    else:
        return True
    if tsf_mt < os.path.getmtime(patch_file):
        return True
    for file_nm in patchfns.files_in_patch(patch):
        if os.path.exists(file_nm) and tsf_mt < os.path.getmtime(file_nm):
            return True
    return False

def check_for_pending_changes(patch):
    patch_file = patchfns.patch_file_name(patch)
    workdir = patchfns.gen_tempfile(template='quilt', asdir=True)
    patchdir = os.path.join(patchfns.QUILT_PC, patch)
    if os.path.isdir(patchdir):
        prefix = os.path.abspath(patchdir)
        if not backup.restore(prefix, to_dir=workdir, keep=True):
            output.error('Failed to copy files to temporary directory\n')
            shutil.rmtree(workdir)
            return False
    if os.path.exists(patch_file) and os.path.getsize(patch_file) > 0:
        patch_args = '%s --no-backup-if-mismatch -E' % ' '.join(patchfns.patch_args(patch))
        result = putils.apply_patch(patch_file, indir=workdir, patch_args=patch_args)
        if result.eflags != 0 and not os.path.exists(patchdir):
            output.write(result.stdout)
            output.error('Failed to patch temporary files\n')
            shutil.rmtree(workdir)
            return False
    failed = False
    for file_nm in patchfns.files_in_patch(patch):
        wfile_nm = os.path.join(workdir, file_nm)
        if not os.path.exists(file_nm):
            if os.path.exists(wfile_nm):
                failed = True
                break
            else:
                continue
        elif not os.path.exists(wfile_nm):
            failed = True
            break
        if not diff.same_contents(file_nm, wfile_nm):
            failed = True
            break
    shutil.rmtree(workdir)
    if failed:
        output.error('Patch %s does not remove cleanly (refresh it or enforce with -f)\n' % patchfns.print_patch(patch))
        return cmd_result.ERROR_SUGGEST_FORCE
    return True

def remove_patch(patch, force, check, silent):
    try:
        status = True
        if not force and (check or files_may_have_changed(patch)):
            status = check_for_pending_changes(patch)
        if status is True:
            patchdir = os.path.join(patchfns.QUILT_PC, patch)
            try:
                os.remove(os.path.join(patchdir, '.timestamp'))
            except OSError:
                pass
            if not os.path.exists(patchdir) or not os.listdir(patchdir):
                output.write('Patch %s appears to be empty, removing\n' % patchfns.print_patch(patch))
                try:
                    os.rmdir(patchdir)
                except OSError as edata:
                    if edata.errno != errno.ENOENT:
                        output.error('%s: %s\n' % (patchdir, edata.errstring))
                        status = False
            else:
                output.write('Removing patch %s\n' % patchfns.print_patch(patch))
                if not backup.restore(patchdir, touch=True, verbose=not silent):
                    status = False
            patchfns.remove_from_db(patch)
            try:
                os.remove(os.path.join(patchdir + '~refresh'))
            except OSError as edata:
                if edata.errno != errno.ENOENT:
                    output.error('%s: %s\n' % (patchdir, edata.errstring))
                    status = False
        return status
    except KeyboardInterrupt:
        return False

def run_pop(args):
    number = stop_at_patch = None
    patchfns.chdir_to_base_dir()
    if args.patchnamornum:
        if args.patchnamornum.isdigit():
            number = int(args.patchnamornum)
        else:
            stop_at_patch = patchfns.find_unapplied_patch(args.patchnamornum)
            if not stop_at_patch:
                return cmd_result.ERROR
    elif not args.opt_all:
        number = 1
    silent = args.opt_quiet
    if patchfns.top_patch_needs_refresh() and not args.opt_force:
        output.error('The topmost patch %s needs to be refreshed first.\n' % patchfns.print_top_patch())
        return cmd_result.ERROR | cmd_result.SUGGEST_FORCE_OR_REFRESH
    patches = list_patches(number=number, stop_at_patch=stop_at_patch)
    if not patches:
        output.error('No patch removed\n')
        return cmd_result.ERROR
    is_ok = True
    for patch in patches:
        result = remove_patch(patch, force=args.opt_force, check=args.opt_remove, silent=silent)
        if result is not True:
            return cmd_result.ERROR if result is False else result
        if not args.opt_quiet:
            output.write('\n')
    if not patchfns.top_patch():
        output.write('No patches applied\n')
    else:
        output.write('Now at patch %s\n' % patchfns.print_top_patch())
    return cmd_result.OK if is_ok is True else cmd_result.ERROR

parser.set_defaults(run_cmd=run_pop)
