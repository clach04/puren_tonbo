#!/usr/bin/env python
# -*- coding: us-ascii -*-
# vim:ts=4:sw=4:softtabstop=4:smarttab:expandtab
"""Command line tool to re-encrypt Puren Tonbo files from any format into any format, optionally with a new password

    python -m puren_tonbo.tools.ptrecrypt -h
    ptrecrypt -h

    python -m puren_tonbo.tools.ptrecrypt puren_tonbo/tests/data
    python -m puren_tonbo.tools.ptrecrypt --simulate --cipher aes256.zip --new_extension .zip  -p password  --destination_directory /tmp/all_jenc puren_tonbo/tests/data/
    python -m puren_tonbo.tools.ptrecrypt --simulate  -p password  --force_recrypt_same_format_password  --existing_files replace --skip_unencrypted  puren_tonbo/tests/data/
"""

import datetime
import glob
import logging
import os
from optparse import OptionParser
import sys
import tempfile

import puren_tonbo
import puren_tonbo.ui


is_py3 = sys.version_info >= (3,)


## TODO move out of global?
## TODO color logging, see ptgrep logic, needs further refinement and command line control. Also https://betterstack.com/community/questions/how-to-color-python-logging-output/ - https://alexandra-zaharia.github.io/posts/make-your-own-custom-color-formatter-with-python-logging/ (skip colorlog due to wanting same API for py 2.x and 3.x)
# create logger
log = logging.getLogger("pttkview")
log.setLevel(logging.DEBUG)
disable_logging = False
disable_logging = True  # TODO pickup from command line, env, config?
if disable_logging:
    log.setLevel(logging.NOTSET)  # only logs; WARNING, ERROR, CRITICAL
    #log.setLevel(logging.INFO)  # logs; INFO, WARNING, ERROR, CRITICAL

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


def process_file(filename, password, new_password, handler_class_newfile, force_recrypt_same_format_password=False, destination_directory=None, new_extension=None, existing_files_resolution=None, simulate=None):
    new_extension = new_extension or "default"
    existing_files_resolution = existing_files_resolution or 'stop'

    log.info('Processing %s', filename)
    filename_abs = os.path.abspath(filename)
    #print('\t %s' % filename_abs)

    # determine filename sans extension. See new note code in ptig? function to add to handler class? COnsider implemention here then refactor later to place in to pt lib
    #note_contents_load_filename(filename_abs, get_pass=None, dos_newlines=False, return_bytes=True, handler_class=None, note_encoding='utf-8')
    # TODO caching password...
    #plaintext_bytes = puren_tonbo.note_contents_load_filename(filename_abs, get_pass=password, dos_newlines=False, return_bytes=True)  # get raw bytes, do not treat like a notes (text) file
    # alternatively (future?) call pt_open() instead
    #"""# final alt:
    in_handler_class = puren_tonbo.filename2handler(filename)
    in_handler = in_handler_class(key=password)
    in_file = open(filename_abs, 'rb')
    plaintext_bytes = in_handler.read_from(in_file)
    in_file.close()
    base_filename, original_extension = in_handler.split_extension(filename)
    #"""
    #print('\t\t %r' % plaintext_bytes)
    log.debug('%s plaintext_bytes: %s', filename, plaintext_bytes)
    out_handler_class = handler_class_newfile or in_handler_class
    if in_handler_class == out_handler_class and password == new_password and not force_recrypt_same_format_password:
        log.warning('Skipping same format/password for (see force_recrypt_same_format_password) %s', filename)
        return
    log.info('%s -> %s', in_handler_class, out_handler_class)
    out_handler = out_handler_class(new_password)
    print('\t\t %r' % ((base_filename, original_extension, original_extension in out_handler.extensions, out_handler.default_extension()),))

    if new_extension == "default":
        new_file_extension = out_handler.default_extension()
    elif new_extension == "cipher":
        # likely the same as default
        new_file_extension = out_handler.default_extension()
    elif new_extension == "retain":
        new_file_extension = original_extension
    else:
        if not new_extension.startswith('.'):
            raise NotImplementedError('new_extension %r' % (new_extension,))
        new_file_extension = new_extension

    new_filename = base_filename + new_file_extension  # FIXME option needed

    if destination_directory:
        new_filename = os.path.join(destination_directory, new_filename)
        # TODO mkdir
    log.info('%s -> %s', filename, new_filename)

    if new_filename == filename or os.path.exists(new_filename):
        # overwrite decisions
        if existing_files_resolution in ('stop', 'error', 'default'):
            log.error('Existing files for, stopping (see existing_files option) %s', new_filename)
            raise NotImplementedError('new file matches existing, stopping (see option existing_files_resolution)')  # TODO different exception
        elif existing_files_resolution in ('skip',):
            log.warning('Skipping already existing file (see existing_files option) %s', new_filename)
            return
        elif existing_files_resolution in ('overwrite' ,'replace', 'delete'):
            pass
        else:
            raise NotImplementedError('new file matches existing, unknown existing_files_resolution %r', existing_files_resolution)  # TODO different exception

    file_already_exists = os.path.exists(new_filename)  # TODO **potentially** multiple calls by this point, option to refactor
    if not file_already_exists:
        # no need for safe write and file_replace()
        log.error('FAKE WRITTING %s', new_filename)
        if not simulate:
            raise NotImplementedError('Actual writting1')
            """
            out_file = open(new_filename, 'wb')
            out_file.write_to(out_file, plaintext_bytes)
            out_file.close()
            """
            pass  # FIXME implement
    else:
        raise NotImplementedError('writting to existing file')
        if not simulate:
            raise NotImplementedError('Actual writting2')
            pass  # FIXME implement

    if existing_files_resolution == 'delete':
        log.info('about to delete old file %', filename)
        if simulate:
            return
        raise NotImplementedError('Actual delete')
        pass  # FIXME / TODO delete filename
        # os.remove(filename_abs)  # use abs name, for hopefully better error reporting



