#!/usr/bin/env python
# -*- coding: us-ascii -*-
# vim:ts=4:sw=4:softtabstop=4:smarttab:expandtab
"""Command line tool to recursively Search Puren Tonbo files (plain text and encrypted notes).
Example encryption file formats; Tombo CHI Blowfish files, VimCrypt, AES-256.zip, etc.

    python -m puren_tonbo.tools.ptgrep -h
    python -m puren_tonbo.tools.ptgrep --note-root=puren_tonbo/tests/data/ cruel
    python -m puren_tonbo.tools.ptgrep --note-root puren_tonbo/tests/data/ cruel
    python -m puren_tonbo.tools.ptgrep --note-root puren_tonbo/tests/data/aesop.txt cruel

"""

import os
from optparse import OptionParser
import sys
import time

try:
    import colorama
except ImportError:
    colorama = None

import puren_tonbo
from puren_tonbo import SearchCancelled


is_py3 = sys.version_info >= (3,)


def main(argv=None):
    if argv is None:
        argv = sys.argv

    if is_py3:
        stream_encoding = 'utf-8'  # FIXME hard coded

    usage = "usage: %prog [options] [search_term] [dir_name_or_filename1] [dir_name_or_filename2...]"
    parser = OptionParser(usage=usage, version="%%prog %s" % puren_tonbo.__version__)
    parser.add_option("--list-formats", help="Which encryption/file formats are available", action="store_true")
    parser.add_option("--note-root", help="Directory of notes, or dir_name_or_filename1.... will pick up from config file and default to '.'")
    parser.add_option("-i", "--ignore_case", help="Case insensitive search", action="store_true")
    parser.add_option("-s", "--search_term", help="Term to search for, if omitted, [search_term] is used instead")
    parser.add_option("-c", "--codec", help="Override config file encoding (can be a list TODO format comma?)")
    parser.add_option("-p", "--password", help="password, if omitted and OS env PT_PASSWORD is set use that, if missing prompt")  # TODO keyring support
    parser.add_option("-P", "--password_file", help="file name where password is to be read from, trailing blanks are ignored")
    parser.add_option("-t", "--time", action="store_true")
    parser.add_option("-e", "--search_encrypted", help='Search encrypted files (default false)', action="store_true")
    parser.add_option("-v", "--verbose", help='Print query search time', action="store_true")
    parser.add_option("--config-file", help="Override config file")
    parser.add_option("--grep", help='Use grep-like output format instead of ripgrep-like', action="store_true")
    """ TODO
    -r, --regex_search:     Treat search term as a regex (default is to treat as literal word/phrase)
    -n, --line_numbers:     Print line number with output lines
    -p, --password=PASSWORD: Password to use for all encrypted notes (if omitted will be prompted for password,
        specifying password at command line can be a security risk as password _may_ be visible in process/task list and/or shell history)
    """
    # TODO add option to show absolute paths of filenames
    # TODO add option similar to grep -A/B/C for lines of context?

    (options, args) = parser.parse_args(argv[1:])
    #print('%r' % ((options, args),))
    verbose = options.verbose
    if verbose:
        print('Python %s on %s' % (sys.version.replace('\n', ' - '), sys.platform))
    if options.list_formats:
        print('')
        print('Formats:')
        print('')
        for file_extension in puren_tonbo.file_type_handlers:
            handler_class = puren_tonbo.file_type_handlers[file_extension]
            print('%17s - %s - %s' % (file_extension[1:], handler_class.__name__, handler_class.description))  # TODO description
        return 0

    def usage():
        parser.print_usage()

    if not args:
        parser.print_usage()
        return 1
    in_filename = args[0]

    if options.password_file:
        f = open(options.password_file, 'rb')
        password_file = f.read()
        f.close()
        password_file = password_file.strip()
    else:
        password_file = None

    #password = options.password or password_file or os.environ.get('PT_PASSWORD') or getpass.getpass("Password:")  # TODO FIXME replace with password prompt generator
    password = options.password or password_file or os.environ.get('PT_PASSWORD') or puren_tonbo.caching_console_password_prompt
    # TODO text file should NOT prompt for a password
    if password and not callable(password) and not isinstance(password, bytes):
        password = password.encode('us-ascii')


    ###################
    if options.search_term:
        search_term = options.search_term
    else:
        try:
            search_term = args.pop(0)
        except IndexError:
            ## missing search term
            #raise optionparse.Usage('missing search term')
            #optionparse.exit_exception() ##FIXME update exit_exception to append error text to end of usage instead-of "instead of" logic
            #optionparse.exit('missing search term') ##FIXME update exit_exception to append error text to end of usage instead-of "instead of" logic
            usage_error('ERROR: Missing search term')  # FIXME not implemented

    config = puren_tonbo.get_config(options.config_file)
    if options.note_root:
        paths_to_search = [options.note_root]
    else:
        paths_to_search = args or [config.get('note_root', '.')]
        if not paths_to_search:
            # TODO feature enhancement, load config file and default to notes directory if config found
            usage_error('ERROR: Missing search path/directory')  # should never happen now. FIXME not implemented

    if options.codec:
        note_encoding = options.codec
    else:
        note_encoding = config['codec']


    is_win = sys.platform.startswith('win')

    use_color = False
    if not sys.stdout.isatty():
        # skips processing for doing highlighting
        use_color = False
    elif colorama:
        # TODO options for these? These are close facimiles to ripgrep default
        color_filename = colorama.Fore.BLUE
        color_linenum = colorama.Fore.GREEN
        color_searchhit = colorama.Fore.RED
        color_reset = colorama.Style.RESET_ALL  # TODO review...
        # TODO only do below for Windows? looks like it may be a NOOP so may not need a windows check
        try:
            colorama.just_fix_windows_console()
        except AttributeError:
            # older version, for example '0.4.4'
            colorama.init()
        use_color = True
    else:
        # might be linux (not Windows)
        if not is_win:
            # ansi color escape sequences
            color_filename = '\x1b[01;34m'  # Fore.BLUE
            color_linenum = '\x1b[01;32m'  # Fore.GREEN
            #color_searchhit = '\x1b[01;05;37;41m'  # Background Red, foreground flasshing white
            color_searchhit = '\x1b[31m'  # Fore.RED
            color_reset = '\x1b[00m'
            use_color = True


    ripgrep = not options.grep
    """
    line_numbers = options.line_numbers == True
    
    search_is_regex = options.regex_search == True
    
    
    """
    line_numbers = search_is_regex = search_encrypted = False  # DEBUG FIXME TODO


    """
    if options.password:
        password_func = gen_static_password(options.password).gen_func()
    else:
        path_to_search = paths_to_search[0]  # TODO cleanup
        caching_console_password_prompt = gen_caching_get_password(dirname=path_to_search).gen_func()
        password_func = caching_console_password_prompt
    """
    # TODO look at password
    password_func = password  #  DEBUG TODO look at password

    ignore_case = options.ignore_case

    search_encrypted = options.search_encrypted

    if options.time:
        start_time = time.time()
    try:
        for path_to_search in paths_to_search:
            print('%r' % ((search_term, path_to_search, search_is_regex, ignore_case, search_encrypted, password_func),))  # TODO make pretty
            notes = puren_tonbo.FileSystemNotes(path_to_search, note_encoding)
            for hit in notes.search(search_term, search_term_is_a_regex=search_is_regex, ignore_case=ignore_case, search_encrypted=search_encrypted, get_password_callback=password_func):
                filename, hit_detail = hit
                #filename = remove_leading_path(path_to_search, filename)  # abspath2relative()
                if filename:
                    filename = '%s:' % filename
                else:
                    # Single file grep, rather than recursive search
                    # do not want filename
                    filename = ''
                if use_color:
                    filename = color_filename + filename + color_reset
                if ripgrep:
                    print('%s' % (filename, ))
                for result_hit_line, result_hit_text in hit_detail:
                    if use_color:
                        if not search_is_regex:
                            result_hit_text = result_hit_text.replace(search_term, color_searchhit + search_term + color_reset)
                        # else TODO regex ripgrep search color highlighting
                        result_hit_line = color_linenum + str(result_hit_line) + color_reset
                    else:
                        result_hit_line = str(result_hit_line)
                    if ripgrep:
                        # ripgrep like - automatically includes numbers
                        print('%s:%s' % (result_hit_line, result_hit_text))
                    elif line_numbers:
                        # grep-like with numbers
                        print('%s%s:%s' % (filename, result_hit_line, result_hit_text))
                    else:
                        # grep-like without numbers
                        print('%s%s' % (filename, result_hit_text))
    except SearchCancelled as info:
        print('search cancelled', info)
    if options.time:
        end_time = time.time()
        search_time = end_time - start_time
        print('Query time: %.2f seconds' % search_time)

    return 0


if __name__ == "__main__":
    sys.exit(main())
