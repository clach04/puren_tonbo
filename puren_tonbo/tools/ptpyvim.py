#!/usr/bin/env python
# -*- coding: us-ascii -*-
# vim:ts=4:sw=4:softtabstop=4:smarttab:expandtab
"""pyvim support for Puren Tonbo encrypted files (Tombo CHI Blowfish files, VimCrypt, AES-256.zip, etc.)

    python -m puren_tonbo.tools.ptpyvim -h
"""

import datetime
import getpass
import os
from optparse import OptionParser
import sys
import tempfile

# tested with pyvim.__version__ == '3.0.3'
from pyvim.editor import Editor  # https://github.com/prompt-toolkit/pyvim
from pyvim.rc_file import run_rc_file
from pyvim.io import FileIO, DirectoryIO, HttpIO, GZipFileIO

from pyvim.io.backends import ENCODINGS, _auto_decode
from pyvim.io import EditorIO

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


password = 'password'  # FIXME! debug hack for testing, bare minimum is pick up from env or keyring. TODO figure out prompting/IO in pyvim
if not isinstance(password, bytes):
    password = password.encode('us-ascii')


class PureTonboFileIO(EditorIO):
    """
    I/O backend for encrypted files.

    It is possible to edit this file as if it were not encrypted.
    The read and write call will decrypt and encrypt transparently.
    """
    def can_open_location(cls, location):
        """
        if not FileIO().can_open_location(location):  # revisit this, future virtual file system support
            return False
        """

        for file_extension in puren_tonbo.file_type_handlers:
            if location.endswith(file_extension):  # TODO file exists check like other backends?
                return True
        return False

    def exists(self, location):
        return FileIO().exists(location)  # TODO file exists check like other backends?

    def read(self, location):
        """
        Read/decrypt file from disk.
        """
        location = os.path.expanduser(location)  # revisit this, future virtual file system support

        handler_class = puren_tonbo.filename2handler(location)
        handler = handler_class(key=password)
        data = handler.read_from(location)
        """
        if is_py3:
            # encode to stdout encoding  TODO make this optional, potentially useful for py2 too
            stream_encoding = 'utf-8'  # FIXME hard coded
            plain_str = plain_str.decode(note_encoding).encode(stream_encoding)
        """

        return _auto_decode(data)

    def write(self, location, text, encoding):
        """
        Write/encrypt file to disk.
        """
        location = os.path.expanduser(location)  # revisit this

        failed = True
        plain_text = text.encode(encoding)

        handler_class = puren_tonbo.filename2handler(location)
        handler = handler_class(key=password)

        # open temp file in case of problems during write, once safely written rename
        timestamp_now = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
        out_file = tempfile.NamedTemporaryFile(
            mode='wb',
            dir=os.path.dirname(location),
            prefix=os.path.basename(location) + timestamp_now,
            delete=False
        )
        tmp_out_filename = out_file.name

        handler.write_to(out_file, plain_text)
        out_file.close()
        failed = False

        if not failed:
            do_backup = False
            if do_backup:
                if os.path.exists(location):
                    file_replace(location, location + '.bak')  # backup existing
            file_replace(tmp_out_filename, location)


def main(argv=None):
    if argv is None:
        argv = sys.argv

    # TODO any argument processing?
    locations = argv[1:]

    # Create new editor instance.
    editor = Editor()

    # monkey patch PT support into Editor instance
    editor.io_backends = [
            DirectoryIO(),
            HttpIO(),
            PureTonboFileIO(),
            GZipFileIO(),  # Should come before FileIO.
            FileIO(),
        ]  # TODO use existing and inject PureTonboFileIO? where?/how?

    # see run_pyvim.py
    default_pyvimrc = os.path.expanduser('~/.pyvimrc')

    if os.path.exists(default_pyvimrc):
        run_rc_file(editor, default_pyvimrc)

    # Load files and run.
    editor.load_initial_files(locations)
    editor.run()

    return 0


if __name__ == "__main__":
    sys.exit(main())
