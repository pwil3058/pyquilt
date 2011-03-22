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

'''Provide facilities for colourizing output'''

from pyquilt_pkg import customization

def ansi_colour_seq(num):
    return '\033[%dm' % num

CLEAR = ansi_colour_seq(00)
_COLOURIZE = False

MAP = {
    'diff_hdr' : ansi_colour_seq(32),
    'diff_add' : ansi_colour_seq(36),
    'diff_mod' : ansi_colour_seq(35),
    'diff_rem' : ansi_colour_seq(35),
    'diff_hunk' : ansi_colour_seq(33),
    'diff_ctx' : ansi_colour_seq(35),
    'diff_cctx' : ansi_colour_seq(33),
    'patch_offs' : ansi_colour_seq(33),
    'patch_fuzz' : ansi_colour_seq(35),
    'patch_fail' : ansi_colour_seq(31),
    'patch_applied' : ansi_colour_seq(32),
    'series_app' : ansi_colour_seq(32),
    'series_top' : ansi_colour_seq(33),
    'series_una' : ansi_colour_seq(00),
    'clear' : ansi_colour_seq(00),
}

def set_up():
    global _COLOURIZE
    config_str = customization.get_config('QUILT_COLORS', '')
    for cmap in config_str.split(':'):
        if '=' in cmap:
            name, num = cmap.split('=')
            MAP[name] = ansi_colour_seq(num)
    _COLOURIZE = True

def wrap(text, category):
    if not _COLOURIZE:
        return text
    cseq = MAP.get(category, None)
    if not cseq:
        return text
    else:
        return cseq + text + CLEAR
