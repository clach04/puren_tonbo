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
from puren_tonbo import CR, simple_dos2unix, simple_unix2dos
import puren_tonbo.ui
from puren_tonbo.tools import ptgrep

is_py3 = sys.version_info >= (3,)

log = puren_tonbo.log_setup(__file__)

def main(argv=None):
    if argv is None:
        argv = sys.argv

    usage = "usage: %prog [options] [dir_name_or_filename1] [dir_name_or_filename2...]"
    parser = ptgrep.MyParser(
        usage=usage,
        version="%%prog %s" % puren_tonbo.__version__,
    )
    parser.add_option("--list-formats", help="Which encryption/file formats are available", action="store_true")
    parser.add_option("--list-all-formats", help="List all (non-Raw) encryption/file formats are suportted (potentially not available", action="store_true")
    parser.add_option("--password-prompt", "--password_prompt", help="Comma seperated list of prompt mechanism to use, options; " + ','.join(puren_tonbo.ui.supported_password_prompt_mechanisms()), default="any")
    parser.add_option("--no-prompt", "--no_prompt", help="do not prompt for password", action="store_true")
    parser.add_option("--cipher", help="Which encryption mechanism to use (file extension used as hint)")
    parser.add_option("-b", "--bad_only", action="store_true", help="only display broken/bad files")
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

    failed = True  # Assume this for now...

    if options.time:
        start_time = time.time()

    paths_to_search = args
    if not paths_to_search:
        #paths_to_search = ['-']
        usage()

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
    decrypt = True
    if password is None and decrypt:
        password = puren_tonbo.ui.getpassfunc("Puren Tonbo ptnewline_check Password:", preference_list=options.password_prompt, for_decrypt=decrypt)  # FIXME include filename in prompt
    if password and not isinstance(password, bytes):
        password = password.encode('us-ascii')

    if options.cipher:
        #import pdb ; pdb.set_trace()
        handler_class = puren_tonbo.filename2handler('_.' + options.cipher)  # TODO options.cipher to filename extension is less than ideal
    else:
        handler_class = None

    bad_only = options.bad_only
    if options.password_file:
        f = open(options.password_file, 'rb')
        password_file = f.read()
        f.close()
        password_file = password_file.strip()
    else:
        password_file = None

    for in_filename in paths_to_search:  # TODO directory, recursive, and (Windows) glob/wildcard support
        if puren_tonbo.is_encrypted(in_filename):
            decrypt = True
        else:
            decrypt = False

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

        file_handler_class = handler_class
        try:
            if file_handler_class is None:
                file_handler_class = puren_tonbo.filename2handler(in_filename)
            handler = file_handler_class(key=password)

            plain_bytes = handler.read_from(in_file)
            failed = False

            # For now, assume reading Windows (or pure potentially Unix/Linux) text
            #print('DEBUG %r' % plain_bytes)
            if CR in plain_bytes:
                windows_file = True  # or at least Windows-like
            else:
                windows_file = False  # Assume Unix/Linux (not Mac)

            if windows_file:
                plain_bytes_no_CR = simple_dos2unix(plain_bytes)
                if simple_unix2dos(plain_bytes_no_CR) != plain_bytes:
                    print('broken_windows: %s' % (in_filename,))
                else:
                    if bad_only: continue
                    print('windows: %s' % (in_filename,))
            else:
                # Unix/Linux
                if bad_only: continue
                print('unix: %s' % (in_filename,))
        except puren_tonbo.UnsupportedFile as info:
            log.error('%r', info, exc_info=1)  # include traceback
            print('unsupported: %s' % (in_filename,))
            print('skipping...')
        except puren_tonbo.PurenTonboException as info:
            log.error('%r', info, exc_info=1)  # include traceback
            print("ptnewline_check Encrypt/Decrypt problem with %s. %r" % (in_filename, info,))  # FIXME why is re-prompt not happening? Possibly due to "During handling of the above exception, another exception occurred:"
            # TODO stop or continue on error
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
