
import logging
import os
import sys


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
    pyzipper = None


is_py3 = sys.version_info >= (3,)

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

class PurenTomboException(Exception):
    '''Base chi I/O exception'''


class BadPassword(PurenTomboException):
    '''Bad password exception'''


class UnsupportedFile(PurenTomboException):
    '''File not encrypted/not supported exception'''


class EncryptedFile:
    def __init__(self, key=None, password=None, password_encoding='utf8'):
        """
        key - is the actual encryption key in bytes
        password is the passphrase/password as a string
        password_encoding is used to create key from password if key is not provided
        """
        if key is None and password is None:
            raise RuntimeError('need password or key')  # TODO custom exception (needed for read_from()/write_to() failures
        if key:
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
    """

    def read_from(self, file_object):
        return file_object.read()

    def write_to(self, file_object, byte_data):
        file_object.write(byte_data)



class TomboBlowfish(EncryptedFile):
    """Read/write Tombo (modified) Blowfish encrypted files
    Compatible with files in:
      * Tombo - http://tombo.osdn.jp/En/
      * Kumagusu - https://osdn.net/projects/kumagusu/ and https://play.google.com/store/apps/details?id=jp.gr.java_conf.kumagusu
      * miniNoteViewer - http://hatapy.web.fc2.com/mininoteviewer.html and https://play.google.com/store/apps/details?id=jp.gr.java_conf.hatalab.mnv&hl=en_US&gl=US
    """

    def read_from(self, file_object):
        # TODO catch exceptions and raise PurenTomboException()
        try:
            return chi_io.read_encrypted_file(file_object, self.key)
        except chi_io.BadPassword as info:  # FIXME place holder
            # TODO chain exception...
            #print(dir(info))
            #raise BadPassword(info.message)  # does not work for python 3.6.9
            raise BadPassword(info)  # FIXME BadPassword(BadPassword("for 'file-like-object'",),)
        except Exception as info:
            # TODO chain exception...
            #raise PurenTomboException(info.message)
            raise PurenTomboException(info)

    def write_to(self, file_object, byte_data):
        chi_io.write_encrypted_file(file_object, self.key, byte_data)


class ZipAES(EncryptedFile):
    """Read/write ZIP AES(256) encrypted files (not old ZipCrypto)
    Compatible with files in WinZIP and 7z.
    Example 7z demo (Windows or Linux, assuming 7z is in the path):
        echo encrypted > encrypted.md
        7z a -ptest test_file.aes.zip encrypted.md
    """

    _filename = 'encrypted.md'  # filename inside of (AES encrypted) zip file

    def read_from(self, file_object):
        # TODO catch exceptions and raise PurenTomboException()
        try:
            with pyzipper.AESZipFile(file_object) as zf:
                zf.setpassword(self.key)
                return zf.read(self._filename)
        except chi_io.BadPassword as info:
            # TODO chain exception...
            print(dir(info))
            raise BadPassword()
        except Exception as info:
            # TODO chain exception...
            print(dir(info))
            raise PurenTomboException()

    def write_to(self, file_object, byte_data):
        with pyzipper.AESZipFile(file_object,
                                 'w',
                                 compression=pyzipper.ZIP_LZMA,  # TODO revisit this
                                 encryption=pyzipper.WZ_AES,
                                 ) as zf:
            # defaults to nbits=256 - TODO make explict?
            zf.setpassword(self.key)
            zf.writestr(self._filename, byte_data)  # pyzipper can take string or bytes


# note uses file extension - could also sniff file header and use file magic
file_type_handlers = {
    '.txt': RawFile,  # these are not needed, filename2handler() defaults
    '.md': RawFile,
}
if chi_io :
    file_type_handlers['.chi'] = TomboBlowfish  # created by http://tombo.osdn.jp/En/
if pyzipper :
    file_type_handlers['.aes.zip'] = ZipAES  # Zip file with AES-256 - Standard WinZip/7z (not the old ZipCrypto!)
    file_type_handlers['.aes256.zip'] = ZipAES  # Zip file with AES-256 - Standard WinZip/7z (not the old ZipCrypto!)

# Consider command line crypto (via pipe to avoid plaintext on disk)
# TODO? openssl aes-128-cbc -in in_file -out out_file.aes128
# TODO? openpgp

def filename2handler(filename):
    filename = filename.lower()
    if filename.endswith('.aes256.zip'):
        file_extn = '.aes.zip'
    elif filename.endswith('.aes.zip'):
        file_extn = '.aes.zip'
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




def main(argv=None):
    if argv is None:
        argv = sys.argv

    print('Python %s on %s\n\n' % (sys.version, sys.platform))
    print('Python %s on %s\n\n' % (sys.version.replace('\n', ' - '), sys.platform))
    print('Python %r on %r\n\n' % (sys.version, sys.platform))

    return 0


if __name__ == "__main__":
    sys.exit(main())
