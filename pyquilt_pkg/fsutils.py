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

'''Provide utility functions for file manipulation'''

import zlib
import gzip
import bz2
import os

def get_file_contents(srcfile):
    '''
    Get the contents of filename to text after applying decompression
    as indicated by filename's suffix.
    '''
    _root, ext = os.path.splitext(srcfile)
    res = 0
    if ext == '.gz':
        return gzip.open(srcfile).read()
    elif ext == '.bz2':
        bz2f = bz2.BZ2File(srcfile, 'r')
        text = bz2f.read()
        bz2f.close()
        return text
    elif ext == '.xz':
        res, text, serr = shell.run_cmd('xz -cd %s' % srcfile)
    elif ext == '.lzma':
        res, text, serr = shell.run_cmd('lzma -cd %s' % srcfile)
    else:
        return open(srcfile).read()
    if res != 0:
        sys.stderr.write(serr)
    return text

def set_file_contents(filename, text):
    '''
    Set the contents of filename to text after applying compression
    as indicated by filename's suffix.
    '''
    _root, ext = os.path.splitext(filename)
    res = 0
    if ext == '.gz':
        try:
            gzip.open(filename, 'wb').write(text)
            return True
        except IOError, zlib.error:
            return False
    elif ext == '.bz2':
        try:
            bz2f = bz2.BZ2File(filename, 'w')
            text = bz2f.write(text)
            bz2f.close()
            return True
        except IOError:
            return False
    elif ext == '.xz':
        res, text, serr = shell.run_cmd('xz -c', text)
    elif ext == '.lzma':
        res, text, serr = shell.run_cmd('lzma -c', text)
    if res != 0:
        sys.stderr.write(serr)
        return False
    try:
        open(filename, 'w').write(text)
    except IOError:
        return False
    return True

def file_contents_equal(filename, text):
    '''Return whether filename exists and has contents equal to text'''
    if not os.path.isfile(filename):
        return False
    return get_file_contents(filename) == text

def files_in_dir(dirname, recurse=True, exclude_timestamp=True):
    '''Return a list of the files in the given directory.'''
    def _files_in_subdir(subdir):
        files = list()
        for entry in os.listdir(subdir):
            entry_path = os.path.join(subdir, entry)
            if os.path.isdir(entry_path):
                files += _files_in_subdir(entry_path)
            else:
                files.append(entry_path)
        return files
    files = []
    for entry in os.listdir(dirname):
        if os.path.isdir(entry):
            if recurse:
                files += _files_in_subdir(entry)
        elif not exclude_timestamp or not entry == '.timestamp':
            files.append(entry)
    return files

def touch(path):
    '''
    Update path's access/modification times to the current time.
    Create path if necessary.
    ''' 
    if os.path.exists(path):
        os.utime(path, None)
    else:
        open(path, 'w').close()
