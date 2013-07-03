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
### Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA

import getopt
import os

from pyquilt_pkg import cmd_line
from pyquilt_pkg import cmd_result
from pyquilt_pkg import patchfns
from pyquilt_pkg import customization
from pyquilt_pkg import output
from pyquilt_pkg import shell

parser = cmd_line.SUB_CMD_PARSER.add_parser(
    'grep',
    description='''Grep through the source files, recursively, skipping
        patches and quilt meta-information. If no filename argument is
        given, the whole source tree is searched.
        Please see the grep(1) manual page for options.''',
    epilog='''The grep -h option can be passed after a
        double-dash (--). Search expressions that start with a dash
        can be passed after a second double-dash (-- --).''',
    usage='''pyquilt grep [-h|options [pattern] [file [file ...]]]\n'''
)

grep_options = 'EFGPe:f:iwxzsvVm:bHnhqoaId:D:RrlLcB:ZA:C:Uu'
grep_long_options = [
    'extended-regexp', 'fixed-strings', 'basic-regexp', 'perl-regexp',
    'regexp=', 'file=', 'ignore-case', 'word-regexp',
    'line-regexp', 'null-data', 'no-messages', 'invert-match', 'version',
    'help', 'mmap', 'max-count=', 'byte-offset', 'line-number',
    'line-buffered', 'with-filename', 'no-filename', 'label=',
    'only-matching', 'quiet', 'silent', 'binary-files=', 'text',
    'directories=', 'devices=', 'recursive', 'include=', 'exclude=',
    'exclude-from=', 'files-without-match', 'files-with-matches',
    'count', 'null', 'before-context=', 'after-context=', 'context=',
    'color=', 'colour=', 'binary', 'unix-byte-offsets',
]

def expect_pattern(opts):
    for opt in opts:
        if isinstance(opt, tuple):
            if opt[0] in ['-e', '--regexp', '-f', '--file']:
                return False
    return True

def make_opt_list(opts):
    opt_list = []
    for opt in opts:
        if isinstance(opt, str):
            opt_list.append(opt)
        elif opt[0].startswith('--'):
            opt_list.append('%s=%s' % opt)
        else:
            opt_list += list(opt)
    return opt_list

def get_files():
    '''Return a list of the files in the current directory.
    Omitting those that are quilt metadata files.'''
    files = []
    def onerror(exception):
        raise exception
    try:
        dirname = os.getcwd()
        for basedir, dirnames, filenames in os.walk(dirname, onerror=onerror):
            reldir = '' if basedir == dirname else os.path.relpath(basedir, dirname)
            if reldir.split(os.sep)[0] in [patchfns.QUILT_PC, patchfns.QUILT_PATCHES]:
                continue
            for entry in filenames:
                files.append(os.path.join(reldir, entry))
    except OSError as edata:
        output.perror(edata)
        return []
    return files

def run_grep(args):
    patchfns.chdir_to_base_dir()
    problem_args = [] # i.e. those wit optional arguments
    for arg in ['--color', '--colour']:
        while arg in args.remainder_of_args:
            problem_args.append(arg)
            args.remainder_of_args.remove(arg)
    grep_opts, grep_args = getopt.getopt(args.remainder_of_args, grep_options, grep_long_options)
    opt_list = make_opt_list(grep_opts) + problem_args
    if expect_pattern(grep_opts):
        files = grep_args[1:]
        opt_list += grep_args[0:1]
    else:
        files = grep_args
    if not files:
        files = get_files()
    if len(files) == 1 and '-h' not in opt_list and '--no-filename' not in opt_list:
        opt_list.append('-H')
    result = shell.run_cmd(['grep'] + opt_list + files)
    output.write(result.stdout)
    output.error(result.stderr)
    return result.eflags

parser.set_defaults(run_cmd=run_grep)
