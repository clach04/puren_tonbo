# from https://moltenform.com/page/scite-with-python/doc/writingplugin.html
# NOTE see register.properties which scite global props needs to include

import os
import subprocess
import sys

from scite_extend_ui import ScConst
from scite_extend_ui import ScEditor  # what is the harm from doing this here?

is_win = sys.platform.startswith('win')


PTCIPHER_EXE = os.environ.get('PTCIPHER_EXE', 'ptcipher')
file_extensions = []
def determine_encrypted_file_extensions():
    if is_win:
        expand_shell = True  # avoid pop-up black CMD window
    else:
        expand_shell = False

    cmd = [PTCIPHER_EXE, '--list-formats', '--no-prompt']
    p = subprocess.Popen(cmd, shell=expand_shell, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    stdout_value, stderr_value = p.communicate()
    if p.returncode != 0 or stderr_value != '':
        # error
        print('Error determining puren tonbo support')
        print('cmd: %r' % cmd)
        print('stdout: %r' % stdout_value)
        print('stderr: %r' % stderr_value)
        print('stderr: %s' % stderr_value)
        print('returncode: %r' % p.returncode)
        #print('errors: %r' % p.errors)  # py3 only
        return

    #print('post com')
    #print('stdout: %r' % stdout_value)
    #print('stderr: %r' % stderr_value)
    #print('returncode: %r' % p.returncode)

    for line in stdout_value.decode('utf-8').replace('\r', '').split('\n')[3:]:
        line = line.strip()
        if not line:
            continue
        x = line.split(' - ', 1)
        file_extension = x[0]
        if file_extension not in ('txt', 'md'):
            #file_extensions.append(file_extension)
            file_extensions.append('.' + file_extension)
    #print('stdout: %r' % file_extensions)

def OnBeforeSave(filename):
    """Save files unless supported encrypted file extension. No support for save/encrypt yet
    """
    #print('plugin %s file %s' % (__file__, filename))  # goes to output pane
    for file_extension in file_extensions:
        if filename.lower().endswith(file_extension):
            file_contents, file_contents_len = ScEditor.GetText()
            # NOTE file_contents is utf-8 encoded and file_contents_len the length of those utf-8 bytes
            #print('file_contents %r' % (file_contents,))  # DEBUG
            #print('file_contents len%r' % (len(file_contents),))  # DEBUG
            #print('file_contents_len %r' % (file_contents_len,))  # DEBUG
            file_contents = file_contents.replace('\n', '\r\n')  # dos newlines conversion
            # encrypt file - send scite buffer via stdio of PTCIPHER_EXE and have PTCIPHER_EXE  write to disk
            # assuming no failure; ScEditor.SetSavePoint()  # indicate to editor that save happened and file is unchanged
            #return ScConst.StopEventPropagation  # works, tells Scite to NOT save
            expand_shell = True  # avoid pop-up black CMD window
            cmd = [PTCIPHER_EXE, '--silent', '--no-prompt', '--encrypt', '--cipher', file_extension, '--output', filename]
            p = subprocess.Popen(cmd, shell=expand_shell, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            stdout_value, stderr_value = p.communicate(input=file_contents)

            if p.returncode == 0 and stdout_value == '' and stderr_value == '':
                # success!
                ScEditor.SetSavePoint()  # indicate to editor that save happened and file is unchanged - whether it really did or not ;-)
            else:
                print('Error saving/encrypting/writing')
                print('cmd: %r' % cmd)
                print('stdout: %r' % stdout_value)
                print('stderr: %r' % stderr_value)
                print('stderr: %s' % stderr_value)
                print('returncode: %r' % p.returncode)
                #print('errors: %r' % p.errors)  # py3 only
            return ScConst.StopEventPropagation  # works, tells Scite to NOT save
    return False  # Scite will handle save
    #return "StopEventPropagation"  # works
    #return ScConst.StopEventPropagation  # works, tells Scite to NOT save
    # https://www.scintilla.org/SciTEExtension.html

def OnSave(filename):
    print('plugin %s file %s' % (__file__, filename))  # goes to output pane
    # file has ALREADY been saved at this point

def OnOpen(filename):
    """Opens a file, if supported file extension attempt to decrypt/load by spawning external tool which expects password to be set in OS variable
    """
    #print('plugin saw OnOpen', filename)  # goes to output pane
    is_encrypted = False
    for file_extension in file_extensions:
        if filename.lower().endswith(file_extension):
            is_encrypted = True
            break
    if not is_encrypted:
        return

    if is_win:
        expand_shell = True  # avoid pop-up black CMD window
    else:
        expand_shell = False
    # TODO prompt for password, for now pick up from env (by default)
    cmd = [PTCIPHER_EXE, '--silent', '--no-prompt', '--decrypt', filename, '--output=-']
    # DEBUG code that shows we can inject into the sub-process environment
    #os.environ['PT_PASSWORD'] = 'bad'
    #os.environ['PT_PASSWORD'] = 'password'  # works  # FIXME prompt!
    # re-read from disk using PTCIPHER_EXE, could potential send scite buffer via stdio to avoid the disk IO but easier to re-read.
    p = subprocess.Popen(cmd, shell=expand_shell, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    # time out is py3 (3.3+?)
    """
    try:
        timeout = 15
        timeout = 3
        stdout_value, stderr_value = p.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        p.kill()
        #stdout_value, stderr_value = p.communicate()  # just hangs again
        stdout_value, stderr_value = '', ''
    """
    stdout_value, stderr_value = p.communicate()

    if p.returncode == 0 and stderr_value == '':
        # success!
        ScEditor.SetSavePoint()  # indicate to editor that save happened and file is unchanged - whether it really did or not ;-)
    else:
        print('Error loading/decrypting')
        print('cmd: %r' % cmd)
        print('stdout: %r' % stdout_value)
        print('stderr: %r' % stderr_value)
        print('stderr: %s' % stderr_value)
        print('returncode: %r' % p.returncode)
        #print('errors: %r' % p.errors)  # py3 only

    # TODO other stuff
    # for example check exit code and stderr

    #ScEditor.BeginUndoAction()
    ScEditor.SetText(stdout_value)
    #ScEditor.EndUndoAction()  # this did not allow undo after all
    ScEditor.SetSavePoint()  # indicate to editor that save happened and file is unchanged - whether it really did or not ;-)



#log.info('loaded %s', __file__)
#print('loaded %s' % __file__)  # DEBUG goes to output pane
determine_encrypted_file_extensions()
#log.info('completed init %s', % __file__)  # DEBUG goes to output pane
#print('completed init %s' % __file__)  # DEBUG goes to output pane
