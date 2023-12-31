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

    if EasyDialogs and ('EasyDialogs' in preference_list or 'gui' in preference_list or 'any' in preference_list):
        return easydialogs_getpass(prompt)

    if tkinter and ('tk' in preference_list or 'gui' in preference_list or 'any' in preference_list):
        return tk_getpass(prompt)

