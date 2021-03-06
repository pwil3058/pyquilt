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
### Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA

'''Provide an interface to common utility commands'''

import argparse

from pyquilt_pkg import patchlib
from pyquilt_pkg import customization
from pyquilt_pkg import output

PARSER = None

def make_parser():
    global PARSER
    PARSER = argparse.ArgumentParser(description='parse diffstat options', add_help=False)
    PARSER.add_argument('-c', dest='opt_comment', action='store_true')
    #PARSER.add_argument('-d', dest='opt_debug', action='store_true')
    #PARSER.add_argument('-D', dest='opt_dpath', action='store')
    #PARSER.add_argument('-e', dest='opt_stderr', action='store')
    PARSER.add_argument('-f', dest='opt_format', action='store', choices=['0', '1', '2', '4'])
    #PARSER.add_argument('-h', dest='opt_help', action='store_true')
    PARSER.add_argument('-k', dest='opt_no_merge', action='store_true')
    PARSER.add_argument('-l', dest='opt_file_names_only', action='store_true')
    PARSER.add_argument('-m', dest='opt_merge_ins_del', action='store_true')
    PARSER.add_argument('-n', dest='opt_min_fnw', action='store')
    PARSER.add_argument('-N', dest='opt_max_fnw', action='store')
    #PARSER.add_argument('-o', dest='opt_stdout', action='store')
    #PARSER.add_argument('-p', dest='opt_strip', action='store')
    PARSER.add_argument('-q', dest='opt_quiet', action='store_true')
    PARSER.add_argument('-r', dest='opt_rounding', action='store', choices=['0', '1', '2'])
    #PARSER.add_argument('-S', dest='opt_opath', action='store')
    PARSER.add_argument('-t', dest='opt_table', action='store_true')
    PARSER.add_argument('-u', dest='opt_unsorted', action='store_true')
    #PARSER.add_argument('-v', dest='opt_show_progress', action='store_true')
    #PARSER.add_argument('-V', dest='opt_version', action='store_true')
    PARSER.add_argument('-w', dest='opt_max_width', action='store', default='80')

def get_diffstat(text, strip_level, quiet=True):
    if not PARSER:
        make_parser()
    diffstat_options = customization.get_default_opts('diffstat')
    args, leftovers = PARSER.parse_known_args(diffstat_options.split())
    if leftovers and not quiet:
        output.error('diffstat default options: %; ignored\n' % ' '.join(leftovers))
    obj = patchlib.Patch.parse_text(text)
    stats_list = obj.get_diffstat_stats(int(strip_level))
    return stats_list.list_format_string(quiet=args.opt_quiet, comment=args.opt_comment, max_width=int(args.opt_max_width))
