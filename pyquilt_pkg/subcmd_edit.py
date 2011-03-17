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

import os

from pyquilt_pkg import cmd_line
from pyquilt_pkg import cmd_result
from pyquilt_pkg import patchfns
from pyquilt_pkg import customization
from pyquilt_pkg import output
from pyquilt_pkg import shell

parser = cmd_line.SUB_CMD_PARSER.add_parser(
    'edit',
    description='''Edit the specified file(s) in $EDITOR (%s) after
        adding it (them) to the topmost patch.''' % os.getenv('EDITOR', 'None'),
)

parser.add_argument(
    'filelist',
    help='File(s) to be added and edited.',
    metavar='file',
    nargs='+',
)

def run_edit(args):
    patchfns.chdir_to_base_dir()
    if patchfns.pyquilt_command('add %s' % ' '.join(args.filelist)) not in [0, 2]:
        return cmd_result.ERROR
    efilelist = args.filelist if not patchfns.SUBDIR else [os.path.join(patchfns.SUBDIR, fnm) for fnm in args.filelist]
    os.environ['LANG'] = patchfns.ORIGINAL_LANG
    result = shell.run_cmd('%s %s' % (os.getenv('EDITOR'), ' '.join(efilelist)))
    output.error(result.stderr)
    output.write(result.stdout)
    status = cmd_result.OK
    for filename in args.filelist:
        efname = filename if not patchfns.SUBDIR else os.path.join(patchfns.SUBDIR, filename)
        if not os.path.exists(efname):
            patchfns.pyquilt_command('revert %s' % filename)
            status = cmd_result.ERROR
    return status

parser.set_defaults(run_cmd=run_edit)
