
import bisect
import datetime
import errno
import inspect
from io import BytesIO as FakeFile
import json
import locale
import logging
import os
import re
import sqlite3  # TODO make optional?
import subprocess
import sys
import tempfile
import uuid
import zlib

try:
    maketrans = bytearray.maketrans
except AttributeError:
    # Python 2
    from string import maketrans

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
        chi_io = fake_module('chi_io')

try:
    import colorlog  # https://github.com/borntyping/python-colorlog
except ImportError:
    colorlog = None

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
    import jenc  # https://github.com/clach04/jenc-py/
except ImportError:
    jenc = fake_module('jenc')

try:
    import keyring  # python -m pip install keyring
    import keyring.backend
except ImportError:
    keyring = fake_module('keyring')

try:
    from openssl_enc_compat.cipher import OpenSslEncDecCompat  # https://github.com/clach04/openssl_enc_compat/
    import openssl_enc_compat
except ImportError:
    OpenSslEncDecCompat = fake_module('openssl_enc_compat')

try:
    import pyzipper  # https://github.com/danifus/pyzipper  NOTE py3 only
except ImportError:
    pyzipper = fake_module('pyzipper')

try:
    #import vimdecrypt  # https://github.com/nlitsme/vimdecrypt
    from puren_tonbo import vimdecrypt  # https://github.com/nlitsme/vimdecrypt
except ImportError:
    vimdecrypt = fake_module('vimdecrypt')

try:
    if os.environ.get('FORCE_AGEEXE'):  raise ImportError()  # force usage of age command line binary exe
    #import ssage  # https://github.com/esoadamo/ssage/  # does not (yet?) support passphrases
    import age  # https://github.com/jojonas/pyage
    import age.file
    import age.keys.password
except ImportError:
    #ssage = fake_module('ssage')
    age = fake_module('age')

try:
    import puren_tonbo.mzipaes as mzipaes
    from puren_tonbo.mzipaes import ZIP_DEFLATED, ZIP_STORED
except ImportError:
    mzipaes = fake_module('mzipaes')
    #ZIP_DEFLATED, ZIP_STORED = mzipaes.ZIP_DEFLATED, mzipaes.ZIP_STORED
    ZIP_STORED = 0
    ZIP_DEFLATED = 8



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

def log_setup(log_name):
    # create log
    # TODO check NO_COLOR - see existing NO_COLOR code, simple option would be to set colorlog to None
    if colorlog:
        log = colorlog.getLogger(log_name)
    else:
        log = logging.getLogger(log_name)
    log.setLevel(logging.WARN)  # bare minimum
    log.setLevel(logging.INFO)
    log.setLevel(logging.DEBUG)
    disable_logging = False
    disable_logging = True
    if disable_logging:
        log.setLevel(logging.NOTSET)  # only logs; WARNING, ERROR, CRITICAL

    if colorlog:
        ch = colorlog.StreamHandler()
    else:
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

    if colorlog:
        formatter = colorlog.ColoredFormatter('%(log_color)s' + logging_fmt_str)
    else:
        formatter = logging.Formatter(logging_fmt_str)
    ch.setFormatter(formatter)
    log.addHandler(ch)
    return log

log = log_setup("mylogger")
log.debug('encodings %r', (sys.getdefaultencoding(), sys.getfilesystemencoding(), locale.getdefaultlocale()))

class PurenTonboException(Exception):
    '''Base chi I/O exception'''


class BadPassword(PurenTonboException):
    '''Bad password exception'''


class UnsupportedFile(PurenTonboException):
    '''File not encrypted/not supported exception'''

class PurenTonboIO(PurenTonboException):
    '''(File) I/O exception'''

class PurenTonboBadCall(PurenTonboException):
    '''Incorrect API call'''


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


"""The core of the encryption/decryption API revolves around file objects, that is file-like API objects
This differs substantially from PEP 272 - API for Block Encryption Algorithms v1.0 - https://peps.python.org/pep-0272/
which is based on block input.

puren_tonbo expects to be dealing with (on-disk) files, hence the focus on file-like objects.
"""

class BaseFile:

    description = 'Base Encrypted File'
    extensions = []  # non-empty list of file extensions, first is the default (e.g. for writing) and last should be the most generic
    implementation = 'py'  # exe
    kdf = None  # OPTIONAL key derivation function, that takes a single parameter of bytes for the password/key. See TomboBlowfish  # TODO review this
    needs_key = True  # if not true, then this class does not require a key (password) to operate

    def default_extension(self):
        return self.extensions[0]  # pick the first one

    def split_extension(self, filename):
        for extn in self.extensions:
            if filename.endswith(extn):
                return filename[:-len(extn)], extn
        pass

    def __init__(self, key=None, password=None, password_encoding='utf8'):
        """
        key - is the actual encryption key in bytes
        password is the passphrase/password as a string
        password_encoding is used to create key from password if key is not provided
        """
        if key is None and password is None:
            raise PurenTonboBadCall('need password or key')
        if key is not None:
            self.key = key
        elif password:
            key = password.encode(password_encoding)
            if self.kdf:
                self.key = self.kdf(key)
            else:
                self.key = key

    ## TODO rename read_from() -> read() - NOTE this would not be file-like
    # TODO add wrapper class for file-like object api
    def read_from(self, file_object):
        """Decrypt"""
        raise NotImplementedError

    def write_to(self, file_object, byte_data):
        """Encrypt"""
        raise NotImplementedError


class EncryptedFile(BaseFile):
    pass

class RawFile(BaseFile):
    """Raw/binary/text file - Read/write raw bytes. 
    Use for plain text files.
    TODO this requires a password on init, plain text/unencrypted files should not need a password
    """

    description = 'Raw file, no encryption support'
    extensions = ['.txt', '.md']
    needs_key = False  # raw files are not encrypted and do not require a key/password

    def __init__(self, key=None, password=None, password_encoding='utf8'):
        pass  # NOOP, password/key is NOT required

    def read_from(self, file_object):
        return file_object.read()

    def write_to(self, file_object, byte_data):
        file_object.write(byte_data)

class CompressedFile(BaseFile):
    description = 'Compressed file Base Class - not encrypted'
    needs_key = False  # not encrpypted

    def __init__(self, key=None, password=None, password_encoding='utf8'):
        pass  # NOOP, password/key is NOT required and IGNORED!

class CompressedZlib(CompressedFile):
    description = 'zlib - could be gz or Z'
    extensions = ['.gz', '.Z']  # NOTE this is a little greedy, matches .tar.gz (which is currently not supported) which really should be ignored (until/if archive support is added) TODO how to skip tar files (etc.)

    def read_from(self, file_object):
        # NOTE no password/key usage!
        data = file_object.read()
        try:
            if is_py3:
                return zlib.decompress(data, wbits=47)
            else:
                # Python 2 has now idea about wbits
                return zlib.decompress(data)
        except Exception as info:
            #raise  # debug
            # chain exception...
            raise PurenTonboException(info)

    def write_to(self, file_object, byte_data):
        file_object.write(zlib.compress(byte_data))


class SubstitutionCipher(EncryptedFile):
    description = '*Unsecure* Substitution Cipher Base Class - do NOT use for sensitive data, provided for testing purposes!'
    needs_key = False  # Substitution Cipher files do not require a key/password - which is why they are unsecure!

    def __init__(self, key=None, password=None, password_encoding='utf8'):
        pass  # NOOP, password/key is NOT required and IGNORED!


class Rot13(SubstitutionCipher):
    description = 'rot-13 UNSECURE!'
    extensions = ['.rot13']

    substitution_table = maketrans(b'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz', b'NOPQRSTUVWXYZABCDEFGHIJKLMnopqrstuvwxyzabcdefghijklm')

    def read_from(self, file_object):
        # NOTE no password/key usage!
        data = file_object.read()
        try:
            return data.translate(self.substitution_table)
        except Exception as info:
            #raise  # debug
            # chain exception...
            raise PurenTonboException(info)

    def write_to(self, file_object, byte_data):
        file_object.write(byte_data.translate(self.substitution_table))


class Rot47(Rot13):
    description = 'rot-47 UNSECURE!'
    extensions = ['.rot47']

    substitution_table = maketrans(
        b'!"#$%&\'()*+,-./0123456789:;<=>?@ABCDEFGHIJKLMNOPQRSTUVWXYZ[\\]^_`abcdefghijklmnopqrstuvwxyz{|}~',
        b'PQRSTUVWXYZ[\\]^_`abcdefghijklmnopqrstuvwxyz{|}~!"#$%&\'()*+,-./0123456789:;<=>?@ABCDEFGHIJKLMNO'
    )


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
ccrypt_version = 'MISSING'  # TODO make this part of Ccrypt class

class CcryptExe(EncryptedFile):  # TODO refactor into a shared spawn exe class
    """ccrypt - ccrypt - https://ccrypt.sourceforge.net/
    NOTE uses external command line tool, rather than use files
    with ccrypt exe stdin/stdout is used instead to adhere to
    API and also avoid hitting filesystem (with plain text).
    """

    description = 'ccrypt symmetric Rijndael'
    extensions = [
        '.cpt',  # binary
    ]
    implementation = 'exe'


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

