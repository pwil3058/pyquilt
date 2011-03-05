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

from pyquilt_pkg import cmd_line
from pyquilt_pkg import cmd_result
from pyquilt_pkg import patchfns
from pyquilt_pkg import customization
from pyquilt_pkg import output

parser = cmd_line.SUB_CMD_PARSER.add_parser(
    'fork',
    description='''Fork the topmost patch.  Forking a patch means
        creating a verbatim copy of it under a new name, and use that
        new name instead of the original one in the current series.
        This is useful when a patch has to be modified, but the
        original version of it should be preserved, e.g. because it is
        used in another series, or for the history.  A typical sequence
        of commands would be: fork, edit, refresh.\n\n
        If new_name is missing, the name of the forked patch will be
        the current patch name, followed by \`-2'.  If the patch name
        already ends in a dash-and-number, the number is further
        incremented (e.g., patch.diff, patch-2.diff, patch-3.diff).''',
)

parser.add_argument(
    'arg_new_name',
    help='Name to use for the forked patch.',
    metavar='new_name',
    nargs='?',
)

def run_fork(args):
    patchfns.chdir_to_base_dir()
    top_patch = patchfns.find_top_patch()
    if not top_patch:
        return cmd_result.ERROR
    new_patch = args.arg_new_name if args.arg_new_name else patchfns.next_filename(top_patch)
    new_patch_file = patchfns.patch_file_name(new_patch)
    new_patch_dir = os.path.join(patchfns.QUILT_PC, new_patch)
    if patchfns.patch_in_series(new_patch) or os.path.isdir(new_patch_dir) or os.path.exists(new_patch_file):
        output.error('Patch %s exists already, please choose a new name\n' % patchfns.print_patch(new_patch))
        return cmd_result.ERROR | cmd_result.SUGGEST_RENAME
    is_ok = patchfns.rename_in_db(top_patch, new_patch)
    is_ok = is_ok if not is_ok else patchfns.rename_in_series(top_patch, new_patch)
    if is_ok:
        top_patch_dir = os.path.join(patchfns.QUILT_PC, top_patch)
        try:
            os.rename(top_patch_dir, new_patch_dir)
        except OSError:
            is_ok = False
    if is_ok:
        top_patch_file = patchfns.patch_file_name(top_patch)
        if os.path.exists(top_patch_file):
            try:
                shutil.copy2(top_patch_file, new_patch_file)
            except Exception:
                is_ok = False
    if not is_ok:
        output.write('Fork of patch %s to patch %s failed\n' % (patchfns.print_patch(top_patch), patchfns.print_patch(new_patch)))
    else:
        output.error('Fork of patch %s created as %s\n' % (patchfns.print_patch(top_patch), patchfns.print_patch(new_patch)))
    return cmd_result.OK if is_ok else cmd_result.ERROR

parser.set_defaults(run_cmd=run_fork)
