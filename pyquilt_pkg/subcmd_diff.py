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

import shutil
import os
import argparse
import atexit
import re

from pyquilt_pkg import cmd_line
from pyquilt_pkg import cmd_result
from pyquilt_pkg import patchfns
from pyquilt_pkg import customization
from pyquilt_pkg import output
from pyquilt_pkg import diff
from pyquilt_pkg import colour

parser = cmd_line.SUB_CMD_PARSER.add_parser(
    'diff',
    description='''Produces a diff of the specified file(s) in the
        topmost or specified patch.  If no files are specified, all
        files that are modified are included.''',
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
    '-z',
    help='''Write to standard output the changes that have been made
        relative to the topmost or specified patch.''',
    dest='opt_relative',
    action='store_true',
)

parser.add_argument(
    '-R',
    help='Create a reverse diff.',
    dest='opt_reverse',
    action='store_true',
)

parser.add_argument(
    '-P',
    help='Create a diff for the specified patch.  (Defaults to the topmost patch.)',
    dest='last_patch',
    metavar='patch',
)

parser.add_argument(
    '--combine',
    help='''Create a combined diff for all patches between this patch
        and the patch specified with -P. A patch name of `-' is
        equivalent to specifying the first applied patch.''',
    dest='opt_combine',
    metavar='patch',
)

parser.add_argument(
    '--snapshot',
    help='Diff against snapshot (see `pyquilt snapshot -h\').',
    dest='opt_snapshot',
    action='store_true',
)

parser.add_argument(
    '--diff',
    help='''Use the specified utility for generating the diff. The
        utility is invoked with the original and new file name as
        arguments.''',
    dest='opt_diff',
    metavar='utility',
)

parser.add_argument(
    '--color',
    help='''Use syntax coloring.''',
    dest='opt_color',
    nargs='?',
    choices=['always', 'auto', 'never',],
    const='always'
)

parser.add_argument(
    '--sort',
    help='Sort files by their name instead of preserving the original order.',
    dest='opt_sort',
    action='store_true',
)

parser.add_argument(
    'opt_files',
    help='File(s) to be included in diff.',
    metavar='file',
    nargs='*',
)

def colorize(text):
    ctext = ''
    hunk_cre = re.compile(r'^(@@ -[0-9]+(,[0-9]+)? +[0-9]+(,[0-9]+)? @@)([ \t]*)(.*\n?)')
    for line in text.splitlines(True):
        if line.startswith(('Index: ', '--- ', '+++ ', '*** ')):
            ctext += colour.wrap(line, 'diff_hdr')
        elif line.startwith('+'):
            ctext += colour.wrap(line, 'diff_add')
        elif line.startwith('-'):
            ctext += colour.wrap(line, 'diff_rem')
        elif line.startwith('!'):
            ctext += colour.wrap(line, 'diff_mod')
        elif line.startwith('*' * 15):
            ctext += colour.wrap(line, 'diff_cctx')
        else:
            match = hunk_cre.match(line)
            if match:
                ctext += wrap(match.group(1), 'diff_hunk')
                if match.group(4) is not None:
                    ctext += match.group(4)
                if match.group(5) is not None:
                    ctext += wrap(match.group(5), 'diff_ctx')
            else:
                ctext += line
    return ctext

def do_diff(filename, old_file, new_file, args):
    """Output the diff for the nominated files"""
    if args.opt_reverse:
        old_file, new_file = new_file, old_file
    if args.opt_diff:
        if not os.path.exists(old_file):
            old_file = '/dev/null'
        if not os.path.exists(new_file):
            new_file = '/dev/null'
        if not diff.same_contents(old_file, new_file):
            os.environ['LANG'] = patchfns.ORIGINAL_LANG
            shell.run_cmd('%s %s %s' % (args.opt_diff, old_file, new_file))
            os.environ['LANG'] = 'POSIX'
            return True
    else:
        result = diff.diff_file(filename, old_file, new_file, args)
        output.error(result.stderr)
        if args.opt_color:
            output.write(colorize(result.stdout))
        else:
            output.write(result.stdout)
        return result.eflags < 2

