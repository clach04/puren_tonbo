#!/usr/bin/env python
# -*- coding: us-ascii -*-
# vim:ts=4:sw=4:softtabstop=4:smarttab:expandtab
"""Command line tool to encrypt/decrypt Puren Tonbo files (Tombo CHI Blowfish files, VimCrypt, AES-256.zip, etc.)

    python -m puren_tonbo.tools.ptcipher -h
    ptcipher -h
"""

import datetime
import os
from optparse import OptionParser
import sys
import tempfile
import time

import puren_tonbo
from puren_tonbo import simple_dos2unix, simple_unix2dos
import puren_tonbo.ui
from puren_tonbo.tools import ptgrep

is_py3 = sys.version_info >= (3,)

log = puren_tonbo.log_setup(__file__)

def file_replace(src, dst):
    if is_py3:
        os.replace(src, dst)
    else:
        # can't use rename on Windows if file already exists.
        # Non-Atomic but try and be as safe as possible
        # aim to avoid clobbering existing files, rather than handling race conditions with concurrency

        if os.path.exists(dst):
            dest_exists = True
            t = tempfile.NamedTemporaryFile(
                mode='wb',
                dir=os.path.dirname(dst),
                prefix=os.path.basename(dst) + datetime.datetime.now().strftime('%Y%m%d_%H%M%S'),
                delete=False
            )
            tmp_backup = t.name
            t.close()
            os.remove(tmp_backup)
            os.rename(dst, tmp_backup)
        else:
            dest_exists = False
        os.rename(src, dst)
        if dest_exists:
            os.remove(tmp_backup)


ptcipher_examples = """
Examples:

Show all supported formats

    ptcipher --list-formats

Quick demos:

    ptcipher --cipher rot13 --encrypt -p password_ignored README.md
    ptcipher -p password_ignored puren_tonbo/tests/data/aesop.rot13

    ptcipher --password password --decrypt puren_tonbo/tests/data/aesop.chi
    ptcipher --password password --decrypt puren_tonbo/tests/data/aesop_linux_7z.aes256.zip

    ptcipher --cipher jenc --encrypt -p password README.md -o README.md.jenc

    # NOTE underscore in cipher
    ptcipher --cipher .u001_jenc --encrypt -p password README.md -o README.md.jenc
    ptcipher --cipher .u001_jenc --encrypt -p password README.md -o README.md.u001.jenc
    ptcipher --encrypt -p password README.md -o README.md.u001.jenc  # DOES NOT YET WORK - https://github.com/clach04/puren_tonbo/issues/171
    ptcipher --encrypt -p password README.md -o README.md.jenc

"""

