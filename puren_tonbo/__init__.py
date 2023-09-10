
import bisect
import datetime
import errno
import json
import locale
import logging
import os
import re
import subprocess
import sys
import tempfile

from ._version import __version__, __version_info__
from . import ui

def fake_module(name):
    # Fail with a clear message (possibly at an unexpected time)
    class MissingModule(object):
        def __call__(self, attr):
            raise ImportError('No module named %s' % name)

        def __getattr__(self, attr):
            #raise ImportError('No module named %s' % name)  # allow attribute lookup to pass through without error
            return 'No module named %s' % name

        def __bool__(self):
            # if checks on this will fail
            return False
        __nonzero__ = __bool__  # support py3 and py2

    return MissingModule()

try:
    import chi_io  # https://github.com/clach04/chi_io/
except ImportError:
    try:
        from . import chi_io  # https://github.com/clach04/chi_io/
    except ImportError:
        chi_io = None

try:
    raise ImportError()  # on my armbian distro the SWIG layer appears to have issues and caches plaintext, test_aesop_win_encryptpad_gpg_bad_password fails due to NOT getting bad password exception
    import gpg as gpgme  # `apt install python3-gpg` https://github.com/gpg/gpgme
    gpg = gpgme.core.Context()
except ImportError:
    gpgme = None
    try:
        import gnupg  # https://github.com/vsajip/python-gnupg
        try:
            gpg = gnupg.GPG()
            #gpg = gnupg.GPG(ignore_homedir_permissions=True)
        except RuntimeError:
            # Assume;     RuntimeError: GnuPG is not installed!
            gpg = None
        except OSError:
            # Assume;     GnuPG is not installed!
            gpg = None
    except ImportError:
        gpg = gnupg = None

try:
    import keyring  # python -m pip install keyring
    import keyring.backend
except ImportError:
    keyring = fake_module('keyring')

try:
    import pyzipper  # https://github.com/danifus/pyzipper  NOTE py3 only
except ImportError:
    pyzipper = fake_module('pyzipper')

try:
    #import vimdecrypt  # https://github.com/nlitsme/vimdecrypt
    from puren_tonbo import vimdecrypt  # https://github.com/nlitsme/vimdecrypt
except ImportError:
    vimdecrypt = fake_module('vimdecrypt')


import puren_tonbo.mzipaes
from puren_tonbo.mzipaes import ZIP_DEFLATED, ZIP_STORED


is_py3 = sys.version_info >= (3,)
is_win = sys.platform.startswith('win')

try:
    FileNotFoundError  # in this module; only used for subprocess, command available check
except NameError:
    # Probably Python 2.7 or earlier
    FileNotFoundError = Exception

try:
    basestring  # only used to determine if parameter is a filename
except NameError:
    basestring = (
        str  # py3 - in this module, only used to determine if parameter is a filename
    )

# create log
log = logging.getLogger("mylogger")
log.setLevel(logging.DEBUG)
disable_logging = False
disable_logging = True
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

log.debug('encodings %r', (sys.getdefaultencoding(), sys.getfilesystemencoding(), locale.getdefaultlocale()))

class PurenTonboException(Exception):
    '''Base chi I/O exception'''


class BadPassword(PurenTonboException):
    '''Bad password exception'''


class UnsupportedFile(PurenTonboException):
    '''File not encrypted/not supported exception'''

class PurenTonboIO(PurenTonboException):
    '''(File) I/O exception'''


class SearchException(Exception):
    def __init__(self, value):
        self.value = value

    def __str__(self):
        return repr(self.value)


class SearchCancelled(SearchException):
    def __init__(self, value):
        self.value = value

    def __str__(self):
        return repr(self.value)


class EncryptedFile:

    description = 'Base Encrypted File'
    extensions = []  # non-empty list of file extensions, first is the default (e.g. for writing)

    def __init__(self, key=None, password=None, password_encoding='utf8'):
        """
        key - is the actual encryption key in bytes
        password is the passphrase/password as a string
        password_encoding is used to create key from password if key is not provided
        """
        if key is None and password is None:
            raise RuntimeError('need password or key')  # TODO custom exception (needed for read_from()/write_to() failures
        if key is not None:
            self.key = key
        elif password:
            key = password.encode(password_encoding)
            # KDF could be applied here if write_to() does not handle this
            self.key = key

    ## TODO rename read_from() -> read() - NOTE this would not be file-like
    # TODO add wrapper class for file-like object api
    def read_from(self, file_object):
        """Decrypt"""
        raise NotImplementedError

    def write_to(self, file_object, byte_data):
        """Encrypt"""
        raise NotImplementedError


class RawFile(EncryptedFile):
    """Raw/binary/text file - Read/write raw bytes. 
    Use for plain text files.
    TODO this requires a password on init, plain text/unencrypted files should not need a password
    """

    description = 'Raw file, no encryption support'
    extensions = ['.txt', '.md']

    def __init__(self, key=None, password=None, password_encoding='utf8'):
        pass  # NOOP, password/key is NOT required

    def read_from(self, file_object):
        return file_object.read()

    def write_to(self, file_object, byte_data):
        file_object.write(byte_data)



class VimDecryptArgs():
    verbose = False

class VimDecrypt(EncryptedFile):
    """vimcrypt - can ONLY decrypt
    TODO add blowfish2 ONLY write support
    """

    description = 'vimcrypt 1, 2, 3'
    extensions = [
        '.vimcrypt',  # VimCrypt~03 - blowfish2
        '.vimcrypt1',  # VimCrypt~01 - zip
        '.vimcrypt2',  # VimCrypt~02 - blowfish
        '.vimcrypt3',  # VimCrypt~03 - blowfish2
    ]

    def read_from(self, file_object):
        # TODO catch exceptions and raise PurenTonboException()
        # due to the design of VIMs crypto support, bad passwords can NOT be detected
        # but a Unicode decode error is a good sign that the password is bad as will have junk bytes
        data = file_object.read()
        password = self.key
        if isinstance(password, bytes):
            password = password.decode("utf-8")  # vimdecrypt expects passwords as strings and will encode to utf8 - TODO update vimdecrypt library to support bytes
        args = VimDecryptArgs
        try:
            return vimdecrypt.decryptfile(data, password, args)
        except Exception as info:
            raise  # debug
            # TODO chain exception...
            raise PurenTonboException(info)


CCRYPT_EXE = os.environ.get('CCRYPT_EXE', 'ccrypt')
ccrypt = None
ccrypt_version = 'MISSING'

