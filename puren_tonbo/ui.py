# UI

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


def tk_getpass(prompt):
    tkinter.Tk().withdraw()
    password = askstring('pttkview', 'Password', show='*')
    if password and not isinstance(password, bytes):
        password = password.encode('us-ascii')
    return password


# TODO replace with plugin classes
def supported_password_prompt_mechanisms():
    return ('any', 'text', 'gui', 'tk')

# TODO see dirname param in gen_caching_get_password()
def getpassfunc(prompt=None, preference_list=None):
    preference_list = preference_list or ['any']
    if 'tk' in preference_list or 'any' in preference_list:
        return tk_getpass(prompt)

    # text
    if prompt:
        if sys.platform == 'win32':  # and isinstance(prompt, unicode):  # FIXME better windows check and unicode check
            #if windows, deal with unicode problem in console
            # TODO add Windows check here!
            prompt = repr(prompt)  # consider us-ascii with replacement character encoding...
        return getpass.getpass(prompt)
    else:
        return getpass.getpass()
