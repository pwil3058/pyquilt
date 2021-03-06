#!/bin/env python
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

import argparse
import sys
import os

from pyquilt_pkg import patchlib

PARSER = argparse.ArgumentParser(description='Print patch statistics.')

PARSER.add_argument(
    '-u',
    help='do not sort the input list',
    dest='opt_unsorted',
    action='store_true',
)

PARSER.add_argument(
    '-p',
    help='strip level to use',
    dest='opt_strip_level',
    metavar='level',
)

PARSER.add_argument(
    'arg_patch_list',
    help='The name of the patch file to be processed.',
    metavar='patch',
    nargs='*',
)

ARGS = PARSER.parse_args()

# This will keep track of the order in which files were discovered
stats_list = patchlib.DiffStat.PathStatsList()

def process_text(text, strip_level=1):
    for stat in patchlib.Patch.parse_text(text).get_diffstat_stats(strip_level):
        if stat not in stats_list:
            stats_list.append(stat)
        else:
            stats_list[stats_list.index(stat)] += stat.diff_stats

if len(ARGS.arg_patch_list) == 0:
    try:
        process_text(sys.stdin.read(), ARGS.opt_strip_level)
    except patchlib.ParseError as pedata:
        print 'ERROR:', pedata.message, 'LINE NO:', pedata.lineno
        sys.exit(1)
    except patchlib.TooMayStripLevels as tsmldata:
        print 'ERROR:', tsmldata.message, 'LEVELS:', tsmldata.levels, 'FILE:', tsmldata.path
        sys.exit(1)
else:
    bad_files = [filename for filename in ARGS.arg_patch_list if not os.path.isfile(filename)]
    if len(bad_files) > 0:
        if len(bad_files) > 1:
            sys.stderr.write('{0} are not a files\n'.format(', '.join(bad_files)))
        else:
            sys.stderr.write('{0} is not a file\n'.format(bad_files[0]))
        sys.exit(1)
    for patch_filename in ARGS.arg_patch_list:
        try:
            process_text(open(patch_filename).read(), ARGS.opt_strip_level)
        except patchlib.ParseError as pedata:
            print 'ERROR:', pedata.message, 'LINE NO:', pedata.lineno, 'FILE:', patch_filename
            sys.exit(1)
        except patchlib.TooMayStripLevels as tsmldata:
            print 'ERROR:', tsmldata.message, 'LEVELS:', tsmldata.levels, 'FILE:', tsmldata.path, 'IN:', patch_filename
            sys.exit(1)

if not ARGS.opt_unsorted:
    stats_list.sort()

print stats_list.list_format_string(),
