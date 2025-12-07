#!/usr/bin/env python
# -*- coding: us-ascii -*-
# vim:ts=4:sw=4:softtabstop=4:smarttab:expandtab
"""Command line tool to decrypt Puren Tonbo files (Tombo CHI Blowfish files, VimCrypt, AES-256.zip, etc.) and sanity check newlines

    python -m puren_tonbo.tools.ptnewline_check -h
    ptnewline_check -h
"""

import datetime
import os
from optparse import OptionParser
import sys
import tempfile
import time

import puren_tonbo
import puren_tonbo.ui
from puren_tonbo.tools import ptgrep

is_py3 = sys.version_info >= (3,)

log = puren_tonbo.log_setup(__file__)

def main(argv=None):
    if argv is None:
        argv = sys.argv

    usage = "usage: %prog [options] in_filename"  # TODO filenames plural (and recursive) see ptgrep
    parser = ptgrep.MyParser(
        usage=usage,
        version="%%prog %s" % puren_tonbo.__version__,
    )
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

    decrypt = True  # Assume this for now...
    failed = True  # Assume this for now...

    """
    if not args:
        parser.print_usage()
    """
    try:
        in_filename = args[0]
    except IndexError:
        # no filename specified so default to stdin
        in_filename = '-'

    if options.password_file:
        f = open(options.password_file, 'rb')
        password_file = f.read()
        f.close()
        password_file = password_file.strip()
    else:
        password_file = None

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




    if options.password_file:
        f = open(options.password_file, 'rb')
        password_file = f.read()
        f.close()
        password_file = password_file.strip()
    else:
        password_file = None

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

    if handler_class is None:
        handler_class = puren_tonbo.filename2handler(in_filename)
    handler = handler_class(key=password)

    try:
        plain_str = handler.read_from(in_file)
        failed = False

        # For now, assume reading Windows (or pure potentially Unix/Linux) text
        print('DEBUG %r' % plain_str)
        CR = b'\r'
        NL = b'\n'
        if CR in plain_str:
            windows_file = True
        else:
            windows_file = False  # Assume Unix/Linux (not Mac)

        if windows_file:
            plain_str_no_CR = plain_str.replace(CR, b'')
            if plain_str_no_CR.replace(NL, CR + NL) != plain_str:
                print('broken_windows')
            else:
                print('windows')
        else:
            # Unix/Linux
            print('unix')
    except puren_tonbo.PurenTonboException as info:
        log.error('%r', info, exc_info=1)  # include traceback
        print("ptcipher Encrypt/Decrypt problem. %r" % (info,))
    finally:
        if in_filename != '-':  # i.e. sys.stdin
            in_file.close()



    if options.time:
        end_time = time.time()
        total_time = end_time - start_time
        print('Total time: %.2f seconds' % total_time)

    if failed:
        return 1


    return 0


if __name__ == "__main__":
    sys.exit(main())
