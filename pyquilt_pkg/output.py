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

'''Output wrapper to address buffering issues, paging, etc.'''

import subprocess
import sys
import os
import errno

_PAGER = None

def start_pager():
    global _PAGER
    QUILT_PAGER = os.getenv('QUILT_PAGER', os.getenv('GIT_PAGER', 'less'))
    if QUILT_PAGER and QUILT_PAGER != 'cat':
        os.putenv('LESS', '-FRSX')
        _PAGER = subprocess.Popen([QUILT_PAGER], stdin=subprocess.PIPE)

def wait_for_pager():
    global _PAGER
    if _PAGER is not None:
        _PAGER.stdin.close()
        rval = _PAGER.wait()
        _PAGER = None
        return rval

def write(text):
    if _PAGER:
        try:
            _PAGER.stdin.write(text)
        except IOError as edata:
            if edata.errno != errno.EPIPE:
                raise edata
    else:
        sys.stdout.write(text)
        sys.stdout.flush()

_SWALLOW_ERRORS = False

def set_swallow_errors(value):
    global _SWALLOW_ERRORS
    _SWALLOW_ERRORS = value

def error(text):
    if not _SWALLOW_ERRORS:
        sys.stderr.write(text)
        sys.stderr.flush()

def perror(exception, prefix=None):
    if prefix:
        error('%s: %s\n' % (prefix, exception.strerror))
    else:
        try:
            error('%s: %s\n' % (exception.filename, exception.strerror))
        except AttributeError:
            error('%s\n' % exception.strerror)