Ccrypt = CcryptExe

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
        r"""
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


class OpenSslEnc10k(EncryptedFile):
    description = 'OpenSSL 1.1.0 pbkdf2 iterations 10000 aes-256-cbc'
    extensions = [
        '.openssl_aes256cbc_pbkdf2_10k',  # generated via openssl enc -e -aes-256-cbc -in plain_in -out crypted_out.openssl_aes256cbc_pbkdf2_10k -salt -pbkdf2 -iter 10000
    ]
    # TODO KeepOut .kpt files - https://antofthy.gitlab.io/software/keepout.sh.txt

    def read_from(self, file_object):
        # TODO catch exceptions and raise PurenTonboException()
        data = file_object.read()
        password = self.key
        if not isinstance(password, bytes):
            password = password.decode("utf-8")
        cipher = OpenSslEncDecCompat(password)
        plaintext = cipher.decrypt(data)  # guesses if base64 encoded or note
        return plaintext

    def write_to(self, file_object, byte_data):
        password = self.key
        if not isinstance(password, bytes):
            password = password.decode("utf-8")
        cipher = OpenSslEncDecCompat(password)
        crypted_bytes = cipher.encrypt(byte_data)
        file_object.write(crypted_bytes)

class Jenc(EncryptedFile):
    description = 'Markor / jpencconverter pbkdf2-hmac-sha512 iterations 10000 AES-256-GCM'
    extensions = [
        '.jenc',  # md and txt?
    ]
    _jenc_version = None  # use default (latest)

    def read_from(self, file_object):
        # TODO catch exceptions and raise PurenTonboException()
        encrypted_bytes = file_object.read()
        password = self.key
        if not isinstance(password, bytes):
            password = password.decode("utf-8")

        plaintext = jenc.decrypt(password, encrypted_bytes)
        return plaintext

    def write_to(self, file_object, byte_data):
        password = self.key
        if not isinstance(password, bytes):
            password = password.decode("utf-8")

        crypted_bytes = jenc.encrypt(password, byte_data, jenc_version=self._jenc_version)
        file_object.write(crypted_bytes)

class JencU001(Jenc):
    description = 'Markor / jpencconverter U001 PBKDF2WithHmacSHA1 iterations 10000 AES-256-GCM, legacy for older Android versions'
    extensions = [
        '.u001.jenc',  # md and txt?
        '.u001_jenc',  # md and txt?
        # Do NOT include generic .jenc
    ]
    _jenc_version = 'U001'  # FIXME constant from jenc instead of literal

class JencV001(Jenc):
    description = 'Markor / jpencconverter pbkdf2-hmac-sha512 iterations 10000 AES-256-GCM'
    extensions = [
        '.v001.jenc',  # md and txt?
        '.v001_jenc',  # md and txt?
        # Do NOT include generic .jenc
    ]
    _jenc_version = 'V001'

class JencV002(Jenc):
    description = 'Markor / jpencconverter pbkdf2-hmac-sha512 iterations 210000 AES-256-GCM - EXPERIMENTAL https://github.com/clach04/jenc-py/issues/7'
    extensions = [
        '.v002.jenc',  # md and txt?
        '.v002_jenc',  # md and txt?
        # Do NOT include generic .jenc
    ]
    _jenc_version = 'V002'


class TomboBlowfish(EncryptedFile):
    """Read/write Tombo (modified) Blowfish encrypted files
    Compatible with files in:
      * Tombo - http://tombo.osdn.jp/En/
      * Kumagusu - https://osdn.net/projects/kumagusu/ and https://play.google.com/store/apps/details?id=jp.gr.java_conf.kumagusu
      * miniNoteViewer - http://hatapy.web.fc2.com/mininoteviewer.html and https://play.google.com/store/apps/details?id=jp.gr.java_conf.hatalab.mnv&hl=en_US&gl=US
    """

    description = 'Tombo Blowfish ECB (not recommended)'
    extensions = ['.chi', '.chs']

    def kdf(self, in_bytes):
        return chi_io.CHI_cipher(in_bytes)

    def read_from(self, file_object):
        # TODO catch exceptions and raise PurenTonboException()
        try:
            return chi_io.read_encrypted_file(file_object, self.key)
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


class Age(EncryptedFile):
    description = 'AGE - Actually Good Encryption (passphrase ONLY)'
    extensions = [
        '.age',
    ]

    def read_from(self, file_object):
        # TODO catch exceptions and raise PurenTonboException()
        # TODO AsciiArmoredInput()
        #encrypted_bytes = file_object.read()
        password = self.key
        if not isinstance(password, bytes):
            password = password.decode("utf-8")

        try:
            identities = [age.keys.password.PasswordKey(password)]
            with age.file.Decryptor(identities, file_object) as decryptor:
                plaintext = decryptor.read()
        except age.exceptions.NoIdentity as info:
            # probbaly NoIdentity("No matching key")
            raise BadPassword(info)  # FIXME BadPassword(BadPassword("for 'file-like-object'",),)
        except Exception as info:
            #raise  # DEBUG
            # TODO chain exception...
            #raise PurenTonboException(info.message)
            raise PurenTonboException(info)

        return plaintext

    def write_to(self, file_object, byte_data):
        # TODO catch exceptions and raise PurenTonboException()
        # TODO AsciiArmoredInput()
        password = self.key
        if not isinstance(password, bytes):
            password = password.decode("utf-8")

        try:
            identities = [age.keys.password.PasswordKey(password)]
            with age.file.Encryptor(identities, file_object) as encryptor:
                encryptor.write(byte_data)
        except Exception as info:
            #raise  # DEBUG
            # TODO chain exception...
            #raise PurenTonboException(info.message)
            raise PurenTonboException(info)

class AgeExe(EncryptedFile):  # TODO refactor into a shared spawn exe class
    """
    """

    description = Age.description + ' (EXE)'
    extensions = Age.extensions
    implementation = 'exe'
    _exe_name = os.environ.get('AGE_EXE', 'age')  # https://github.com/wj/age.git (https://github.com/clach04/age/tree/pr520_osenv_password) - that supports environment variable for passphrase
    _envvar_name = 'AGE_PASSPHRASE'  # TODO allow config...
    _exe_present = False
    _exe_version_str = None
    _exe_version = None

    #@classmethod()
    def exe_version_check(self):
        # combination exe present and version check
        cmd = [self._exe_name, '--version']
        if is_win:
            expand_shell = True  # avoid pop-up black CMD window - TODO review safety
        else:
            expand_shell = False

        try:
            p_exe = subprocess.Popen(cmd, shell=expand_shell, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            # timeout not suported by older python versions, pre 3.3?
            stdout_value, stderr_value = p_exe.communicate()

            """
            print('stdout: %r' % stdout_value)
            print('stderr: %r' % stderr_value)
            print('returncode: %r' % p_exe.returncode)
            """
            if p_exe.returncode == 0:
                self._exe_present = True
                self._exe_version_str = stdout_value.strip()
                #self._exe_version = self._exe_version_str.split(b' ', 2)[1].decode('utf-8')  # will fail on "(develop)" and other non integer-period/dot strings
        except FileNotFoundError:
            # some (but not all, Windows does not require this) platforms raise exception on missing binary
            pass

    def read_from(self, file_object):
        password = self.key  # TODO enforce byte check?
        if isinstance(password, bytes):
            # environment variables (in Microsoft Windows) have to be strings in py3
            password = password.decode("utf-8")

        os.environ[self._envvar_name] = password
        cmd = [self._exe_name, '--decrypt']

        # expand-shell true for windows to avoid pop-up window, no user input used so shell escape/esculation not expected
        # TODO look at alernative, Windows only startupinfo param STARTUPINFO class, wShowWindow = SW_HIDE
        byte_data = file_object.read()
        # FIXME TODO - ensure passphrae prompt does not occur....
        p_exe = subprocess.Popen(cmd, shell=expand_shell, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        # timeout not suported by older python versions, pre 3.3
        #stdout_value, stderr_value = p_exe.communicate()
        stdout_value, stderr_value = p_exe.communicate(input=byte_data)
        if p_exe.returncode != 0:
            """
            if stderr_value== b'TODO EXE SPECIFIC CHECK GOES HERE\n':
                raise BadPassword('with %r' % file_object)
            """
            if stderr_value.startswith(b'age: error: incorrect passphrase'):
                raise BadPassword('with %r' % file_object)
            raise PurenTonboException('failed to spawn, %r' % stderr_value)
        return stdout_value

    def write_to(self, file_object, byte_data):
        password = self.key  # TODO enforce byte check?
        if isinstance(password, bytes):
            # environment variables (in Microsoft Windows) have to be strings in py3
            password = password.decode("utf-8")

        os.environ[self._envvar_name] = password
        cmd = [self._exe_name, '--encrypt', '--passphrase']
        # FIXME TODO - ensure passphrae prompt does not occur....
        p_exe = subprocess.Popen(cmd, shell=expand_shell, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        # timeout not suported by older python versions, pre 3.3
        stdout_value, stderr_value = p_exe.communicate(input=byte_data)
        if p_exe.returncode != 0:
            raise PurenTonboException('failed to spawn, %r' % stderr_value)  # TODO test and review
        file_object.write(stdout_value)  # only write to fileobject on successful encryption
if is_py3:
    AgeExe.exe_version_check(AgeExe)  # TODO review this and classmethod
# ELSE todo py2.7 - TypeError: unbound method exe_version_check() must be called with AgeExe instance as first argument (got classobj instance instead)

# TODO AE-2 (no CRC), otherwise the same as AE-1 - see https://github.com/clach04/puren_tonbo/wiki/zip-format
class ZipEncryptedFileBase(EncryptedFile):
    _filename = 'encrypted.md'  # filename inside of (encrypted) zip file
    _compression = ZIP_DEFLATED  # which compression to apply `_filename` in the zip; DEFLATED == regular zip compression
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
    extensions = ZipEncryptedFileBase.extensions + [
        # TODO '.zip', see ZipAES() implementation
        #'.zip',  # any Zip file - NOTE if included, some tools may then attempt to treat regular zip files as potentially readable encrypted files and then fail; puren_tonbo.PurenTonboException: "There is no item named 'encrypted.md' in the archive"
    ]

    def read_from(self, file_object):
        # TODO catch specific exceptions and raise better mapped exception
        try:
            zf = mzipaes.MiniZipAE1Reader(file_object, self.key)
            return zf.get()  # first file in zip, ignores self._filename  # TODO revisit this
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
    _compression = ZIP_STORED  # no zip compression
    extensions = [
        '.aes256stored.zip',  # uncompressed Zip file with AES-256 - Standard WinZip/7z (not the old ZipCrypto!)
    ]


class ZipAES(ZipEncryptedFileBase):
    """Read/write ZIP AES(256) encrypted files (read-only old ZipCrypto)
    Compatible with files in WinZIP and 7z.
    Example 7z demo (Windows or Linux, assuming 7z is in the path):
        echo encrypted > encrypted.md
        7z a -ptest test_file.aes.zip encrypted.md
    """

    description = 'AES-256 ZIP AE-1 DEFLATED (regular compression), and read-only ZipCrypto'
    extensions = ZipEncryptedFileBase.extensions + [
        '.old.zip',  # Zip file with old old ZipCrypto - reading/decrypting (writing not supported/implemented)
        '.zip',  # any Zip file - NOTE if included, some tools may then attempt to treat regular zip files as potentially readable encrypted files and then fail; puren_tonbo.PurenTonboException: "There is no item named 'encrypted.md' in the archive"
    ]

    def read_from(self, file_object):
        # TODO catch exceptions and raise PurenTonboException()
        try:
            with pyzipper.AESZipFile(file_object) as zf:
                zf.setpassword(self.key)
                return zf.read(self._filename)
        except RuntimeError as info:
            # so far only seen for; RuntimeError("Bad password for file 'encrypted.md'")
            raise BadPassword(info)
        except KeyError as info:
            # Probably; KeyError: "There is no item named 'encrypted.md' in the archive"
            raise UnsupportedFile(info)
            # TODO chain exception...
        except Exception as info:
            # TODO chain exception...
            #raise
            # TODO decide how to handle regular zip files that do NOT contain encrypted notes; KeyError: "There is no item named 'encrypted.md' in the archive"
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
all_file_type_handlers = {}  # all but RawFile
file_type_handlers = {}

for enc_class_name in dir():  #(RawFile, Rot13):
    enc_class = globals()[enc_class_name]
    if not inspect.isclass(enc_class):
        continue
    if issubclass(enc_class, RawFile):
        continue
    if not issubclass(enc_class, BaseFile):
        continue
    for file_extension in enc_class.extensions:
        all_file_type_handlers[file_extension] = enc_class

# Dumb introspect code for RawFile and SubstitutionCipher (rot13 and rot47)
for enc_class_name in dir():  #(RawFile, Rot13):
    enc_class = globals()[enc_class_name]
    if not inspect.isclass(enc_class):
        continue
    if not issubclass(enc_class, RawFile) and not issubclass(enc_class, SubstitutionCipher) and not issubclass(enc_class, CompressedFile):
        continue
    for file_extension in enc_class.extensions:
        file_type_handlers[file_extension] = enc_class


if age:
    for enc_class in (Age, ):
        for file_extension in enc_class.extensions:
            file_type_handlers[file_extension] = enc_class
elif AgeExe._exe_present:
    for enc_class in (AgeExe, ):
        for file_extension in enc_class.extensions:
            file_type_handlers[file_extension] = enc_class

if jenc:  # FIXME, handle this via introspection, see code above for RawFile

    # https://github.com/clach04/jenc-py/issues/7
    if 'V002' not in jenc.jenc_version_details:
        jenc.jenc_version_details['V002'] = {
            'keyFactory': jenc.JENC_PBKDF2WithHmacSHA512,
            'keyIterationCount': 210000,  # taken 2024-11-12 from https://cheatsheetseries.owasp.org/cheatsheets/Password_Storage_Cheat_Sheet.html#pbkdf2
            'keyLength': 256,
            'keyAlgorithm': 'AES',
            'keySaltLength': 64,  # in bytes
            'cipher': jenc.JENC_AES_GCM_NoPadding,
            'nonceLenth': 32,  # nonceLenth (sic.) == Nonce Length, i.e. IV length  # in bytes
        }

    for enc_class in (JencV002, JencV001, JencU001, Jenc):  # order significant for filename extension lookup
        for file_extension in enc_class.extensions:
            file_type_handlers[file_extension] = enc_class

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

if mzipaes:
    for enc_class in (PurePyZipAES, ZipNoCompressionPurePyZipAES):
        for file_extension in enc_class.extensions:
            file_type_handlers[file_extension] = enc_class
if OpenSslEncDecCompat:
    for enc_class in (OpenSslEnc10k, ):
        for file_extension in enc_class.extensions:
            file_type_handlers[file_extension] = enc_class
if pyzipper:  # potentially overwrite PurePyZipAES and ZipNoCompressionPurePyZipAES as default zip support
    for enc_class in (ZipAES, ZipNoCompressionAES, ZipLzmaAES, ZipBzip2AES):
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
    # check for extensions with multiple periods/dots/fullstops
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
        # TODO loop through extensions in class
        _dummy, file_extn = os.path.splitext(filename)  # this is very agressive, splits on most-right-hand side (maybe want cipher name lookup ASWELL as filename extension)
    log.debug('clach04 DEBUG file_extn: %r', file_extn)
    log.debug('clach04 DEBUG file_type_handlers: %r', file_type_handlers)
    handler_class = file_type_handlers.get(file_extn) or default_handler
    if handler_class is None:
        raise UnsupportedFile('no support for %r' % file_extn)
    log.debug('clach04 DEBUG handler_class: %r', handler_class)
    return handler_class

encrypted_file_extensions = []
supported_handlers = {}  # supported handlers, mapped to first (default) filename extension
for file_extension in file_type_handlers.keys():
    supported_handlers[file_type_handlers[file_extension]] = file_type_handlers[file_extension].extensions[0]
    if issubclass(file_type_handlers[file_extension], EncryptedFile):
        encrypted_file_extensions.append(file_extension)
if mzipaes:
    for enc_class in (PurePyZipAES, ZipNoCompressionPurePyZipAES):
        if enc_class not in supported_handlers:
            supported_handlers[enc_class] = enc_class.extensions[0]


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
        def get_pass(prompt=None, filename=None, reset=False, for_decrypt=False, brave_mode=False):
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
                self.user_password = ui.getpassfunc(prompt, for_decrypt=for_decrypt, brave_mode=brave_mode)
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
    if not keyring or os.environ.get('PT_USE_KEYRING') is None:
        return None
    app, username = 'puren_tonbo', 'dumb'  # TODO review
    password = keyring.get_password(app, username)
    return password


any_filename_filter = lambda x: True  # allows any filename, i.e. no filtering


def supported_filetypes_info(encrypted_only=False, unencrypted_only=False, list_all=False):
    if list_all:
        handlers_to_check = all_file_type_handlers
        encrypted_only = False
        unencrypted_only = False
    else:
        handlers_to_check = file_type_handlers

    for file_extension in handlers_to_check:
        handler_class = handlers_to_check[file_extension]
        if encrypted_only and not issubclass(handler_class, EncryptedFile):
            continue
        if unencrypted_only and issubclass(handler_class, EncryptedFile):
            continue
        yield (file_extension, handler_class.__name__, handler_class.description)

def encrypted_filename_filter(in_filename):
    name = in_filename.lower()
    for file_extension in encrypted_file_extensions:
        if name.endswith(file_extension):
            return True
    return False

def supported_filename_filter(in_filename):
    name = in_filename.lower()
    #print('DEBUG %r %r' % (in_filename, list(file_type_handlers.keys())))
    for file_extension in file_type_handlers:
        if name.endswith(file_extension):
            # TODO could look at mapping and check that too, e.g. only Raw files
            return True
    return False

encrypted_extensions = list(supported_filetypes_info(encrypted_only=True))  # generator gets exhusted and encrypted check only works the first time!. TODO for (future) dynamic plugins with discovery to work, can't use a static list here
unencrypted_extensions = list(supported_filetypes_info(unencrypted_only=True))  # generator gets exhusted and encrypted check only works the first time!. TODO for (future) dynamic plugins with discovery to work, can't use a static list here

def plaintext_filename_filter(in_filename):
    name = in_filename.lower()
    #print('DEBUG %r %r' % (in_filename, list(file_type_handlers.keys())))
    #for file_extension in ('.txt', '.md', ):  # FIXME hard coded for known plain text extensions that Rawfile is configured with. See supported_filetypes_info() for less fragile approach
    for file_extension in unencrypted_extensions:
        if name.endswith(file_extension):
            # TODO could look at mapping and check that too, e.g. only Raw files
            return True
    return False

def encrypted_filename_filter(filename):  # TODO if ever support zip without encryption check inside and see if a password is needed
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
    files_with_matches?? - only return filename, not line matches, stops after first line hit. Similar to grep -l, --files-with-matches
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
        """load/read/decrypt notes file, also see note_contents_save()

        @filename is relative to `self.note_root` and includes directory name if not in the root.
        @filename (extension) dictates encryption mode/format (if any)
        @get_pass is either plaintext (bytes) password or a callback function that returns a password, get_pass() should return None for 'cancel'. See caching_console_password_prompt() for an example.
            get_pass(filename=filename, reset=reset_password)
        dos_newlines=True means use Windows/DOS newlines, emulates win32 behavior of Tombo and is the default
        @return_bytes returns bytes rather than (Unicode) strings
        """
        raise NotImplementedError('Implement in sub-class')

    def note_contents_save(self, note_text, sub_dir=None, filename=None, original_full_filename=None, get_pass=None, dos_newlines=True, backup=True):
        """Save/write/encrypt the contents, also see note_contents()

        Save contents of the string @note_text, to @filename if specified else derive filename from first line in note.
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

