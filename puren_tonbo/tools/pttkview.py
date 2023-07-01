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

is_win = (sys.platform == 'win32')

if is_win:
    import ctypes

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
    parser.add_option("-c", "--codec", help="Override config file encoding (can be a list TODO format comma?)")
    parser.add_option("--config-file", help="Override config file")
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

    config = puren_tonbo.get_config(options.config_file)
    if options.codec:
        note_encoding = options.codec
    else:
        note_encoding = config['codec']

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

    if is_win:
        # before GUI code, inform Windows to use the icon provided at runtime, not from the (exe) resource
        # https://learn.microsoft.com/en-us/windows/win32/shell/appids?redirectedfrom=MSDN#host
        myappid = u'mycompany.myproduct.subproduct.version' # arbitrary string
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)

    icon_full_path = os.path.join(os.path.dirname(puren_tonbo.__file__), 'resources', 'icon512x512.png')

    main_window = tkinter.Tk()
    main_window.title('pttkview - ' + os.path.basename(in_filename))
    #main_window.iconbitmap(default=icon_full_path)  # PNG not supported, needs to be Windows ico (icon) format?
    main_window.iconphoto(False, tkinter.PhotoImage(file=icon_full_path))  # currently a place holder image


    if not password and puren_tonbo.is_encrypted(in_filename):
        password = tkinter.simpledialog.askstring('pttkview', 'Password', show='*')
    if password and not isinstance(password, bytes):
        password = password.encode('us-ascii')

    handler_class = puren_tonbo.filename2handler(in_filename, default_handler=puren_tonbo.RawFile)
    handler = handler_class(key=password)
    in_file = open(in_filename, 'rb')
    plain_str_bytes = handler.read_from(in_file)
    print('plain_str_bytes: %r' % plain_str_bytes)
    in_file.close()
    plain_str = puren_tonbo.to_string(plain_str_bytes, note_encoding=note_encoding)
    print('plain_str:        %r' % plain_str)
    dos_newlines = True  # assume windows newlines
    if dos_newlines:
        plain_str = plain_str.replace('\r', '')

    menubar = tkinter.Menu(main_window)
    filemenu = tkinter.Menu(menubar, tearoff=0)

    st = ScrolledText.ScrolledText(main_window, wrap=tkinter.WORD, undo=True, autoseparators=True, maxundo=-1)

    def save_file(p=None, evt=None):
        print('save_file')
        print('p: %r' % p)
        print('evt: %r' % evt)
        if not st.edit_modified():
            print('no changes, so not saving')
            return
        buffer_plain_str = st.get('1.0', tkinter.END + '-1c')  # tk adds a new line by default, skip it
        #print('buffer            %r' % buffer_plain_str)
        #print('%r' % (buffer_plain_str == plain_str))
        # reuse handler, no need to reinit
        try:
            puren_tonbo.note_contents_save_filename(buffer_plain_str, filename=in_filename, handler=handler, note_encoding=note_encoding, dos_newlines=dos_newlines)
            # if save successful (no exceptions);
            st.edit_modified(False)
            st.edit_separator()
        except Exception as info:
            # anything
            print('%r' % info)
            tkinter.messagebox.showerror('Error', 'while saving %s' % in_filename)
            raise

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

    filemenu.add_command(label="Save", command=save_file, underline=0, accelerator='CTRL+S')  # DEBUG/WIP
    # TODO add SaveAs
    # TODO add Load
    filemenu.add_separator()
    filemenu.add_command(label="Exit", command=exit, underline=1)
    main_window.wm_protocol("WM_DELETE_WINDOW", exit)
    main_window.bind('<Control-s>', save_file)
    menubar.add_cascade(label="File", menu=filemenu)
    main_window.config(menu=menubar)

    st.pack(fill=tkinter.BOTH, expand=True)  # make visible, and resizable

    st.insert(tkinter.INSERT, plain_str)  # TODO review usage, pass into ScrolledText instead?
    st.edit_modified(False)
    st.edit_reset()  # undo/redo reset
    # NOTE Cursor will be at EOF
    st.focus_set()  # This is ineffective if password prompt (tkinter.simpledialog.askstring()) took place
    st.focus_force()  # this ensures window is on top with focus even if askstring() was called
    # cursor is at EOF, in window but view is of head/top of file

    main_window.mainloop()  # TODO detect (type of) exit (modified/unmodified), etc.

    return 0


if __name__ == "__main__":
    sys.exit(main())
