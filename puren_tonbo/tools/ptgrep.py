#!/usr/bin/env python
# -*- coding: us-ascii -*-
# vim:ts=4:sw=4:softtabstop=4:smarttab:expandtab
r"""Command line tool to recursively Search Puren Tonbo files (plain text and encrypted notes).
Example encryption file formats; Tombo CHI Blowfish files, VimCrypt, AES-256.zip, etc.
Essentially; ack, ripgrep, pss, ag/The Silver Searcher for plain text and encrypted files.

    python -m puren_tonbo.tools.ptgrep -h
    python -m puren_tonbo.tools.ptgrep better puren_tonbo\tests\data
    python -m puren_tonbo.tools.ptgrep better puren_tonbo/tests/data
    python -m puren_tonbo.tools.ptgrep Better puren_tonbo/tests/data
    python -m puren_tonbo.tools.ptgrep -i better puren_tonbo/tests/data
    python -m puren_tonbo.tools.ptgrep -r th.n puren_tonbo/tests/data
    python -m puren_tonbo.tools.ptgrep --note-root=puren_tonbo/tests/data/ cruel
    python -m puren_tonbo.tools.ptgrep --note-root puren_tonbo/tests/data/ cruel
    python -m puren_tonbo.tools.ptgrep --note-root puren_tonbo/tests/data/aesop.txt cruel  # FIXME fails TODO test suite
    python -m puren_tonbo.tools.ptgrep cruel puren_tonbo/tests/data/
    python -m puren_tonbo.tools.ptgrep cruel puren_tonbo/tests/data/aesop.txt  # FIXME fails
    python -m puren_tonbo.tools.ptgrep -r the. puren_tonbo/tests/data/

    ptgrep King
    ptgrep -i King
    ptgrep --regex_search  K.ng
    ptgrep   K.ng
    ptgrep --search_encrypted --password=password King

"""

import codecs
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
is_win = sys.platform.startswith('win')

guess_color_available = colorama or (not is_win) or (is_win and ('TERM' in os.environ or 'TERM_PROGRAM' in os.environ))

if colorama:
    # TODO options for these? These are close facimiles to ripgrep default
    color_error = colorama.Fore.RED  # Background instead?
    color_filename = colorama.Fore.BLUE
    color_filename_zebra = color_filename + colorama.Back.WHITE  # TODO allow control and override of thiss
    color_linenum = colorama.Fore.GREEN
    color_searchhit = colorama.Fore.RED
    color_reset = colorama.Style.RESET_ALL
else:
    if guess_color_available:
        # ansi color escape sequences
        color_error = '\x1b[31m'  # Fore.RED
        color_filename = '\x1b[01;34m'  # Fore.BLUE
        color_filename_zebra = color_filename + '\x1b[47m'  # TODO allow control and override of thiss
        color_linenum = '\x1b[01;32m'  # Fore.GREEN
        #color_searchhit = '\x1b[01;05;37;41m'  # Background Red, foreground flasshing white
        color_searchhit = '\x1b[31m'  # Fore.RED
        color_reset = '\x1b[00m'

# TODO
"""
if not (os.environ.get('PYTHONIOENCODING') and py2 and win:
    warn
    'recommend PYTHONIOENCODING=ascii:backslashreplace  so as to avoid loss of characters'
    if sys.__stdout__.isatty() or sys.__stderr__.isatty():
        sleep / pause

"""

PTGREP_STDOUT_MODE = os.environ.get('PTGREP_STDOUT_MODE', '')
if not PTGREP_STDOUT_MODE and is_win and not is_py3 and (not os.environ.get('PYTHONIOENCODING') or not os.environ.get('PYTHONUTF8')):
    # for python2 under Windows force hack, so that do not get UnicodeEncodeError: errors, set to 'disabled' to keep default behavior
    PTGREP_STDOUT_MODE = 'ascii:backslashreplace'  # FIXME review for Windows with Terminal rather than CMD.exe / Command Window
print(PTGREP_STDOUT_MODE)

sys_stdout = sys.stdout

def stdout_hack_required():
    if not PTGREP_STDOUT_MODE:
        return False
    if PTGREP_STDOUT_MODE:
        if PTGREP_STDOUT_MODE == 'disabled':
            return False
    return True

