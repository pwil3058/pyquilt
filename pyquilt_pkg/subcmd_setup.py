### Copyright (C) 2011 Peter Williams <peter_ono@users.sourceforge.net>
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
import tarfile
import errno

from pyquilt_pkg import cmd_line
from pyquilt_pkg import cmd_result
from pyquilt_pkg import patchfns
from pyquilt_pkg import output

parser = cmd_line.SUB_CMD_PARSER.add_parser(
    'setup',
    description='Initializes a source tree from an rpm spec file or a quilt series file.',
)

parser.add_argument(
    '-d',
    help='Optional path prefix for the resulting source tree.',
    dest='prefix',
    metavar='path-prefix',
)

parser.add_argument(
    '-v',
    help='Verbose debug output.',
    dest='verbose',
    action='store_true',
)

parser.add_argument(
    '--sourcedir',
    help='Directory that contains the package sources. Defaults to `.\'.' ,
    dest='sourcedir',
    metavar='dir',
)

parser.add_argument(
    '--fuzz',
    help='Set the maximum fuzz factor (needs rpm 4.6 or later).',
    dest='opt_fuzz',
    metavar='N',
)

parser.add_argument(
    'series_file',
    help='name of the patch to delete',
    metavar='{specfile|seriesfile}'
)

def check_for_existing_directories(args, script):
    status=False
    dircty_set = set()
    for action in script:
        if action[0] == 'patch':
            if args.prefix:
                dircty_set.add(os.path.join(args.prefix, action[1]))
            else:
                dircty_set.add(action[1])
    last_dir = None
    for dircty in dircty_set:
        if dircty == ".":
            continue
        if os.path.exists(dircty):
            output.error('Directory %s exists\n' % dircty)
            status = True
    return status

def check_for_existing_files(args, script):
    status=False
    dircty_set = set()
    for action in script:
        if action[0] == 'patch':
            if args.prefix:
                dircty_set.add(os.path.join(args.prefix, action[1]))
            else:
                dircty_set.add(action[1])
    for dircty in dircty_set:
        patch_dir = os.path.join(dircty, patchfns.QUILT_PATCHES)
        if os.path.exists(patch_dir):
            output.error('Directory %s exists\n' % patch_dir)
            status = True
        series_file = os.path.join(dircty, patchfns.QUILT_SERIES)
        if os.path.exists(series_file):
            output.error('File %s exists\n' % series_file)
            status = True
    return status

def create_symlink(target, link):
    if target is None:
        target = '.'
    if os.path.isabs(target) or os.path.isabs(link):
        os.symlink(target, link)
    else:
        target = os.path.relpath(os.path.abspath(target), os.path.dirname(os.path.abspath(link)))
        os.symlink(target, link)

def run_setup(args):
    spec_file = series_file = None
    patchfns.chdir_to_base_dir()
    tmpfile = patchfns.gen_tempfile()
    def add_exit_handler():
        try:
            os.remove(tmpfile)
        except OSError:
            pass
    script = []
    if args.series_file.endswith('.spec'):
        spec_file = args.series_file
        print 'not yet implemented'
    else:
        series_file = args.series_file
        tar_dir = patch_dir = '.'
        for line in open(series_file).readlines():
            if line.startswith('# Sourcedir: '):
                tar_dir = line[len('# Sourcedir: '):].rstrip()
            elif line.startswith('# Source: '):
                script.append(('tar', tar_dir, line[len('# Source: '):].rstrip()))
            elif line.startswith('# Patchdir: '):
                patch_dir = line[len('# Patchdir: '):].rstrip()
            elif line.startswith('#') or len(line.strip()) == 0:
                pass
            else:
                script.append(('patch', patch_dir, line.rstrip()))
    if check_for_existing_directories(args, script):
        return cmd_result.ERROR
    for action in script:
        if action[0] == 'tar':
            tarball = os.path.join(args.sourcedir, action[2]) if args.sourcedir else action[2]
            if not os.path.exists(tarball):
                output.error('File %s not found\n' % tarball)
                return cmd_result.ERROR
            output.write('Unpacking archive %s\n' % tarball)
            target_dir = os.path.join(args.prefix, action[1]) if args.prefix else action[1]
            try:
                os.makedirs(target_dir)
            except OSError as edata:
                if edata.errno != errno.EEXIST:
                    output.error('%s: %s\n' % (target_dir, edata.strerror))
                    return cmd_result.ERROR
            if tarfile.is_tarfile(tarball):
                tarobj = tarfile.open(tarball, 'r')
                tarobj.extractall(target_dir)
                tarobj.close()
            else:
                output.error('%s: is not a supported tar format\n' % tarball)
                return cmd_result.ERROR
    if check_for_existing_files(args, script):
        output.error("Trying alternative patches and series names...\n")
        patchfns.QUILT_PATCHES = "quilt_patches"
        patchfns.QUILT_SERIES = "quilt_series"
        if check_for_existing_files(args, script):
            return cmd_result.ERROR
    tar_dir = tar_file = None
    for action in script:
        if action[0] == 'tar':
            tar_dir = None if action[1] == '.' else action[1]
            tar_file = action[2]
        elif action[0] == 'patch':
            patches_dir = os.path.join(action[1], patchfns.QUILT_PATCHES)
            if args.prefix:
                patches_dir = os.path.join(args.prefix, patches_dir)
            if not os.path.exists(patches_dir):
                create_symlink(args.sourcedir, patches_dir)
                patchfns.create_db(os.path.dirname(patches_dir))
            this_series_file = os.path.join(action[1], patchfns.QUILT_SERIES)
            if args.prefix:
                this_series_file = os.path.join(args.prefix, this_series_file)
            if series_file:
                if not os.path.exists(this_series_file):
                    create_symlink(series_file, this_series_file)
            else:
                if not os.path.exists(this_series_file):
                    fobj = open(this_series_file, 'w')
                    fobj.write('# Patch series file for quilt," created by pyquilt\n')
                    if tar_dir is not None:
                        fobj.write('# Sourcedir: %s\n' % tar_dir)
                    if tar_file is not None:
                        fobj.write('# Source: %s\n' % tar_file)
                    fobj.write('# Patchdir: %s\n' % action[1])
                    fobj.write('# \n' % action[1])
                else:
                    fobj = open(this_series_file, 'a')
                fobj.write('%s\n' % action[2])
                fobj.close()
    return cmd_result.OK

parser.set_defaults(run_cmd=run_setup)
