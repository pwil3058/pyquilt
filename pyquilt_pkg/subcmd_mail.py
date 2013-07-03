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
### Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA

import os
import socket
import re
import atexit
import shutil
import time
import email
import email.utils

from pyquilt_pkg import cmd_line
from pyquilt_pkg import cmd_result
from pyquilt_pkg import patchfns
from pyquilt_pkg import customization
from pyquilt_pkg import output
from pyquilt_pkg import shell
from pyquilt_pkg import fsutils
from pyquilt_pkg import putils

parser = cmd_line.SUB_CMD_PARSER.add_parser(
    'mail',
    description='''Create mail messages from a specified range of
        patches, or all patches in the series file, and either store
        them in a mailbox file, or send them immediately. The editor
        is opened with a template for the introduction.
        Please see %s for details.
        When specifying a range of patches, a first patch name of `-'
        denotes the first, and a last patch name of `-' denotes the
        last patch in the series.''' % '/usr/local/share/doc/quilt-0.48/README.MAIL',
)

aparser = parser.add_mutually_exclusive_group(required=True)
aparser.add_argument(
    '--mbox',
    help='''Store all messages in the specified file in mbox format.
        The mbox can later be sent using formail, for example.''',
    dest='opt_mbox',
    metavar='file',
)

aparser.add_argument(
    '--send',
    help='Send the messages directly.',
    dest='opt_send',
    action='store_true',
)

parser.add_argument(
    '-m',
    help='''Text to use as the text in the introduction. When this
        option is used, the editor will not be invoked, and the patches
        will be processed immediately.''',
    dest='opt_message',
    metavar='text',
)

parser.add_argument(
    '--prefix',
    help='''Use an alternate prefix in the bracketed part of the
        subjects generated. Defaults to `patch'.''',
    dest='opt_prefix',
    metavar='prefix',
    default='patch'
)

parser.add_argument(
    '--sender',
    help='''The envelope sender address to use. The address must be of
        the form `user@domain.name'. No display name is allowed.''',
    dest='opt_sender',
    metavar='address',
)

parser.add_argument(
    '--from',
    help='''The value for the From header to use. If no --from
        option is given, the value of the --sender option is used.''',
    dest='opt_from',
    metavar='address',
)

parser.add_argument(
    '--subject',
    help='The value for the Subject header to use.',
    dest='opt_subject',
    metavar='text',
)

parser.add_argument(
    '--to',
    help='Append a recipient to the To header.',
    dest='opt_to',
    metavar='address',
    action='append'
)

parser.add_argument(
    '--cc',
    help='Append a recipient to the Cc header.',
    dest='opt_cc',
    metavar='address',
    action='append'
)

parser.add_argument(
    '--bcc',
    help='Append a recipient to the Bcc header.',
    dest='opt_bcc',
    metavar='address',
    action='append'
)

_DEFAULT_SIG_FILE = os.path.join(os.getenv('HOME'), '.signature')

parser.add_argument(
    '--signature',
    help='''Append the specified signature to messages (defaults to
        ~/.signature if found; use `-' for no signature).''',
    dest='opt_signature',
    metavar='file',
    default=_DEFAULT_SIG_FILE if os.path.isfile(_DEFAULT_SIG_FILE) else None
)

parser.add_argument(
    '--reply-to',
    help='Add the appropriate headers to reply to the specified message.',
    dest='opt_reply_to',
    metavar='message',
)

parser.add_argument(
    '--charset',
    help='Charset to use in the mail.',
    dest='opt_charset',
    metavar='name',
)

parser.add_argument(
    'first_patch',
    nargs='?',
)

parser.add_argument(
    'last_patch',
    nargs='?',
)

def clean_up_subject(text):
    cre = re.compile('^(\s*(fwd:|fw:|re:|aw:|\[[^]]*\])[ \t]*)+', flags=re.I)
    return cre.sub('', text.lstrip())

def join_lines(text):
    lines = [line.strip() for line in text.splitlines()]
    return ' '.join(lines)

def is_ascii(text):
    for char in text:
        if (ord(char) < 32 and char != '\t') or (ord(char) > 126):
            return False
    return True

def encode_display(display, charset):
    etext = '=?%s?q?' % charset
    for char in display:
        if (ord(char) < 33 and char != '\t') or (ord(char) > 126) or (char == '?'):
            etext += '={0:02X}'.format(ord(char))
        else:
            etext += char
    return etext + '?='