def stdout_hack():
    if not stdout_hack_required():
        return

    # NOTE1 py3 has reconfigure for stdout, py2 does NOT.
    # NOTE2 py3 also has detach() for stdout, py2 does NOT.
    if PTGREP_STDOUT_MODE == 'utf8':
        sys.stdout = codecs.getwriter("utf-8")(sys.stdout)
    else:
        sys.stdout = codecs.getwriter('ascii')(sys.stdout, errors='backslashreplace')  # don't loose detail
        #sys.stdout = codecs.getwriter('ascii')(sys.stdout, errors='xmlcharrefreplace')

def stdout_restore():
    if not stdout_hack_required():
        return
    sys.stdout = sys_stdout


# TODO remove/replace args and consolidate into options
def grep(search_term, paths_to_search, options, use_color, password_func, note_encoding):
    zebra_color_filenames = getattr(options, 'zebra_color_filenames', False)
    count_files_matched = getattr(options, 'count_files_matched', False)  # if true, count result filenames (starting at 1). Prefix filenames with a number
    ignore_case = options.ignore_case
    line_numbers = options.line_numbers == True  # include line numbers of match in file
    ripgrep = not options.grep
    search_encrypted = options.search_encrypted
    search_is_regex = options.regex_search == True  # TODO consider renaming to match option name
    only_filename_results = options.find_only_filename or options.files_with_matches  # do not include file content matches, just filenames in results
    find_only_filename = options.find_only_filename  # do NOT search file content, only search for filenames
    if find_only_filename:
        search_encrypted = True  # TODO ?
    if zebra_color_filenames:
        count_files_matched = True

    if options.time:
        start_time = time.time()
    try:
        stdout_hack()
        if use_color:
            highlight_text_start, highlight_text_stop = color_searchhit, color_reset
        else:
            highlight_text_start, highlight_text_stop = None, None

        if count_files_matched:
            result = []
            counter = 1  # manually count, rather than use enumerate()
        for path_to_search in paths_to_search:
            #print('%r' % ((search_term, path_to_search, search_is_regex, ignore_case, search_encrypted, password_func),))  # TODO make pretty and/or log instead
            notes = puren_tonbo.FileSystemNotes(path_to_search, note_encoding)

            for hit in notes.search(search_term, search_term_is_a_regex=search_is_regex, ignore_case=ignore_case, search_encrypted=search_encrypted, find_only_filename=find_only_filename, files_with_matches=options.files_with_matches, get_password_callback=password_func, highlight_text_start=highlight_text_start, highlight_text_stop=highlight_text_stop):
                filename, hit_detail = hit
                #filename = remove_leading_path(path_to_search, filename)  # abspath2relative()
                if filename:
                    if options.display_full_path:
                        filename = os.path.join(path_to_search, filename)
                    if count_files_matched:
                        result.append(filename)
                    if ripgrep or only_filename_results:
                        filename = '%s' % filename  # ripgrep/ack/ag uses filename only
                    else:
                        # grep - TODO should this be conditional on line numbers and/or wild card?
                        filename = '%s:' % filename
                    if count_files_matched:
                        filename = '[%d] %s' % (counter, filename)
                        counter += 1
                else:
                    # Single file grep, rather than recursive search
                    # do not want filename
                    filename = ''
                if use_color:
                    if not zebra_color_filenames:
                        filename = color_filename + filename + color_reset
                    else:
                        # zebra_color_filenames  NOTE requires counter
                        if counter % 2:
                            filename = color_filename_zebra + filename + color_reset
                        else:
                            filename = color_filename + filename + color_reset
                if only_filename_results:
                    print('%s' % (filename, ))
                    continue
                if ripgrep:
                    print('%s' % (filename, ))
                for result_hit_line, result_hit_text in hit_detail:
                    if use_color:
                        """
                        if not search_is_regex:
                            result_hit_text = result_hit_text.replace(search_term, color_searchhit + search_term + color_reset)  # no longer needed search func does highlight
                        """
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
    except (SearchCancelled, KeyboardInterrupt) as info:
        print('search cancelled', info)
    finally:
        stdout_restore()
    if options.time:
        end_time = time.time()
        search_time = end_time - start_time
        print('Query time: %.2f seconds' % search_time)
    if count_files_matched:
        return result


