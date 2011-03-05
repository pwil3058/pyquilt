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

import sys
import os
import shutil
import argparse
import re

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
    'push',
    description='''
        Apply patch(es) from the series file.  Without options, the next patch
        in the series file is applied.  When a number is specified, apply the
        specified number of patches.  When a patch name is specified, apply
        all patches up to and including the specified patch.''',
    epilog='''
        Patch names may include the patches/ prefix, which means that
        filename completion can be used.''',
)

what_parser = parser.add_mutually_exclusive_group()
what_parser.add_argument(
    'patchnamornum',
    help='(optional) name/number of the patch(es) to be pushed',
    default=None,
    nargs='?',
    metavar='patch|num'
)

what_parser.add_argument(
    '-a',
    help='''Apply all patches in the series file.''',
    dest='opt_all',
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

parser.add_argument(
    '-f',
    help='''
    Force apply, even if the patch has rejects. Unless in quiet mode,
    apply the patch interactively: the patch utility may ask questions.
    ''',
    dest='opt_force',
    action='store_true',
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
    '--fuzz',
    help='''Set the maximum fuzz factor (default: 2).''',
    dest='opt_fuzz',
    type=int,
    metavar='N'
)

class MergeAction(argparse.Action):
    def __call__(self, parser, namespace, values, option_string=None):
        if values is None:
            setattr(namespace, self.dest, 'default')
        else:
            setattr(namespace, self.dest, values)

parser.add_argument(
    '-m', '--merge',
    help='''Merge the patch file into the original files (see patch(1)).''',
    dest='opt_merge',
    nargs='?',
    choices=['merge', 'diff3'],
    action=MergeAction
)

parser.add_argument(
    '--leave-rejects',
    help='''Leave around the reject files patch produced, even if the patch
    is not actually applied.''',
    dest='opt_leave_rejects',
    action='store_true'
)

def list_patches(number=None, stop_at_patch=None, push_all=False):
    top = patchfns.top_patch()
    n = 0
    patch = None
    if top:
        patch_list = patchfns.patches_after(top)
    else:
        patch_list = patchfns.cat_series()
    if push_all:
        return patch_list
    if not number:
        number = patch_list.index(stop_at_patch) + 1
    if number < len(patch_list):
        return patch_list[:number]
    return patch_list

def push_patch_args(patch, reverse=False):
    patch_args = patchfns.patch_args(patch)
    if reverse:
        if '-R' in patch_args:
            patch_args.remove('-R')
        else:
            patch_args.append('-R')
    return ' '.join(patch_args)

def cleanup_patch_output(text, args):
    if args.opt_leave_rejects:
        return text
    ret = ''
    if args.opt_quiet:
        cre = re.compile('( -- saving rejects to (file )?.*)')
        for line in text.splitlines(True):
            ret += cre.sub('', line)
    else:
        cre1 = re.compile('^patching file (.*).')
        cre2 = re.compile('( -- saving rejects to (file )?.*)')
        for line in text.splitlines(True):
            pnm = cre1.match(line)
            if pnm:
                filename = pnm.group(1)
                ret += cre2.sub(' -- rejects in file %s' % filename, line)
            else:
                ret += line
    return ret

_FAIL_CRE = re.compile('FAILED|hunks? ignored|can\'t find file|file .* already exists|NOT MERGED')
_FUZZ_CRE = re.compile('^(Hunk .* with fuzz [0-9]*)')
_OFFSET_CRE = re.compile('(offset -?[0-9]* lines)')

def colorize(text):
    ret = ''
    for line in text.splitlines(True):
        if _FAIL_CRE.search(line):
            ret += colours.wrap(line, 'patch_fail')
        elif line.endswith('already applied'):
            ret += colour.wrap(line, 'patch_fuzz')
        elif line.startswith('Hunk'):
            match = _FUZZ_CRE.match(line)
            if match:
                line = _FUZZ_CRE.sub(colour.wrap(match.group(1), 'patch_fuzz'), line)
            match = _OFFSET_CRE.search(line)
            if match:
                line = _OFFSET_CRE.sub(colour.wrap(match.group(1), 'patch_offs'), line)
            ret += line
        else:
            ret += line
    return ret

def rollback_patch(patch, verbose=False):
    backup_dir = os.path.join(patchfns.QUILT_PC, patch)
    return backup.restore(backup_dir, verbose=verbose)

def run_push(args):
    def add_patch(patch):
        def apply_patch(patch_file, patch_args):
            if not os.path.exists(patch_file) or os.path.getsize(patch_file) == 0:
                return cmd_result.Result(0, '', '')
            return putils.apply_patch(patch_file, patch_args=patch_args)
        tmp = None
        patch_file = patchfns.patch_file_name(patch)
        output.write('Applying patch %s\n' % patchfns.print_patch(patch))
        try:
            pp_args = push_patch_args(patch, reverse=False)
            prefix = os.path.join(patchfns.QUILT_PC, patch)
            if not args.opt_leave_rejects:
                tmp = patchfns.gen_tempfile()
                trf = '-r %s' % tmp
            else:
                trf = ''
            patch_args = '%s --backup --prefix="%s/" %s -E %s' % (pp_args, prefix, trf, more_patch_args)
            result = apply_patch(patch_file, patch_args=patch_args)
            if result.eflags != 0 or not args.opt_quiet:
                if do_colorize:
                    output.error(colorize(cleanup_patch_output(result.stderr, args)))
                    output.write(colorize(cleanup_patch_output(result.stdout, args)))
                else:
                    output.error(cleanup_patch_output(result.stderr, args))
                    output.write(cleanup_patch_output(result.stdout, args))
        except KeyboardInterrupt:
            rollback_patch(patch)
            output.error('Interrupted by user; patch %s was not applied.\n' % patchfns.print_patch(patch))
            return False
        finally:
            if tmp:
                os.remove(tmp)
        if result.eflags == 0 or (result.eflags == 1 and args.opt_force):
            patchfns.add_to_db(patch)
            refresh_file = os.path.join(patchfns.QUILT_PC, patch + '~refresh')
            if result.eflags == 0:
                if os.path.exists(refresh_file):
                    os.remove(refresh_file)
            else:
                fsutils.touch(refresh_file)
            patch_dir = os.path.join(patchfns.QUILT_PC, patch)
            if os.path.exists(patch_dir):
                fsutils.touch(os.path.join(patch_dir, '.timestamp'))
            else:
                os.mkdir(patch_dir)
            if not os.path.exists(patch_file):
                output.write('Patch %s does not exist; applied empty patch\n' % patchfns.print_patch(patch))
            elif not putils.get_patch_diff(patch_file):
                output.write('Patch %s appears to be empty; applied\n' % patchfns.print_patch(patch))
            elif result.eflags != 0:
                output.write('Applied patch %s (forced; needs refresh)\n' % patchfns.print_patch(patch))
                return False
        else:
            rollback_patch(patch)
            tmp = patchfns.gen_tempfile()
            trf = '-r %s' % tmp
            pp_args = push_patch_args(patch, reverse=True)
            patch_args = '%s --backup --prefix="%s/" %s -E %s' % (pp_args, prefix, trf, more_patch_args)
            result = apply_patch(patch_file, patch_args=patch_args)
            if result.eflags == 0:
                output.write('Patch %s can be reverse-applied\n' % patchfns.print_patch(patch))
            else:
                output.write('Patch %s does not apply (enforce with -f)\n' % patchfns.print_patch(patch))
            rollback_patch(patch)
            os.remove(tmp)
            return False
        return True
    number = stop_at_patch = None
    patchfns.chdir_to_base_dir()
    customization.merge_default_args(args, parser, 'push')
    if args.patchnamornum:
        if args.patchnamornum.isdigit():
            number = int(args.patchnamornum)
        else:
            stop_at_patch = args.patchnamornum
    elif not args.opt_all:
        number = 1
    stop_at_patch = patchfns.find_unapplied_patch(stop_at_patch)
    if not stop_at_patch:
        return cmd_result.ERROR
    silent_unless_verbose = '-s' if not args.opt_verbose else None
    opt_leave_rejects = 1 if args.opt_force else None
    more_patch_args = ' -s' if args.opt_quiet else ''
    more_patch_args += ' -f' if not args.opt_force or args.opt_quiet else ''
    if args.opt_merge is 'default':
        more_patch_args += ' --merge'
    elif args.opt_merge:
        more_patch_args += ' --merge=%s' % args.opt_merge
    more_patch_args += ' -F%d' % args.opt_fuzz if args.opt_fuzz else ''
    if patchfns.top_patch_needs_refresh():
        output.write('The topmost patch %s needs to be refreshed first.\n' % patchfns.print_top_patch())
        return cmd_result.ERROR | cmd_result.SUGGEST_REFRESH
    patches = list_patches(number=number, stop_at_patch=stop_at_patch, push_all=args.opt_all)
    patchfns.create_db()
    do_colorize = args.opt_color == 'always' or (args.opt_color == 'auto' and sys.stderr.isatty())
    if do_colorize:
        colour.set_up()
    is_ok = True
    for patch in patches:
        is_ok = add_patch(patch)
        output.write('\n')
        if not is_ok:
            break
    if is_ok:
        output.write('Now at patch %s\n' % patchfns.print_top_patch())
    return cmd_result.OK if is_ok else cmd_result.ERROR

parser.set_defaults(run_cmd=run_push)
