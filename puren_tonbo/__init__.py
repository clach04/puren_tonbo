
import errno

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

import logging
import os
import sys


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
    import pyzipper  # https://github.com/danifus/pyzipper  NOTE py3 only
except ImportError:
    pyzipper = fake_module('pyzipper')

try:
    #import vimdecrypt  # https://github.com/nlitsme/vimdecrypt
    from puren_tonbo import vimdecrypt  # https://github.com/nlitsme/vimdecrypt
except ImportError:
    vimdecrypt = fake_module('vimdecrypt')


import puren_tonbo.mzipaes


is_py3 = sys.version_info >= (3,)

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
#disable_logging = True
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

class PurenTomboException(Exception):  # FIXME typo Tonbo
    '''Base chi I/O exception'''


class BadPassword(PurenTomboException):
    '''Bad password exception'''


class UnsupportedFile(PurenTomboException):
    '''File not encrypted/not supported exception'''

class PurenTomboIO(PurenTomboException):
    '''(File) I/O exception'''


class EncryptedFile:

    description = 'Base Encrypted File'

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

    def read_from(self, file_object):
        raise NotImplementedError

    def write_to(self, file_object, byte_data):
        raise NotImplementedError


class RawFile(EncryptedFile):
    """Raw/binary/text file - Read/write raw bytes. 
    Use for plain text files.
    TODO this requires a password on init, plain text/unencrypted files should not need a password
    """

    description = 'Raw file, no encryption support'

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

    def read_from(self, file_object):
        # TODO catch exceptions and raise PurenTomboException()
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
            raise PurenTomboException(info)


class TomboBlowfish(EncryptedFile):
    """Read/write Tombo (modified) Blowfish encrypted files
    Compatible with files in:
      * Tombo - http://tombo.osdn.jp/En/
      * Kumagusu - https://osdn.net/projects/kumagusu/ and https://play.google.com/store/apps/details?id=jp.gr.java_conf.kumagusu
      * miniNoteViewer - http://hatapy.web.fc2.com/mininoteviewer.html and https://play.google.com/store/apps/details?id=jp.gr.java_conf.hatalab.mnv&hl=en_US&gl=US
    """

    description = 'Tombo Blowfish ECB (not recommended)'

    def read_from(self, file_object):
        # TODO catch exceptions and raise PurenTomboException()
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
            #raise PurenTomboException(info.message)
            raise PurenTomboException(info)

    def write_to(self, file_object, byte_data):
        chi_io.write_encrypted_file(file_object, self.key, byte_data)

class ZipEncryptedFileBase(EncryptedFile):
    _filename = 'encrypted.md'  # filename inside of (encrypted) zip file
    _compression = pyzipper.ZIP_DEFLATED


class PurePyZipAES(ZipEncryptedFileBase):
    """mzipaes - Read/write ZIP AES(256) encrypted files (not old ZipCrypto)
    Suitable for Python 2.7 and 3.x
    """

    description = 'AES-256 ZIP AE-1 DEFLATED (regular compression)'

    def read_from(self, file_object):
        # TODO catch specific exceptions and raise better mapped exception
        try:
            zf = mzipaes.MiniZipAE1Reader(file_object, self.key)
            return zf.get()  # first file in zip, ignore self._filename
        except Exception as info:
            # TODO chain exception...
            #raise PurenTomboException(info.message)
            raise PurenTomboException(info)

    def write_to(self, file_object, byte_data):
        assert self._compression == pyzipper.ZIP_DEFLATED  # FIXME/TODO add proper check and raise explict exception
        # TODO catch specific exceptions and raise better mapped exception
        # TODO e.g. Exception('BAD PASSWORD',)
        try:
            zf = mzipaes.MiniZipAE1Writer(file_object, self.key)
            zf.append(self._filename, byte_data)
            #zf.zipcomment = 'optional comment'
            zf.write()
        except Exception as info:
            # TODO chain exception...
            #raise PurenTomboException(info.message)
            raise PurenTomboException(info)


class ZipAES(ZipEncryptedFileBase):
    """Read/write ZIP AES(256) encrypted files (not old ZipCrypto)
    Compatible with files in WinZIP and 7z.
    Example 7z demo (Windows or Linux, assuming 7z is in the path):
        echo encrypted > encrypted.md
        7z a -ptest test_file.aes.zip encrypted.md
    """

    description = 'AES-256 ZIP AE-1 DEFLATED (regular compression)'
    _filename = 'encrypted.md'  # filename inside of (AES encrypted) zip file
    _compression = pyzipper.ZIP_DEFLATED

    def read_from(self, file_object):
        # TODO catch exceptions and raise PurenTomboException()
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
            raise PurenTomboException(info)

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
    _compression = pyzipper.ZIP_STORED
    # .aes256stored.zip

