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
Provide command line parsing mechanism including provision of a
mechanism for sub commands to add their components.
'''

import argparse
        
PARSER = argparse.ArgumentParser(description='Manage stacked patches')

PARSER.add_argument('--version', action='version', version='0.1')

PARSER.add_argument(
    '--quiltrc',
    help='''Use the specified configuration file instead of ~/.quiltrc (or
    /etc/pyquilt.pyquiltrc if ~/.quiltrc does not exist).  See the pdf
    documentation for details about its possible contents.  The
    special value \"-\" causes pyquilt not to read any configuration
    file.''',
    metavar='file'
)

SUB_CMD_PARSER = PARSER.add_subparsers(title='commands')
