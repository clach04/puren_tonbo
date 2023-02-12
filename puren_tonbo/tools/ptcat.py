#!/usr/bin/env python
# -*- coding: us-ascii -*-
# vim:ts=4:sw=4:softtabstop=4:smarttab:expandtab
"""Command line tool to decrypt to stdout Puren Tonbo files (Tombo CHI Blowfish files, VimCrypt, AES-256.zip, etc.)

python2 -m puren_tonbo.tools.ptcat -p test test.chi

"""

import os
from optparse import OptionParser
import sys

import puren_tonbo


is_py3 = sys.version_info >= (3,)


def main(argv=None):
    if argv is None:
        argv = sys.argv

    if is_py3:
        stream_encoding = 'utf-8'  # FIXME hard coded

    usage = "usage: %prog [options] in_filename"
    parser = OptionParser(usage=usage, version="%%prog %s" % puren_tonbo.__version__)
    parser.add_option("--list-formats", help="Which encryption/file formats are available", action="store_true")
    parser.add_option("--note-root", help="Direcory of notes", default='.')  # TODO pick up from a config file
    parser.add_option("-c", "--codec", help="File encoding", default='utf-8')
    parser.add_option("-p", "--password", help="password, if omitted but OS env PT_PASSWORD is set use that, if missing prompt")
    parser.add_option("-P", "--password_file", help="file name where password is to be read from, trailing blanks are ignored")
    parser.add_option("-v", "--verbose", action="store_true")

    (options, args) = parser.parse_args(argv[1:])
    #print('%r' % ((options, args),))
    verbose = options.verbose
    if verbose:
        print('Python %s on %s' % (sys.version.replace('\n', ' - '), sys.platform))
    if options.list_formats:
        print('')
        print('Formats:')
        print('')
        for file_extension in puren_tonbo.file_type_handlers:
            handler_class = puren_tonbo.file_type_handlers[file_extension]
            print('%17s - %s - %s' % (file_extension[1:], handler_class.__name__, handler_class.description))  # TODO description
        return 0

    def usage():
        parser.print_usage()

    if not args:
        parser.print_usage()
        return 1
    in_filename = args[0]

    if options.password_file:
        f = open(options.password_file, 'rb')
        password_file = f.read()
        f.close()
        password_file = password_file.strip()
    else:
        password_file = None

    #password = options.password or password_file or os.environ.get('PT_PASSWORD') or getpass.getpass("Password:")  # TODO FIXME replace with password prompt generator
    password = options.password or password_file or os.environ.get('PT_PASSWORD') or puren_tonbo.caching_console_password_prompt
    # TODO text file should NOT prompt for a password
    if password and not callable(password) and not isinstance(password, bytes):
        password = password.encode('us-ascii')

    note_encoding = options.codec

    note_root = puren_tonbo.FileSystemNotes(options.note_root, note_encoding)
    data = note_root.note_contents(in_filename, password)
    #print('%r' % data)
    print('%s' % data)

    return 0


if __name__ == "__main__":
    sys.exit(main())
