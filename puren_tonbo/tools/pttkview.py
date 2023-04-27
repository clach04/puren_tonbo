#!/usr/bin/env python
# -*- coding: us-ascii -*-
# vim:ts=4:sw=4:softtabstop=4:smarttab:expandtab
"""tk GUI tool to decrypt/view Puren Tonbo files (Tombo CHI Blowfish files, VimCrypt, AES-256.zip, etc.)

    python -m puren_tonbo.tools.pttkview -h
    pttkview -h
"""
# TODO encrypt support, with safe-save as the default ala ptcipher - either reuse/call ptcipher more move that logic into main lib

import os
from optparse import OptionParser
import sys

import tkinter
import tkinter.simpledialog
import tkinter.scrolledtext as ScrolledText

import puren_tonbo


is_py3 = sys.version_info >= (3,)

def main(argv=None):
    if argv is None:
        argv = sys.argv

    usage = "usage: %prog [options] in_filename"
    parser = OptionParser(usage=usage, version="%%prog %s" % puren_tonbo.__version__)
    # ONLY use filename as format indicator
    parser.add_option("-c", "--codec", help="File encoding", default='utf-8')
    parser.add_option("-p", "--password", help="password, if omitted but OS env PT_PASSWORD is set use that, if missing prompt")
    parser.add_option("-P", "--password_file", help="file name where password is to be read from, trailing blanks are ignored")
    parser.add_option("--list-formats", help="Which encryption/file formats are available", action="store_true")
    parser.add_option("--no-prompt", help="do not prompt for password", action="store_true")
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

    default_password_value = None
    if options.no_prompt:
        default_password_value = ''  # empty password, cause a bad password error
    """
    else:
        default_password_value = puren_tonbo.caching_console_password_prompt
    else:
        default_password_value = getpass.getpass("Password:")  # FIXME don't do this
    """
    password = options.password or password_file or os.environ.get('PT_PASSWORD') or default_password_value
    if not password:
        password = tkinter.simpledialog.askstring('pttkview', 'Password', show='*')
    if not isinstance(password, bytes):
        password = password.encode('us-ascii')
    note_encoding = options.codec

    handler_class = puren_tonbo.filename2handler(in_filename)
    handler = handler_class(key=password)
    in_file = open(in_filename, 'rb')
    plain_str = handler.read_from(in_file)
    in_file.close()
    plain_str = plain_str.decode(note_encoding)  # TODO review other usage of list of encodings..

    main_window = tkinter.Tk()  # TODO title (icon?)
    main_window.title('pttkview')

    menubar = tkinter.Menu(main_window)
    filemenu = tkinter.Menu(menubar, tearoff=0)

    st = ScrolledText.ScrolledText(main_window, wrap=tkinter.WORD, undo=True)

    def save_file():
        print('save_file')
        print('NOT IMPLEMENTED')
        # if save successful; st.edit_modified(False)

    def exit():
        #print('exit')
        buffer_status = st.edit_modified()
        #print(buffer_status)
        if buffer_status:
            # TODO really want dialog like scite; save changes? yes, no, cancel
            # Currently hitting enter will exit
            really_quit_result = tkinter.messagebox.askokcancel('Exit', 'Really exit without saving?')
            #print(really_quit_result)
            if not really_quit_result:
                return
        main_window.destroy()

    filemenu.add_command(label="Save", command=save_file)
    # TODO add SaveAs
    # TODO add Load
    filemenu.add_separator()
    filemenu.add_command(label="Exit", command=exit)
    main_window.wm_protocol ("WM_DELETE_WINDOW", exit)
    menubar.add_cascade(label="File", menu=filemenu)
    main_window.config(menu=menubar)

    st.focus_set()
    st.pack(fill=tkinter.BOTH, expand=True)  # make visible, and resizable

    st.insert(tkinter.INSERT, plain_str)  # TODO review usage, pass into ScrolledText instead?
    st.edit_modified(False)
    # NOTE Cursor will be at EOF

    main_window.mainloop()  # TODO detect (type of) exit (modified/unmodified), etc.

    return 0


if __name__ == "__main__":
    sys.exit(main())
