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
    win32_getpassword = None

try:
    import ctypes
    from ctypes import wintypes

    from pywin.mfc import dialog  # pywin32
    import win32con
    import win32gui
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


    def win32_getpassword_internal(title="Password", password=""):
        """win32 Dialog"""
        d = PasswordDlg(title)
        d["password"] = password
        if d.DoModal() != win32con.IDOK:
            return None
        return d["password"]

    if win32_getpassword is None:
        win32_getpassword = win32_getpassword_internal  # TODO revisit this

    def win32_getpassword_window(title="Password", password=""):
        initial_password = password or ""
        hinstance = win32gui.GetModuleHandle(None)
        result = [None]
        ctrl_handles = {}

        IDC_EDIT = 100

        def wnd_proc(hwnd, msg, wparam, lparam):
            if msg == win32con.WM_COMMAND:
                ctrl_id = win32gui.LOWORD(wparam)
                if ctrl_id == win32con.IDOK:
                    h_edit = ctrl_handles.get('edit')
                    if h_edit:
                        result[0] = win32gui.GetWindowText(h_edit)
                    win32gui.DestroyWindow(hwnd)
                elif ctrl_id == win32con.IDCANCEL:
                    result[0] = None
                    win32gui.DestroyWindow(hwnd)
            elif msg == win32con.WM_DESTROY:
                win32gui.PostQuitMessage(0)
            return win32gui.DefWindowProc(hwnd, msg, wparam, lparam)

        class_name = "PurenTonboPwdWnd"
        wc = win32gui.WNDCLASS()
        wc.hInstance = hinstance
        wc.lpszClassName = class_name
        wc.lpfnWndProc = wnd_proc
        wc.hbrBackground = win32con.COLOR_WINDOW + 1
        wc.hCursor = win32gui.LoadCursor(0, win32con.IDC_ARROW)
        wc_atom = win32gui.RegisterClass(wc)

        style = (
            win32con.WS_OVERLAPPED
            | win32con.WS_CAPTION
            | win32con.WS_SYSMENU
            | win32con.WS_VISIBLE
        )

        hwnd = win32gui.CreateWindowEx(
            win32con.WS_EX_APPWINDOW, wc_atom, title, style,
            100, 100, 280, 110,
            0, 0, hinstance, None
        )

        hfont = win32gui.GetStockObject(17)  # DEFAULT_GUI_FONT

        win32gui.CreateWindow("STATIC", "Password:",
            win32con.WS_CHILD | win32con.WS_VISIBLE,
            10, 12, 70, 20, hwnd, 0, hinstance, None)

        h_edit = win32gui.CreateWindow("EDIT", initial_password,
            win32con.WS_CHILD | win32con.WS_VISIBLE | win32con.WS_BORDER | win32con.ES_PASSWORD,
            85, 10, 170, 22, hwnd, IDC_EDIT, hinstance, None)
        win32gui.SendMessage(h_edit, win32con.WM_SETFONT, hfont, 1)

        h_ok = win32gui.CreateWindow("BUTTON", "OK",
            win32con.WS_CHILD | win32con.WS_VISIBLE | win32con.BS_PUSHBUTTON | win32con.BS_DEFPUSHBUTTON,
            85, 42, 80, 24, hwnd, win32con.IDOK, hinstance, None)
        win32gui.SendMessage(h_ok, win32con.WM_SETFONT, hfont, 1)

        h_cancel = win32gui.CreateWindow("BUTTON", "Cancel",
            win32con.WS_CHILD | win32con.WS_VISIBLE | win32con.BS_PUSHBUTTON,
            175, 42, 80, 24, hwnd, win32con.IDCANCEL, hinstance, None)
        win32gui.SendMessage(h_cancel, win32con.WM_SETFONT, hfont, 1)

        ctrl_handles['edit'] = h_edit

        win32gui.SetFocus(h_edit)
        win32gui.SendMessage(h_edit, win32con.EM_SETSEL, 0, -1)

        class MSG(ctypes.Structure):
            _fields_ = [
                ("hwnd", wintypes.HWND),
                ("message", wintypes.UINT),
                ("wParam", wintypes.WPARAM),
                ("lParam", wintypes.LPARAM),
                ("time", wintypes.DWORD),
                ("pt", wintypes.POINT),
            ]

        _user32 = ctypes.windll.user32
        msg = MSG()
        while _user32.GetMessageW(ctypes.byref(msg), None, 0, 0) > 0:
            if not _user32.IsDialogMessageW(hwnd, ctypes.byref(msg)):
                _user32.TranslateMessage(ctypes.byref(msg))
                _user32.DispatchMessageW(ctypes.byref(msg))
        return result[0]

except ImportError:
    win32_getpassword = None
    win32_getpassword_window = None


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
if win32_getpassword_window:
    supported_password_prompt += ('win32_window',)  # TODO revisit
if EasyDialogs:
    supported_password_prompt += ('EasyDialogs',)  # case?
if tkinter:
    supported_password_prompt += ('tk',)

# TODO replace with plugin classes
def supported_password_prompt_mechanisms():
    return supported_password_prompt  # ('any', 'text', 'gui', 'tk')
    # TODO return ('any', 'text', 'gui', 'tk', 'psidialog' , 'external')  # external would use os var PT_ASKPASS

# TODO see dirname param in gen_caching_get_password()
def call_getpassfunc(prompt=None, preference_list=None):
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

    if win32_getpassword_window and ('win32_window' in preference_list or 'gui' in preference_list or 'any' in preference_list):
        return win32_getpassword_window(prompt)  # TODO double prompt dialog

    # NOTE due to win32_getpassword_window() this may never get called. For standalone tools, this is ideal, for built-in tools likely not desirable
    if win32_getpassword and ('win32' in preference_list or 'gui' in preference_list or 'any' in preference_list):
        return win32_getpassword(prompt)

    if EasyDialogs and ('EasyDialogs' in preference_list or 'gui' in preference_list or 'any' in preference_list):
        return easydialogs_getpass(prompt)

    if tkinter and ('tk' in preference_list or 'gui' in preference_list or 'any' in preference_list):
        return tk_getpass(prompt)

    raise NotImplementedError('Unsure which password function to use')

def getpassfunc(prompt=None, preference_list=None, for_decrypt=False, brave_mode=False):
    """
    if for_decrypt is true, only need to prompt once
    brave_mode = opposite of timid; timid prompt for password and confirmation, brave prompt once
    """
    preference_list = preference_list or ['any']
    prompt_counter = 2
    if for_decrypt:
        prompt_counter = 1
    else:
        if brave_mode:
            prompt_counter = 1

    if prompt_counter == 1:
        return call_getpassfunc(prompt=prompt, preference_list=preference_list)

    passwords_match = False
    while not passwords_match:
        password1 = call_getpassfunc(prompt=prompt, preference_list=preference_list)
        password2 = call_getpassfunc(prompt='Re-confirm ' + prompt, preference_list=preference_list)
        if password1 == password2:
            passwords_match = True
            break
        else:
            # TODO GUI options for feedback.... Also GUI has the option to show 2 fields rather than prompt UI twice...
            print('Passwords do NOT match, re-enter.')
    return password1
