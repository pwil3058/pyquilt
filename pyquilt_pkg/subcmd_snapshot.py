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
from pyquilt_pkg import backup

parser = cmd_line.SUB_CMD_PARSER.add_parser(
    'snapshot',
    description='''Take a snapshot of the current working state.  After
        taking the snapshot, the tree can be modified in the usual
        ways, including pushing and popping patches.  A diff against
        the tree at the moment of the snapshot can be generated with
        `quilt diff --snapshot'.''',
)

parser.add_argument(
    '-d',
    help='Only remove current snapshot.',
    dest='opt_remove',
    action='store_true',
)

def run_snapshot(args):
    patchfns.chdir_to_base_dir()
    snap_subdir = '.snap'
    snap_subdir_path = os.path.join(patchfns.QUILT_PC, snap_subdir)
    if os.path.exists(snap_subdir_path):
        shutil.rmtree(snap_subdir_path)
    if args.opt_remove:
        return cmd_result.OK
    os.makedirs(snap_subdir_path)
    files = []
    for patch in patchfns.applied_patches():
        files += patchfns.files_in_patch(patch)
    # Use set functionality to remove duplicates
    result = backup.backup(snap_subdir_path, set(files))
    return cmd_result.OK if result else cmd_result.ERROR

parser.set_defaults(run_cmd=run_snapshot)
