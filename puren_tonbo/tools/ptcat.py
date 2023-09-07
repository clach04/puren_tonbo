#!/usr/bin/env python
# -*- coding: us-ascii -*-
# vim:ts=4:sw=4:softtabstop=4:smarttab:expandtab
"""Command line tool to decrypt to stdout Puren Tonbo files (Tombo CHI Blowfish files, VimCrypt, AES-256.zip, etc.)

    python -m puren_tonbo.tools.ptcat -h
    python -m puren_tonbo.tools.ptcat -p test test.chi

TODO consider arbitary (absolute, possibly even relative "../../") paths as command line, avoiding directory sandbox sanity check (FileSystemNotes.abspath2relative())?
i.e. just like ptcipher, e.g.:

    python -m puren_tonbo.tools.ptcat -p test /tmp/test.chi
    python -m puren_tonbo.tools.ptcat -p test C:\tmp\test.chi

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
    parser.add_option("--note-root", help="Directory of notes override")
    parser.add_option("-c", "--codec", help="Override config file encoding (can be a list TODO format comma?)")
    parser.add_option("-p", "--password", help="password, if omitted but OS env PT_PASSWORD is set use that, if missing prompt")
    parser.add_option("-P", "--password_file", help="file name where password is to be read from, trailing blanks are ignored")
    parser.add_option("--config-file", "--config_file", help="Override config file")
    parser.add_option("-v", "--verbose", action="store_true")

    (options, args) = parser.parse_args(argv[1:])
    #print('%r' % ((options, args),))
    verbose = options.verbose
    if verbose:
        print('Python %s on %s' % (sys.version.replace('\n', ' - '), sys.platform))
    if options.list_formats:
        puren_tonbo.print_version_info()
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
    password = options.password or password_file or os.environ.get('PT_PASSWORD') or puren_tonbo.keyring_get_password() or puren_tonbo.caching_console_password_prompt
    # TODO text file should NOT prompt for a password
    if password and not callable(password) and not isinstance(password, bytes):
        password = password.encode('us-ascii')

    config = puren_tonbo.get_config(options.config_file)

    if options.codec:
        note_encoding = options.codec
    else:
        note_encoding = config['codec']

    if options.note_root:
        note_root = options.note_root
    else:
        note_root = config.get('note_root', '.')

    notes = puren_tonbo.FileSystemNotes(note_root, note_encoding)
    data = notes.note_contents(in_filename, password)
    #print('%r' % data)
    print('%s' % data)

    return 0


if __name__ == "__main__":
    sys.exit(main())
