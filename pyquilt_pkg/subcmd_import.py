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
import sys

from pyquilt_pkg import cmd_line
from pyquilt_pkg import cmd_result
from pyquilt_pkg import patchfns
from pyquilt_pkg import customization
from pyquilt_pkg import output
from pyquilt_pkg import putils
from pyquilt_pkg import shell
from pyquilt_pkg import fsutils

parser = cmd_line.SUB_CMD_PARSER.add_parser(
    'import',
    description='''Import external patches.  The patches will be
        inserted following the  current top patch, and must be pushed
        after import to apply them.''',
)

parser.add_argument(
    '-p',
    help='Number of directory levels to strip when applying (default=1)',
    dest='opt_strip',
    metavar='num',
)

parser.add_argument(
    '-R',
    help='Apply patch in reverse.',
    dest='opt_reverse',
    action='store_true',
)

parser.add_argument(
    '-P',
    help='''Patch filename to use inside quilt. This option can only be
        used when importing a single patch.''',
    dest='opt_patch',
    metavar='patch',
)

parser.add_argument(
    '-f',
    help='Overwite/update existing patches.',
    dest='opt_force',
    action='store_true',
)

parser.add_argument(
    '-d',
    help='''When overwriting in existing patch, keep the old (o),
        all (a), or new (n) patch header. If both patches include
        headers, this option must be specified. This option is only
        effective when -f is used.''',
    dest='opt_desc',
    choices=['o', 'a', 'n'],
)

parser.add_argument(
    'patchfiles',
    help='Patch file(s) to be imported',
    metavar='patchfile',
    nargs='+',
)

def merge_patches(old, new, opt_desc):
    """Return the merge of the old and new patches"""
    old_desc = patchfns.gen_tempfile()
    open(old_desc, 'w').write(putils.get_patch_descr(old))
    new_desc = patchfns.gen_tempfile()
    open(new_desc, 'w').write(putils.get_patch_descr(new))
    if opt_desc is None:
        if os.path.getsize(old_desc) == 0:
            opt_desc = 'n'
        elif os.path.getsize(new_desc) == 0:
            opt_desc = 'o'
        if opt_desc is None:
            result = shell.run_cmd('diff -u %s %s' % (old_desc, new_desc))
            diff_lines = result.stdout.splitlines(True)
            if len(diff_lines) > 2:
                output.error('Patch headers differ:\n')
                output.error(''.join(diff_lines[2:]))
                output.error('Please use -d {o|a|n} to specify which patch header(s) to keep.\n')
                os.remove(old_desc)
                os.remove(new_desc)
                return False
    patchtext = open(old_desc).read() if opt_desc != 'n' else ''
    if opt_desc == 'a':
        patchtext += '---\n'
    if opt_desc == 'o':
        patchtext += putils.get_patch_diff(new)
    else:
        patchtext += fsutils.get_file_contents(new)
    os.remove(old_desc)
    os.remove(new_desc)
    return patchtext

def run_import(args):
    patchfns.chdir_to_base_dir()
    if args.opt_patch and len(args.patchfiles) > 1:
        output.error('Option `-P\' can only be used when importing a single patch\n')
        return cmd_result.ERROR
    patch_args = '-p%s' % args.opt_strip if args.opt_strip else ''
    if args.opt_reverse:
        patch_args = '-R' if not patch_args else patch_args + ' -R'
    before = patchfns.patch_after(patchfns.top_patch())
    for patch_file in args.patchfiles:
        patch = args.opt_patch if args.opt_patch else os.path.basename(patch_file)
        patch_file = patchfns.find_patch_file(patch_file)
        if not patch_file:
            return cmd_result.ERROR
        merged = False
        if patchfns.is_applied(patch):
            output.error('Patch %s is applied\n', patchfns.print_patch(patch))
            return cmd_result.ERROR
        dest = patchfns.patch_file_name(patch)
        if patchfns.patch_in_series(patch):
            if patch_file == dest:
                output.error('Patch %s already exists in series.\n' % patchfns.print_patch(patch))
                return cmd_result.ERROR
            if not args.opt_force:
                output.error('Patch %s exists. Replace with -f.\n' % patchfns.print_patch(patch))
                return cmd_result.ERROR_SUGGEST_FORCE
            if args.opt_desc != 'n':
                merged_patch = merge_patches(dest, patch_file, args.opt_desc)
                if merged_patch is False:
                    return cmd_result.ERROR
                merged = True
            output.error('Replacing patch %s with new version\n' % patchfns.print_patch(patch))
        elif os.path.exists(dest):
            output.write('Importing patch %s\n' % patchfns.print_patch(patch))
        else:
            output.write('Importing patch %s (stored as %s)\n' % (patch_file, patchfns.print_patch(patch)))
            dest_dir = os.path.dirname(dest)
            if not os.path.exists(dest_dir):
                os.makedirs(dest_dir)
        try:
            if merged:
                fsutils.set_file_contents(dest, merged_patch)
            else:
                # just in case dest == patch_file do it this way
                text = fsutils.get_file_contents(patch_file)
                fsutils.set_file_contents(dest, text)
        except IOError as edata:
            output.error('Failed to import patch %s\n' % patchfns.print_patch(patch))
            return cmd_result.ERROR
        if not patchfns.patch_in_series(patch) and not patchfns.insert_in_series(patch, patch_args, before):
            output.error('Failed to insert patch %s into file series\n' % patchfns.print_patch(patch))
    return cmd_result.OK

parser.set_defaults(run_cmd=run_import)