def is_bytes(b):
    return isinstance(b, bytes)


def is_text(s):
    return not is_bytes(s)

# Local file system functions
def to_bytes(data_in_string, note_encoding='utf-8'):
    """Where note_encoding can also be a list, e.g. ['utf8', 'cp1252']
    """
    if isinstance(data_in_string, (bytes, bytearray)):
        return data_in_string  # assume bytes already
    if isinstance(note_encoding, basestring):
        return data_in_string.encode(note_encoding)
    for encoding in note_encoding:
        try:
            result = data_in_string.encode(encoding)
            return result
        except UnicodeEncodeError:
            pass  # try next
    raise NotImplementedError('ran out of valid encodings to try, %r' % (data_in_string[:20],))

def to_string(data_in_bytes, note_encoding='utf-8'):  # TODO add option to support best effort, use replacement characters (ideally XML/html ref ot hex ala git - to avoid data loss)?
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
    raise UnsupportedFile('ran out of valid encodings to try, %r' % (data_in_bytes[:20],))  # likely user error (incorrect encodings) or simply a bad /unsupported file

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

# filename derivation/generation options/techniques
FILENAME_TIMESTAMP = 'TIMESTAMP'  # could have lots of options, this one will be YYYY-MM-DD_hhmmss ## TODO handle case whdre generate more than one file in less than a sec?
FILENAME_FIRSTLINE = 'FIRSTLINE'  # Tombo like, needs to be file system safe but retains spaces
FILENAME_FIRSTLINE_CLEAN = 'FIRSTLINE_CLEAN'  # TODO firstline but clean, remove dupe hypens, underscores, spaces, etc.
FILENAME_FIRSTLINE_SNAKE_CASE = 'FIRSTLINE_SNAKE_CASE'
FILENAME_FIRSTLINE_KEBAB_CASE = 'FIRSTLINE_KEBAB_CASE'
FILENAME_UUID4 = 'UUID4'

