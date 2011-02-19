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
Command return values
'''

import collections

Result = collections.namedtuple('Result', ['eflags', 'stdout', 'stderr'])

OK = 0
WARNING, ERROR, SUGGEST_FORCE, SUGGEST_REFRESH, SUGGEST_RENAME, \
SUGGEST_DISCARD, SUGGEST_EDIT, SUGGEST_MERGE, \
SUGGEST_RECOVER = [2 ** bit for bit in range(9)]
SUGGEST_ALL = (SUGGEST_RECOVER * 2) - 1 - WARNING|ERROR
SUGGEST_FORCE_OR_REFRESH = SUGGEST_FORCE | SUGGEST_REFRESH
WARNING_SUGGEST_FORCE = WARNING | SUGGEST_FORCE
ERROR_SUGGEST_FORCE = ERROR | SUGGEST_FORCE
WARNING_SUGGEST_REFRESH = WARNING | SUGGEST_REFRESH
ERROR_SUGGEST_REFRESH = ERROR | SUGGEST_REFRESH
WARNING_SUGGEST_FORCE_OR_REFRESH = WARNING | SUGGEST_FORCE_OR_REFRESH
ERROR_SUGGEST_FORCE_OR_REFRESH = ERROR | SUGGEST_FORCE_OR_REFRESH
SUGGEST_FORCE_OR_RENAME = SUGGEST_FORCE | SUGGEST_RENAME
SUGGEST_MERGE_OR_DISCARD = SUGGEST_MERGE | SUGGEST_DISCARD

BASIC_VALUES_MASK = OK | WARNING | ERROR
