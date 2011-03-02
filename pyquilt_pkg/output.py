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

'''Output wrapper to address buffering issues, paging, etc.'''

import subprocess
import sys
import os

_PAGER = None

def start_pager():
    global _PAGER
    QUILT_PAGER = os.getenv('QUILT_PAGER', os.getenv('GIT_PAGER', 'less'))
    if QUILT_PAGER and QUILT_PAGER != 'cat':
        os.putenv('LESS', '-FRSX')
        _PAGER = subprocess.Popen([QUILT_PAGER], stdin=subprocess.PIPE)

def wait_for_pager():
    if _PAGER is not None:
        _PAGER.stdin.close()
        return _PAGER.wait()

def write(text):
    if _PAGER:
        _PAGER.stdin.write(text)
    else:
        sys.stdout.write(text)
        sys.stdout.flush()

def error(text):
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