def format_address(display, address, charset):
    if not display:
        return address
    elif not is_ascii(display):
        display = encode_display(display, charset)
    return email.utils.formataddr((display, address))

def message_from_patch(text, charset):
    header = putils.get_patch_hdr_fm_text(text)
    subject = email.message_from_string(header)['Subject']
    if subject:
        msg = email.message_from_string(text)
        del msg['Subject']
    else:
        body = desc = ''
        in_desc = False
        header_lines = header.splitlines(True)
        for line in header_lines:
            if line.startswith('EDESC'):
                in_desc = False
            elif in_desc:
                desc += line
            elif line.startswith('DESC'):
                in_desc = True
            else:
                body += line
        if desc:
            subject = join_lines(desc)
            msg = email.message_from_string(body + text[len(header):])
        if not subject:
            lineno = 0
            for line in header_lines:
                if not line.strip():
                    break
                lineno += 1
            para = header if lineno == len(header_lines) else ''.join(header_lines[:lineno])
            if para and len(para) < 150:
                subject = join_lines(para)
                msg = email.message_from_string(text[lineno:])
        if not subject:
            return False
    msg['Replace-Subject'] = clean_up_subject(subject)
    # Extract potential addresses from the patch (including those that
    # may have been already processes by email.message_from_string()
    tos = msg.get_all('To')
    if tos is None:
        tos = []
    else:
        del msg['To']
    ccs = []
    for field in ['Cc', 'Signed-off-by', 'Acked-by']:
        items = msg.get_all(field)
        if items:
            ccs += items
        del msg[field]
    for line in header.splitlines():
        if line.startswith('To:'):
            tos.append(line[3:])
        elif line.startswith('Cc:') or line.startswith('Signed-off-by:') or line.startswith('Acked-by:'):
            ccs.append(line[line.index(':') + 1:])
    logname_ptn = os.getenv('LOGNAME', os.getlogin()) + '@'
    for item in tos:
        display, address = email.utils.parseaddr(item)
        if address and not address.startswith(logname_ptn):
            msg['Recipient-To'] = format_address(display, address, charset)
    for item in ccs:
        display, address = email.utils.parseaddr(item)
        if address and not address.startswith(logname_ptn):
            msg['Recipient-Cc'] = format_address(display, address, charset)
    return msg

def msgid(args):
    secs = time.time()
    nsecs = int((secs % 1) * 1000000000)
    domain = re.sub('^[^@]*@', '', args.opt_sender_address)
    fmtstr = '+%Y%m%d%H%M%S.{0:09}@{1}'.format(nsecs, domain)
    return time.strftime(fmtstr, time.gmtime(secs))

def in_reply_to_header(message):
    message_id = message['Message-ID'].lstrip()
    return '' if not message_id else 'In-Reply-To: %s' % message_id

def get_reference_to(message):
    message_id = message.get('Message-ID', '').lstrip()
    references = message.get('References', '').lstrip()
    if not references:
        in_reply_to = message.get('In-Reply-To', '').lstrip()
        if in_reply_to and in_reply_to.count('@') != 2:
            references = in_reply_to
    if not references:
        references = message_id
    elif message_id:
        references = '%s$\n %s' % (references, message_id)
    return references

def references_header(message):
    references = get_reference_to(message)
    return '' if not references else 'References: %s' % references

def extract_recipients(message, classes=['To', 'Cc', 'Bcc']):
    recipients = []
    for eclass in classes:
        items = message.get_all(eclass)
        del message[eclass]
        if item in items if items else []:
            display, address = email.utils.parseaddr(item)
            if address:
                recipients.append(item)
    return ' '.join(recipients)

def remove_empty_headers(message):
    """Remove any empty headers from the email message"""
    for key in message.keys():
        items = message.get_all(key)
        non_empty_items = []
        for item in items:
            if item.strip():
                non_empty_items.append(item)
        if len(items) != len(non_empty_items):
            del message[key]
            for item in non_empty_items:
                message[key] = items
    return message