def note_contents_load_filename(filename, get_pass=None, dos_newlines=True, return_bytes=False, handler_class=None, note_encoding='utf-8'):
    """Uses local file system IO api
        @handler dictates encryption mode/format (if any)
        @filename if handler is ommited, file extension derives handler - i.e. encryption mode/format (if any)
        @get_pass is either plaintext (bytes) password or a callback function that returns a password, get_pass() should return None for 'cancel'.
            See caching_console_password_prompt() for an example. API expected:
                get_pass(filename=filename, reset=reset_password)
        dos_newlines=True means use Windows/DOS newlines, emulates win32 behavior of Tombo and is the default
        @return_bytes returns bytes rather than (Unicode) strings
        @note_encoding can also be a list, e.g. ['utf8', 'cp1252']
    """
    try:
        #log.debug('filename: %r', filename)
        filename = unicode_path(filename)

        handler_class = handler_class or filename2handler(filename)
        reset_password = False
        while True:
            #import pdb ; pdb.set_trace()
            if not handler_class.needs_key:
                log.debug('key not required (maybe it is plain text)')
                note_password = ''  # fake it. Alternatively override init for RawFile, etc. to remove check
            else:
                #import pdb ; pdb.set_trace()
                if callable(get_pass):
                    note_password = get_pass(filename=filename, reset=reset_password, for_decrypt=True)
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
            log.debug('DEBUG filename %r', filename)

            in_file = None
            try:
                in_file = open(filename, 'rb')  # TODO open once and seek back on failure
                plain_str = handler.read_from(in_file)
                if dos_newlines:
                    # FIXME TODO only do newline processing after decode
                    # NOTE this will NOT work for utf-16
                    plain_str = plain_str.replace(b'\r\n', b'\n')  # TODO consider remove all \r first as a cleaning step?

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

#          note_contents_save_filename(note_text, filename=None, original_filename=None, folder=None, handler=None, dos_newlines=True, backup=True, use_tempfile=True, note_encoding='utf-8', filename_generator=FILENAME_FIRSTLINE):
#             note_contents_save(self, note_text, filename=None, original_filename=None, folder=None, get_pass=None, dos_newlines=True, backup=True, filename_generator=FILENAME_FIRSTLINE, handler_class=None):
# TODO https://github.com/clach04/puren_tonbo/issues/173 allow warning to be disabled on duplicate derived filename
def note_contents_save_native_filename(note_text, filename=None, original_filename=None, folder=None, handler=None, dos_newlines=True, backup=True, use_tempfile=True, note_encoding='utf-8', filename_generator=FILENAME_FIRSTLINE):
    """Uses native/local file system IO api
    @handler is the encryption file handler to use, that is already initialized with a password
    @note_encoding if None, assume note_text is bytes, if a string use as the encoding, can also be a list, e.g. ['utf8', 'cp1252'] in which case use the first one
    folder - if specified (new) filename and original_filename are relative. if missing filename and original_filename are absolute
    """
    #import pdb; pdb.set_trace()
    #log.setLevel(logging.DEBUG)
    log.debug('original file %r', original_filename)
    log.debug('new file %r', filename)
    # Start - restrictions/checks that should be removed
    """
    if original_filename is not None:
        # then if folder specified, original_filename MUST be absolute path
        # then if folder missing , original_filename MUST be relative path
        raise NotImplementedError('original_filename is not None')
        #original_filename = unicode_path(original_filename)
    """
    # End - restrictions/checks that should be removed

    if handler is None:
        if filename is None:
            raise NotImplementedError('handler is required')  # Idea filename required, then use that to detemine handler
        else:
            raise NotImplementedError('handler is required, no way to pass in password (yet)')
            handler_class = None
            handler_class = handler_class or filename2handler(filename)
            #handler = handler_class(key=note_password)
            handler = handler_class()
    filename_generator_func = None
    if filename is None:
        if original_filename and filename_generator in (None, FILENAME_TIMESTAMP, FILENAME_UUID4):
            # do not rename... or they could have passed in the "new name"
            filename = original_filename
            log.debug('filename is original_filename: %r', filename)
        else:
            if folder:
                # relative path names for files as given as input to this function
                if original_filename:
                    original_filename = os.path.join(folder, original_filename)  # TODO abspath for safety?
                    folder = os.path.dirname(original_filename)
            else:
                # folder not set, so absolute paths given as input to this function
                folder = os.path.dirname(original_filename)

            validate_filename_generator(filename_generator)
            filename_generator_func = filename_generators[filename_generator]
            log.debug('filename_generator_func %r', filename_generator_func)
            file_extension = handler.extensions[0]  # pick the first one - TODO refactor into a function/method - call handler.default_extension()
            filename_without_path_and_extension = filename_generator_func(note_text)

            filename = os.path.join(folder, filename_without_path_and_extension + file_extension)
            if filename != original_filename:  # TODO folder check....
                # now check if generated filename already exists, if so need to make unique
                unique_counter = 1
                while os.path.exists(filename):
                    log.warning('generated filename %r already exists, generating alternative', filename)  # TODO consider making optional and also info instead of warning? Test suite triggers this which is simply not useful information as the test does it's own validation https://github.com/clach04/puren_tonbo/issues/173
                    unique_part = '(%d)' % unique_counter  # match Tombo duplicate names avoidance
                    filename = os.path.join(folder, filename_without_path_and_extension + unique_part + file_extension)
                    unique_counter += 1

            # TODO handle format conversion (e.g. original text, new encrypted)
            log.debug('generated filename: %r', filename)
    else:
        filename = unicode_path(filename)


    """
    # sanity checks
    if filename is not None and folder is not None:
        raise NotImplementedError('incompatible/inconsistent filename: %r folder: %r ' % (filename, folder))
    if original_filename is not None and folder is not None:
        raise NotImplementedError('incompatible/inconsistent original_filename: %r folder: %r ' % (original_filename, folder))
    if filename is None and original_filename:
        raise NotImplementedError('renaming files base on content - incompatible/inconsistent original_filename: %r filename: %r ' % (original_filename, filename))
    validate_filename_generator(filename_generator)
    filename_generator_func = filename_generators[filename_generator]


    if original_filename:
        # TODO just use the old name? or handle rename. rename depends on filename generator
        if filename_generator in (FILENAME_TIMESTAMP, FILENAME_UUID4):
            # do not rename... or they could have passed in the "new name"
            filename = original_filename

    # START FROM pttkview save_file()
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
        log.error('not implemented deleting old filename')
    # END FROM pttkview save_file()

    generated_filename = False
    if filename is None:
        if handler_class is None:
            raise NotImplementedError('Missing handler_class for missing filename, could default to Raw - make decision')
        file_extension = handler_class.extensions[0]  # pick the first one
        if folder:
            native_folder = self.native_full_path(folder)
        else:
            native_folder = self.note_root
        filename_without_path_and_extension = filename_generator_func(note_text)
        native_filename = os.path.join(native_folder, filename_without_path_and_extension + file_extension)
        # now check if generated filename already exists, if so need to make unique
        unique_counter = 1
        while os.path.exists(native_filename):
            #log.warning('generated filename %r already exists', native_filename)
            unique_part = '(%d)' % unique_counter  # match Tombo duplicate names avoidance
            native_filename = os.path.join(native_folder, filename_without_path_and_extension + unique_part + file_extension)
            unique_counter += 1
        filename = self.abspath2relative(native_filename)
        generated_filename = True

    if original_filename and filename != original_filename:
        raise NotImplementedError('renaming files not yet supported; original_filename !=  filename  %r != %r ' % (original_filename, filename))

    handler_class = handler_class or filename2handler(filename)
    #handler = handler_class(key=note_password)
    handler = handler_class()
    """

    if note_encoding is None:
        plain_str_bytes = note_text  # Assume bytes passed in (if so.. why not check here to enforce)
    else:
        if dos_newlines:
            note_text = note_text.replace('\n', '\r\n')  # TODO remove all \r first as a cleaning step?
        # see to_string() for reverse
        plain_str_bytes = to_bytes(note_text, note_encoding)

    ### same below as class method()
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
        log.debug('about to open %r', filename)
        out_file = open(filename, 'wb')  # Untested

    log.debug('writting bytes')
    #log.setLevel(logging.NOTSET)
    handler.write_to(out_file, plain_str_bytes)
    #log.setLevel(logging.DEBUG)
    out_file.close()

    if backup:
        if os.path.exists(filename):
            log.debug('about to perform backup %r', filename)
            file_replace(filename, filename + '.bak')  # backup existing
        elif original_filename and os.path.exists(original_filename):
            log.debug('about to perform RENAME backup %r', original_filename)
            file_replace(original_filename, original_filename + '.bak')  # backup existing
        # TODO do the same for original

    if use_tempfile:
        log.debug('about to replace %r with temporary file %r', filename, tmp_out_filename)
        file_replace(tmp_out_filename, filename)

    # handle rename/delete
    if filename_generator_func:
        # filename generator was used, have have an old file to cleanup
        if original_filename and filename != original_filename and os.path.exists(original_filename):
            log.debug('about to remove original file %r', original_filename)
            os.remove(original_filename)

    return filename

