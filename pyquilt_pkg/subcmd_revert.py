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
import shutil
import atexit

from pyquilt_pkg import cmd_line
from pyquilt_pkg import cmd_result
from pyquilt_pkg import patchfns
from pyquilt_pkg import customization
from pyquilt_pkg import output
from pyquilt_pkg import diff

parser = cmd_line.SUB_CMD_PARSER.add_parser(
    'revert',
    description='''Revert uncommitted changes to the topmost or named
        patch for the specified file(s): after the revert,
        'pyquilt diff -z' will show no differences for those files.
        Changes to files that are modified by patches on top of the
        specified patch cannot be reverted.''',
)

parser.add_argument(
    '-P',
    help='Revert changes in the named patch.',
    dest='opt_patch',
    metavar='patch',
)

parser.add_argument(
    'files',
    help='Files to be reverted.',
    metavar='file',
    nargs='*',
)

def clean_up(workdir):
    if workdir and os.path.exists(workdir):
        shutil.rmtree(workdir)

def run_revert(args):
    patchfns.chdir_to_base_dir()
    patch = patchfns.find_applied_patch(args.opt_patch)
    if not patch:
        return cmd_result.ERROR
    prpatch = patchfns.print_patch(patch)
    if patchfns.SUBDIR:
        args.files = [os.path.join(patchfns.SUBDIR, item) for item in args.files]
    is_ok = True
    for filename in args.files:
        if not patchfns.file_in_patch(filename, patch):
            is_ok = False
            output.error('File %s is not in patch %s\n' % (filename, prpatch))
            continue
        next_patch = patchfns.next_patch_for_file(patch, filename)
        if next_patch:
            is_ok = False
            output.error('' % (filename, patchfns.print_patch(next_patch)))
            continue
    if not is_ok:
        return cmd_result.ERROR
    workdir = patchfns.gen_tempfile(os.getcwd(), asdir=True)
    atexit.register(clean_up, workdir)
    if not patchfns.apply_patch_temporarily(workdir, patch, args.files):
        return cmd_result.ERROR
    for filename in args.files:
        revert_ok = True
        wdfilename = os.path.join(workdir, filename)
        if os.path.exists(wdfilename) and os.path.getsize(wdfilename) > 0:
            if os.path.exists(filename) and diff.same_contents(filename, wdfilename):
                output.write('File %s is unchanged\n' % filename)
                continue
            try:
                fdir = os.path.dirname(filename)
                if fdir and not os.path.exists(fdir):
                    os.makedirs(fdir)
                shutil.copy2(wdfilename, filename)
            except OSError as edata:
                revert_ok = False
        else:
            if not os.path.exists(filename):
                output.write('File %s is unchanged\n' % filename)
                continue
            try:
                os.remove(filename)
                fdir = os.path.dirname(filename)
                if os.path.exists(fdir) and len(os.listdir(fdir)) == 0:
                    os.removedirs(fdir)
            except OSError as edata:
                revert_ok = False
        if revert_ok:
            output.write('Changes to %s in patch %s reverted\n' % (filename, prpatch))
        else:
            output.error('Failed to revert changes to %s in patch %s\n' % (filename, prpatch))
            is_ok = False
    return cmd_result.OK if is_ok else cmd_result.ERROR

parser.set_defaults(run_cmd=run_revert)
