#!/usr/bin/env python
### Copyright (C) 2003, 2004, 2005, 2006, 2007, 2008
### Andreas Gruenbacher <agruen@suse.de>, SuSE Labs
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


'''
Provide functions to replace the features provided by quilt's
backup-files program.
'''

import os
import sys
import errno
import tempfile
import stat
import collections
from pyquilt_pkg import output

def _create_parents(filename):
    last_sep = filename.rfind(os.sep)
    if last_sep == -1 or os.path.exists(filename[:last_sep]):
        return
    next_sep = filename.find(os.sep)
    while next_sep != -1:
        dirname = filename[:next_sep]
        if not os.path.isdir(dirname):
            try:
                os.mkdir(dirname, 0777)
            except OSError:
                output.error('Could not create directory %s.\n' % dirname)
                sys.exit(1)
        next_sep = filename.find(os.sep, next_sep + 1)

def _remove_parents(filename):
    last_sep = filename.rfind(os.sep)
    while last_sep != -1:
        dirname = filename[0:last_sep]
        try:
            os.rmdir(dirname)
        except OSError as edata:
            if edata.errno == errno.ENOTEMPTY:
                return
            else:
                raise
        last_sep = dirname.rfind(os.sep)

def _copy_fd(from_fd, to_fd):
    CNT = 16384
    # let clients catch the exceptions
    while True:
        data = os.read(from_fd, CNT)
        if len(data) == 0:
            break
        total = 0
        while total < len(data):
            total += os.write(to_fd, data[total:])
    return True

def _creat(name, mode=0777):
    return os.open(name, os.O_WRONLY|os.O_CREAT|os.O_TRUNC, mode)

def _copy_file(from_fn, stat_data, to_fn):
    is_ok = True;
    try:
        from_fd = os.open(from_fn, os.O_RDONLY)
    except OSError as edata:
        output.perror(edata)
        return False
    try:
        # make sure we don't inherit this file's mode.
        os.unlink(to_fn)
    except OSError as edata:
        if edata.errno != errno.ENOENT:
            output.perror(edata)
            return False
    try:
        to_fd = _creat(to_fn, mode=stat_data.st_mode)
    except OSError as edata:
        output.perror(edata);
        os.close(from_fd);
        return False
    os.fchmod(to_fd, stat_data.st_mode)
    try:
        _copy_fd(from_fd, to_fd)
    except OSError as edata:
        output.perror(edata, '%s -> %s' % (from_fn, to_fn))
        os.unlink(to_fn)
        return False
    finally:
        os.close(from_fd)
        os.close(to_fd)
    return True

def _link_or_copy_file(from_fn, stat_data, to_fn):
    try:
        os.link(from_fn, to_fn)
    except OSError as edata:
        if edata.errno not in [errno.EXDEV, errno.EPERM, errno.EMLINK, errno.ENOSYS]:
            output.perror(edata, 'Could not link file \`%s\' to \`%s\'' % (from_fn, to_fn))
            return False
    else:
        return True
    return _copy_file(from_fn, stat_data, to_fn)

def ensure_nolinks(filename):
    try:
        stat_data = os.stat(filename)
    except OSError as edata:
        output.perror(edata)
        return False
    if stat_data.st_nlink > 1:
        from_fd = to_fd = None
        try:
            from_fd = os.open(filename, os.O_RDONLY)
            # Temp file name is "path/to/.file.XXXXXX"
            to_fd, tmpname = tempfile.mkstemp(prefix=os.path.abspath(filename))
            _copy_fd(from_fd, to_fd)
            os.fchmod(to_fd, stat_data.st_mode)
            os.rename(tmpname, filename)
            return True;
        except OSError as edata:
            output.perror(edata)
            return False
        finally:
            if from_fd is not None:
                os.close(from_fd);
            if to_fd is not None:
                os.close(to_fd);
    else:
        return True

