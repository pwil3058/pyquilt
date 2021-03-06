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
from pyquilt_pkg import subcmd_applied
from pyquilt_pkg import subcmd_import
from pyquilt_pkg import subcmd_header
from pyquilt_pkg import subcmd_fork
from pyquilt_pkg import subcmd_diff
from pyquilt_pkg import subcmd_revert
from pyquilt_pkg import subcmd_files
from pyquilt_pkg import subcmd_edit
from pyquilt_pkg import subcmd_snapshot
from pyquilt_pkg import subcmd_top
from pyquilt_pkg import subcmd_patches
from pyquilt_pkg import subcmd_remove
from pyquilt_pkg import subcmd_fold
from pyquilt_pkg import subcmd_next
from pyquilt_pkg import subcmd_previous
from pyquilt_pkg import subcmd_unapplied
from pyquilt_pkg import subcmd_mail
from pyquilt_pkg import subcmd_grep