class Ccrypt(EncryptedFile):
    """ccrypt - ccrypt - https://ccrypt.sourceforge.net/
    NOTE uses external command line tool, rather than use files
    with ccrypt exe stdin/stdout is used instead to adhere to
    API and also avoid hitting filesystem (with plain text).
    """

    description = 'ccrypt symmetric Rijndael'
    extensions = [
        '.cpt',  # binary
    ]

    def read_from(self, file_object):
        password = self.key  # TODO enforce byte check?
        if isinstance(password, bytes):
            # environment variables (in Microsoft Windows) have to be strings in py3
            password = password.decode("utf-8")

        CCRYPT_ENVVAR_NAME = 'PT_PASSWORD'
        os.environ[CCRYPT_ENVVAR_NAME] = password
        cmd = [CCRYPT_EXE, '-cb', '-E', CCRYPT_ENVVAR_NAME]

        # expand-shell true for windows to avoid pop-up window, no user input used so shell escape/esculation not expected
        # TODO look at alernative, Windows onlyl startupinfo param STARTUPINFO class, wShowWindow = SW_HIDE
        #p_ccrypt = subprocess.Popen(cmd, shell=expand_shell, stdin=file_object, stdout=subprocess.PIPE, stderr=subprocess.PIPE)  # works for real files, fails in test suite under Windows with fake files as Windows stdlib goes looking for a fileno()
        byte_data = file_object.read()
        p_ccrypt = subprocess.Popen(cmd, shell=expand_shell, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        # timeout not suported by older python versions, pre 3.3
        #stdout_value, stderr_value = p_ccrypt.communicate()
        stdout_value, stderr_value = p_ccrypt.communicate(input=byte_data)
        if p_ccrypt.returncode != 0:
            if stderr_value== b'ccrypt: key does not match\n':
                raise BadPassword('with %r' % file_object)
            raise PurenTonboException('failed to spawn, %r' % stderr_value)  # TODO test and review
        return stdout_value

    def write_to(self, file_object, byte_data):
        password = self.key  # TODO enforce byte check?
        if isinstance(password, bytes):
            # environment variables (in Microsoft Windows) have to be strings in py3
            password = password.decode("utf-8")

        CCRYPT_ENVVAR_NAME = 'PT_PASSWORD'
        os.environ[CCRYPT_ENVVAR_NAME] = password
        cmd = [CCRYPT_EXE, '-e', '-E', CCRYPT_ENVVAR_NAME]
        p_ccrypt = subprocess.Popen(cmd, shell=expand_shell, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        # timeout not suported by older python versions, pre 3.3
        stdout_value, stderr_value = p_ccrypt.communicate(input=byte_data)
        if p_ccrypt.returncode != 0:
            raise PurenTonboException('failed to spawn, %r' % stderr_value)  # TODO test and review
        file_object.write(stdout_value)  # only write to fileobject on successful encryption


cmd = [CCRYPT_EXE, '--version']
if is_win:
    expand_shell = True  # avoid pop-up black CMD window - TODO review safety
else:
    expand_shell = False

try:
    p_ccrypt = subprocess.Popen(cmd, shell=expand_shell, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    # timeout not suported by older python versions, pre 3.3?
    stdout_value, stderr_value = p_ccrypt.communicate()

    """
    print('stdout: %r' % stdout_value)
    print('stderr: %r' % stderr_value)
    print('returncode: %r' % p_ccrypt.returncode)
    """
    if p_ccrypt.returncode == 0:
        ccrypt = True
        ccrypt_version = stdout_value.split(b' ', 2)[1].decode('utf-8')
except FileNotFoundError:
    # some (but not all, Windows does not require this) platforms raise exception on missing binary
    pass  # leave ccrypt as None

class GnuPG(EncryptedFile):
    """GnuPG - GPG binary
    """

    description = 'gpg (GnuPG) symmetric 1.x and 2.x, does NOT uses keys'
    extensions = [
        '.gpg',  # binary
        # potentially .epd for _some_ EncryptPad created files
    ]

    def read_from(self, file_object):
        # TODO catch exceptions and raise PurenTonboException()
        # bad passwords result in empty string results
        password = self.key
        """
when bytes passed actually get misleading error:

Traceback (most recent call last):
  File "C:\code\py\puren_tonbo\puren_tonbo\tests\testsuite.py", line 291, in test_aesop_win_encryptpad_gpg
    data = note_root.note_contents(test_note_filename, password)
  File "C:\code\py\puren_tonbo\puren_tonbo\__init__.py", line 872, in note_contents
    plain_str = handler.read_from(in_file)
  File "C:\code\py\puren_tonbo\puren_tonbo\__init__.py", line 247, in read_from
    result = gpg.decrypt_file(file_object, passphrase=password)
  File "C:\py310venv\lib\site-packages\gnupg.py", line 1768, in decrypt_file
    if passphrase and not self.is_valid_passphrase(passphrase):
  File "C:\py310venv\lib\site-packages\gnupg.py", line 1158, in is_valid_passphrase
    return ('\n' not in passphrase and '\r' not in passphrase and '\x00' not in passphrase)
TypeError: a bytes-like object is required, not 'str'

        """
        # Seems to require strings - TODO open a bug upstream for this
        if isinstance(password, bytes):
            password = password.decode("utf-8")
        edata = file_object.read()
        if gpgme:
            try:
                result = gpg.decrypt(edata, passphrase=password)
            except gpgme.errors.GPGMEError:
                # just assume
                raise BadPassword('with %r' % file_object)
        else:
            result = gpg.decrypt(edata, passphrase=password)
        #result = gpgme.core.Context().decrypt(edata, passphrase=password)
        #result = gpgme.core.Context().decrypt(edata, passphrase='this is shot')
        #result = gpg.decrypt_file(file_object, passphrase=password)
        if result:
            if gpgme:
                result = result[0]  # just ignore the validation.. # FIXME!
                return result
            else:
                return result.data
        raise BadPassword('with %r' % file_object)

    # if gpgme:
    # crypted_text, _, _ = context.encrypt('hello', sign=False, passphrase='test')

    def write_to(self, file_object, byte_data):
        password = self.key
        # Seems to require strings - TODO open a bug upstream for this
        if isinstance(password, bytes):
            password = password.decode("utf-8")
        enc_data = gpg.encrypt(byte_data, recipients=[], symmetric=True, armor=False, passphrase=password)
        file_object.write(enc_data.data)

class GnuPGascii(GnuPG):
    """GnuPG - GPG ASCII armored
    """

    extensions = [
        '.asc',  # ASCII Armored File
    ]

    def write_to(self, file_object, byte_data):
        password = self.key
        # Seems to require strings - TODO open a bug upstream for this
        if isinstance(password, bytes):
            password = password.decode("utf-8")
        enc_data = gpg.encrypt(byte_data, recipients=[], symmetric=True, passphrase=password)
        file_object.write(enc_data.data)


class TomboBlowfish(EncryptedFile):
    """Read/write Tombo (modified) Blowfish encrypted files
    Compatible with files in:
      * Tombo - http://tombo.osdn.jp/En/
      * Kumagusu - https://osdn.net/projects/kumagusu/ and https://play.google.com/store/apps/details?id=jp.gr.java_conf.kumagusu
      * miniNoteViewer - http://hatapy.web.fc2.com/mininoteviewer.html and https://play.google.com/store/apps/details?id=jp.gr.java_conf.hatalab.mnv&hl=en_US&gl=US
    """

    description = 'Tombo Blowfish ECB (not recommended)'
    extensions = ['.chi']

    def read_from(self, file_object):
        # TODO catch exceptions and raise PurenTonboException()
        try:
            return chi_io.read_encrypted_file(file_object, self.key)  # TODO if key is bytes/plaintext this will be slow for multiple files. Ideal is to derive actually password from plaintext once and feed in here for performance
        except chi_io.BadPassword as info:  # FIXME place holder
            # TODO chain exception...
            #print(dir(info))
            #raise BadPassword(info.message)  # does not work for python 3.6.9
            raise BadPassword(info)  # FIXME BadPassword(BadPassword("for 'file-like-object'",),)
        except Exception as info:
            raise  # DEBUG
            # TODO chain exception...
            #raise PurenTonboException(info.message)
            raise PurenTonboException(info)

    def write_to(self, file_object, byte_data):
        chi_io.write_encrypted_file(file_object, self.key, byte_data)

class ZipEncryptedFileBase(EncryptedFile):
    _filename = 'encrypted.md'  # filename inside of (encrypted) zip file
    _compression = ZIP_DEFLATED
    extensions = [
        '.aes.zip',  # AE-1 only Zip file with AES-256 - Standard WinZip/7z (not the old ZipCrypto!)
        '.aes256.zip',  # Zip file with AES-256 - Standard WinZip/7z (not the old ZipCrypto!)
        '.aeszip',  # Catch all Zip file with AES encryption of some sort
    ]


class PurePyZipAES(ZipEncryptedFileBase):
    """mzipaes - Read/write ZIP AES(256) encrypted files (not old ZipCrypto)
    Suitable for Python 2.7 and 3.x
    """

    description = 'AES-256 ZIP AE-1 DEFLATED (regular compression)'
    extensions = ZipEncryptedFileBase.extensions

    def read_from(self, file_object):
        # TODO catch specific exceptions and raise better mapped exception
        try:
            zf = mzipaes.MiniZipAE1Reader(file_object, self.key)
            return zf.get()  # first file in zip, ignore self._filename
        except mzipaes.BadPassword as info:
            raise BadPassword(info)
        except mzipaes.UnsupportedFile as info:
            raise UnsupportedFile(info)
        except mzipaes.AesZipException as info:
            # TODO chain exception...
            #raise PurenTonboException(info.message)
            raise PurenTonboException(info)

    def write_to(self, file_object, byte_data):
        assert self._compression in (ZIP_DEFLATED, ZIP_STORED)  # FIXME/TODO add proper check and raise explict exception
        # TODO catch specific exceptions and raise better mapped exception
        # TODO e.g. Exception('BAD PASSWORD',)
        try:
            zf = mzipaes.MiniZipAE1Writer(file_object, self.key, compression=self._compression)
            zf.append(self._filename, byte_data)
            #zf.zipcomment = 'optional comment'
            zf.write()
        except mzipaes.AesZipException as info:
            # TODO chain exception...
            #raise PurenTonboException(info.message)
            raise PurenTonboException(info)


class ZipNoCompressionPurePyZipAES(PurePyZipAES):
    description = 'AES-256 ZIP AE-1 STORED (uncompressed)'
    _compression = ZIP_STORED
    extensions = [
        '.aes256stored.zip',  # uncompressed Zip file with AES-256 - Standard WinZip/7z (not the old ZipCrypto!)
    ]


class ZipAES(ZipEncryptedFileBase):
    """Read/write ZIP AES(256) encrypted files (not old ZipCrypto)
    Compatible with files in WinZIP and 7z.
    Example 7z demo (Windows or Linux, assuming 7z is in the path):
        echo encrypted > encrypted.md
        7z a -ptest test_file.aes.zip encrypted.md
    """

    description = 'AES-256 ZIP AE-1 DEFLATED (regular compression)'
    extensions = extensions = ZipEncryptedFileBase.extensions + [
        '.old.zip',  # Zip file with old old ZipCrypto - writing not supported/implemented
    ]
    _filename = 'encrypted.md'  # filename inside of (AES encrypted) zip file
    _compression = ZIP_DEFLATED

    def read_from(self, file_object):
        # TODO catch exceptions and raise PurenTonboException()
        try:
            with pyzipper.AESZipFile(file_object) as zf:
                zf.setpassword(self.key)
                return zf.read(self._filename)
        except RuntimeError as info:
            # so far only seen for; RuntimeError("Bad password for file 'encrypted.md'")
            raise BadPassword(info)
        except Exception as info:
            # TODO chain exception...
            #print(info)
            #print(type(info))
            #print(dir(info))
            raise PurenTonboException(info)

    def write_to(self, file_object, byte_data):
        with pyzipper.AESZipFile(file_object,
                                 'w',
                                 compression=self._compression,
                                 encryption=pyzipper.WZ_AES,  # no other options
                                 ) as zf:
            # defaults to nbits=256 - TODO make explict?
            zf.setpassword(self.key)
            zf.writestr(self._filename, byte_data)  # pyzipper can take string or bytes


class ZipNoCompressionAES(ZipAES):
    description = 'AES-256 ZIP AE-1 STORED (uncompressed)'
    _compression = ZIP_STORED
    extensions = [
        '.aes256stored.zip',  # uncompressed Zip file with AES-256 - Standard WinZip/7z (not the old ZipCrypto!)
        '.oldstored.zip',  # Zip file with old old ZipCrypto - writing not supported/implemented
    ]

class ZipLzmaAES(ZipAES):
    description = 'AES-256 ZIP AE-1 LZMA'
    _compression = pyzipper.ZIP_LZMA
    extensions = [
        '.aes256lzma.zip',  # LZMA Zip file with AES-256 7z .zip (not the old ZipCrypto!)
    ]

class ZipBzip2AES(ZipAES):
    description = 'AES-256 ZIP AE-1 BZIP2'
    _compression = pyzipper.ZIP_BZIP2
    extensions = [
        '.aes256bzip2.zip',  # bzip2 Zip file with AES-256 7z .zip (not the old ZipCrypto!)
    ]

# note uses file extension - could also sniff file header and use file magic
file_type_handlers = {}
"""
    '.txt': RawFile,  # these are not needed, filename2handler() defaults
    '.md': RawFile,
}
"""
for file_extension in RawFile.extensions:
    file_type_handlers[file_extension] = RawFile

if chi_io:
    for file_extension in TomboBlowfish.extensions:
        file_type_handlers[file_extension] = TomboBlowfish  # created by http://tombo.osdn.jp/En/

if gpg:
    for enc_class in (GnuPG, GnuPGascii):
        for file_extension in enc_class.extensions:
            file_type_handlers[file_extension] = enc_class

if ccrypt:
    for enc_class in (Ccrypt,):
        for file_extension in enc_class.extensions:
            file_type_handlers[file_extension] = enc_class

if pyzipper:
    for enc_class in (ZipAES, ZipNoCompressionAES, ZipLzmaAES, ZipBzip2AES):
        for file_extension in enc_class.extensions:
            file_type_handlers[file_extension] = enc_class
else:
    for enc_class in (PurePyZipAES, ZipNoCompressionPurePyZipAES):
        for file_extension in enc_class.extensions:
            file_type_handlers[file_extension] = enc_class
if vimdecrypt:
    for file_extension in VimDecrypt.extensions:
        file_type_handlers[file_extension] = VimDecrypt

# Consider command line crypto (via pipe to avoid plaintext on disk)
# TODO? openssl aes-128-cbc -in in_file -out out_file.aes128
# TODO? openpgp

def filename2handler(filename, default_handler=None):
    filename = filename.lower()
    if filename.endswith('.aes256.zip'):
        file_extn = '.aes.zip'
    elif filename.endswith('.aes.zip'):
        file_extn = '.aes.zip'
    elif filename.endswith('.aes256stored.zip'):
        file_extn = '.aes256stored.zip'
    elif filename.endswith('.aes256lzma.zip'):
        file_extn = '.aes256lzma.zip'
    elif filename.endswith('.old.zip'):
        file_extn = '.old.zip'
    elif filename.endswith('.oldstored.zip'):
        file_extn = '.oldstored.zip'
    else:
        _dummy, file_extn = os.path.splitext(filename)
    log.debug('clach04 DEBUG file_extn: %r', file_extn)
    log.debug('clach04 DEBUG file_type_handlers: %r', file_type_handlers)
    handler_class = file_type_handlers.get(file_extn) or default_handler
    if handler_class is None:
        raise UnsupportedFile('no support for %r' % file_extn)
    log.debug('clach04 DEBUG handler_class: %r', handler_class)
    return handler_class

def debug_get_password():
    # DEBUG this should be a callback mechanism
    crypto_key = os.getenv('DEBUG_CRYPTO_KEY', 'test')  # dumb default password, should raise exception on missing password
    log.debug('clach04 DEBUG key: %r', crypto_key)
    return crypto_key

    handler_class = filename2handler(path)
    if handler_class:
        crypto_password = debug_get_password()
        handler = handler_class(password=crypto_password)
        content = handler.read_from(path)
        log.debug('bytes from decrypt')
        log.debug('clach04 DEBUG data: %r', content)
        log.debug(repr(content))
        content = content.decode('utf8')  # hard coded for now
    else:
        log.debug('clach04 DEBUG : regular read')
        with open(path, 'r') as f:
          content = f.read()


#################

# TODO replace with plugin classes
class gen_caching_get_password(object):
    def __init__(self, dirname=None):
        """If dirname is specified, removes that part of the pathname when prompting for the password for that file"""
        self.user_password = None
        self.dirname = dirname
    def gen_func(self):
        ## TODO add (optional) timeout "forget"/wipe password from memory
        def get_pass(prompt=None, filename=None, reset=False):
            """Caching password prompt for CONSOLE.
                prompt - the prompt to print for password prompt
                reset - if set to True will forget the cached password and prompt for it
            """
            if reset:
                self.user_password = None
            if self.user_password is None:
                if prompt is None:
                    if filename is None:
                        prompt = "Password:"
                    else:
                        if self.dirname is not None:
                            filename = remove_leading_path(self.dirname, filename)
                            prompt = "Password for note %s:" % filename
                        else:
                            prompt = "Password for file %s:" % filename
                self.user_password = ui.getpassfunc(prompt)
                if self.user_password  is None or self.user_password  == b'':
                    self.user_password = None
                """
                else:
                    ## not sure if this logic belongs at this level....
                    self.user_password = chi_io.CHI_cipher(self.user_password)
                """
            return self.user_password
        return get_pass

class gen_caching_get_passwordWIP(object):
    def __init__(self, dirname=None, promptfunc=None):
        """If dirname is specified, removes that part of the pathname when prompting for the password for that file
        if promptfunc is specified, promptfunc is called to prompt for password, if ommitted std getpass.getpass() is used"""
        self.user_password = None
        self.dirname = dirname
        if promptfunc is None:
            promptfunc = ui.getpassfunc
        self.promptfunc = promptfunc
    def gen_func(self):
        ## TODO add (optional) timeout "forget"/wipe password from memory
        def get_pass(prompt_str=None, filename=None, reset=False, value=None, prompt=True):
            """Caching password prompt for CONSOLE.
                prompt_str - the prompt to print for password prompt
                filename - the filename the password is required for
                reset - if set to True will set cached password to "value" (which is set to default of None means forget the cached password and prompt for it)
                value - see reset parameter
                prompt - if not True will NOT prompt user and simply return the cached password
            """
            if reset:
                self.user_password = value
                if self.user_password is not None:
                    ## not sure if this logic belongs at this level....
                    self.user_password = chi_io.CHI_cipher(self.user_password)
            if self.user_password is None and prompt:
                if prompt_str is None:
                    if filename is None:
                        prompt_str = "Password:"
                    else:
                        if self.dirname is not None:
                            filename = remove_leading_path(self.dirname, filename)
                            prompt = "Password for note %s:" % filename
                        else:
                            prompt = "Password for file %s:" % filename
                self.user_password = self.promptfunc(prompt)
                if self.user_password  is None or self.user_password  == b'':
                    self.user_password = None  # Alternatively could raise SearchCancelled
                else:
                    ## not sure if this logic belongs at this level....
                    self.user_password = chi_io.CHI_cipher(self.user_password)
            return self.user_password
        return get_pass


caching_console_password_prompt = gen_caching_get_password().gen_func()


if keyring:
    try:
        # Py3
        from urllib.request import urlopen, Request
        from urllib.parse import urlencode
    except ImportError:
        # Py2
        from urllib2 import urlopen, Request
        from urllib import urlencode

    def urllib_get_url(url, headers=None, ignore_errors=False):
        """
        @url - web address/url (string)
        @headers - dictionary - optional
        """
        log.debug('get_url=%r', url)
        #log.debug('headers=%r', headers)
        response = None
        try:
            if headers:
                request = Request(url, headers=headers)
            else:
                request = Request(url)  # may not be needed
            response = urlopen(request)
            url = response.geturl()  # may have changed in case of redirect
            code = response.getcode()
            #log("getURL [{}] response code:{}".format(url, code))
            result = response.read()
            return result
        except:  # HTTPError, ConnectionRefusedError
            # probably got HTTPError, may be ConnectionRefusedError
            if ignore_errors:
               return None
            else:
               raise
        finally:
            if response != None:
                response.close()

    # FIXME import from https://github.com/clach04/clach04.keyring.dumbserver instead
    class DumbServer(keyring.backend.KeyringBackend):
        """http server access, local only across regular tcp_ip socket (no need for unix domain sockets)
        ONLY uses GET calls (not POST)
        """
        def __init__(self):
            self._server_url = 'http://127.0.0.1:4277/'

        priority = 0

        def supported(self):
            return 0

        def get_password(self, service, username):
            log.debug('get_password called')
            vars = {
                'service': service,
                'username': username,
            }
            url = self._server_url + 'get' + '?' + urlencode(vars)
            log.debug('get_password url=%r', url)
            password = urllib_get_url(url, ignore_errors=True)
            if password is not None:
                password = password.decode('utf-8')
            return password

        def set_password(self, service, username, password):
            # NOOP - could do the same as get_password
            return 0  # return something else?

        def delete_password(self, service, username):
            # NOOP
            pass

    if os.environ.get('PT_KEYRING_SERVER'):
        new_keyring = DumbServer()  # NOTE this introduces a delay if server not present when calling keyring.get_password()
        keyring.set_keyring(new_keyring)


def keyring_get_password():
    """If keyring lib available, make a lookup
    Returns None if no password available
    TODO
      * Determine which backend
      * Determine service/username
    """
    log.info('keyring_get_password called')
    if not keyring:
        return None
    app, username = 'puren_tonbo', 'dumb'  # TODO review
    password = keyring.get_password(app, username)
    return password


any_filename_filter = lambda x: True  # allows any filename, i.e. no filtering


def supported_filetypes_info(encrypted_only=False):
    for file_extension in file_type_handlers:
        if encrypted_only and file_extension in RawFile.extensions:
            continue
        handler_class = file_type_handlers[file_extension]
        yield (file_extension, handler_class.__name__, handler_class.description)

def supported_filename_filter(in_filename):
    name = in_filename.lower()
    #print('DEBUG %r %r' % (in_filename, list(file_type_handlers.keys())))
    for file_extension in file_type_handlers:
        if name.endswith(file_extension):
            # TODO could look at mapping and check that too, e.g. only Raw files
            return True
    return False

def plaintext_filename_filter(in_filename):
    name = in_filename.lower()
    #print('DEBUG %r %r' % (in_filename, list(file_type_handlers.keys())))
    for file_extension in ('.txt', '.md', ):  # FIXME hard coded for known plain text extensions that Rawfile is configured with. See supported_filetypes_info() for less fragile approach
        if name.endswith(file_extension):
            # TODO could look at mapping and check that too, e.g. only Raw files
            return True
    return False

encrypted_extensions = list(puren_tonbo.supported_filetypes_info(encrypted_only=True))  # generator gets exhusted and encrypted check only works the first time!. TODO for (future) dynamic plugins with discovery to work, can't use a static list here
def encrypted_filename_filter(filename):
    filename_lower = filename.lower()
    for file_extension in encrypted_extensions:
        if filename_lower.endswith(file_extension):
            return True
    return False
is_encrypted = encrypted_filename_filter

## TODO implement generator function that takes in filename search term

def example_progess_callback(*args, **kwargs):
    print('example_progess_callback:', args, kwargs)

def grep_string(search_text, regex_object, highlight_text_start=None, highlight_text_stop=None, files_with_matches=False):
    """Given input string "search_text" and compiled regex regex_object
    search for regex matches and return list of tuples of line number and text for that line
    for matches, prefix and postfix with highlight_text_start, highlight_text_stop
    """
    def process_matches(match):
        return highlight_text_start + match.group(0) + highlight_text_stop

    linecount = 0
    results = []
    #print('%r' % ((regex_object, search_text,),))
    for x in search_text.split('\n'):
        linecount += 1
        if regex_object.search(x):
            if not highlight_text_start:
                results.append((linecount, x))
            else:
                # simplisic highlighting with prefix/postfix - no escaping or processing of non-match text performed
                tmp_x = regex_object.sub(process_matches, x)
                results.append((linecount, tmp_x))
            if files_with_matches:
                break  # stop after first hit. TODO refactor check?
    return results


class BaseNotes(object):
    restrict_to_note_root = True  # if True do not allow access to files outside of self.note_root

    def __init__(self, note_root, note_encoding=None):
        self.note_root = note_root
        #self.note_encoding = note_encoding or 'utf8'
        self.note_encoding = note_encoding or ('utf8', 'cp1252')

    def recurse_notes(self, sub_dir=None, filename_filter=any_filename_filter):  # Also supported_filename_filter
        """Recursive Tombo note lister.
        Iterator of files in @sub_dir"""
        raise NotImplementedError('Implement in sub-class')

    def directory_contents(self, sub_dir=None):
        """Simple non-recursive Tombo note lister.
        Returns tuple (list of directories, list of files) in @sub_dir"""
        raise NotImplementedError('Implement in sub-class')

    #def search(self, *args, **kwargs):
    def search(self, search_term):
        """iterator that searches note directory, grep/regex-like
        returns values like:
            ('somefile.txt', [(2, 'line two'),])"""
        raise NotImplementedError('Implement in sub-class')

    def note_contents(self, filename, get_pass=None, dos_newlines=True, return_bytes=False, handler_class=None):
        """@filename is relative to `self.note_root` and includes directory name if not in the root.
        @filename (extension) dictates encryption mode/format (if any)
        @get_pass is either plaintext (bytes) password or a callback function that returns a password, get_pass() should return None for 'cancel'. See caching_console_password_prompt() for an example.
            get_pass(filename=filename, reset=reset_password)
        dos_newlines=True means use Windows/DOS newlines, emulates win32 behavior of Tombo and is the default
        @return_bytes returns bytes rather than (Unicode) strings
        """
        raise NotImplementedError('Implement in sub-class')

    def note_contents_save(self, note_text, sub_dir=None, filename=None, original_full_filename=None, get_pass=None, dos_newlines=True, backup=True):
        """Save the contents in the string @note_text, to @filename if specified else derive filename from first line in note.
        if sub_dir is not specified `self.note_root` is assumed
        @original_full_filename should be relative to `self.note_root` and include directory name - will also help determine type and potentially remove once saved if filename has changed
        force  encryption or is filename the only technique?
        Failures during call should leave original filename present and untouched
        """
        raise NotImplementedError('Implement in sub-class')

    def note_delete(self, filename, backup=True):
        pass

    def note_size(self, filename):
        return 9999999999  # more likely to be noticed as an anomaly
        return -1


##############################

# Local file system functions
def to_string(data_in_bytes, note_encoding='utf-8'):
    """Where note_encoding can also be a list, e.g. ['utf8', 'cp1252']
    """
    #log.debug('note_encoding %r', note_encoding)
    #log.debug('data_in_bytes %r', data_in_bytes)
    if not isinstance(data_in_bytes, (bytes, bytearray)):  # FIXME revisit this, "is string" check
        return data_in_bytes  # assume a string already
    if isinstance(note_encoding, basestring):
        return data_in_bytes.decode(note_encoding)
    for encoding in note_encoding:
        try:
            result = data_in_bytes.decode(encoding)
            return result
        except UnicodeDecodeError:
            pass  # try next
        # TODO try/except

def unicode_path(filename):
    if isinstance(filename, bytes):
        # want unicode string so that all file interaction is unicode based
        filename = filename.decode('utf8')  # FIXME hard coded, pick up from config or locale/system encoding
    return filename

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

def note_contents_load_filename(filename, get_pass=None, dos_newlines=True, return_bytes=False, handler_class=None, note_encoding='utf-8'):
    """Uses local file system IO api
        @handler dictates encryption mode/format (if any)
        @filename if handlerommited, extension dictates encryption mode/format (if any)
        @get_pass is either plaintext (bytes) password or a callback function that returns a password, get_pass() should return None for 'cancel'.
            See caching_console_password_prompt() for an example. API expected:
                get_pass(filename=filename, reset=reset_password)
        dos_newlines=True means use Windows/DOS newlines, emulates win32 behavior of Tombo and is the default
        @return_bytes returns bytes rather than (Unicode) strings
        @note_encoding can also be a list, e.g. ['utf8', 'cp1252']
    """
    try:
        filename = unicode_path(filename)

        handler_class = handler_class or filename2handler(filename)
        reset_password = False
        while True:
            #import pdb ; pdb.set_trace()
            if handler_class is RawFile:
                log.debug('it is plain text')
                note_password = ''  # fake it. Alternatively override init for RawFile to remove check
            else:
                #import pdb ; pdb.set_trace()
                if callable(get_pass):
                    note_password = get_pass(filename=filename, reset=reset_password)
                    # sanity check needed in case function returned string
                    if not isinstance(note_password, bytes):
                        note_password = note_password.encode("utf-8")
                else:
                    # Assume password bytes passed in
                    note_password = get_pass
                if note_password is None:
                    raise SearchCancelled('empty password for for %s' % filename)

            #import pdb ; pdb.set_trace()
            handler = handler_class(key=note_password)  # FIXME callback function support for password func
            # TODO repeat on bad password func
            log.debug('DEBUG filename %r', fullpath_filename)

            in_file = None
            try:
                in_file = open(fullpath_filename, 'rb')  # TODO open once and seek back on failure
                plain_str = handler.read_from(in_file)
                if return_bytes:
                    return plain_str
                else:
                    return to_string(plain_str, note_encoding=note_encoding)
            except BadPassword as info:
                ## We will try the file again with a new (reset) password
                if not callable(get_pass):
                    raise
                reset_password = True
            finally:
                if in_file:
                    in_file.close()
    except IOError as info:
        if info.errno == errno.ENOENT:
            raise PurenTonboIO('Error opening %r file/directory does not exist' % filename)
        else:
            raise
    except PurenTonboException as info:
        log.debug("Encrypt/Decrypt problem. %r", (info,))
        raise

def note_contents_save_filename(note_text, filename=None, original_filename=None, handler=None, dos_newlines=True, backup=True, use_tempfile=True, note_encoding='utf-8'):
    """Uses local file system IO api
    @handler is the encryption file handler to use, that is already initialized with a password
    @note_encoding if None, assume note_text is bytes, if a string use as the encoding, can also be a list, e.g. ['utf8', 'cp1252'] in which case use the first one
    """
    if filename is None:
        NotImplementedError('filename is None')
    if original_filename is not None:
        NotImplementedError('original_filename is not None')

    filename = unicode_path(filename)
    if note_encoding is None:
        plain_str_bytes = note_text
    else:
        if dos_newlines:
            note_text = note_text.replace('\n', '\r\n')  # TODO remove all \r first as a cleaning step?
        # see to_string() for reverse
        if isinstance(note_encoding, basestring):
            plain_str_bytes = note_text.encode(note_encoding)
        else:
            plain_str_bytes = note_text.encode(note_encoding[0])

    if use_tempfile:
        timestamp_now = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
        out_file = tempfile.NamedTemporaryFile(
            mode='wb',
            dir=os.path.dirname(filename),
            prefix=os.path.basename(filename) + timestamp_now,
            delete=False
        )
        tmp_out_filename = out_file.name
        log.debug('DEBUG tmp_out_filename %r', tmp_out_filename)
    else:
        out_file = open(filename, 'wb')  # Untested

    handler.write_to(out_file, plain_str_bytes)
    out_file.close()

    if backup:
        if os.path.exists(filename):
            file_replace(filename, filename + '.bak')  # backup existing

    if use_tempfile:
        file_replace(tmp_out_filename, filename)

# Local file system navigation functions
def walker(directory_name, process_file_function=None, process_dir_function=None, extra_params_dict=None):
    """extra_params_dict optional dict to be passed into process_file_function() and process_dir_function()

    def process_file_function(full_path, extra_params_dict=None)
        extra_params_dict = extra_params_dict or {}
    """
    extra_params_dict or {}
    # TODO scandir instead... would be faster - but for py2.7 requires external lib
    for root, subdirs, files in os.walk(directory_name):
        if process_file_function:
            for filepath in files:
                full_path = os.path.join(root,filepath)
                process_file_function(full_path, extra_params_dict=extra_params_dict)
        if process_dir_function:
            for sub in subdirs:
                full_path = os.path.join(root, sub)
                process_dir_function(full_path, extra_params_dict=extra_params_dict)

def recent_files_filter(full_path, extra_params_dict=None):
    max_recent_files = extra_params_dict['max_recent_files']
    recent_files = extra_params_dict['recent_files']
    mtime = int(os.path.getmtime(full_path))
    list_value = (mtime, full_path)
    do_insert = False
    if len(recent_files) < max_recent_files:
        do_insert = True
    elif recent_files:
        oldest_entry = recent_files[0]
        if list_value > oldest_entry:
            do_insert = True
    if do_insert:
        position = bisect.bisect(recent_files, (mtime, full_path))
        bisect.insort(recent_files, (mtime, full_path))
        if len(recent_files) > max_recent_files:
            del recent_files[0]

ORDER_ASCENDING = 'ascending'
ORDER_DESCENDING = 'descending'
def find_recent_files(test_path, number_of_files=20, order=ORDER_ASCENDING):
    extra_params_dict = {
        #'directory_path': directory_path,  # not used
        #'directory_path_len': directory_path_len,
        'max_recent_files': number_of_files,
        'recent_files': [],
    }

    walker(test_path, process_file_function=recent_files_filter, extra_params_dict=extra_params_dict)
    recent_files = extra_params_dict['recent_files']
    if ORDER_DESCENDING == order:
        recent_files.reverse()
    for mtime, filename in recent_files:
        yield filename

def recurse_notes(path_to_search, filename_filter):
    """Walk (local file system) directory of notes, directory depth first (just like Tombo find does), returns generator
    """
    ## Requires os.walk (python 2.3 and later).
    ## Pure Python versions for earlier versions available from:
    ##  http://osdir.com/ml/lang.jython.user/2006-04/msg00032.html
    ## but lacks "topdown" support, walk class later
    for dirpath, dirnames, filenames in os.walk(path_to_search, topdown=False):
        #print('walker', repr((dirnames, filenames)))
        filenames.sort()
        #print('walker', repr((dirnames, filenames)))
        for temp_filename in filenames:
            if filename_filter(temp_filename):
                #print('filename filter true ', repr((temp_filename,)))
                temp_filename = os.path.join(dirpath, temp_filename)
                #print 'yield ', temp_filename
                yield temp_filename


def fake_recurse_notes(path_to_search, filename_filter):
    """Same API as recurse_notes(), returns generator
        BUT used on a single file (and ignores filename_filter)
    """
    yield path_to_search


def directory_contents(dirname, filename_filter=None):
    """Simple non-recursive Tombo note lister.
    Returns tuple (list of directories, list of files) in @dirname"""
    filename_filter = filename_filter or supported_filename_filter  # or perhaps any_filename_filter
    ## TODO consider using 'dircache' instead of os.listdir?
    ## should not be re-reading so probably not a good idea
    file_list = []
    dir_list = []
    if os.path.isdir(dirname):
        for name in os.listdir(dirname):
            path = os.path.join(dirname, name)
            if os.path.isfile(path):
                if filename_filter(name):
                    file_list.append(name)
            if os.path.isdir(path):
                dir_list.append(name)
    else:
        # assume a file, ignores s-links
        file_list.append(os.path.basename(dirname))

    dir_list.sort()
    file_list.sort()
    return dir_list, file_list

##############################


class FileSystemNotes(BaseNotes):
    """PyTombo notes on local file system, just like original Windows Tombo
    """

    def __init__(self, note_root, note_encoding=None):
        note_root = self.unicode_path(note_root)  # either a file or a directory of files
        self.note_root = os.path.abspath(note_root)
        self.abs_ignore_path = os.path.join(self.note_root, '') ## add trailing slash.. unless this is a file
        #self.note_encoding = note_encoding or 'utf8'
        self.note_encoding = note_encoding or ('utf8', 'cp1252')

    def abspath2relative(self, input_path):
        """returns input_path with (leading) self.note_root removed.
        If ignore_path is not at the start of the input_path, raise error"""
        abs_ignore_path = self.abs_ignore_path
        #abs_input_path = os.path.abspath(input_path)
        abs_input_path = input_path
        if abs_input_path.startswith(abs_ignore_path):
            return abs_input_path[len(abs_ignore_path):]
        raise PurenTonboException('path not in note tree')

    def abspath(self, sub_dir, filename):
        filename = self.unicode_path(filename)
        fullpath_filename = os.path.join(self.note_root, filename)
        fullpath_filename = os.path.abspath(fullpath_filename)
        if not fullpath_filename.startswith(self.note_root):
            raise PurenTonboIO('outside of note tree root')
        return fullpath_filename

    def to_string(self, data_in_bytes):
        #log.debug('self.note_encoding %r', self.note_encoding)
        #log.debug('data_in_bytes %r', data_in_bytes)
        if not isinstance(data_in_bytes, (bytes, bytearray)):  # FIXME revisit this, "is string" check
            return data_in_bytes  # assume a string already
        if isinstance(self.note_encoding, basestring):
            return data_in_bytes.decode(self.note_encoding)
        for encoding in self.note_encoding:
            try:
                result = data_in_bytes.decode(encoding)
                return result
            except UnicodeDecodeError:
                pass  # try next
            # TODO try/except

    def unicode_path(self, filename):
        if isinstance(filename, bytes):
            # want unicode string so that all file interaction is unicode based
            filename = filename.decode('utf8')  # FIXME hard coded, pick up from config or locale/system encoding
        return filename

    def recent_notes(self, sub_dir=None, number_of_files=20, order=ORDER_ASCENDING):
        """Recursive Tombo note lister for recently updated/modified files.
        Iterator of files in @sub_dir"""
        return find_recent_files(self.note_root, number_of_files=number_of_files, order=order)

    def recurse_notes(self, sub_dir=None, filename_filter=any_filename_filter):
        """Recursive Tombo note lister.
        Iterator of files in @sub_dir"""
        return recurse_notes(self.note_root, filename_filter)

    def directory_contents(self, sub_dir=None):
        """Simple non-recursive Tombo note lister.
        Returns tuple (list of directories, list of files) in @sub_dir"""
        if sub_dir and not self.restrict_to_note_root:
            raise NotImplementedError('sub_dir param not implemented (and restriction code missing)')
        sub_dir = self.note_root  # TODO implement sub_dir parameter suport
        return directory_contents(dirname=sub_dir)

    # FIXME Consider adding dictionary parameter for search options rather than new keywords each time?
    #         (self, search_term, search_term_is_a_regex=True,  ignore_case=True,  search_encrypted=False, get_password_callback=None, progess_callback=None, find_only_filename=None, index_name=None, note_encoding=None):
    #               (search_term, search_term_is_a_regex=True , ignore_case=True,  search_encrypted=False, get_password_callback=None, progess_callback=None, find_only_filename=None, index_name=None, note_encoding=None):
    def search(self, search_term, search_term_is_a_regex=False, ignore_case=False, search_encrypted=False, find_only_filename=False, files_with_matches=False, get_password_callback=None, progess_callback=None, highlight_text_start=None, highlight_text_stop=None):
        """search note directory, grep/regex like actualy an iterator"""
        #print('get_password_callback %r' % get_password_callback)

        search_path = self.note_root
        """
        if (highlight_text_start or highlight_text_stop) and None in (highlight_text_start or highlight_text_stop):
            raise SearchException('highlight_text_start and highlight_text_stop need to both be set or both not-set %r %r' % (highlight_text_start, highlight_text_stop))
        """
        if not search_term_is_a_regex:
            search_term = re.escape(search_term)
        if ignore_case:
            regex_object = re.compile(search_term, re.IGNORECASE)
        else:
            regex_object = re.compile(search_term)
        filename_filter_str = None
        if find_only_filename:
            filename_filter_str = regex_object
        #is_note_filename_filter = pytombo.search.note_filename_filter_gen(allow_encrypted=search_encrypted, filename_filter_str=filename_filter_str)  # FIXME implement
        if search_encrypted:
            is_note_filename_filter = supported_filename_filter
        else:
            # plain text only, right now this is hard coded
            is_note_filename_filter = plaintext_filename_filter
        if os.path.isfile(search_path):
            recurse_notes_func = fake_recurse_notes
        else:
            recurse_notes_func = self.recurse_notes
        for tmp_filename in recurse_notes_func(search_path, is_note_filename_filter):
            if recurse_notes_func == fake_recurse_notes:
                filename = tmp_filename  # already absolute?  TODO check abspath2relative() - could sanity check already absoloute?
            else:
                filename = self.abspath2relative(tmp_filename)
            if progess_callback:
                progess_callback(filename=x)
            if filename_filter_str:
                if regex_object.search(filename):
                    yield (filename, [(1, 'FILENAME SEARCH HIT\n')])
            include_contents = True  # possible override to include line matches but ONLY doing that for filename matches
            include_contents = False
            ## TODO decide what to do with include_contents - default or make a parameter
            if not filename_filter_str or include_contents:
                #import pdb ; pdb.set_trace()
                note_text = self.note_contents(filename, get_pass=get_password_callback, dos_newlines=True)  # FIXME determine what to do about dos_newlines (rename?)
                search_res = grep_string(note_text, regex_object, highlight_text_start, highlight_text_stop, files_with_matches=files_with_matches)
                if search_res:
                    yield (filename, search_res)


    def note_contents(self, filename, get_pass=None, dos_newlines=True, return_bytes=False, handler_class=None):
        """@filename is relative to `self.note_root` and includes directory name if not in the root.
        @filename (extension) dictates encryption mode/format (if any)
        @get_pass is either plaintext (bytes) password or a callback function that returns a password, get_pass() should return None for 'cancel'.
            See caching_console_password_prompt() for an example. API expected:
                get_pass(filename=filename, reset=reset_password)
        dos_newlines=True means use Windows/DOS newlines, emulates win32 behavior of Tombo and is the default
        @return_bytes returns bytes rather than (Unicode) strings
        """
        try:
            filename = self.unicode_path(filename)
            fullpath_filename = self.abspath(self.note_root, filename)


            handler_class = handler_class or filename2handler(filename)
            reset_password = False
            while True:
                #import pdb ; pdb.set_trace()
                if handler_class is RawFile:
                    log.debug('it is plain text')
                    note_password = ''  # fake it. Alternatively override init for RawFile to remove check
                else:
                    #import pdb ; pdb.set_trace()
                    if callable(get_pass):
                        note_password = get_pass(filename=filename, reset=reset_password)
                        # sanity check needed in case function returned string
                        if not isinstance(note_password, bytes):
                            note_password = note_password.encode("utf-8")
                    else:
                        # Assume password bytes passed in
                        note_password = get_pass
                    if note_password is None:
                        raise SearchCancelled('empty password for for %s' % filename)

                #import pdb ; pdb.set_trace()
                handler = handler_class(key=note_password)  # FIXME callback function support for password func
                # TODO repeat on bad password func
                log.debug('DEBUG filename %r', fullpath_filename)

                in_file = None
                try:
                    in_file = open(fullpath_filename, 'rb')  # TODO open once and seek back on failure
                    plain_str = handler.read_from(in_file)
                    # TODO could stash away handler..key for reuse as self.last_used_key .... or derived_key (which would be a new attribute)
                    if return_bytes:
                        return plain_str
                    else:
                        return self.to_string(plain_str)
                except BadPassword as info:
                    ## We will try the file again with a new (reset) password
                    if not callable(get_pass):
                        raise
                    reset_password = True
                finally:
                    if in_file:
                        in_file.close()
        except IOError as info:
            if info.errno == errno.ENOENT:
                raise PurenTonboIO('Error opening %r file/directory does not exist' % filename)
            else:
                raise
        except PurenTonboException as info:
            log.debug("Encrypt/Decrypt problem. %r", (info,))
            raise

    def note_contents_save(self, note_text, filename=None, original_filename=None, get_pass=None, dos_newlines=True, backup=True):
        raise NotImplementedError('Implement in sub-class')

    def note_delete(self, filename, backup=True):
        pass

    def note_size(self, filename):
        return 9999999999  # more likely to be noticed as an anomaly
        return -1


#############

# Config files

default_config_filename = 'pt.ini'  # if using https://github.com/DiffSK/configobj
# Consider YAML? toml - https://toml.io/ https://github.com/hukkin/tomli
default_config_filename = 'pt.json'  # built in so easy choice for now
# TODO Android home directory?
default_config_dirname = os.environ.get('HOME', os.environ.get('USERPROFILE'))  # TODO consider os.path.expanduser("~") and for Windows My Documents


def get_config_path(config_filename=None, dirs_to_search=None, dir_if_not_found=None):
    """Attempts to find (and return) existing config file name.
    If config file can not be found default name is returned.

        - @dirs_to_search list of directories to search, if not specified defaults
        - @dir_if_not_found is the directory to use if no config file is found
    """
    config_filename  = config_filename or default_config_filename
    dirs_to_search = dirs_to_search or ['.', default_config_dirname]
    dir_if_not_found = dir_if_not_found or default_config_dirname

    full_config_pathname = None
    for tmp_dirname in dirs_to_search:
        tmp_config_filename = os.path.join(tmp_dirname, config_filename)
        if os.path.exists(tmp_config_filename):
            full_config_pathname = tmp_config_filename
            break

    if full_config_pathname is None:
        #print('no config file found, defaulting')
        full_config_pathname = os.path.join(dir_if_not_found, config_filename)

    #print('full_config_pathname = %r' % full_config_pathname)
    full_config_pathname = os.path.normpath(full_config_pathname)  # abspath?
    return full_config_pathname

def get_config(config_filename=None):
    config_filename = config_filename or get_config_path()
    config_filename = os.path.abspath(config_filename)
    if os.path.exists(config_filename):
        with open(config_filename) as config_file:
            config = json.load(config_file)
    else:
        config = {}
    defaults = {
        '_version_created_with': '%s' % __version__,
        'note_root': '.',  # root directory of notes
        'codec': ('utf8', 'cp1252'),  # note encoding(s) in order to try for reading, first is the encoding for writing
        'default_text_ext': 'txt',
        'default_encryption_ext': 'chi',
        #'default_encryption_ext': 'aes256.zip',
        #'new_lines': 'dos',
        #'new_lines': 'unix',
        #'': '',
        'ptig': {
            'use_pager': False,
            'prompt': u'ptig: \U0001f50e ',
        }
    }

    # platform specific
    if is_win:
        # For Microsoft Windows can not use "start", that only works for directories withOUT spaces
        # as soon as double quotes are used, opens up wrong location
        defaults['ptig']['file_browser'] = 'explorer'
    else:
        # Assume Linux
        # For now default to LXDE PCManFM, user needs to override
        # TODO add heuristics; xdg-open, jaro, mc, etc.
        defaults['ptig']['file_browser'] = 'pcfileman'

    defaults.update(config)  # NOTE this does not handle nested, i.e. if config file has 'ptig' but not ptig.prompt, default above will not be retained
    # TODO codec may need to be parsed if it came from config file as was a comma seperate string
    return defaults

def print_version_info():
    print(sys.version)
    print('')
    print('Puren Tonbo puren_tonbo version %s' % puren_tonbo.__version__)
    print('Formats:')
    print('')
    for file_extension, file_type, file_description in supported_filetypes_info():
        print('%17s - %s - %s' % (file_extension[1:], file_type, file_description))
    print('')
    print('Libs:')
    if chi_io:
        print('\tchi_io.implementation: %s' % chi_io.implementation)
    print('\tccrypt version: %s exe: %s' % (ccrypt_version, CCRYPT_EXE))
    if gnupg:
        print('\tpython-gnupg version: %s' % gnupg.__version__)
    if gpg:
        print('\tgpg version: %r' % (gpg.version,))
    if pyzipper:
        print('\tpyzipper version: %s' % pyzipper.__version__)
    print('')



def main(argv=None):
    if argv is None:
        argv = sys.argv

    print('Python %s on %s\n\n' % (sys.version, sys.platform))
    print('Python %s on %s\n\n' % (sys.version.replace('\n', ' - '), sys.platform))
    print('Python %r on %r\n\n' % (sys.version, sys.platform))

    return 0


if __name__ == "__main__":
    sys.exit(main())