def validate_filename_generator(filename_generator):
    if filename_generator not in (
        FILENAME_TIMESTAMP,
        FILENAME_FIRSTLINE,  # TODO Tombo like, for missing first line returns "memo", "memo(1)", "memo(2)", ....
        FILENAME_FIRSTLINE_CLEAN,
        FILENAME_FIRSTLINE_SNAKE_CASE,
        FILENAME_FIRSTLINE_KEBAB_CASE,
        FILENAME_UUID4,  # TODO
    ):
        raise NotImplementedError('filename generator %r' % filename_generator)

def filename_generator_timestamp(note_text):
    """FILENAME_TIMESTAMP
    """
    filename_without_path_and_extension = datetime.datetime.now().strftime('%Y-%m-%d_%H%M%S')  # FILENAME_TIMESTAMP
    return filename_without_path_and_extension


def safe_filename(filename, replacement_char='_', allow_space=False, max_filename_length=100):
    """safe filename for almost any platform, NOTE filename NOT pathname. defaults to snake_case
    does NOT handle paths, see blocked_filenames comments section below for details/example.
    aka slugify()
    # TODO max filename truncation?
    """

    if allow_space:  # UNTESTED
        additional_allowed_characters = '-_ '
    else:
        additional_allowed_characters = '-_'
    result = []
    last_char = ''
    for x in filename:
        if not(x.isalnum() or x in additional_allowed_characters):
            x = replacement_char
        if x not in ['-', replacement_char] or last_char not in ['-', replacement_char]:
            # avoid duplicate '_'
            result.append(x)
        last_char = x

    new_filename = ''.join(result)
    r"""now prefix _ infront of special names, mostly impacts Windows.
    For example handle this sort of mess:

        C:\tmp>echo hello > con.txt
        hello

        C:\tmp>echo hello > \tmp\con.txt
        hello

        C:\tmp>echo hello > C:\tmp\con.txt
        hello

        C:\tmp>echo hello > C:\tmp\_con.txt
        C:\tmp>echo hello > C:\tmp\con_.txt

    Doc refs:
    * https://en.wikipedia.org/wiki/Filename#In_Windows
    * https://learn.microsoft.com/en-us/windows/win32/fileio/naming-a-file?redirectedfrom=MSDN
        blocked_filenames = 'CON, PRN, AUX, NUL, COM0, COM1, COM2, COM3, COM4, COM5, COM6, COM7, COM8, COM9, LPT0, LPT1, LPT2, LPT3, LPT4, LPT5, LPT6, LPT7, LPT8, LPT9'
        and NULL for good measure

    """
    blocked_filenames = [
        'CON',
        'PRN',
        'AUX',
        'NUL',
        'NULL',  # redundant but here for saftey incase approach changes
        'COM0',
        'COM1',
        'COM2',
        'COM3',
        'COM4',
        'COM5',
        'COM6',
        'COM7',
        'COM8',
        'COM9',
        'LPT0',
        'LPT1',
        'LPT2',
        'LPT3',
        'LPT4',
        'LPT5',
        'LPT6',
        'LPT7',
        'LPT8',
        'LPT9'
        ]
    new_filename_upper = new_filename.upper()
    for device_name in blocked_filenames:
        """
        if new_filename_upper.startswith(device_name):
            new_filename = '_' + new_filename
            break
        """
        #if new_filename_upper == device_name or new_filename_upper.startswith(device_name + '.'):
        # postfix an underscore/bar '_'  # TODO use double do help id possible problem filenames?
        if new_filename_upper == device_name:
            new_filename = new_filename + '_'
            break
        elif new_filename_upper.startswith(device_name + '.'):
            new_filename = new_filename[:len(device_name)] + '_' +new_filename[len(device_name):]
            break


    if new_filename == '':
        new_filename = 'memo'

    if max_filename_length:
        if len(new_filename) > max_filename_length:
            new_filename = new_filename[:max_filename_length-2] + '__'  # append multiple '__' to indicate may want review

    return new_filename

def filename_generator_firstline(note_text):
    """FILENAME_FIRSTLINE
    """
    generated_name = note_text[:note_text.find('\n')].strip()
    return safe_filename(generated_name, allow_space=True)

def filename_generator_firstline_clean_kebab_case(note_text):
    """FILENAME_FIRSTLINE_KEBAB_CASE
    """
    generated_name = note_text[:note_text.find('\n')].strip()
    return safe_filename(generated_name, replacement_char='-')

def filename_generator_firstline_clean(note_text):
    """snake_case, example: FILENAME_FIRSTLINE_CLEAN
    """
    generated_name = note_text[:note_text.find('\n')].strip()
    return safe_filename(generated_name)

def filename_generator_uuid4(note_text):
    """FILENAME_FIRSTLINE_UUID4
    """
    return str(uuid.uuid4())

filename_generators = {
    FILENAME_FIRSTLINE: filename_generator_firstline,
    FILENAME_FIRSTLINE_CLEAN: filename_generator_firstline_clean,
    FILENAME_FIRSTLINE_SNAKE_CASE: filename_generator_firstline_clean,
    FILENAME_FIRSTLINE_KEBAB_CASE: filename_generator_firstline_clean_kebab_case,
    FILENAME_TIMESTAMP: filename_generator_timestamp,
    FILENAME_UUID4: filename_generator_uuid4,
}

#      note_contents_save(self, note_text, filename=None, original_filename=None, folder=None, get_pass=None, dos_newlines=True, backup=True, filename_generator=FILENAME_FIRSTLINE, handler_class=None):
def note_contents_save_filename(note_text, filename=None, original_filename=None, folder=None, handler=None, dos_newlines=True, backup=True, use_tempfile=True, note_encoding='utf-8', filename_generator=FILENAME_FIRSTLINE):
    """Save/write/encrypt the notes contents, also see note_contents()

    @note_text string contents to Save/write/encrypt, using self.to_string() to encode to disk (if bytes use as-is)
    @filename if specified is the filename to save to should be relative to `self.note_root` and include directory name
        - if missing/None/False, use @folder to determine (new) location and original_filename to determine file type with @filename_generator to determine new filename
    if sub_dir is not specified `self.note_root` is assumed
    @original_full_filename should be relative to `self.note_root` and include directory name - will also help determine type and potentially remove once saved if filename has changed
    force  encryption or is filename the only technique?
    Failures during call should leave original filename present and untouched


    See note_contents_save_native_filename() docs
    """
    validate_filename_generator(filename_generator)

    return note_contents_save_native_filename(note_text, filename=filename, original_filename=original_filename, folder=folder, handler=handler, dos_newlines=dos_newlines, backup=backup, use_tempfile=use_tempfile, note_encoding=note_encoding, filename_generator=filename_generator)


# Local file system navigation functions
def walker(directory_name, process_file_function=None, process_dir_function=None, extra_params_dict=None):
    """extra_params_dict optional dict to be passed into process_file_function() and process_dir_function()

    def process_file_function(full_path, extra_params_dict=None)
        extra_params_dict = extra_params_dict or {}

    Also see recurse_notes()
    """
    extra_params_dict or {}
    ignore_folders = extra_params_dict.get('ignore_folders', [])
    # TODO scandir instead... would be faster - but for py2.7 requires external lib
    for root, subdirs, files in os.walk(directory_name):
        # skip .git directories hack/side effect - also see recurse_notes()
        for ignore_dir in ignore_folders:
            try:
                subdirs.remove(ignore_dir)
            except ValueError:
                pass
        # TODO even more hacky, exclude list/set parameter:
        #dirs[:] = [d for d in dirs if d not in exclude]
        # for d in exclude: subdirs.remove(d)

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
def find_recent_files(test_path, number_of_files=20, order=ORDER_ASCENDING, ignore_folders=None):
    extra_params_dict = {
        #'directory_path': directory_path,  # not used
        #'directory_path_len': directory_path_len,
        'ignore_folders': [],
        'max_recent_files': number_of_files,
        'recent_files': [],
    }
    if ignore_folders:
        extra_params_dict['ignore_folders'] += ignore_folders

    walker(test_path, process_file_function=recent_files_filter, extra_params_dict=extra_params_dict)
    recent_files = extra_params_dict['recent_files']
    if ORDER_DESCENDING == order:
        recent_files.reverse()
    for mtime, filename in recent_files:
        yield filename

def unsupported_files_filter(full_path, extra_params_dict=None):
    # TODO lower filename
    for extn in extra_params_dict['supported_extensions']:
        if full_path.endswith(extn):
            return
    extra_params_dict['unsupported_files'].append(full_path)

def find_unsupported_files(test_path, order=ORDER_ASCENDING, ignore_files=None, ignore_folders=None):
    extra_params_dict = {
        #'directory_path': directory_path,  # not used
        #'directory_path_len': directory_path_len,
        'ignore_folders': [],
        'unsupported_files': [],
        'supported_extensions': [],
    }
    if ignore_folders:
        extra_params_dict['ignore_folders'] += ignore_folders
    ignore_folders = ignore_folders or ['.git']
    if ignore_files:
        # TODO lowercase extensions
        extra_params_dict['supported_extensions'] += ignore_files

    for handler in supported_handlers:
        extra_params_dict['supported_extensions'] += handler.extensions
    walker(test_path, process_file_function=unsupported_files_filter, extra_params_dict=extra_params_dict)
    if ORDER_DESCENDING == order:
        extra_params_dict['unsupported_files'].reverse()
    for filename in extra_params_dict['unsupported_files']:
        yield filename