def main(argv=None):
    if argv is None:
        argv = sys.argv

    usage = "usage: %prog [options] in_filename"
    parser = ptgrep.MyParser(
        usage=usage,
        version="%%prog %s" % puren_tonbo.__version__,
        epilog=ptcipher_examples
    )
    parser.add_option("-o", "--output", dest="out_filename", default='-',
                        help="write output to FILE", metavar="FILE")
    parser.add_option("-d", "--decrypt", action="store_true", dest="decrypt", default=True,
                        help="decrypt in_filename")
    parser.add_option("-e", "--encrypt", action="store_false", dest="decrypt",
                        help="encrypt in_filename")
    # TODO force Windows newline fixes option when writting out - and use with scite (and maybe vim too?)
    parser.add_option("--force-newline", "--force_newline", help="If set, force newlines. Options; dos, windows, CRLF, unix, LF")
    parser.add_option("--list-formats", help="Which encryption/file formats are available", action="store_true")
    parser.add_option("--list-all-formats", help="List all (non-Raw) encryption/file formats are suportted (potentially not available", action="store_true")
    parser.add_option("--password-prompt", "--password_prompt", help="Comma seperated list of prompt mechanism to use, options; " + ','.join(puren_tonbo.ui.supported_password_prompt_mechanisms()), default="any")
    parser.add_option("--no-prompt", "--no_prompt", help="do not prompt for password", action="store_true")
    parser.add_option("--cipher", help="Which encryption mechanism to use (file extension used as hint)")
    parser.add_option("-p", "--password", help="password, if omitted but OS env PT_PASSWORD is set use that, if missing prompt")
    parser.add_option("-P", "--password_file", help="file name where password is to be read from, trailing blanks are ignored")
    parser.add_option("-t", "--time", action="store_true")
    parser.add_option("-v", "--verbose", action="store_true")
    parser.add_option("-s", "--silent", help="if specified do not warn about stdin using", action="store_false", default=True)
    (options, args) = parser.parse_args(argv[1:])
    #print('%r' % ((options, args),))
    verbose = options.verbose
    if verbose:
        print('Python %s on %s' % (sys.version.replace('\n', ' - '), sys.platform))
    if options.list_formats or options.list_all_formats:
        puren_tonbo.print_version_info(list_all=options.list_all_formats)
        return 0

    def usage():
        parser.print_usage()

    """
    if not args:
        parser.print_usage()
    """
    try:
        in_filename = args[0]
    except IndexError:
        # no filename specified so default to stdin
        in_filename = '-'

    force_newline = None
    if options.force_newline:
        force_newline = options.force_newline.lower()
        if force_newline not in ('dos', 'windows', 'CRLF', 'unix', 'LF'):
            usage()
            print('Invalid force-newline %r' % (force_newline,))
            return 1
        if force_newline in ('dos', 'windows', 'CRLF'):
            force_newline = 'dos'
        elif force_newline in ('unix', 'LF'):
            force_newline = 'unix'

    if options.password_file:
        f = open(options.password_file, 'rb')
        password_file = f.read()
        f.close()
        password_file = password_file.strip()
    else:
        password_file = None
    decrypt = options.decrypt
    out_filename = options.out_filename

    if in_filename == '-':
        if is_py3:
            in_file = sys.stdin.buffer
        else:
            in_file = sys.stdin
        if options.silent:
            sys.stderr.write('Read in from stdin...')
            sys.stderr.flush()
        # TODO for py3 handle string versus bytes
    else:
        in_file = open(in_filename, 'rb')
    if out_filename == '-':
        if is_py3:
            out_file = sys.stdout.buffer
        else:
            out_file = sys.stdout
        # handle string versus bytes....?
    else:
        timestamp_now = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
        out_file = tempfile.NamedTemporaryFile(
            mode='wb',
            dir=os.path.dirname(out_filename),
            prefix=os.path.basename(out_filename) + timestamp_now,
            delete=False
        )
        tmp_out_filename = out_file.name
        #print('DEBUG tmp_out_filename %r' % tmp_out_filename)  # TODO replace with logging.debug call

    if options.no_prompt:
        options.password_prompt = None
        default_password_value = ''  # empty password, cause a bad password error
    else:
        options.password_prompt = options.password_prompt.split(',')  # TODO validation options? for now rely on puren_tonbo.getpassfunc()
        default_password_value = None
    password = options.password or password_file or os.environ.get('PT_PASSWORD') or puren_tonbo.keyring_get_password() or default_password_value
    if password is None:
        if puren_tonbo.is_encrypted(in_filename):
            password = puren_tonbo.ui.getpassfunc("Puren Tonbo ptcipher Password:", preference_list=options.password_prompt, for_decrypt=decrypt)
        else:
            password = puren_tonbo.ui.getpassfunc("Puren Tonbo ptcipher Password:", preference_list=options.password_prompt, for_decrypt=False)
    if password and not isinstance(password, bytes):
        password = password.encode('us-ascii')

    if options.cipher:
        #import pdb ; pdb.set_trace()
        handler_class = puren_tonbo.filename2handler('_.' + options.cipher)  # TODO options.cipher to filename extension is less than ideal
    else:
        handler_class = None

    if options.time:
        start_time = time.time()

    failed = True
    try:
        if decrypt:
            #import pdb ; pdb.set_trace()
            if handler_class is None:
                handler_class = puren_tonbo.filename2handler(in_filename)
            handler = handler_class(key=password)
            plain_str = handler.read_from(in_file)
            if force_newline:
                #sys.stderr.write('plain_str %r\n' % (plain_str,))
                plain_str = simple_dos2unix(plain_str)
                #sys.stderr.write('plain_str %r\n' % (plain_str,))
                if force_newline == 'dos':
                    plain_str = simple_unix2dos(plain_str)
                #sys.stderr.write('plain_str %r\n' % (plain_str,))
            out_file.write(plain_str)
            failed = False
        else:
            # encrypt
            #import pdb ; pdb.set_trace()
            if handler_class is None:
                handler_class = puren_tonbo.filename2handler(out_filename)  # FIXME handle -
            handler = handler_class(key=password)
            plain_text = in_file.read()
            if force_newline:
                plain_text = simple_dos2unix(plain_text)
                if force_newline == 'dos':
                    plain_text = simple_unix2dos(plain_text)
            handler.write_to(out_file, plain_text)
            failed = False
    except puren_tonbo.PurenTonboException as info:
        log.error('%r', info, exc_info=1)  # include traceback
        print("ptcipher Encrypt/Decrypt problem. %r" % (info,))
    finally:
        if in_filename != '-':  # i.e. sys.stdin
            in_file.close()
        if out_filename != '-':  # i.e. sys.stdout
            out_file.close()
            if not failed:
                do_backup = True
                if do_backup:
                    if os.path.exists(out_filename):
                        file_replace(out_filename, out_filename + '.bak')  # backup existing
                file_replace(tmp_out_filename, out_filename)

    if options.time:
        end_time = time.time()
        total_time = end_time - start_time
        print('Total time: %.2f seconds' % total_time)

    if failed:
        return 1


    return 0


if __name__ == "__main__":
    sys.exit(main())
