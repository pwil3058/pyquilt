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

'''
Provide access to some quilt support scripts if they're intalled
'''

import os

from pyquilt_pkg import cmd_result
from pyquilt_pkg import shell

_QUILT_DIR = None
_QUILT_LIBDIR = None

for bindir in os.getenv('PATH').split(':'):
    if 'quilt' in os.listdir(bindir):
        pdir = os.path.dirname(bindir)
        _cand = os.path.join(pdir, 'share', 'quilt')
        if os.path.isdir(_cand):
            _QUILT_DIR = _cand
            for lib in ['lib', 'lib64']:
                _cand = os.path.join(pdir, lib, 'quilt')
                if os.path.isdir(_cand):
                    _QUILT_LIBDIR = _cand
                    break
            break

def is_available():
    return _QUILT_DIR is not None

_QUILT_REMOVE_TRAILING_WS = None

if is_available():
    _cand = os.path.join(_QUILT_DIR, 'scripts', 'remove-trailing-ws')
    if os.path.isfile(_cand):
        _QUILT_REMOVE_TRAILING_WS = _cand

def get_remove_trailing_ws_path():
    return _QUILT_REMOVE_TRAILING_WS