# Backup
def backup(bu_dir, filelist, verbose=False):
    def backup_file(file_nm):
        backup = os.path.join(bu_dir, file_nm)
        try:
            stat_data = os.stat(file_nm)
        except OSError as edata:
            missing_file = edata.errno == errno.ENOENT
        else:
            missing_file = False
        try:
            os.unlink(backup)
        except OSError as edata:
            if edata.errno != errno.ENOENT:
                output.perror(edata)
                return False
        _create_parents(backup)
        if missing_file:
            if verbose:
                output.write('New file %s\n' % file_nm)
            try:
                os.close(_creat(backup, mode=0666))
            except OSError as edata:
                output.perror(edata)
                return False
        else:
            if verbose:
                output.write('Copying %s\n' % file_nm)
            if stat_data.st_nlink == 1:
                result = _copy_file(file_nm, stat_data, backup)
                if result is not True:
                    return result
            else:
                result = _link_or_copy_file(file_nm, stat_data, backup)
                if result is not True:
                    return result
                result = ensure_nolinks(file_nm)
                if result is not True:
                    return result
            os.utime(backup, (stat_data.st_mtime, stat_data.st_mtime,))
        return True
    for filename in filelist:
        if not backup_file(filename):
            return False
    return True

# Restore
def restore(bu_dir, filelist=None, to_dir='.', verbose=False, keep=False, touch=False):
    def restore_file(file_nm):
        backup = os.path.join(bu_dir, file_nm)
        file_nm = file_nm if to_dir is None else os.path.relpath(os.path.join(to_dir, file_nm))
        _create_parents(file_nm)
        try:
            stat_data = os.stat(backup)
        except OSError as edata:
            output.perror(edata, backup)
            return False
        if stat_data.st_size == 0:
            try:
                os.unlink(file_nm)
            except OSError as edata:
                if edata.errno != errno.ENOENT:
                    output.perror(edata, file_nm)
                    return False
            if verbose:
                output.write('Removing %s\n' % file_nm)
            if not keep:
                os.unlink(backup)
                _remove_parents(backup)
        else:
            if verbose:
                output.write('Restoring %s\n' % file_nm)
            try:
                os.unlink(file_nm)
            except OSError as edata:
                if edata.errno != errno.ENOENT:
                    raise
            if not _link_or_copy_file(backup, stat_data, file_nm):
                return False
            if not keep:
                os.unlink(backup)
                _remove_parents(backup)
            if touch:
                os.utime(file_nm, None)
            else:
                os.utime(file_nm, (stat_data.st_mtime, stat_data.st_mtime))
        return True
    if not os.path.isdir(bu_dir):
        return False
    status = True
    if filelist is None or len(filelist) == 0:
        def onerror(exception):
            raise exception
        try:
            for basedir, dirnames, filenames in os.walk(bu_dir, onerror=onerror):
                reldir = '' if basedir == bu_dir else os.path.relpath(basedir, bu_dir)
                for filename in filenames:
                    if not restore_file(os.path.join(reldir, filename)):
                        return False
        except OSError as edata:
            output.perror(edata)
            return False
    else:
        for filename in filelist:
            if not restore_file(filename):
                return False
    return True

# Delink
def ensure_nolinks_in_dir(in_dir, verbose=False):
    def onerror(exception):
        raise exception
    if not os.path.isdir(in_dir):
        return False
    try:
        for basedir, dirnames, filenames in os.walk(in_dir, onerror=onerror):
            for filename in filenames:
                filename = os.path.join(basedir, filename)
                if verbose:
                    output.write('Delinking %s\n' % filename)
                if not ensure_nolinks(filename):
                    return False
    except IOError as edata:
        output.perror(edata)
        return False
    return True

# Remove
def remove(bu_dir, filelist=False, verbose=False):
    '''Remove backup files'''
    def remove_file(backup):
        try:
            if verbose:
                output.write('Removing %s\n' % backup)
            os.unlink(backup)
        except OSError as edata:
            output.perror(edata, backup)
            return False
        try:
            _remove_parents(backup)
        except IOError as edata:
            output.perror(edata, backup)
            return False
        return True
    if not os.path.isdir(bu_dir):
        return False
    status = True
    if filelist is None or len(filelist) == 0:
        def onerror(exception):
            raise exception
        try:
            for basedir, dirnames, filenames in os.walk(bu_dir):
                for filename in filenames:
                    if not remove_file(os.path.join(basedir, filename)):
                        return False
        except IOError as edata:
            output.perror(edata)
            return False
    else:
        for filename in filelist:
            if not remove_file(os.path.join(bu_dir, filename)):
                return False
    return True
