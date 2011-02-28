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

import sys
import os
import re

from pyquilt_pkg import cmd_line
from pyquilt_pkg import cmd_result
from pyquilt_pkg import patchfns
from pyquilt_pkg import customization
from pyquilt_pkg import shell

parser = cmd_line.SUB_CMD_PARSER.add_parser(
    'annotate',
    description='''Print an annotated listing of the specified
        file showing which patches modify which lines.
        Only applied patches are included.''',
)

parser.add_argument(
    'filename',
    help='name of file to be annotated',
    metavar='file',
)

parser.add_argument(
    '-P',
    help='Stop checking for changes at the specified rather than the topmost patch.',
    dest='opt_patch',
    metavar='patch',
)

def annotation_for(old_file, new_file, annotation):
    """Return diff for annotation for changes from osd_file to new_file"""
    if not os.path.exists(old_file) or os.path.getsize(old_file) == 0:
        old_file = '/dev/null'
    if not os.path.exists(new_file) or os.path.getsize(new_file) == 0:
        new_file = '/dev/null'
    result = shell.run_cmd('diff -e "%s" "%s"' % (old_file, new_file))
    if result.eflags > 1:
        sys.stderr.write(result.stderr)
        sys.exit(result.eflags)
    difftxt = ''
    start_cre = re.compile('^(\d+)(,\d+)?([acd])$')
    end_cre = re.compile('^\.$')
    lines = result.stdout.splitlines(True)
    index = 0
    aline = '%s\n' % annotation
    while index < len(lines):
        match = start_cre.match(lines[index])
        if match:
            difftxt += lines[index]
            start = int(match.group(1))
            if match.group(3) == 'a':
                index += 1
                while end_cre.match(lines[index]) is None:
                    difftxt += aline
                    index += 1
                difftxt += lines[index]
            elif match.group(3) == 'c':
                end = int(match.group(2)[1:]) if match.group(2) is not None else start
                cnt = end - start + 1
                index += cnt + 1
                difftxt += aline * cnt
                assert end_cre.match(lines[index])
                difftxt += lines[index]
            else:
                assert match.group(3) == 'd'
            index += 1
        else:
            assert False
            index += 1
    return difftxt

def run_annotate(args):
    patchfns.chdir_to_base_dir()
    args.opt_patch = patchfns.find_applied_patch(args.opt_patch)
    opt_file = os.path.join(patchfns.SUBDIR, args.filename)
    if not args.opt_patch:
        return cmd_result.ERROR
    patches = []
    files = []
    next_patch = None
    for patch in patchfns.applied_patches():
        old_file = patchfns.backup_file_name(patch, opt_file)
        if os.path.isfile(old_file):
            patches.append(patch)
            files.append(old_file)
        if patch == args.opt_patch:
            next_patch = patchfns.next_patch_for_file(patch, opt_file)
            break
    if not next_patch:
        files.append(opt_file)
    else:
        files.append(patchfns.backup_file_name(next_patch, opt_file))
    if len(patches) == 0:
        for line in open(files[-1]).readlines():
            sys.stdout.write('\t%s\n' % line)
        return cmd_result.OK
    difftxt = ''
    for index in range(len(patches)):
        difftxt += annotation_for(files[index], files[index + 1], index + 1)
    template = patchfns.gen_tempfile()
    open(template, 'w').write('\n' * len(open(files[0]).readlines()))
    shell.run_cmd('patch %s' % template, difftxt)
    annotations = [line.rstrip() for line in open(template).readlines()]
    os.remove(template)
    pager = shell.Pager()
    if os.path.exists(files[-1]):
        for annotation, line in zip(annotations, open(files[-1]).readlines()):
            pager.write('%s\t%s' % (annotation, line))
    pager.write('\n')
    for index, patch in zip(range(len(patches)), patches):
        pager.write('%s\t%s\n' % (index + 1, patchfns.print_patch(patch)))
    return pager.wait()

parser.set_defaults(run_cmd=run_annotate)