def clean_up(workdir):
    if workdir and os.path.exists(workdir):
        shutil.rmtree(workdir)

def run_diff(args):
    patchfns.chdir_to_base_dir()
    snap_subdir = '.snap' if args.opt_snapshot else None
    if args.opt_combine:
        first_patch = '-' if args.opt_combine == '-' else patchfns.find_applied_patch(args.opt_combine)
    else:
        first_patch = None
    if len([opt for opt in [args.opt_combine, args.opt_snapshot, args.opt_relative] if opt]) > 1:
        output.error('Options `--combine\', `--snapshot\', and `-z\' cannot be combined.\n')
        return cmd_result.ERROR
    last_patch = patchfns.find_applied_patch(args.last_patch)
    if not last_patch:
        return cmd_result.ERROR
    if args.opt_strip_level is None:
        args.opt_strip_level = patchfns.patch_strip_level(last_patch)
    if args.opt_strip_level not in ['0', '1', 'ab']:
        output.error('Cannot diff patches with -p%s, please specify -p0, -p1, or -pab instead\n' % args.opt_strip_level)
        return cmd_result.ERROR
    files = []
    if args.opt_snapshot and len(args.opt_files) == 0:
        for path, _dirs, bases in os.walk(snap_subdir):
            files += [os.path.join(path, base) for base in bases]
        files.sort()
        args.opt_combine = True
        first_patch = patchfns.applied_patches()[0]
    if args.opt_combine:
        patches = patchfns.patches_before(last_patch) + [last_patch]
        if first_patch != '-':
            try:
                patches = patches[patches.index(first_patch):]
            except ValueError:
                output.error('Patch %s not applied before patch %s\n' % (patchfns.print_patch(first_patch), patchfns.print_patch(last_patch)))
                return cmd_result.ERROR
    else:
        patches = [last_patch]
    if len(args.opt_files) > 0:
        # use a set as it should be more efficient
        ofiles = set()
        for ofile in args.opt_files:
            if ofile.startswith('.' + os.sep):
                ofiles.add(ofile[2:])
            else:
                ofiles.add(ofile)
        for patch in patches:
            for fname in patchfns.files_in_patch_ordered(patch):
                if fname in ofiles and fname not in files:
                    files.append(fname)
    else:
        for patch in patches:
            for fname in patchfns.files_in_patch_ordered(patch):
                if fname not in files:
                    files.append(fname)
    if args.opt_sort:
        files.sort()
    if args.opt_relative:
        workdir = patchfns.gen_tempfile(os.path.join(os.getcwd(), 'quilt'), asdir=True)
        atexit.register(clean_up, workdir)
        if not patchfns.apply_patch_temporarily(workdir, last_patch, files):
            return cmd_result.ERROR
    is_ok = True
    files_were_shadowed = False
    output.start_pager()
    for filename in files:
        snapshot_path = os.path.join(patchfns.QUILT_PC, snap_subdir, filename) if snap_subdir else None
        if snapshot_path and os.path.exists(snapshot_path):
            old_file = snapshot_path
        elif args.opt_relative:
            old_file = os.path.join(workdir, filename)
        else:
            patch = patchfns.first_modified_by(filename, patches)
            if not patch:
                if not args.opt_snapshot:
                    output.error('File %s is not being modified\n' % filename)
                continue
            old_file = patchfns.backup_file_name(patch, filename)
        next_patch = patchfns.next_patch_for_file(last_patch, filename)
        if not next_patch:
            new_file = filename
        else:
            new_file = patchfns.backup_file_name(next_patch, filename)
            files_were_shadowed = True
        if not do_diff(filename, old_file, new_file, args):
            output.error('Diff failed, aborting\n')
            return cmd_result.ERROR
    if files_were_shadowed:
        output.error('Warning: more recent patches modify files in patch %s\n' % patchfns.print_patch(last_patch))
    output.wait_for_pager()
    return cmd_result.OK

parser.set_defaults(run_cmd=run_diff)
