#!/usr/bin/env python
# -*- coding: us-ascii -*-
# vim:ts=4:sw=4:softtabstop=4:smarttab:expandtab
"""tk GUI tool to decrypt/view as well as encrypt/edit Puren Tonbo text files (plain text/markdown, Tombo CHI Blowfish files, VimCrypt, AES-256.zip, etc.)

    python -m puren_tonbo.tools.pttkview -h
    pttkview -h
"""

import datetime
import logging
import os
from optparse import OptionParser
import sys

is_win = (sys.platform == 'win32')

if is_win:
    import ctypes

try:
    # Python 3
    import tkinter
    #import tkinter.simpledialog
    from tkinter.simpledialog import askstring
    import tkinter.scrolledtext as ScrolledText
except ImportError:
    # Python 2
    import Tkinter as tkinter
    from tkSimpleDialog import askstring
    import ScrolledText


import puren_tonbo


is_py3 = sys.version_info >= (3,)


debug_dump_data = os.environ.get('PTTKVIEW_DATA', False)
if debug_dump_data:
    debug_dump_data = True
else:
    debug_dump_data = False


def main(argv=None):
    if argv is None:
        argv = sys.argv

    usage = "usage: %prog [options] in_filename"
    parser = OptionParser(usage=usage, version="%%prog %s" % puren_tonbo.__version__)
    # ONLY use filename as format indicator
    parser.add_option("-c", "--codec", help="Override config file encoding (can be a list TODO format comma?)")
    parser.add_option("--config-file", "--config_file", help="Override config file")
    parser.add_option("-p", "--password", help="password, if omitted but OS env PT_PASSWORD is set use that, if missing prompt")
    parser.add_option("-P", "--password_file", help="file name where password is to be read from, trailing blanks are ignored")
    parser.add_option("--list-formats", help="Which encryption/file formats are available", action="store_true")
    parser.add_option("--no-prompt", help="do not prompt for password", action="store_true")
    parser.add_option("--gen-filename", "--gen_filename", help="generate filename (based on first line. TODO options)", action="store_true")
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


    # create log
    log = logging.getLogger("pttkview")
    log.setLevel(logging.DEBUG)
    disable_logging = False
    #disable_logging = True  # TODO pickup from command line, env, config?
    if disable_logging:
        log.setLevel(logging.NOTSET)  # only logs; WARNING, ERROR, CRITICAL

    ch = logging.StreamHandler()  # use stdio

    if sys.version_info >= (2, 5):
        # 2.5 added function name tracing
        logging_fmt_str = "%(process)d %(thread)d %(asctime)s - %(name)s %(filename)s:%(lineno)d %(funcName)s() - %(levelname)s - %(message)s"
    else:
        if JYTHON_RUNTIME_DETECTED:
            # process is None under Jython 2.2
            logging_fmt_str = "%(thread)d %(asctime)s - %(name)s %(filename)s:%(lineno)d - %(levelname)s - %(message)s"
        else:
            logging_fmt_str = "%(process)d %(thread)d %(asctime)s - %(name)s %(filename)s:%(lineno)d - %(levelname)s - %(message)s"

    formatter = logging.Formatter(logging_fmt_str)
    ch.setFormatter(formatter)
    log.addHandler(ch)


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
    password = options.password or password_file or os.environ.get('PT_PASSWORD') or puren_tonbo.keyring_get_password() or default_password_value

    if is_win:
        # before GUI code, inform Windows to use the icon provided at runtime, not from the (exe) resource
        # https://learn.microsoft.com/en-us/windows/win32/shell/appids?redirectedfrom=MSDN#host
        myappid = u'mycompany.myproduct.subproduct.version' # arbitrary string
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)

    icon_full_path = os.path.join(os.path.dirname(puren_tonbo.__file__), 'resources', 'icon512x512.png')

    main_window = tkinter.Tk()
    main_window.title('pttkview - ' + os.path.basename(in_filename))
    #main_window.iconbitmap(default=icon_full_path)  # PNG not supported, needs to be Windows ico (icon) format?
    try:
        main_window.iconphoto(False, tkinter.PhotoImage(file=icon_full_path))  # currently a place holder image  - py3
    except AttributeError:
        # py2
        pass  # take default for now
        #icon_full_path = os.path.join(os.path.dirname(puren_tonbo.__file__), 'resources', 'icon512x512.gif')
        #main_window.iconbitmap(False, tkinter.PhotoImage(canvas=tkinter.Canvas(main_window, width=512, height=512, bg="#000000"), file=icon_full_path))  # py2?
    #iconbitmap = wm_iconbitmap(self, bitmap=None, default=None)
    """
    iconbitmap = wm_iconbitmap(self, bitmap=None, default=None)
        Set bitmap for the iconified widget to BITMAP. Return
        the bitmap if None is given.

        Under Windows, the DEFAULT parameter can be used to set the icon
        for the widget and any descendents that don't have an icon set
        explicitly.  DEFAULT can be the relative path to a .ico file
        (example: root.iconbitmap(default='myicon.ico') ).  See Tk
        documentation for more information.
    """


    if not password and puren_tonbo.is_encrypted(in_filename):
        main_window.withdraw()  # hide/remove blank window that shows up with Python 2.7, not seen with 3.11
        password = askstring('pttkview', 'Password', show='*')
        main_window.deiconify()  # restore hidden window
    if password and not isinstance(password, bytes):
        password = password.encode('us-ascii')

    menubar = tkinter.Menu(main_window)
    filemenu = tkinter.Menu(menubar, tearoff=0)

    st = ScrolledText.ScrolledText(main_window, wrap=tkinter.WORD, undo=True, autoseparators=True, maxundo=-1)
    dos_newlines = True  # assume windows newlines

    def insert_timestamp(p=None, evt=None):
        st.insert(tkinter.INSERT, datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'))  # inserts at current cursor position

    def load_file(p=None, evt=None):
        # TODO move password prompt logic here?, password expected to be set earlier
        log.debug('load_file')
        log.debug('p: %r', p)
        log.debug('evt: %r', evt)
        if st.edit_modified():
            raise NotImplementedError('Loading when text buffer has been modified')

        if os.path.exists(in_filename):  # FIXME this is limited to native file system
            plain_str = puren_tonbo.note_contents_load_filename(in_filename, get_pass=password, dos_newlines=dos_newlines, return_bytes=False, note_encoding=note_encoding)
            modfied = False
        else:
            handler_class = puren_tonbo.filename2handler(in_filename, default_handler=puren_tonbo.RawFile)
            handler = handler_class(key=password)
            base_filename = os.path.basename(in_filename)  # FIXME this is **probably** limited to native file system
            for extension in handler_class.extensions:
                if base_filename.endswith(extension):
                    base_filename = base_filename[:-len(extension)]
                    break
            plain_str = '%s\n\n%s\n' % (base_filename, datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
            modfied = True
        if debug_dump_data:
            log.debug('plain_str:        %r', plain_str)
        if dos_newlines:
            plain_str = plain_str.replace('\r', '')

        st.insert(tkinter.INSERT, plain_str)  # TODO review usage, pass into ScrolledText instead?
        st.edit_modified(modfied)
        st.edit_reset()  # undo/redo reset
        # NOTE Cursor will be at EOF.. BUT scroll/view will be top of the file


    def save_file(p=None, evt=None):
        log.debug('save_file')
        log.debug('p: %r', p)
        log.debug('evt: %r', evt)
        log.debug('in_filename: %r', in_filename)

        #"""
        if not st.edit_modified():
            log.info('no changes, so not saving')
            return
        #"""
        buffer_plain_str = st.get('1.0', tkinter.END + '-1c')  # tk adds a new line by default, skip it
        #print('buffer            %r' % buffer_plain_str)
        #print('%r' % (buffer_plain_str == plain_str))
        # reuse handler, no need to reinit
        original_filename = in_filename
        handler_class = puren_tonbo.filename2handler(original_filename, default_handler=puren_tonbo.RawFile)
        handler = handler_class(key=password)

        # note_contents_save_native_filename(note_text, filename=None, original_filename=None, handler=None, dos_newlines=True, backup=True, use_tempfile=True, note_encoding='utf-8'):
        # TODO transplant into note_contents_save_native_filename()
        # TODO original_filename should be passed in
        if options.gen_filename:
            filename_generator = puren_tonbo.FILENAME_FIRSTLINE
            puren_tonbo.validate_filename_generator(filename_generator)
            filename_generator_func = puren_tonbo.filename_generators[filename_generator]
            _dummy, file_extn = os.path.splitext(original_filename)
            log.debug('original file_extn: %r', file_extn)

            if filename_generator in (puren_tonbo.FILENAME_TIMESTAMP, puren_tonbo.FILENAME_UUID4):
                # do not rename... or they could have passed in the "new name"
                filename = original_filename
            else:
                file_extension = file_extn or handler_class.extensions[0]  # pick the first one
                filename_without_path_and_extension = filename_generator_func(buffer_plain_str)
                filename = os.path.join(os.path.dirname(original_filename), filename_without_path_and_extension + file_extension)
            log.debug('generated filename: %r', filename)
            if filename != original_filename:
                log.error('not implemented deleting old filename')  # NOTE also doesn't actualy save to the new name, overwrites the original name
        # DEBUG remove, and uncomment orig
        if not st.edit_modified():
            log.info('no changes, so not saving')
            return

        try:
            puren_tonbo.note_contents_save_filename(buffer_plain_str, filename=in_filename, handler=handler, note_encoding=note_encoding, dos_newlines=dos_newlines)
            # if save successful (no exceptions);
            st.edit_modified(False)
            st.edit_separator()
        except Exception as info:
            # anything
            log.error('%r', info, exc_info=1)  # include traceback
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
    #main_window.bind('<Control-1>', insert_timestamp)  # this is Control and mouse button 1 (left/primary mouse button)
    main_window.bind('<Control-Key-1>', insert_timestamp)  # Control and number one on keyboard NOT the Numeric Keypad
    menubar.add_cascade(label="File", menu=filemenu)
    main_window.config(menu=menubar)

    st.pack(fill=tkinter.BOTH, expand=True)  # make visible, and resizable

    load_file()  # NOTE in_filename needs to be set
    st.focus_set()  # This is ineffective if password prompt (tkinter.simpledialog.askstring()) took place
    st.focus_force()  # this ensures window is on top with focus even if askstring() was called
    # cursor is at EOF, in window but view is of head/top of file

    main_window.mainloop()  # TODO detect (type of) exit (modified/unmodified), etc.

    return 0


if __name__ == "__main__":
    sys.exit(main())
