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

from pyquilt_pkg import cmd_line
from pyquilt_pkg import cmd_result
from pyquilt_pkg import patchfns
from pyquilt_pkg import customization
from pyquilt_pkg import output

parser = cmd_line.SUB_CMD_PARSER.add_parser(
    'files',
    description='''Print the list of files that the topmost or specified patch changes.''',
)

parser.add_argument(
    '-a',
    help='List all files in all applied patches.',
    dest='opt_all',
    action='store_true',
)

parser.add_argument(
    '-l',
    help='Add patch name to output.',
    dest='opt_labels',
    action='store_true',
)

parser.add_argument(
    '-v',
    help='Verbose, more user friendly output.',
    dest='opt_verbose',
    action='store_true',
)

parser.add_argument(
    '--combine',
    help='''Create a listing for all patches between this patch and
        the topmost or specified patch. A patch name of `-' is
        equivalent to specifying the first applied patch.''',
    dest='opt_combine',
    metavar='patch',
)

parser.add_argument(
    'patch',
    help='the specified patch.',
    nargs='?',
)

def run_files(args):
    patchfns.chdir_to_base_dir()
    first_patch = None
    if args.opt_combine:
        args.opt_all = True
        if args.opt_combine != '-':
            first_patch = patchfns.find_patch_in_series(args.opt_combine)
            if not first_patch:
                return cmd_result.ERROR
    last_patch = patchfns.find_applied_patch(args.patch)
    if not last_patch:
        return cmd_result.ERROR
    if args.opt_all:
        if not first_patch:
            first_patch = patchfns.applied_patches()[0]
        patches = patchfns.patches_before(last_patch) + [last_patch]
        if first_patch not in patches:
            output.error('Patch %s not applied before patch %s\n' % (patchfns.print_patch(first_patch), patchfns.print_patch(last_patch)))
            return cmd_result.ERROR
        patches = patches[patches.index(first_patch):]
    else:
        patches = [last_patch]
    use_status = args.opt_verbose and not args.opt_labels
    # Note: If opt_labels is set, then use_status is not set.
    output.start_pager()
    for patch in patches:
        if args.opt_all and args.opt_verbose and not args.opt_labels:
            output.write('%s\n' % patch)
        for filename in sorted(patchfns.files_in_patch(patch)):
            if args.opt_labels:
                if args.opt_verbose:
                    output.write('[%s] ' % patch)
                else:
                    output.write('%s ' % patch)
            if not use_status:
                output.write('%s\n' % filename)
            else:
                status = ' '
                buname = patchfns.backup_file_name(filename)
                if os.path.exists(buname) and os.path.getsize(buname) > 0:
                    if not os.path.exists(filename) or os.path.getsize(filename) == 0:
                        status = '-'
                elif os.path.exists(filename) or os.path.getsize(filename) > 0:
                    status = '+'
                output.write('%s %s\n' % (status, file))
    output.wait_for_pager()
    return cmd_result.OK

parser.set_defaults(run_cmd=run_files)