def recurse_notes(path_to_search, filename_filter, ignore_folders=None):
    """Walk (local file system) directory of notes, directory depth first (just like Tombo find does), returns generator
      * filename_filter - examples, see; supported_filename_filter, plaintext_filename_filter, plaintext_filename_filter
      * ignore_folders - a list/tuple of directory/folder names to ignore/skip.

    Also see walker()
    """
    ## Requires os.walk (python 2.3 and later).
    ## Pure Python versions for earlier versions available from:
    ##  http://osdir.com/ml/lang.jython.user/2006-04/msg00032.html
    ## but lacks "topdown" support, walk class later
    ignore_folders = ignore_folders or ['.git']
    #import pdb ; pdb.set_trace()
    #topdown = False
    topdown = True
    for dirpath, dirnames, filenames in os.walk(path_to_search, topdown=topdown):
        #print('walker', repr((dirnames, filenames)))

        # skip .git directories hack/side effect - also see recurse_notes()
        # hacking directory requires topdown=True... else need to filter files to ignore directory
        for ignore_dir in ignore_folders:
            try:
                dirnames.remove(ignore_dir)
            except ValueError:
                pass

        # TODO even more hacky, exclude list/set parameter:
        #dirs[:] = [d for d in dirnames if d not in exclude]
        # for d in exclude: dirnames.remove(d)

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
            if '.git' == name:
                continue
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

# NIH FTS Abstraction.. focused on plain text notes

class FullTextSearch:
    def __init__(self, index_location):
        """Potentially opens index
        """
        self.index_location = index_location  # unspecified type, could be; URL (auth handled by implementation), file, directory, ....
        raise NotImplementedError()

    def index_close(self):
        raise NotImplementedError()

    def index_delete(self):
        raise NotImplementedError()

    def create_index_start(self):
        raise NotImplementedError()

    def create_index_end(self):
        raise NotImplementedError()

    def add_to_index(self, filename, contents=None, contents_size=None, mtime=None, line_number=None):
        """Add to index self.index_location (from scratch, no update support API.... yet.)
        """
        if contents and not contents_size:
            contents_size = length(contents)
        raise NotImplementedError()

    # TODO date (size) query parameter restrictions (with ranges)
    # FIXME context_distance / snippet length parameter support needed - ideas; here as parameter, init parameter, attribute that can be changed at runtime - leaning towards the later
    def search(self, search_term, find_only_filename=False, files_with_matches=False, highlight_text_start=None, highlight_text_stop=None):
        """Search self.index_location for `search_term`
        """
        raise NotImplementedError()

class FullTextSearchSqlite:  # TODO either inherit from or document why not inherited from FullTextSearch - possibly mtime param difference?
    def __init__(self, index_location, index_lines=False):
        """index_location - SQLite database, probably a pathname could be memory
        SQLite FTS5 - https://www.sqlite.org/fts5.html - TODO FTS4/FTS3 fallback support?
        """
        self.index_location = index_location  # unspecified type, could be; URL (auth handled by implementation), file, directory, ....
        self.index_lines = index_lines  # if true, index lines in each file seperately
        con = sqlite3.connect(index_location)
        #if index_location == ':memory:':
        self.db = con
        cur = con.cursor()
        self.cursor = cur

        cur.execute('pragma compile_options;')
        available_pragmas = cur.fetchall()

        if ('ENABLE_FTS5',) not in available_pragmas:
            raise NotImplementedError('FTS5 missing %r' % (available_pragmas, ) )

    def index_close(self):
        self.db.close()

    def index_delete(self):
        cur = self.cursor
        try:
            cur.execute("""DROP TABLE note""")
        except:  # sqlite3.OperationalError: no such table: note
            pass

    def create_index_start(self):
        cur = self.cursor
        index_lines = self.index_lines
        # defaults to unicode61, TODO test with options, also ascii
        # TODO check out trigram
        ddl_sql = "CREATE VIRTUAL TABLE note USING fts5(filename, contents, size, tokenize='porter')"  # TODO mtime/date/timestamp unindexed (https://www.sqlite.org/fts5.html#the_unindexed_column_option)
        if index_lines:
            ddl_sql = "CREATE VIRTUAL TABLE note USING fts5(filename, contents, size, line_number, tokenize='porter')"  # TODO mtime/date/timestamp unindexed (https://www.sqlite.org/fts5.html#the_unindexed_column_option)

        cur.execute(ddl_sql)
        # Checkout https://www.sqlite.org/fts5.html#prefix_indexes

    def create_index_end(self):
        self.db.commit()

    def add_to_index(self, filename, contents=None, contents_size=None, line_number=None):  #, TODO mtime=None):
        """Add to index self.index_location (from scratch, no update support API.... yet.)
        """
        index_lines = self.index_lines
        if contents and not contents_size:
            contents_size = len(contents)
        cur = self.cursor
        if index_lines:
            cur.execute("""INSERT INTO note (filename, contents, size, line_number) VALUES (?, ?, ?, ?)""", (filename, contents, contents_size, line_number) )
        else:
            cur.execute("""INSERT INTO note (filename, contents, size) VALUES (?, ?, ?)""", (filename, contents, contents_size) )

    def search(self, search_term, find_only_filename=False, files_with_matches=False, highlight_text_start=None, highlight_text_stop=None):
        """Search self.index_location for `search_term`
        TODO control over context_distance

          * search_term  # search term to look for, string
          * find_only_filename=False - Not Implemented!  # do NOT search file content, only search for filenames
          * files_with_matches=False - Not Implemented!  # only display filename, do not include file content matches, just filenames in results
          * highlight_text_start=None  # (ANSI escape) characters to prefix search start
          * highlight_text_stop=None  # (ANSI escape) characters to prefix search end/stop
        """
        index_lines = self.index_lines
        # FIXME here and grep find_only_filename=False == files_with_matches? duplicate?
        if find_only_filename:
            raise NotImplementedError('find_only_filename')
        if files_with_matches:
            raise NotImplementedError('files_with_matches')
        if highlight_text_start is None:
            highlight_text_start = '**'
        if highlight_text_stop is None:
            highlight_text_stop = '**'
        # TODO doc demos
        context_distance = 3  # fts_search aesop king - only shows aesop
        context_distance = 6  # fts_search aesop king - shows both
        context_distance = 10  # FIXME / TODO this needs to be a parameter

        cur = self.cursor
        '''
        cur.execute("""SELECT
                            snippet(note, 0, '<b>', '</b>', '...', ?) as title,
                            snippet(note, 1, '<b>', '</b>', '...', ?) as body
                        FROM note(?)
                        ORDER  BY rank""",
                        (context_distance, context_distance, search_term) )
        cur.execute("""SELECT
                            snippet(note, 0, '<b>', '</b>', '...', 10) as title,
                            snippet(note, 1, '<b>', '</b>', '...', 10) as body
                        FROM note(?)
                        ORDER  BY rank""",
                        (search_term, ) )

        # works
        cur.execute("""SELECT
                            snippet(note, 0, '<b>', '</b>', '...', ?) as title,
                            snippet(note, 1, '<b>', '</b>', '...', ?) as body
                        FROM note(?)
                        ORDER  BY rank""",
                        (context_distance, context_distance, search_term, ) )

        '''

        if index_lines:
            cur.execute("""SELECT
                            filename,
                            snippet(note, 0, ?, ?, '...', ?) as title,
                            CAST(line_number as TEXT) || ':' || snippet(note, 1, ?, ?, '...', ?) as body,
                            size
                        FROM note(?)
                        ORDER  BY rank""",
                        (highlight_text_start, highlight_text_stop, context_distance, highlight_text_start, highlight_text_stop, context_distance, search_term, ) )
        else:
            cur.execute("""SELECT
                            filename,
                            snippet(note, 0, ?, ?, '...', ?) as title,
                            snippet(note, 1, ?, ?, '...', ?) as body,
                            size
                        FROM note(?)
                        ORDER  BY rank""",
                        (highlight_text_start, highlight_text_stop, context_distance, highlight_text_start, highlight_text_stop, context_distance, search_term, ) )

        return cur.fetchall()  # [(filename, title, body, size), ...]

##############################


