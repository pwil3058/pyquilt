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
### Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA

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
    'arg_patch_list',
    help='The name of the patch file to be processed.',
    metavar='patch',
    nargs='*',
)

ARGS = PARSER.parse_args()

# Keep track of the order in which files were discovered
ORDERED_FILE_LIST = []
FILE_MAP = {}

def process_text(text):
    for stat in patchlib.parse_text(text).get_diffstat_stats():
        if not stat.path in ORDERED_FILE_LIST:
            ORDERED_FILE_LIST.append(stat.path)
            FILE_MAP[stat.path] = stat.diff_stats
        else:
            FILE_MAP[stat.path] += stat.diff_stats

if len(ARGS.arg_patch_list) == 0:
    try:
        process_text(sys.stdin.read())
    except patchlib.ParseError as pedata:
        print 'ERROR:', pedata.message, 'LINE NO:', pedata.lineno
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
            process_text(open(patch_filename).read())
        except patchlib.ParseError as pedata:
            print 'ERROR:', pedata.message, 'LINE NO:', pedata.lineno, 'FILE:', patch_filename
            sys.exit(1)

# Sanity check
assert len(ORDERED_FILE_LIST) == len(FILE_MAP)

if ARGS.opt_unsorted:
    # Put the data into a list in the order in which files were encountered
    STATS_LIST = [patchlib.FILE_DIFF_STATS(path, FILE_MAP[path]) for path in ORDERED_FILE_LIST]
else:
    # Put them in alphabetical order
    STATS_LIST = [patchlib.FILE_DIFF_STATS(path, FILE_MAP[path]) for path in sorted(ORDERED_FILE_LIST)]

print patchlib.list_format_diff_stats(STATS_LIST),
