#!/usr/bin/env python
# -*- coding: us-ascii -*-
# vim:ts=4:sw=4:softtabstop=4:smarttab:expandtab
"""Command line tool to decrypt and 3-way merge Puren Tonbo files (Tombo CHI Blowfish files, VimCrypt, AES-256.zip, etc.) to stdout

    python -m puren_tonbo.tools.ptcat -h
    python -m puren_tonbo.tools.ptcat -p test test.chi

TODO consider arbitary (absolute, possibly even relative "../../") paths as command line, avoiding directory sandbox sanity check (FileSystemNotes.abspath2relative())?
i.e. just like ptcipher, e.g.:

    python -m puren_tonbo.tools.ptdiff3merge -p test base mine theirs
    python -m puren_tonbo.tools.ptdiff3merge -p test base mine theirs

"""

import os
from optparse import OptionParser
import sys

import puren_tonbo
import puren_tonbo.diff3merge


is_py3 = sys.version_info >= (3,)


def main(argv=None):
    if argv is None:
        argv = sys.argv

    if is_py3:
        stream_encoding = 'utf-8'  # FIXME hard coded

    usage = "usage: %prog [options] base_filename modified1 modified2"
    parser = OptionParser(usage=usage, version="%%prog %s" % puren_tonbo.__version__)
    parser.add_option("--list-formats", help="Which encryption/file formats are available", action="store_true")
    parser.add_option("--note-root", help="Directory of notes override")  # FIXME not needed
    parser.add_option("-c", "--codec", help="Override config file encoding (can be a list TODO format comma?)")
    parser.add_option("-p", "--password", help="password, if omitted but OS env PT_PASSWORD is set use that, if missing prompt")
    parser.add_option("-P", "--password_file", help="file name where password is to be read from, trailing blanks are ignored")
    parser.add_option("--config-file", "--config_file", help="Override config file")
    parser.add_option("-v", "--verbose", action="store_true")
    parser.add_option("-o", "--output", dest="out_filename", default='-',
                        help="write output to FILE", metavar="FILE")
    parser.add_option("-d", "--diff-type", "--diff_type", dest="diff_type", default='myers',
                        help="Options; myers,diff, histogram")


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
    filename_base = args[0]
    filename_mine = args[1]
    filename_theirs = args[2]

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
    # FIXME prompt not working, testing with explicit password works fine

    config = puren_tonbo.get_config(options.config_file)

    if options.codec:
        note_encoding = options.codec
    else:
        note_encoding = config['codec']

    if options.note_root:
        note_root = options.note_root
    else:
        note_root = config.get('note_root', '.')

    dos_newlines = True
    base_file_contents = puren_tonbo.note_contents_load_filename(filename_base, get_pass=password, dos_newlines=dos_newlines, return_bytes=True)
    mine_file_contents = puren_tonbo.note_contents_load_filename(filename_mine, get_pass=password, dos_newlines=dos_newlines, return_bytes=True)
    theirs_file_contents = puren_tonbo.note_contents_load_filename(filename_theirs, get_pass=password, dos_newlines=dos_newlines, return_bytes=True)

    moptions = puren_tonbo.diff3merge.MergeOptions()
    moptions.file_merger = puren_tonbo.diff3merge.diff3_file_merge
    moptions.strategy = "ort"
    moptions.diff_type= options.diff_type

    merged_result, conflicts = puren_tonbo.diff3merge.diff3_file_merge(mine_file_contents, theirs_file_contents, base_file_contents, moptions)
    if options.out_filename == '-':
        print(puren_tonbo.to_string(merged_result, note_encoding=note_encoding), end='')
    else:
        out_filename = options.out_filename
        handler_class = puren_tonbo.filename2handler(out_filename)
        handler = handler_class(key=password)
        puren_tonbo.note_contents_save_native_filename(merged_result, filename=out_filename, original_filename=None, folder=None, handler=handler, dos_newlines=dos_newlines, backup=False, use_tempfile=False, note_encoding=None, filename_generator=None)
    print(conflicts)  # TODO make optional, and with more details/stats explanation

    return 0


if __name__ == "__main__":
    sys.exit(main())
