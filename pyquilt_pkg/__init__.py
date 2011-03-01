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
Library functions that are ony of interest CLI programs
'''

# This should be the only place that subcmd_* modules should be imported
# as this is sufficient to activate them.
from pyquilt_pkg import subcmd_new
from pyquilt_pkg import subcmd_refresh
from pyquilt_pkg import subcmd_push
from pyquilt_pkg import subcmd_pop
from pyquilt_pkg import subcmd_add
from pyquilt_pkg import subcmd_rename
from pyquilt_pkg import subcmd_delete
from pyquilt_pkg import subcmd_setup
from pyquilt_pkg import subcmd_annotate
from pyquilt_pkg import subcmd_series
