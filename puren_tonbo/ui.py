# UI

import os
import sys


try:
    # Multiple EasyDialogs implementations out there, we don't care what we get so long as it works
    import EasyDialogs
except ImportError:
    EasyDialogs = None

try:
    import getpass
except ImportError:
    class getpass(object):
        def getpass(cls, prompt=None, stream=None):
            if prompt is None:
                prompt=''
            if stream is None:
                stream=sys.stdout
            prompt=prompt+ ' (warning password WILL echo): '
            stream.write(prompt)
            result = raw_input('') # or simply ignore stream??
            return result
        getpass = classmethod(getpass)

try:
    # Python 3
    import tkinter
    #import tkinter.simpledialog
    from tkinter.simpledialog import askstring
except ImportError:
    try:
        # Python 2
        import Tkinter as tkinter
        from tkSimpleDialog import askstring
    except ImportError:
        tkinter = None

try:
    # pywin32
    from pythonwin.pywin.dialogs.login import GetPassword as win32_getpassword
except ImportError:
    try:
        from pywin.mfc import dialog  # pywin32
        import win32con
        import win32ui

        # from pythonwin.pywin.dialogs.login -- https://github.com/mhammond/pywin32/blob/main/Pythonwin/pywin/dialogs/login.py
        def MakePasswordDlgTemplate(title):
            style = (
                win32con.DS_MODALFRAME
                | win32con.WS_POPUP
                | win32con.WS_VISIBLE
                | win32con.WS_CAPTION
                | win32con.WS_SYSMENU
                | win32con.DS_SETFONT
            )
            cs = win32con.WS_CHILD | win32con.WS_VISIBLE
            # Window frame and title
            dlg = [
                [title, (0, 0, 177, 45), style, None, (8, "MS Sans Serif")],
            ]

            # Password label and text box
            dlg.append([130, "Password:", -1, (7, 7, 69, 9), cs | win32con.SS_LEFT])
            s = cs | win32con.WS_TABSTOP | win32con.WS_BORDER
            dlg.append(
                ["EDIT", None, win32ui.IDC_EDIT1, (50, 7, 60, 12), s | win32con.ES_PASSWORD]
            )

            # OK/Cancel Buttons
            s = cs | win32con.WS_TABSTOP | win32con.BS_PUSHBUTTON
            dlg.append(
                [128, "OK", win32con.IDOK, (124, 5, 50, 14), s | win32con.BS_DEFPUSHBUTTON]
            )
            dlg.append([128, "Cancel", win32con.IDCANCEL, (124, 22, 50, 14), s])
            return dlg

        class PasswordDlg(dialog.Dialog):
            def __init__(self, title):
                dialog.Dialog.__init__(self, MakePasswordDlgTemplate(title))
                self.AddDDX(win32ui.IDC_EDIT1, "password")


        def win32_getpassword(title="Password", password=""):
            d = PasswordDlg(title)
            d["password"] = password
            if d.DoModal() != win32con.IDOK:
                return None
            return d["password"]
    except ImportError:
        win32_getpassword = None


def easydialogs_getpass(prompt):
    password = EasyDialogs.AskPassword('password?', default='')
    # if password is None, cancel was issued
    # if password == '', no password issue, OK was issued. See , `default` parameter above
    if password and not isinstance(password, bytes):
        password = password.encode('us-ascii')
    return password

def tk_getpass(prompt):
    tkinter.Tk().withdraw()
    password = askstring('puren tonbo', 'Password', show='*')
    if password and not isinstance(password, bytes):
        password = password.encode('us-ascii')
    return password


supported_password_prompt = ('any', 'text', 'gui',)  # although GUI may not be possible
if win32_getpassword:
    supported_password_prompt += ('win32',)
if EasyDialogs:
    supported_password_prompt += ('EasyDialogs',)  # case?
if tkinter:
    supported_password_prompt += ('tk',)

# TODO replace with plugin classes
def supported_password_prompt_mechanisms():
    return supported_password_prompt  # ('any', 'text', 'gui', 'tk')
    # TODO return ('any', 'text', 'gui', 'tk', 'psidialog' , 'external')  # external would use os var PT_ASKPASS

# TODO see dirname param in gen_caching_get_password()
def getpassfunc(prompt=None, preference_list=None):
    preference_list = preference_list or ['any']
    # TODO text first?
    if getpass and ('text' in preference_list or 'any' in preference_list):
        # text
        if prompt:
            if sys.platform == 'win32':  # and isinstance(prompt, unicode):  # FIXME better windows check and unicode check
                #if windows, deal with unicode problem in console
                # TODO add Windows check here!
                prompt = repr(prompt)  # consider us-ascii with replacement character encoding...
            return getpass.getpass(prompt)
        else:
            return getpass.getpass()

    if win32_getpassword and ('win32' in preference_list or 'gui' in preference_list or 'any' in preference_list):
        return win32_getpassword(prompt)

    if EasyDialogs and ('EasyDialogs' in preference_list or 'gui' in preference_list or 'any' in preference_list):
        return easydialogs_getpass(prompt)

    if tkinter and ('tk' in preference_list or 'gui' in preference_list or 'any' in preference_list):
        return tk_getpass(prompt)