class FileSystemNotes(BaseNotes):
    """PyTombo notes on local file system, just like original Windows Tombo
    """

    def __init__(self, note_root, note_encoding=None, fts_class=FullTextSearchSqlite):  # FIXME default fts to None?
        note_root = self.unicode_path(note_root)  # either a file or a directory of files
        self.note_root = os.path.abspath(note_root)
        self.abs_ignore_path = os.path.join(self.note_root, '') ## add trailing slash.. unless this is a file
        #self.note_encoding = note_encoding or 'utf8'
        self.note_encoding = note_encoding or ('utf8', 'cp1252')
        self.fts_class = fts_class  # FIXME how do parameters get passed in?
        self.fts_instance = None

    def abspath2relative(self, input_path):
        """validate absolute native path, return relative path with with (leading) self.note_root removed.
        If ignore_path is not at the start of the input_path, raise error
        TODO how is the root dir handled? return / or '' empty string?"""
        abs_ignore_path = self.abs_ignore_path
        abs_input_path = os.path.abspath(input_path)  # normalize the path - normpath()
        if abs_input_path.startswith(abs_ignore_path):
            return abs_input_path[len(abs_ignore_path):]
        elif abs_input_path + '/' == abs_ignore_path:
            return ''
        raise PurenTonboException('path not in note tree')  # TODO compare with native_full_path() exception

    def native_full_path(self, filename):
        """validate and convert relative path to absolute native path
        """
        filename = self.unicode_path(filename)
        fullpath_filename = os.path.join(self.note_root, filename)
        fullpath_filename = os.path.abspath(fullpath_filename)
        if not fullpath_filename.startswith(self.note_root):
            raise PurenTonboIO('outside of note tree root')  # TODO compare with native_full_path() abspath2relative
        return fullpath_filename

    def to_bytes(self, data_in_string):
        return to_bytes(data_in_string, note_encoding=self.note_encoding)

    def to_string(self, data_in_bytes):
        return to_string(data_in_bytes, note_encoding=self.note_encoding)

    def unicode_path(self, filename):
        if isinstance(filename, bytes):
            # want unicode string so that all file interaction is unicode based
            filename = filename.decode('utf8')  # FIXME hard coded, pick up from config or locale/system encoding
        return filename

    def recent_notes(self, sub_dir=None, number_of_files=20, order=ORDER_ASCENDING, ignore_folders=None):
        """Recursive Tombo note lister for recently updated/modified files.
        Iterator of files in @sub_dir"""
        return find_recent_files(self.note_root, number_of_files=number_of_files, order=order, ignore_folders=ignore_folders)

    def recurse_notes(self, sub_dir=None, filename_filter=any_filename_filter):
        """Recursive Tombo note lister.
        Iterator of files in @sub_dir"""
        return recurse_notes(self.note_root, filename_filter)

    def directory_contents(self, sub_dir=None):
        """Simple non-recursive Tombo note lister.
        Returns tuple (list of directories, list of files) in @sub_dir"""
        if sub_dir:
            sub_dir = self.native_full_path(sub_dir)  # see if path is valid, get native path
        else:
            sub_dir = self.note_root
        return directory_contents(dirname=sub_dir)


    def fts_search(self, s, highlight_text_start=None, highlight_text_stop=None):  # FIXME API
        fts_instance = self.fts_instance
        return fts_instance.search(search_term=s, highlight_text_start=highlight_text_start, highlight_text_stop=highlight_text_stop)  # or yield...

    def fts_index(self, sub_dir=None, get_password_callback=None):
        """only files that do not need passwords are indexed
        If get_password_callback is set, all files are indexed, and password prompted for. FIXME curently no way to skip a file (either becauase want to for some reason or have to as password not available)
        """
        if sub_dir:
            raise NotImplementedError('sub_dir')
        search_path = self.note_root
        recurse_notes_func = self.recurse_notes

        """
        search_encrypted = False
        #search_encrypted = True  # TODO test
        if search_encrypted:
            if search_encrypted == 'only':
                is_note_filename_filter = encrypted_filename_filter
            else:
                is_note_filename_filter = supported_filename_filter
        """
        if get_password_callback:
            is_note_filename_filter = supported_filename_filter
        else:
            is_note_filename_filter = plaintext_filename_filter


        # FIXME store constucted
        if self.fts_instance:
            fts_instance = self.fts_instance
        else:
            fts_instance = self.fts_class(':memory:')
        self.fts_instance = fts_instance
        fts_instance.index_delete()
        fts_instance.create_index_start()
        index_lines = fts_instance.index_lines
        ignore_unsupported_filetypes = True
        for tmp_filename in recurse_notes_func(search_path, is_note_filename_filter):
                filename = self.abspath2relative(tmp_filename)
                log.debug('index %r', filename)
                log.info('index %s', filename)
                try:
                    contents = self.note_contents(filename, get_pass=get_password_callback, dos_newlines=True)
                    # TODO contents_size, mtime
                    #stored_filename = filename  # relative
                    stored_filename = tmp_filename  # absolute
                    if not index_lines:
                        fts_instance.add_to_index(stored_filename, contents=contents)
                    else:
                        for line_number, line in enumerate(contents.split('\n')):
                            line = line.strip()
                            if line:
                                fts_instance.add_to_index(stored_filename, contents=line, line_number=line_number)
                except UnsupportedFile as error_info:
                    # TODO - what!? options; ignore, raise, treat as RawFile type
                    log.warning('UnsupportedFile Ignored %r - reason %r', filename, error_info)
                    if ignore_unsupported_filetypes:
                        continue
                    else:
                        log.error('UnsupportedFile %r', filename)  # todo exception trace?
                        raise

        fts_instance.create_index_end()


    # TODO remove (or depreicate) search_term_is_a_regex and replace with search_type=(plain, regex, fts)
    # FIXME Consider adding dictionary parameter for search options rather than new keywords each time?
    #         (self, search_term, search_term_is_a_regex=True,  ignore_case=True,  search_encrypted=False, get_password_callback=None, progess_callback=None, find_only_filename=None, index_name=None, note_encoding=None):
    #               (search_term, search_term_is_a_regex=True , ignore_case=True,  search_encrypted=False, get_password_callback=None, progess_callback=None, find_only_filename=None, index_name=None, note_encoding=None):
    def search(self, search_term, search_term_is_a_regex=False, ignore_case=False, search_encrypted=False, find_only_filename=False, files_with_matches=False, get_password_callback=None, progess_callback=None, highlight_text_start=None, highlight_text_stop=None):
        """search note directory, grep/regex like actualy an iterator

        search_encrypted - special value "only" means will only search encrypted files (based on filename) either truthy check performed

          * search_term  # search term to look for, string
          * search_term_is_a_regex=False  # treat `search_term` as a regex or plain string
          * ignore_case=False  # case insensitive or not
          * search_encrypted=False  # whether to search encrypted files - special value "only" means will only search encrypted files (based on filename) either truthy check performed
          * get_password_callback=None  # function that will be called when/if a password is required
          * progess_callback=None  # function that will be called for progress updates/information

          * find_only_filename=False  # do NOT search file content, only search for filenames
          * files_with_matches=False  # only display filename, do not include file content matches, just filenames in results
          * highlight_text_start=None  # (ANSI escape) characters to prefix search start
          * highlight_text_stop=None  # (ANSI escape) characters to prefix search end/stop

        """
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
            if search_encrypted == 'only':
                is_note_filename_filter = encrypted_filename_filter
            else:
                is_note_filename_filter = supported_filename_filter
        else:
            # plain text only, right now this is hard coded
            is_note_filename_filter = plaintext_filename_filter
        if os.path.isfile(search_path):
            recurse_notes_func = fake_recurse_notes
        else:
            recurse_notes_func = self.recurse_notes
        ignore_unsupported_filetypes = True
        #ignore_unsupported_filetypes = False  # original behavior
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
                try:
                    note_text = self.note_contents(filename, get_pass=get_password_callback, dos_newlines=True)  # FIXME determine what to do about dos_newlines (rename?)
                except UnsupportedFile as error_info:
                    # TODO - what!? options; ignore, raise, treat as RawFile type
                    log.warning('UnsupportedFile Ignored %r - reason %r', filename, error_info)
                    if ignore_unsupported_filetypes:
                        pass
                        note_text = ''
                        continue
                    else:
                        log.error('UnsupportedFile %r', filename)  # todo exception trace?
                        raise
                except:
                    # we have no idea what happened :-(
                    if is_py3:
                        log.error('UnsupportedFile %r', filename, exc_info=1, stack_info=1)  # include traceback, and and Python 3 only full stack/trace
                    else:
                        log.error('UnsupportedFile %r', filename, exc_info=1)  # include traceback
                    raise
                search_res = grep_string(note_text, regex_object, highlight_text_start, highlight_text_stop, files_with_matches=files_with_matches)
                if search_res:
                    yield (filename, search_res)


    def note_contents(self, filename, get_pass=None, dos_newlines=True, return_bytes=False, handler_class=None):
        """load/read/decrypt notes file, also see note_contents_save()
        TODO take/merge doc comments from function note_contents_load_filename()

        @filename is relative to `self.note_root` and includes directory name if not in the root.
        @filename (extension) dictates encryption mode/format (if any)
        @get_pass is either plaintext (bytes) password or a callback function that returns a password, get_pass() should return None for 'cancel'.
            See caching_console_password_prompt() for an example. API expected:
                get_pass(filename=filename, reset=reset_password)
        dos_newlines=True means use Windows/DOS newlines, emulates win32 behavior of Tombo and is the default
        @return_bytes returns bytes rather than (Unicode) strings
        @handler_class override handler, if ommited filename derives handler
        """
        filename = self.unicode_path(filename)
        fullpath_filename = self.native_full_path(filename)
        plain_str = note_contents_load_filename(fullpath_filename, get_pass=get_pass, dos_newlines=dos_newlines, return_bytes=True, handler_class=handler_class)
        if return_bytes:
            return plain_str
        else:
            return self.to_string(plain_str)

    def note_contents_save(self, note_text, filename=None, original_filename=None, folder=None, get_pass=None, dos_newlines=True, backup=True, use_tempfile=True, filename_generator=FILENAME_FIRSTLINE, handler_class=None):
        """Save/write/encrypt the notes contents, also see note_contents() for load/read/decrypt
        FIXME make calls to note_contents_save_filename() function instead

        @note_text string contents to Save/write/encrypt, using self.to_string() to encode to disk (if bytes use as-is)
        @filename if specified is the filename to save to should be relative to `self.note_root` and include directory name
            - if missing/None/False, use @folder to determine (new) location and original_filename to determine file type with @filename_generator to determine new filename
        if sub_dir is not specified `self.note_root` is assumed
        @original_full_filename should be relative to `self.note_root` and include directory name - will also help determine type and potentially remove once saved if filename has changed
        force  encryption or is filename the only technique?
        @handler_class override handler, if ommited filename derives handler
        Failures during call should leave original filename present and untouched


        See note_contents_save_native_filename() docs
        TODO refactor, there is code duplication (and some differences) between method note_contents_save() and functions note_contents_save_filename() / note_contents_save_native_filename()
        """
        # sanity checks
        if filename is not None and folder is not None:
            raise NotImplementedError('incompatible/inconsistent filename: %r folder: %r ' % (filename, folder))
        if original_filename is not None and folder is not None:
            raise NotImplementedError('incompatible/inconsistent original_filename: %r folder: %r ' % (original_filename, folder))
        if filename is None and original_filename:
            raise NotImplementedError('renaming files base on content - incompatible/inconsistent original_filename: %r filename: %r ' % (original_filename, filename))
        if filename_generator:
            validate_filename_generator(filename_generator)
            filename_generator_func = filename_generators[filename_generator]


        if original_filename:
            # TODO just use the old name? or handle rename. rename depends on filename generator
            if filename_generator in (None, FILENAME_TIMESTAMP, FILENAME_UUID4):
                # do not rename... or they could have passed in the "new name"
                filename = original_filename

        generated_filename = False
        if filename is None:
            if handler_class is None:
                raise NotImplementedError('Missing handler_class for missing filename, could default to Raw - make decision')
            file_extension = handler_class.extensions[0]  # pick the first one - TODO refactor into a function/method - call handler_class.default_extension() - Is this callable? Is there a test suite for this code path?
            if folder:
                native_folder = self.native_full_path(folder)
            else:
                native_folder = self.note_root
            filename_without_path_and_extension = filename_generator_func(note_text)
            native_filename = os.path.join(native_folder, filename_without_path_and_extension + file_extension)
            # now check if generated filename already exists, if so need to make unique
            unique_counter = 1
            while os.path.exists(native_filename):
                #log.warning('generated filename %r already exists', native_filename)
                unique_part = '(%d)' % unique_counter  # match Tombo duplicate names avoidance
                native_filename = os.path.join(native_folder, filename_without_path_and_extension + unique_part + file_extension)
                unique_counter += 1
            filename = self.abspath2relative(native_filename)
            generated_filename = True


        filename = self.unicode_path(filename)
        fullpath_native_filename = self.native_full_path(filename)
        if original_filename and filename != original_filename:
            raise NotImplementedError('renaming files not yet supported; original_filename !=  filename  %r != %r ' % (original_filename, filename))

        handler_class = handler_class or filename2handler(filename)
        if get_pass:
            handler = handler_class(key=get_pass)
        else:
            handler = handler_class()

        # x TODO unicode filename
        # x TODO handler lookup
        # TODO handler password pass in - see load code above
        # TODO original filename and rename
        plain_str_bytes = self.to_bytes(note_text)

        #use_tempfile = True  # do not offer external control over this?
        if use_tempfile:
            timestamp_now = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
            out_file = tempfile.NamedTemporaryFile(
                mode='wb',
                dir=os.path.dirname(fullpath_native_filename),
                prefix=os.path.basename(fullpath_native_filename) + timestamp_now,
                delete=False
            )
            tmp_out_filename = out_file.name
            log.debug('DEBUG tmp_out_filename %r', tmp_out_filename)
        else:
            out_file = open(fullpath_native_filename, 'wb')  # Untested

        handler.write_to(out_file, plain_str_bytes)
        out_file.close()

        if backup:
            if os.path.exists(fullpath_native_filename):
                file_replace(fullpath_native_filename, fullpath_native_filename + '.bak')  # backup existing

        if use_tempfile:
            file_replace(tmp_out_filename, fullpath_native_filename)

    def note_delete(self, filename, backup=True):
        pass

    def note_size(self, filename):
        return 9999999999  # more likely to be noticed as an anomaly
        return -1

