#!/usr/bin/env python
# -*- coding: us-ascii -*-
# vim:ts=4:sw=4:softtabstop=4:smarttab:expandtab
"""Command line tool to encrypt/decrypt Puren Tombo files (Tombo CHI Blowfish files)
"""

import datetime
import getpass
import os
from optparse import OptionParser
import sys
import tempfile

import puren_tonbo


is_py3 = sys.version_info >= (3,)


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


def main(argv=None):
    if argv is None:
        argv = sys.argv

    if is_py3:
        stream_encoding = 'utf-8'  # FIXME hard coded

    usage = "usage: %prog [options] in_filename"
    parser = OptionParser(usage=usage, version="%prog 1.0")
    parser.add_option("-o", "--output", dest="out_filename", default='-',
                        help="write output to FILE", metavar="FILE")
    parser.add_option("-d", "--decrypt", action="store_true", dest="decrypt", default=True,
                        help="decrypt in_filename")
    parser.add_option("-e", "--encrypt", action="store_false", dest="decrypt",
                        help="encrypt in_filename")
    parser.add_option("--list-formats", help="Which encryption/file formats are available", action="store_true")
    parser.add_option("--cipher", help="Which encryption mechanism to use (file extension used as hint)")
    parser.add_option("-c", "--codec", help="File encoding", default='utf-8')
    parser.add_option("-p", "--password", help="password, if omitted but OS env PT_PASSWORD is set use that, if missing prompt")
    parser.add_option("-P", "--password_file", help="file name where password is to be read from, trailing blanks are ignored")
    parser.add_option("-v", "--verbose", action="store_true")
    parser.add_option("-s", "--silent", help="if specified do not warn about stdin using", action="store_false", default=True)
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
    decrypt = options.decrypt
    out_filename = options.out_filename
    note_encoding = options.codec

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
        print('DEBUG tmp_out_filename %r' % tmp_out_filename)

    password = options.password or password_file or os.environ.get('PT_PASSWORD') or getpass.getpass("Password:")
    if not isinstance(password, bytes):
        password = password.encode('us-ascii')

    if options.cipher:
        handler_class = puren_tonbo.filename2handler('_.' + options.cipher)  # TODO options.cipher to filename extension is less than ideal
    else:
        handler_class = None

    failed = True
    try:
        if decrypt:
            #import pdb ; pdb.set_trace()
            if handler_class is None:
                handler_class = puren_tonbo.filename2handler(in_filename)
            handler = handler_class(key=password)
            plain_str = handler.read_from(in_file)
            if is_py3:
                # encode to stdout encoding  TODO make this optional, potentially useful for py2 too
                plain_str = plain_str.decode(note_encoding).encode(stream_encoding)
            out_file.write(plain_str)
            failed = False
        else:
            # encrypt
            #import pdb ; pdb.set_trace()
            if handler_class is None:
                handler_class = puren_tonbo.filename2handler(out_filename)  # FIXME handle -
            handler = handler_class(key=password)
            plain_text = in_file.read()
            handler.write_to(out_file, plain_text)
            failed = False
    except puren_tonbo.PurenTomboException as info:
        print("Encrypt/Decrypt problem. %r" % (info,))
    finally:
        if in_file != sys.stdin:
            in_file.close()
        if out_file != sys.stdout:
            out_file.close()
            if not failed:
                do_backup = True
                if do_backup:
                    if os.path.exists(out_filename):
                        file_replace(out_filename, out_filename + '.bak')  # backup existing
                file_replace(tmp_out_filename, out_filename)

    if failed:
        return 1


    return 0


if __name__ == "__main__":
    sys.exit(main())