class ZipLzmaAES(ZipAES):
    description = 'AES-256 ZIP AE-1 LZMA'
    _compression = pyzipper.ZIP_LZMA
    # .aes256lzma.zip

class ZipBzip2AES(ZipAES):
    description = 'AES-256 ZIP AE-1 BZIP2'
    _compression = pyzipper.ZIP_BZIP2

# TODO unused/untested; ZipBzip2AES

# note uses file extension - could also sniff file header and use file magic
file_type_handlers = {
    '.txt': RawFile,  # these are not needed, filename2handler() defaults
    '.md': RawFile,
}
if chi_io:
    file_type_handlers['.chi'] = TomboBlowfish  # created by http://tombo.osdn.jp/En/
if pyzipper:
    file_type_handlers['.aes.zip'] = ZipAES  # Zip file with AES-256 - Standard WinZip/7z (not the old ZipCrypto!)
    file_type_handlers['.aes256.zip'] = ZipAES  # Zip file with AES-256 - Standard WinZip/7z (not the old ZipCrypto!)
    file_type_handlers['.aes256stored.zip'] = ZipNoCompressionAES  # uncompressed Zip file with AES-256 - Standard WinZip/7z (not the old ZipCrypto!)
    file_type_handlers['.aes256lzma.zip'] = ZipLzmaAES  # LZMA Zip file with AES-256 7z .zip (not the old ZipCrypto!)
else:
    file_type_handlers['.aes.zip'] = PurePyZipAES  # AE-1 only Zip file with AES-256 - Standard WinZip/7z (not the old ZipCrypto!)
if vimdecrypt:
    file_type_handlers['.vimcrypt'] = VimDecrypt  # vim
    file_type_handlers['.vimcrypt1'] = VimDecrypt  # vim
    file_type_handlers['.vimcrypt2'] = VimDecrypt  # vim
    file_type_handlers['.vimcrypt3'] = VimDecrypt  # vim

# Consider command line crypto (via pipe to avoid plaintext on disk)
# TODO? openssl aes-128-cbc -in in_file -out out_file.aes128
# TODO? openpgp

def filename2handler(filename):
    filename = filename.lower()
    if filename.endswith('.aes256.zip'):
        file_extn = '.aes.zip'
    elif filename.endswith('.aes.zip'):
        file_extn = '.aes.zip'
    elif filename.endswith('.aes256stored.zip'):
        file_extn = '.aes256stored.zip'
    elif filename.endswith('.aes256lzma.zip'):
        file_extn = '.aes256lzma.zip'
    else:
        _dummy, file_extn = os.path.splitext(filename)
    log.debug('clach04 DEBUG file_extn: %r', file_extn)
    log.debug('clach04 DEBUG file_type_handlers: %r', file_type_handlers)
    handler_class = file_type_handlers.get(file_extn)
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
        print('bytes from decrypt')
        log.debug('clach04 DEBUG data: %r', content)
        print(repr(content))
        content = content.decode('utf8')  # hard coded for now
    else:
        log.debug('clach04 DEBUG : regular read')
        with open(path, 'r') as f:
          content = f.read()


#################

def getpassfunc(prompt=None):
    if prompt:
        if sys.platform == 'win32':  # and isinstance(prompt, unicode):  # FIXME better windows check and unicode check
            #if windows, deal with unicode problem in console
            # TODO add Windows check here!
            prompt = repr(prompt)  # consider us-ascii with replacement character encoding...
        return getpass.getpass(prompt)
    else:
        return getpass.getpass()

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
                self.user_password = getpassfunc(prompt)
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
            promptfunc = getpassfunc
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
                    self.user_password = None
                else:
                    ## not sure if this logic belongs at this level....
                    self.user_password = chi_io.CHI_cipher(self.user_password)
            return self.user_password
        return get_pass


caching_console_password_prompt = gen_caching_get_password().gen_func()

any_filename_filter = lambda x: True  # allows any filename, i.e. no filtering

class BaseNotes(object):
    def __init__(self, note_root, note_encoding=None):
        self.note_root = note_root
        #self.note_encoding = note_encoding or 'utf8'
        self.note_encoding = note_encoding or ('utf8', 'cp1252')

    def recurse_notes(self, sub_dir=None, filename_filter=any_filename_filter):
        """Recursive Tombo note lister.
        Iterator of files in @sub_dir"""
        raise NotImplementedError('Implement in sub-class')

    def directory_contents(self, sub_dir=None):
        """Simple non-recursive Tombo note lister.
        Returns tuple (list of directories, list of files) in @sub_dir"""
        raise NotImplementedError('Implement in sub-class')

    def search_iter(self, *args, **kwargs):
        """Same API as search_iter()"""
        raise NotImplementedError('Implement in sub-class')

    def note_contents(self, filename, get_pass=None, dos_newlines=True):
        """get_pass is either plaintext (bytes) password or a password returning func
        """
        raise NotImplementedError('Implement in sub-class')

    def note_contents_save(self, notetext, filename=None, original_filename=None, get_pass=None, dos_newlines=True, backup=True):
        raise NotImplementedError('Implement in sub-class')

    def note_delete(self, filename, backup=True):
        pass

    def note_size(self, filename):
        return 9999999999  # more likely to be noticed as an anomaly
        return -1