def main(argv=None):
    if argv is None:
        argv = sys.argv

    usage = "usage: %prog [options] file_or_dir_pattern1 [file_or_dir_pattern2...]"
    parser = OptionParser(
        usage=usage,
        version="%%prog %s" % puren_tonbo.__version__,
        description="Command line tool to (re-)encrypt files. Any files passed on the command line WILL BE encrypted (in the requested format, if none requested original format) unless it is the same format and password. Any directories may have some form of filtering based on type."
    )
    parser.add_option("--list-formats", help="Which encryption/file formats are available", action="store_true")
    parser.add_option("--password-prompt", "--password_prompt", help="Comma seperated list of prompt mechanism to use, options; " + ','.join(puren_tonbo.ui.supported_password_prompt_mechanisms()), default="any")
    parser.add_option("--no-prompt", "--no_prompt", help="do not prompt for password", action="store_true")
    parser.add_option("--cipher", help="Which encryption mechanism to use (file extension used as hint), use existing cipher if ommited")
    parser.add_option("--new-password", "--new_password", help="new password to use, if omitted use the existing password")
    parser.add_option("-E", "--envvar", help="Name of environment variable to get password from (defaults to PT_PASSWORD) - unsafe", default="PT_PASSWORD")  # similar to https://ccrypt.sourceforge.net/
    parser.add_option("-p", "--password", help="password, if omitted but OS env PT_PASSWORD is set use that, if missing prompt")
    parser.add_option("-P", "--password_file", help="file name where password is to be read from, trailing blanks are ignored")
    parser.add_option("-v", "--verbose", action="store_true")
    parser.add_option("-s", "--silent", help="if specified do not warn about stdin using", action="store_false", default=True)
    parser.add_option("--force-recrypt-same-format-password", "--force_recrypt_same_format_password", help="For re encryption, even if same file format/container and password is to be used", action="store_true")
    parser.add_option("--destination-directory", "--destination_directory", help="If specified where to write to, if ommited uses same directory")
    parser.add_option("--new-extension", "--new_extension", help="file extension to append for new files; 'default' (default for cipher), 'cipher' (what was passed in on command line), 'retain' (if not changing formats, use the original file extension) - and potentially anything else with a period is the new extension to use, for example '.zip'")
    parser.add_option("--skip-encrypted", "--skip_encrypted", help="For directories, skip already encrypted files", action="store_true")  # TODO consider applying to files specified on command line
    parser.add_option("--skip-unencrypted", "--skip_unencrypted", help="For directories, skip files that are not already encrypted", action="store_true")  # TODO consider applying to files specified on command line
    parser.add_option("--existing-files", "--existing_files", help="How to handle existing files; resolving files that already exist; default error/stop, skip, overwrite/replace/delete (in safe mode - needed for same file type, new password), delete (after successful write)")
    parser.add_option("--simulate", help="Do not write/delete/change files", action="store_true")
    # TODO option on saving to delete original file -- see existing-files / --existing_files
    (options, args) = parser.parse_args(argv[1:])
    log.debug('args: %r' % ((options, args),))
    verbose = options.verbose
    if verbose:
        print('Python %s on %s' % (sys.version.replace('\n', ' - '), sys.platform))
    log.info('Python %s on %s' % (sys.version.replace('\n', ' - '), sys.platform))
    if options.list_formats:
        puren_tonbo.print_version_info()
        return 0
    simulate = options.simulate
    if simulate:
        print(dir(log))
        print(log.level)
        if log.level < logging.INFO:
            log.setLevel(logging.INFO)  # ensure logging info enabled for filenames and operations
    destination_directory = options.destination_directory

    def usage():
        parser.print_usage()

    if not args:
        parser.print_usage()

    if options.cipher:
        handler_class_newfile = puren_tonbo.filename2handler('_.' + options.cipher)  # TODO options.cipher to filename extension is less than ideal
    else:
        handler_class_newfile = None

    if options.no_prompt:
        options.password_prompt = None
        default_password_value = ''  # empty password, cause a bad password error
    else:
        options.password_prompt = options.password_prompt.split(',')  # TODO validation options? for now rely on puren_tonbo.getpassfunc()
        default_password_value = None

    if options.password_file:
        f = open(options.password_file, 'rb')
        password_file = f.read()
        f.close()
        password_file = password_file.strip()
    else:
        password_file = None

    password = options.password or password_file or os.environ.get(options.envvar or 'PT_PASSWORD') or puren_tonbo.keyring_get_password() or default_password_value
    if password is None:
        # get password ahead of file reading
        # TODO review wrong password behavior, should prompt.
        password = puren_tonbo.ui.getpassfunc("Puren Tonbo ptcipher Password:", preference_list=options.password_prompt)
    if password and not isinstance(password, bytes):
        password = password.encode('us-ascii')
    new_password = options.new_password or password  # TODO document/make clear - if password changes during processing, first password passed in is what will be used for new password

    filename_pattern_list = args
    directory_list = []
    log.debug('args: %r' % ((argv, args, directory_list),))
    #import pdb; pdb.set_trace()
    for filename_pattern in filename_pattern_list:
        # NOTE local file system only
        #
        if os.path.isdir(filename_pattern):
            directory_list.append(filename_pattern)
            continue
        for filename in glob.glob(filename_pattern):
            process_file(filename, password, new_password, handler_class_newfile, force_recrypt_same_format_password=options.force_recrypt_same_format_password, destination_directory=destination_directory, new_extension=options.new_extension, existing_files_resolution=options.existing_files, simulate=simulate)

    if directory_list:
        # or use puren_tonbo.walker(), potentially more efficient with filename lookup?
        for path_to_search in directory_list:
            for filename in puren_tonbo.recurse_notes(path_to_search, puren_tonbo.supported_filename_filter):
                is_encrypted = puren_tonbo.encrypted_filename_filter(filename)
                if options.skip_encrypted and is_encrypted:
                    log.warning('Skipping already encrypted %s', (filename,))
                    continue
                if options.skip_unencrypted and not is_encrypted:
                    log.warning('Skipping not encrypted %s', (filename,))
                    continue
                process_file(filename, password, new_password, handler_class_newfile, force_recrypt_same_format_password=options.force_recrypt_same_format_password, destination_directory=destination_directory, new_extension=options.new_extension, existing_files_resolution=options.existing_files, simulate=simulate)

    return 0


if __name__ == "__main__":
    sys.exit(main())