def process_mail(message, args):
    if args.opt_send:
        sendmail_cmd = '%s %s --f %s ' % (os.getenv('QUILT_SENDMAIL', 'sendmail'), os.getenv('QUILT_SENDMAIL_ARGS', ''), args.opt_sender)
        sendmail_cmd += extract_recipients(message)
        output.write(sendmail_cmd)
        del message['Bcc']
        result = shell.run_cmd(sendmail_cmd, message.as_string(False))
        output.write(result.stdout)
        output.error(result.stderr)
    else:
        from_date = time.strftime('+%a %b %e %H:%M:%S %Y')
        fobj = open(args.opt_mbox, 'a')
        fobj.write('From %s %s\n' % (args.opt_sender_address, from_date))
        for field, value in message.items():
            fobj.write('%s: %s\n' % (field, value))
        fobj.write('\n')
        for line in message.get_payload().splitlines(True):
            fobj.write(re.sub('^From ', '>From ', line))
        fobj.close()

def run_mail(args):
    patchfns.chdir_to_base_dir()
    if not shell.which('formail'):
        output.write("You have to install 'formail' to use 'quilt mail'")
        return cmd_result.ERROR
    if not args.opt_signature or args.opt_signature == '-':
        args.opt_signature = None
    else:
        try:
            args.opt_signature = open(args.opt_signature).read()
        except IOError as edata:
            output.perror(edata)
    if args.first_patch:
        args.first_patch = patchfns.find_first_patch() if args.first_patch == '-' else patchfns.find_patch(args.first_patch)
        if not args.first_patch:
            return cmd_result.ERROR
        if not args.last_patch:
            args.last_patch = args.first_patch
        else:
            args.last_patch = patchfns.find_last_patch() if args.last_patch == '-' else patchfns.find_patch(args.last_patch)
            if not args.last_patch:
                return cmd_result.ERROR
    if not args.opt_sender:
        hostname = socket.gethostname()
        args.opt_sender = '%s@%s' % (os.getenv('LOGNAME', os.getlogin()), hostname)
        if not re.match('^\S+@\S+\.\S+$', args.opt_sender):
            output.error('Could not determine the envelope sender address. Please use --sender.\n')
            return cmd_result.ERROR
    _dummy, args.opt_sender_address = email.utils.parseaddr(args.opt_sender)
    if not args.opt_charset:
        lc_all = os.getenv('LC_ALL', patchfns.ORIGINAL_LANG)
        if lc_all and lc_all.endswith('UTF-8'):
            args.opt_charset = 'UTF-8'
        else:
            args.opt_charset = 'ISO-8859-15'
    patches = patchfns.cat_series()
    if args.first_patch:
        first_index = patches.index(args.first_patch)
        last_index = patches.index(args.last_patch)
        if last_index < first_index:
            output.error('Patch %s not applied before patch %s\n' % (patchfns.print_patch(args.first_patch), patchfns.print_patch(args.first_patch)))
            return cmd_result.ERROR
        patches = patches[first_index:last_index + 1]
    total = len(patches)
    tmpdir = patchfns.gen_tempfile(asdir=True)
    atexit.register(lambda: not os.path.exists(tmpdir) or shutil.rmtree(tmpdir, ignore_errors=True))
    subject_map = {}
    patch_msgs = []
    for patch in patches:
        contents = fsutils.get_file_contents(patchfns.patch_file_name(patch))
        mailmsg = message_from_patch(contents, args.opt_charset)
        if mailmsg is False:
            subject = None
        else:
            patch_msgs.append(mailmsg)
            subject = mailmsg['Replace-Subject']
        if mailmsg is False or not subject:
            output.error('Unable to extract a subject header from %s\n' % patchfns.print_patch(patch))
            return cmd_result.ERROR
        if subject in subject_map:
            subject_map[subject].append(patch)
        else:
            subject_map[subject] = [patch]
    if len(subject_map) != len(patches):
        duplicates = []
        for key in sorted(subject_map):
            plist = subject_map[key]
            if len(plist) > 1:
                duplicates += plist
        output.error('Patches %s have duplicate subject headers.\n' % ', '.join([patchfns.print_patch(dup) for dup in duplicates]))
        return cmd_result.ERROR
    if args.opt_reply_to:
        if not os.path.exists(args.opt_reply_to):
            output.error('File %s does not exist\n' % args.opt_reply_to)
            return cmd_result.ERROR
        args.opt_reply_to = email.message_from_string(open(args.opt_reply_to).read())
        if not args.opt_subject:
            repto_subject = args.opt_reply_to['Subject']
            args.opt_subject = 'Re: %s' % re.sub('^([ \t]*[rR][eE]:[ \t]*)', '', repto_subject)
    intro = 'Message-Id: <%s>\n' % msgid(args)
    intro += 'User-Agent: pyquilt\n'
    last_ts = time.localtime()
    intro += time.strftime('Date: %a, %d %b %Y %H:%M:%S %z\n', last_ts)
    intro += 'From: %s\n' % (args.opt_from if args.opt_from else args.opt_sender)
    intro += 'To: %s\n' % (', '.join(args.opt_to) if args.opt_to else '')
    intro += 'Cc: %s\n' % (', '.join(args.opt_cc) if args.opt_cc else '')
    intro += 'Bcc: %s\n' % (', '.join(args.opt_bcc) if args.opt_bcc else '')
    if args.opt_reply_to:
        intro += in_reply_to_header(args.opt_reply_to)
        intro += references_header(args.opt_reply_to)
    intro += 'Subject-Prefix: [%s @num@/@total@]\n' % args.opt_prefix
    intro += 'Subject: %s\n\n' % (args.opt_subject if args.opt_subject else '')
    intro += ('%s\n\n' % args.opt_message) if args.opt_message else ''
    intro += ('-- \n%s\n' % args.opt_signature) if args.opt_signature else ''
    intro_message = email.message_from_string(intro)
    intro_message.set_charset(args.opt_charset)
    if not args.opt_message:
        introfile = patchfns.gen_tempfile()
        open(introfile, 'w').write(intro_message.as_string())
        result = shell.run_cmd('%s %s' % (os.getenv('EDITOR'), introfile))
        output.write(result.stdout)
        output.error(result.stderr)
        intro_message = email.message_from_string(open(introfile).read(), charset=args.opt_charset)
        os.remove(introfile)
        if result.eflags != 0:
            return cmd_result.ERROR
    subject = join_lines(intro_message['Subject'])
    if not subject:
        if not args.opt_message:
            savefile = patchfns.gen_tempfile()
            open(savefile, 'w').write(intro_message.as_string())
            output.error('Introduction has no subject header (saved as %s)\n' % savefile)
        else:
            output.error('Introduction has no subject header\n')
        return cmd_result.ERROR
    if args.opt_mbox:
        fsutils.touch(args.opt_mbox)
    subject_prefix = email.utils.quote(join_lines(intro_message['Subject-Prefix']))
    subject_prefix += ' ' if subject_prefix else ''
    subject_prefix = re.sub('@total@', str(total), subject_prefix)
    del intro_message['Subject-Prefix']
    pnum_fmt = '{0:0%s}' % len(str(total))
    pfx = re.sub('@num@', pnum_fmt.format(0), subject_prefix)
    intro_message.replace_header('Subject', pfx + intro_message['Subject'])
    remove_empty_headers(intro_message)
    for key in ['To', 'Cc', 'Bcc']:
        # Consolidate up the various recipient fields
        values = intro_message.get_all(key)
        if values:
            del intro_message[key]
            intro_message[key] = ', '.join(values)
    process_mail(intro_message, args)
    pnum = 0
    for msg in patch_msgs:
        msg.add_header('Content-Disposition', 'inline',  filename=patches[pnum])
        for key in intro_message.keys():
            if key.lower() not in ['message-id', 'references', 'in-reply-to', 'subject']:
                for value in intro_message.get_all(key):
                    msg[key] = value
        msg['References'] = get_reference_to(intro_message)
        msg.set_charset(args.opt_charset)
        for aclass in ['To', 'Cc', 'Bcc']:
            rclass = 'Recipient-' + aclass
            if msg.has_key(rclass):
                msg[aclass] = ',\n '.join(msg.get_all(rclass))
                del msg[rclass]
        pnum += 1
        ppfx = re.sub('@num@', pnum_fmt.format(pnum), subject_prefix)
        msg['Message-Id'] = msgid(args)
        msg['Subject'] = '%s%s' % (ppfx, msg['Replace-Subject']) if ppfx else msg['Replace-Subject']
        del msg['Replace-Subject']
        remove_empty_headers(msg)
        process_mail(msg, args)
    return cmd_result.OK

parser.set_defaults(run_cmd=run_mail)