def main(argv=None):
    if argv is None:
        argv = sys.argv

    if is_py3:
        stream_encoding = 'utf-8'  # FIXME hard coded

    usage = "usage: %prog [options] [search_term] [dir_name_or_filename1] [dir_name_or_filename2...]"
    # TODO mix of snake_case and hypen-case flags/options; list-formats/list_formats and note-root/note_root
    parser = OptionParser(usage=usage, version="%%prog %s" % puren_tonbo.__version__,
                            description='A grep/ripprep like tool. Use "--" to specify search terms that start with a hype "-"')
    parser.add_option("--list-formats", help="Which encryption/file formats are available", action="store_true")
    parser.add_option("--note-root", help="Directory of notes, or dir_name_or_filename1.... will pick up from config file and default to '.'")
    parser.add_option("-i", "--ignore_case", help="Case insensitive search", action="store_true")
    parser.add_option("-y", "--find-only-filename", "--find_only_filename", help="Only search filenames, do not search file content", action="store_true")  # TODO see -g options for rg-like tools
    parser.add_option("-l", "--files-with-matches", "--files_with_matches", help="Only print filenames, do not display matches in file content", action="store_true")
    parser.add_option("-r", "--regex_search", help="Treat search term as a regex (default is to treat as literal word/phrase)", action="store_true")
    parser.add_option("-n", "--line_numbers", help="Print line number with output lines (grep format only)", action="store_true")  # grep uses hypen; --line-number
    parser.add_option("-s", "--search_term", help="Term to search for, if omitted, [search_term] is used instead")
    parser.add_option("-c", "--codec", help="Override config file encoding (can be a list TODO format comma?)")
    parser.add_option("-p", "--password", help="password, if omitted and OS env PT_PASSWORD is set use that, next checks keyring, if missing prompt")
    parser.add_option("-P", "--password_file", help="file name where password is to be read from, trailing blanks are ignored")
    parser.add_option("-t", "--time", action="store_true")
    parser.add_option("-e", "--search_encrypted", help='Search encrypted files (default false)', action="store_true")
    parser.add_option("-k", "--search_encrypted_only", help='Search encrypted files (default false)', action="store_const", const='only', dest='search_encrypted')
    parser.add_option("-v", "--verbose", help='Print query search time', action="store_true")
    parser.add_option("--config-file", "--config_file", help="Override config file")
    parser.add_option("--grep", help='Use grep-like output format instead of ripgrep-like', action="store_true")
    parser.add_option("--display-full-path", "--display_full_path", help='Display full/absolute path/URI in results for note filename', action="store_true")
    parser.add_option("--zebra", "--zebra_color_filenames", "--zebra-color-filenames", help='Display alternate filenames with different (zebra) stripe color (note, counts filenames)', action="store_true", dest='zebra_color_filenames')
    """ TODO
    -p, --password=PASSWORD: Password to use for all encrypted notes (if omitted will be prompted for password,
        specifying password at command line can be a security risk as password _may_ be visible in process/task list and/or shell history)
    """
    # TODO add option to use search only encrypted files (i.g. ignore *.txt and *.md files)
    # TODO add option similar to grep -A/B/C for lines of context?

    (options, args) = parser.parse_args(argv[1:])
    #print('%r' % ((options, args),))  # DEBUG
    verbose = options.verbose
    if verbose:
        print('Python %s on %s' % (sys.version.replace('\n', ' - '), sys.platform))
    if options.list_formats:
        puren_tonbo.print_version_info()
        return 0

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

    password = options.password or password_file or os.environ.get('PT_PASSWORD') or puren_tonbo.keyring_get_password() or puren_tonbo.caching_console_password_prompt
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
            usage_error('ERROR: Missing search path/directory')  # should never happen now, here just-in-case

    if options.codec:
        note_encoding = options.codec
    else:
        note_encoding = config['codec']

    use_color = False
    if not sys.stdout.isatty():
        # skips processing for doing highlighting
        use_color = False
    elif colorama:
        # TODO only do below for Windows? looks like it may be a NOOP so may not need a windows check
        try:
            colorama.just_fix_windows_console()
        except AttributeError:
            # older version, for example '0.4.4'
            colorama.init()
        use_color = True
    else:
        if guess_color_available:
            use_color = True


    """
    if options.password:
        password_func = gen_static_password(options.password).gen_func()
    else:
        path_to_search = paths_to_search[0]  # TODO cleanup
        caching_console_password_prompt = gen_caching_get_password(dirname=path_to_search).gen_func()
        password_func = caching_console_password_prompt
    """

    password_func = password

    grep(search_term, paths_to_search, options, use_color, password_func, note_encoding)

    return 0


if __name__ == "__main__":
    sys.exit(main())