class FileSystemNotes(BaseNotes):
    """PyTombo notes on local file system, just like original Windows Tombo
    """

    def to_string(self, data_in_bytes):
        if isinstance(self.note_encoding, basestring):
            return data_in_bytes.decode(self.note_encoding)
        for encoding in self.note_encoding:
            try:
                result = data_in_bytes.decode(encoding)
                return result
            except UnicodeDecodeError:
                pass  # try next
            # TODO try/except

    def __init__(self, note_root, note_encoding=None):
        self.note_root = os.path.abspath(note_root)
        #self.note_encoding = note_encoding or 'utf8'
        self.note_encoding = note_encoding or ('utf8', 'cp1252')

    def recurse_notes(self, sub_dir=None, filename_filter=any_filename_filter):
        """Recursive Tombo note lister.
        Iterator of files in @sub_dir"""
        raise NotImplementedError('Implement in sub-class')

    def directory_contents(self, sub_dir=None):
        """Simple non-recursive Tombo note lister.
        Returns tuple (list of directories, list of files) in @sub_dir"""
        raise NotImplementedError('Implement in sub-class')

    def search_iter(self, *args, **kwargs):
        """Same API as search_iter()"""
        raise NotImplementedError('Implement in sub-class')

    def note_contents(self, filename, get_pass=None, dos_newlines=True):
        """get_pass is either plaintext (bytes) password or a password returning func
        filename (extension) dictates encryption mode/format (if any)
        get_pass() is a callback function that returns a password, get_pass() should return None for 'cancel'. See caching_console_password_prompt() for an example.
            get_pass(filename=filename, reset=reset_password)
        dos_newlines=True means use Windows/DOS newlines, emulates win32 behavior of Tombo and is the default
        """
        try:
            fullpath_filename = os.path.join(self.note_root, filename)  # FIXME refactor into sanity_method()
            fullpath_filename = os.path.abspath(fullpath_filename)
            if not fullpath_filename.startswith(self.note_root):
                raise PurenTomboIO('outside of note tree root')

            handler_class = filename2handler(filename)
            #import pdb ; pdb.set_trace()
            if handler_class is RawFile:
                print('it is plain text')
                note_password = ''  # fake it. Alternatively override init for RawFile to remove check
            else:
                if callable(get_pass):
                    reset_password = False  # TODO - for now, use this if get bad passwords
                    note_password = get_pass(filename=filename, reset=reset_password)
                else:
                    # Assume password bytes passed in
                    note_password = get_pass
                if note_password is None:
                    raise BadPassword('missing or bad password for %s' % filename)

            #import pdb ; pdb.set_trace()
            handler = handler_class(key=note_password)  # FIXME callback function support for password func
            # TODO repeat on bad password func
            print('DEBUG filename %r' % fullpath_filename)
            in_file = open(fullpath_filename, 'rb')
            try:
                plain_str = handler.read_from(in_file)
                # TODO could stash away handler..key for reuse as self.last_used_key .... or derived_key (which would be a new attribute)
                return self.to_string(plain_str)
            except PurenTomboException as info:
                print("DEBUG Encrypt/Decrypt problem. %r" % (info,))
            finally:
                in_file.close()
        except IOError as info:
            if info.errno == errno.ENOENT:
                raise PurenTomboIO('Error opening %r file/directory does not exist' % filename)
            else:
                raise

    def note_contents_save(self, notetext, filename=None, original_filename=None, get_pass=None, dos_newlines=True, backup=True):
        raise NotImplementedError('Implement in sub-class')

    def note_delete(self, filename, backup=True):
        pass

    def note_size(self, filename):
        return 9999999999  # more likely to be noticed as an anomaly
        return -1


def main(argv=None):
    if argv is None:
        argv = sys.argv

    print('Python %s on %s\n\n' % (sys.version, sys.platform))
    print('Python %s on %s\n\n' % (sys.version.replace('\n', ' - '), sys.platform))
    print('Python %r on %r\n\n' % (sys.version, sys.platform))

    return 0


if __name__ == "__main__":
    sys.exit(main())
