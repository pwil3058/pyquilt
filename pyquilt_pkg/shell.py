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

import os
import signal
import subprocess

from pyquilt_pkg import cmd_result
from pyquilt_pkg import customization

def run_cmd(cmd, input_text=None, use_shell=True):
    """Run the given command and report the outcome as a cmd_result tuple.
    If input_text is not None pass it to the command as standard input.
    """
    if not cmd:
        return cmd_result.Result(0, None, None)
    try:
        oldterm = os.environ['TERM']
        os.environ['TERM'] = "dumb"
    except LookupError:
        oldterm = None
    is_posix = os.name == 'posix'
    if is_posix:
        savedsh = signal.getsignal(signal.SIGPIPE)
        signal.signal(signal.SIGPIPE, signal.SIG_DFL)
    if not isinstance(cmd, str):
        use_shell = False
    sub = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
          stderr=subprocess.PIPE, shell=use_shell, close_fds=is_posix, bufsize=-1)
    outd, errd = sub.communicate(input_text)
    if is_posix:
        signal.signal(signal.SIGPIPE, savedsh)
    if oldterm:
        os.environ['TERM'] = oldterm
    return cmd_result.Result(eflags=sub.returncode, stdout=outd, stderr=errd)

if os.name == 'nt' or os.name == 'dos':
    def _which(cmd):
        """Return the path of the executable for the given command"""
        for dirpath in os.environ['PATH'].split(os.pathsep):
            potential_path = os.path.join(dirpath, cmd)
            if os.path.isfile(potential_path) and \
               os.access(potential_path, os.X_OK):
                return potential_path
        return None

    NT_EXTS = ['.bat', '.bin', '.exe']

    def which(cmd):
        """Return the path of the executable for the given command"""
        path = _which(cmd)
        if path:
            return path
        _, ext = os.path.splitext(cmd)
        if ext in NT_EXTS:
            return None
        for ext in NT_EXTS:
            path = _which(cmd + ext)
            if path is not None:
                return path
        return None
else:
    def which(cmd):
        """Return the path of the executable for the given command"""
        for dirpath in os.environ['PATH'].split(os.pathsep):
            potential_path = os.path.join(dirpath, cmd)
            if os.path.isfile(potential_path) and \
               os.access(potential_path, os.X_OK):
                return potential_path
        return None