class FileLike:
    """Partial API (i.e. incomplete) file-like API that wraps a file like object
    using PurenTonbo BaseFile / EncryptedFile / RawFile encrypted files for reading and writing.
    For example TomboBlowfish
    Partial seek() support for read operations ONLY.
    Works with byte and text mode, NOTE encoding is either encoding name OR list of encoding names.
    """
    def __init__(self, fileptr, pt_object, mode=None, encoding=None):
        """Where pt_object is an initialized object of BaseFile (or subclass)
        """
        self._fileptr = fileptr
        self._pt_object = pt_object
        self._bufferedfileptr = FakeFile()
        mode = mode or 'r'
        if 'w' in mode:
            self._mode = 'w'
        elif '+' in mode:
            self._mode = '+'  # read and write
        elif 'r' in mode:
            self._mode = 'r'
        else:
            # TODO "a" append mode (+), implications for seek()?
            raise NotImplemented('mode=%r' % mode)
        if 'b' in mode:
            self._binary = True
        else:
            self._binary = False
        #encoding = encoding or ... TODO handle None case? Could expect caller to deal with this
        self._encoding = encoding
        if self._mode in ('r', '+'):
            self._read_from_file()  # FIXME make this lazy, rather than at init time

    # context manager protocol - "with" support
    def __enter__(self):
        return self
    def __exit__(self, exc_type, exc_value, traceback):
        self.close()

    def __getattr__(self, attr):
        if self.__dict__.has_key(attr):
            return self.__dict__[attr]
        else:
            return getattr(self._bufferedfileptr, attr)

    def _sanity_check(self):
        ## TODO disallow more read/writes/closes....
        pass

    def _read_from_file(self):
        # TODO this may be the start of allowing read and write support in the same session
        plain_text = self._pt_object.read_from(self._fileptr)
        self._bufferedfileptr = FakeFile(plain_text)

    def read(self, size=None):
        self._sanity_check()
        if self._mode == 'w':
            raise IOError(
                'file was write, and then read issued. read and write are mutually exclusive operations'
            )
        # TODO self._binary check
        if size is None:
            result = self._bufferedfileptr.read()
        else:
            result = self._bufferedfileptr.read(size)
        if not self._binary:
            if is_bytes(result):  # this is a dumb check. it will always be bytes....
                result = to_string(result, note_encoding=self._encoding)
        return result

    def seek(self, offset):  # TODO `whence` support?
        self._sanity_check()
        if self._mode != 'r':
            raise IOError(
                'seek issued for non-read operation'
            )
        return self._bufferedfileptr.seek(offset)

    def write(self, str_or_bytes):
        # TODO ensure str_or_bytes is bytes (and not unicode/string)
        self._sanity_check()
        if self._mode == 'r':
            raise IOError(
                'file was read, and then write issued. read and write are mutually exclusive operations'
            )
        if not self._binary:
            if is_text(str_or_bytes):
                str_or_bytes = to_bytes(str_or_bytes, note_encoding=self._encoding)
        return self._bufferedfileptr.write(str_or_bytes)

    def close(self, *args, **kwargs):
        self._sanity_check()
        ## do we need to call this in __del__?
        if self._mode != 'r':
            # i.e writable file
            plain_text = self._bufferedfileptr.getvalue()
            if self._mode == '+':
                self._fileptr.seek(0)
                self._fileptr.truncate()
            self._pt_object.write_to(self._fileptr, plain_text)
        self._bufferedfileptr.close()
        # self._fileptr.close()  # TODO close here or require caller? Probably makese sense here
        ## TODO disallow more read/writes/closes....

def pt_open(file, mode='r', encoding=None):
    """Partially implemented API to clone builtin https://docs.python.org/3/library/functions.html#open
    If encoding is specified use that, else use (default) config encoding **list**

    Similar to the regular Python open() function but will read/write encrypted files.
    File type is determined by file extension.
    Unrecognized file extension treated as raw (text).

    FIXME Right now password is, in order:
      1. picked up from OS env PT_PASSWORD
      2. obtained from (system) keyring
      3. prompted on command line
    """
    filename = file
    if mode not in ['r', 'w']:
        # TODO binary mode
        raise NotImplemented('mode %r' % mode)
    handler_class = filename2handler(filename, default_handler=RawFile)
    if not encoding:
        config = get_config()
        encoding = config['codec']
    password = os.environ.get('PT_PASSWORD') or keyring_get_password() or caching_console_password_prompt()
    pt_object = handler_class(password=password)
    fileptr = open(filename, mode + 'b')
    filelike = FileLike(fileptr, pt_object, mode, encoding=encoding)
    return filelike

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
        'note_root': '.',  # root directory of notes, other idea; ['.']
        'codec': ('utf8', 'cp1252'),  # note encoding(s) in order to try for reading, first is the encoding for writing
        'default_text_ext': 'txt',
        'default_encryption_ext': 'chi',
        #'default_encryption_ext': 'aes256.zip',
        #'new_lines': 'dos',
        #'new_lines': 'unix',
        #'': '',
        'ignore_folders': ['.git'],  # '.hg', '__pycache__'  TODO doc, other options ['.git', '.hg', '__pycache__', '.mozilla', '.cache'] (also check notes on ignore locations like Mac Dstore)
        'ignore_file_extensions': ['.bak', '~', '_MOD'],  # currently ptig only
        'ptig': {
            "editors": {  # if specified in config, defaults for editors WILL be lost
                "pttkview": "pttkview",  # part of PT
                "bat": "bat",
                "#vi": "tend to be builtin ptpyvim",
                "view": "view",
                "vim": "vim",
                "gvim": "gvim",
                "scite": "start scite",
                "nano": "nano",
            },
            'init': ['set ic', ],  # , "set enc", etc.
            'use_pager': False,
            'prompt': u'ptig: \U0001f50e ',
            '#linuxGUI_file_browser': 'pcmanfm',
            '#linuxCLI_file_browser': 'mc',
            '##win_file_browser': 'explorer',
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

def print_version_info(list_all=False):
    print(sys.version.replace('\n', ' '))
    print('')
    print('Puren Tonbo puren_tonbo version %s' % __version__)
    print('Formats:')
    print('')
    for file_extension, file_type, file_description in supported_filetypes_info(list_all=list_all):
        print('%17s - %s - %s' % (file_extension[1:], file_type, file_description))
    print('')
    print('Libs:')
    if chi_io:
        print('\tchi_io.implementation: %s' % chi_io.implementation)
    print('\tccrypt version: %s exe: %s' % (ccrypt_version, CCRYPT_EXE))
    if OpenSslEncDecCompat:
        print('\topenssl_enc_compat version: %s' % openssl_enc_compat.__version__)
    if gnupg:
        print('\tpython-gnupg version: %s' % gnupg.__version__)
    if gpg:
        print('\tgpg version: %r' % (gpg.version,))
    if vimdecrypt:
        print('\tvimdecrypt version: %s' % 'puren_tonbo_internal')
    if pyzipper:
        print('\tpyzipper version: %s' % pyzipper.__version__)
    if mzipaes:
        #print('\tmzipaes version: %s' % 'puren_tonbo_internal' + repr(mzipaes.crypto_kit))
        print('\tmzipaes version: %s' % 'puren_tonbo_internal implementation ' + mzipaes.crypto_kit.__class__.__name__)
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
