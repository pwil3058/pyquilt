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

PARSER = argparse.ArgumentParser(description='Check a patch for addition of trailing white space.')

PARSER.add_argument(
    '--dry-run',
    help='report only.',
    dest='opt_dry_run',
    action='store_true',
)

PARSER.add_argument(
    'arg_patch_file',
    help='The name of the patch file to be processed.',
    metavar='patch',
    nargs='?',
)

ARGS = PARSER.parse_args()

if not ARGS.arg_patch_file:
    text = sys.stdin.read()
elif os.path.isfile(ARGS.arg_patch_file):
    text = open(ARGS.arg_patch_file).read()

try:
    patch = patchlib.Patch.parse_text(text)
except patchlib.ParseError as pedata:
    print 'ERROR:', pedata.message, 'LINE NO:', pedata.lineno
    sys.exit(1)

if ARGS.opt_dry_run:
    reports = patch.report_trailing_whitespace(strip_level=1)
    for filename, bad_lines in reports:
        if len(bad_lines) > 1:
            sys.stderr.write('Warning: trailing whitespace in lines %s of %s\n' % (','.join(bad_lines), filename))
        else:
            sys.stderr.write('Warning: trailing whitespace in line %s of %s\n' % (bad_lines[0], filename))
else:
    reports = patch.fix_trailing_whitespace(strip_level=1)
    if not ARGS.arg_patch_file:
        sys.stdout.write(str(patch))
    else:
        open(ARGS.arg_patch_file, 'w').write(str(patch))
    for filename, bad_lines in reports:
        if len(bad_lines) > 1:
            sys.stderr.write('Removing trailing whitespace from lines %s of %s\n' % (','.join(bad_lines), filename))
        else:
            sys.stderr.write('Removing trailing whitespace from line %s of %s\n' % (bad_lines[0], filename))

sys.exit(0 if len(reports) == 0 else 1)
