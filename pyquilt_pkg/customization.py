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

'''Manage quilt customization options'''

import os
import re
import sys

from pyquilt_pkg import cmd_result

QUILT_NO_DIFF_TIMESTAMPS = False

QUILT_NO_DIFF_INDEX = False

_QUILT_CONFIG_DICT = {
        'QUILT_PATCHES': 'patches',
        'QUILT_SERIES': 'series',
        'QUILT_PC': '.pc',
    }

_config_line_re = re.compile(r'(^[^=]+)=(.*)$')

def process_configuration_data(filename=None):
    _QUILT_CONFIG_DICT
    if filename is None:
        for candidate in [os.path.join(os.getenv('HOME'), '.quiltrc'), '/etc/quilt.quiltrc']:
            if os.path.exists(candidate):
                filename = candidate
                break
    if filename is not None:
        if not os.path.isfile(filename):
            sys.stderr.write('%s is not a valid file.\n' % filename)
            sys.exit(cmd_result.ERROR)
        try:
            for line in open(filename).readlines():
                if len(line.strip()) == 0 or line[0] == '#':
                    continue
                key, val = line.strip().split('=', 1)
                _QUILT_CONFIG_DICT[key] = val.strip('"')
        except IOError:
            sys.stderr.write('IO errror reading %s.\n' % filename)
            sys.exit(cmd_result.ERROR)
    # Environment variables take precedence for some
    _QUILT_CONFIG_DICT['QUILT_PATCHES'] = os.getenv('QUILT_PATCHES', _QUILT_CONFIG_DICT['QUILT_PATCHES'])

def get_default_args(parser, key):
    args = _QUILT_CONFIG_DICT.get('QUILT_%s_ARGS' % key.upper(), '')
    return parser.parse_args(args.split())

def merge_default_args(args, parser, key):
    default_args = get_default_args(parser, key)
    # Get dictionary keys from default args as they are a subset of args's
    for arg in default_args.__dict__:
        if not args.__dict__[arg]:
            args.__dict__[arg] = default_args.__dict__[arg]

def get_default_opts(key):
    return _QUILT_CONFIG_DICT.get('QUILT_%s_OPTS' % key.upper(), '')

def get_config(varname, default=None):
    return _QUILT_CONFIG_DICT.get(varname, default)
