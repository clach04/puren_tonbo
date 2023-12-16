#!/usr/bin/env python
# -*- coding: us-ascii -*-
# vim:ts=4:sw=4:softtabstop=4:smarttab:expandtab
"""Command line interactive tool to recursively Search Puren Tonbo files (plain text and encrypted notes).
Example encryption file formats; Tombo CHI Blowfish files, VimCrypt, AES-256.zip, etc.

    python -m puren_tonbo.tools.ptig -h

TODO delete support (with confirmation)
"""

import copy
import json
import os
from optparse import OptionParser
import pydoc
import shlex
import sys
import subprocess  # TODO replace os.system() - at least for edit
import time

try:
    from cmd2 import Cmd  # version 0.8.9
except ImportError:
    # use stdlib
    from cmd import Cmd

try:
    from puren_tonbo.tools import ptpyvim  # https://github.com/prompt-toolkit/pyvim - pip install pyvim
except ImportError:
    ptpyvim = None

import puren_tonbo
from puren_tonbo import SearchCancelled
from puren_tonbo.tools import ptcat, ptgrep  # FIXME TODO actually use these


is_py3 = sys.version_info >= (3,)
is_win = sys.platform.startswith('win')

# Python pager, do NOT use temporary files - could be used to monkey patch pydoc.pager
def getpager_no_temp_files():
    """Decide what method to use for paging through text.
    Extracted and modified from pydoc.getpager()"""
    if not hasattr(sys.stdin, "isatty"):
        return pydoc.plainpager
    if not hasattr(sys.stdout, "isatty"):
        return pydoc.plainpager
    if not sys.stdin.isatty() or not sys.stdout.isatty():
        return pydoc.plainpager
    if is_win:
        return pydoc.ttypager
    use_pager = os.environ.get('MANPAGER') or os.environ.get('PAGER')
    if use_pager:
        """
        if sys.platform == 'win32': # pipes completely broken in Windows
            return lambda text: tempfilepager(plain(text), use_pager)
        """
        if os.environ.get('TERM') in ('dumb', 'emacs'):
            return lambda text: pydoc.pipepager(plain(text), use_pager)
        else:
            return lambda text: pydoc.pipepager(text, use_pager)
    if os.environ.get('TERM') in ('dumb', 'emacs'):
        return pydoc.plainpager
    # Under windows for each os.system() below will get: The system cannot find the path specified.
    if hasattr(os, 'system') and os.system('(pager) 2>/dev/null') == 0:
        return lambda text: pydoc.pipepager(text, 'pager')
    if hasattr(os, 'system') and os.system('(less) 2>/dev/null') == 0:
        return lambda text: pydoc.pipepager(text, 'less')

    """
    try:
        if hasattr(os, 'system') and os.system('more "%s"' % filename) == 0:  # under unix/linux; "more /dev/null" is a good substitute, without needing temp file writing
            return lambda text: pydoc.pipepager(text, 'more')
        else:
    """
    return pydoc.ttypager

pager = getpager_no_temp_files()

class FakeOptions:  # to match ptgrep (OptParse) options
    display_full_path = True
    count_files_matched = True  # prefix filenames with a number, for easy reference/selection
    ignore_case = False
    regex_search = False
    line_numbers = True
    grep = False  # i.e ripgrep=True
    find_only_filename = False  # set to True to only search on filename
    files_with_matches = False  # set to True to only list filenames (not lines/hits)
    search_encrypted = False  # TODO add away to change this (set...
    search_is_regex = False
    time = True
    use_color = True
    use_pager = False  # ptig specific

    def __init__(self, options=None):
        if options:
            for attribute_name in dir(options):
                if not attribute_name.startswith('_'):
                    attribute_value = getattr(options, attribute_name)
                    setattr(self, attribute_name, attribute_value)
    def __repr__(self):
        return '<%s (%r)>' % (self.__class__.__name__, self.__dict__)


# Extracted (subset) from ptgrep.main()
grep_parser = OptionParser(usage='usage: %prog [options] [search_term]',
                        prog='grep',
                        description='A grep/ripprep like tool. Use "--" to specify search terms that start with a hype "-"')
grep_parser.add_option("-i", "--ignore_case", help="Case insensitive search", action="store_true")
grep_parser.add_option("-y", "--find-only-filename", "--find_only_filename", help="Only search filenames, do not search file content", action="store_true")
grep_parser.add_option("-l", "--files-with-matches", "--files_with_matches", help="Only print filenames that contain matches", action="store_true")
grep_parser.add_option("-r", "--regex_search", help="Treat search term as a regex (default is to treat as literal word/phrase)", action="store_true")
grep_parser.add_option("-e", "--search_encrypted", help='Search encrypted files (default false)', action="store_true")
grep_parser.add_option("-k", "--search_encrypted_only", help='Search encrypted files (default false)', action="store_const", const='only', dest='search_encrypted')
grep_help = grep_parser.format_help()


class CommandPrompt(Cmd):
    def __init__(self, paths_to_search=None, pt_config=None, grep_options=None):  # TODO refactorm too many options and search path is also potentially a dupe
        """If paths_to_search is omitted, defaults to current directory
        """
        Cmd.__init__(self)
        self.bookmarks = {}
        self.cache = None
        self.paths_to_search = []
        #import pdb ; pdb.set_trace()
        paths_to_search = paths_to_search or ['.']
        for note_path in paths_to_search:
            self.paths_to_search.append(os.path.abspath(note_path))  # TODO future warning native file path code
        self.pt_config = pt_config
        self.grep_options = grep_options or FakeOptions()
        self.file_hits = []  # results
        #import pdb ; pdb.set_trace()
        if self.pt_config['ptig'].get('prompt'):
            self.prompt = self.pt_config['ptig']['prompt']
        else:
            if len(self.paths_to_search) == 1:
                str_paths_to_search = self.paths_to_search[0]
                str_paths_to_search = os.path.basename(str_paths_to_search)  # TODO option trim? Other idea is to add template support for prompt config
            else:
                str_paths_to_search = str(self.paths_to_search)  # TODO review
            self.prompt = 'ptig:' + str_paths_to_search + ' '  # Almost never going to be seen, unless config file entry is false/null, '' empty string, 0, etc.
        if self.grep_options.use_color:
            prompt_color, color_reset = ptgrep.color_linenum, ptgrep.color_reset
            self.prompt = prompt_color + self.prompt + color_reset

    def emptyline(self):
        "NOOP - do not repeat last command like cmd.Cmd"
        pass

    def do_exit(self, line=None):
        """Quit/Exit"""
        print("Quitting...")
        return 1
    do_quit = do_exit
    do_bye = do_exit
    do_EOF = do_exit


    def do_ls(self, line=None):
        if line:
            print('Parameters not supported')  # TODO handle and also cwd support
            return
        note_encoding = self.pt_config['codec']
        note_root = self.paths_to_search[0]  # TODO just pick the first one, ignore everthing else
        # for now, ignore line
        #sub_dir = line
        sub_dir = None
        notes = puren_tonbo.FileSystemNotes(note_root, note_encoding)
        dir_list, file_list = notes.directory_contents(sub_dir=sub_dir)
        for x in dir_list:
            print('%s/' % x)
        for x in file_list:
            print('%s' % x)
    do_dir = do_ls

    def do_bookmarks(self, line=None):
        """Bookmark result (filenames), for use with `results` command
Examples:

Show bookmarks
    bookmarks

Set/Create
    bookmark set bookmark_name

Get/lookup
    bookmark get bookmark_name
    bookmark bookmark_name

        """
        if not line:
            # display bookmarks
            bookmark_names = list(self.bookmarks.keys())
            bookmark_names.sort()
            for bookmark_name in bookmark_names:
                print('\t%s' % bookmark_name)
            return
        parsed_line = shlex.split(line)
        if parsed_line[0] == 'set':  # TODO consider "s" as short cut, would mean that bookmarks called "s" would be a special case
            assert len(parsed_line) == 2
            bookmark_name = parsed_line[1]
            self.bookmarks[bookmark_name] = self.file_hits.copy()
        else:
            # assume get
            if len(parsed_line) == 1:
                bookmark_name = parsed_line[0]
            else:
                bookmark_name = parsed_line[1]
            self.file_hits = self.bookmarks[bookmark_name].copy()  # is a copy needed? Safer to do so..
    do_bookmark = do_bookmarks
    do_b = do_bookmarks

    def do_nocache(self, line=None):
        """Disables cache for find and grep
Also see `cache`.
        """
        if line:
            print('params not supported')
            return
        self.cache = None
        print('cache off')

    def do_cache(self, line=None):
        """Caches filenames for searching in memory. Avoids hitting disk to determine which files to search
Also see `nocache`.

Usage:

    cache off
    cache
    cache on

To disable/enable cache.

find (filename) and grep will then no longer determine filenames on disk dynamically but use the cached version.

NOTE on machines with fast CPU and disk (SSD) cache can be slower for some operations (like filename find).

        """
        if line:
            if line == 'off':
                return self.do_nocache()
        note_root = self.paths_to_search[0]  # TODO loop through them all. For now just pick the first one, ignore everthing else
        note_encoding = self.pt_config['codec']
        notes = puren_tonbo.FileSystemNotes(note_root, note_encoding)
        print('cache on')
        self.cache = list(notes.recurse_notes())

    def do_find_foreign(self, line=None):
        """list files not supported by PurenTonbo
        """
        use_color = self.grep_options.use_color
        note_encoding = self.pt_config['codec']
        note_root = self.paths_to_search[0]  # TODO loop through them all. For now just pick the first one, ignore everthing else
        # for now, ignore line
        ignore_folders = self.pt_config['ignore_folders']
        ignore_files = self.pt_config['ignore_file_extensions']
        notes = puren_tonbo.FileSystemNotes(note_root, note_encoding)
        hits = []
        for counter, filename in enumerate(puren_tonbo.find_unsupported_files(note_root, order=puren_tonbo.ORDER_DESCENDING, ignore_files=ignore_files, ignore_folders=ignore_folders), start=1):
            hits.append(filename)
            result_hit_line = '[%d] %s' % (counter, filename)
            if use_color:
                result_hit_line = ptgrep.color_filename + str(result_hit_line) + ptgrep.color_reset
            else:
                result_hit_line = str(result_hit_line)
            print(result_hit_line)

        # TODO catch SearchCancelled, KeyboardInterrupt
        self.file_hits = hits
    do_ff = do_find_foreign

    def do_recent(self, line=None):
        """list recently modified/updated/edited notes, newest at the top.
Optionally specify number of items to list. Defaults to 20.

Examples

    recent
    recent 5
    recent 24
        """
        use_color = self.grep_options.use_color
        number_of_files = 20
        if line:
            try:
                number_of_files = int(line)
            except ValueError:
                print('invalid parameter/number')
                return
        note_encoding = self.pt_config['codec']
        ignore_folders = self.pt_config['ignore_folders']
        note_root = self.paths_to_search[0]  # TODO loop through them all. For now just pick the first one, ignore everthing else
        # for now, ignore line
        #sub_dir = line
        sub_dir = None
        notes = puren_tonbo.FileSystemNotes(note_root, note_encoding)
        hits = []
        for counter, filename in enumerate(notes.recent_notes(number_of_files=number_of_files, order=puren_tonbo.ORDER_DESCENDING, ignore_folders=ignore_folders), start=1):
            hits.append(filename)
            result_hit_line = '[%d] %s' % (counter, filename)
            if use_color:
                result_hit_line = ptgrep.color_filename + str(result_hit_line) + ptgrep.color_reset
            else:
                result_hit_line = str(result_hit_line)
            print(result_hit_line)

        # TODO catch SearchCancelled, KeyboardInterrupt
        self.file_hits = hits

    def do_set(self, line=None):
        """Set variables/options. No params, show variable settings

Examples

    set ic
    set ignorecase
    set noic
    set noignorecase
    set noenc
    set search_encrypted
    set enc
    set enconly
    set search_encrypted_only
    set use_pager
    set no use_pager
    set use_pager=True
    set use_pager=false

""" ## TODO more examples
        # NOTE only sets options in self.grep_options (not self.pt_config, i.e. pt.json)
        # so use_pager can be controlled via set, but not prompt (at least at the moment)
        if line:
            line = line.strip()

        if not line:
            options = self.grep_options
            if options.use_color:
                name_color, value_color, color_reset = ptgrep.color_linenum, ptgrep.color_searchhit, ptgrep.color_reset
            else:
                name_color, value_color, color_reset = '', '', ''
            print('Changeable options:')
            for attribute_name in dir(options):
                if not attribute_name.startswith('_'):
                    attribute_value = getattr(options, attribute_name)
                    #print('\t%s=%s' % (attribute_name, attribute_value))  # TODO consider sorted dict?
                    print('\t%s%s%s=%s%s%s' % (name_color, attribute_name, color_reset, value_color, attribute_value, color_reset))  # TODO consider sorted dict?
            print('')
            print('ptig (config file) options:')
            options = self.pt_config['ptig']
            for attribute_name in options:
                if not attribute_name.startswith('_'):
                    attribute_value = options[attribute_name]
                    #print('\t%s=%s' % (attribute_name, attribute_value))  # TODO consider sorted dict?
                    print('\t%s%s%s=%s%s%s' % (name_color, attribute_name, color_reset, value_color, attribute_value, color_reset))  # TODO consider sorted dict?
            return

        # vim-like case insensitive
        if line in ('ic', 'ignorecase'):
            self.grep_options.ignore_case = True
            print('search now case insensitive')
            return
        if line in ('noic', 'noignorecase'):
            print('search now case sensitive')
            self.grep_options.ignore_case = False
            return

        # pt specific enc - less typing than full
        if line in ('enc', 'search_encrypted'):
            print('search enabled for encrypted files')
            self.grep_options.search_encrypted = True
            return
        if line in ('enconly', 'search_encrypted_only'):
            print('search enabled for encrypted files ONLY')
            self.grep_options.search_encrypted = 'only'
            return
        if line in ('noenc', 'nosearch_encrypted'):
            print('search disabled for encrypted files')
            self.grep_options.search_encrypted = False
            return

        if '=' in line:
            # got some sort of variable=value
            # NOTE This does NOT allow '=' in a value due to the crappy parser used
            """
                set x=3
                set x="3"
                set x="3 "
                set x=3
                set x = 3
                set x=  3
                set x =3
                set x= 3 sdfs
                set x= "3 sdfs"

                set search_encrypted=true
                set password=password
            """
            # so dumb, but quick to write...
            parsed_line = shlex.split(line)
            #print('\t %r' % parsed_line)
            completely_parsed_line = []
            for x in parsed_line:
                if '=' in x:
                    x = x.split('=')
                else:
                    x = [x]
                for y in x:
                    if y:
                        completely_parsed_line.append(y)
            #print('\t\t %r' % completely_parsed_line)
            if len(completely_parsed_line) != 2:
                print('unsupported set operation: %r' % (completely_parsed_line,))
                return
            attribute_name, attribute_value = completely_parsed_line
            # dumb boolean detection/force
            if attribute_value.lower() in ('true', 'false'):
                attribute_value = attribute_value.lower() == 'true'
            setattr(self.grep_options, attribute_name, attribute_value)
            return

        # assume bool flag
        # e.g. set user_pager
        # e.g. set no user_pager
        # TODO handle "set no " with no other arguments
        if line.startswith('no '):
            print('Assume turn OFF bool option')
            setattr(self.grep_options, line[len('no '):].lstrip(), False)
        else:
            print('Assume turn ON bool option')
            setattr(self.grep_options, line, True)
        return

        # TODO set should support prompt change
        print('unsupported set operation')

    def do_results(self, line=None):
        """Redisplay previous filename search results or perform additional search on previous results
Also see `bookmarks` command. Alias `r`

Usage:

    results

Shows last result set.

Usage:

    results find file_name_term
    results grep search_term
    results rg search_term
    r rg search_term

Search previous results for search term.

        """
        if not self.file_hits:
            print('no results')
            return

        if line:
            command, arg, orig_line = self.parseline(line) # NOTE undocumented cmd internal
            #print('%r' % ((command, arg, orig_line),))
            try:
                func = getattr(self, 'do_' + command)
            except AttributeError:
                print('unknown operation')
                return
            try:
                return func(arg, paths_to_search=self.file_hits)
            except TypeError:
                print('operation does not support paths_to_search')
                return

            # TEST assume find
            #self.do_find(line=line, paths_to_search=self.file_hits)
            #self.do_grep(line=line, paths_to_search=self.file_hits)
        for counter, filename in enumerate(self.file_hits, start=1):
            print('[%d] %s' % (counter, filename))
    do_res = do_results
    do_r = do_results

    def do_edit_multiple(self, line=None):
        """edit multiple files from numbers. Also see `edit`. Alias `en`
            en 1,3
            en 1 3
        would send all two files (assuming there are at least 3 hits) to editor
        NOTE can potentially include filenames (assuming no spaces, there is no lexing going on [yet])
        More control than `edit !`
        """
        if line is None:
            return
        line = line.replace(',', ' ')
        filename_list = []
        for entry in line.split():
            filename_list.append(self.validate_result_id(entry))
        self.do_edit(line=None, filename_list=filename_list)
    do_en = do_em = do_editmultiple = do_edit_multiple

    def do_edit(self, line=None, filename_list=None):
        """Edit using external $PT_VISUAL, $VISUAL or $EDITOR, ptig.editor in config file with fall backs if unset.
Also see `edit_multiple` (alias `en`)

If not set:

  1. Microsoft Windows will use file associations.

  2. Linux/Unix will use editor, which under Debian derivatives like
    Ubuntu can be configured via:

        sudo update-alternatives --config editor
        update-alternatives --list editor

To set in config file:

    {
        ....
        "ptig": {
            "editor": "start scite",   # Windows
            "editor": "start gvim",   # Windows
            "editor": "gvim",   # Linux, etc.
            ....
        }
    }

For Windows use "start" so that ptig does NOT wait for editor to exit.
Use ptconfig commandline tool to generate skeleton config.

Usage:

    edit path/filename

    edit n
        where n is an integer number from find/grep search

    edit !
    edit *
    edit all

        """
        filename_list = filename_list or []
        if not filename_list:
            line = self.validate_result_id(line)
            if line is None and filename_list is None:
                return
            filename = line
            if filename == '!':
                filename_list = filename_list or self.file_hits
        else:
            filename = None
        #import pdb; pdb.set_trace()
        # TODO debug "e `" editor got opened, not a valid file should this be caught? see validate_result_id() which currently does NOT validate filenames (callers do that later)
        editor = os.environ.get('PT_VISUAL') or os.environ.get('VISUAL') or os.environ.get('EDITOR') or self.pt_config['ptig'].get('editor')
        if not filename_list:
            if puren_tonbo.is_encrypted(filename):
                # Prompt for password for editors that won't prompt
                # TODO how to indicate whether ptig should prompt (and set environment variable)?
                # FIXME if a bad password is used, the same bad password will be used on next edit (unless cat is issued first)
                password_func = self.grep_options.password or puren_tonbo.caching_console_password_prompt
                if callable(password_func):
                    password = password_func('Password for %s' % filename)
                else:
                    password = password_func
                if password and  isinstance(password, bytes):
                    password = password.decode('us-ascii')
                os.environ['PT_PASSWORD'] = password  # Python 3.10.4 only supports strings for environment variables
        if not editor:
            # TODO pickup from config file
            # default a sane editor
            if is_win:
                # NOTE this only works for a single file
                editor = 'start "ptig"'  # Let Windows figure it out based on file extension
            else:
                # Assume Linux
                editor = 'editor' # TODO full path "/usr/bin/editor" -> /etc/alternatives/editor, or xdg-open, jaro, etc.
        # TODO what about password? For now let external tool handle that. To support tools that don't support password, need to pipe in plain text
        print('Using: %s' % editor)
        print('file: %s' % filename)

        # TODO edit all result filenames
        #   e !
        #   e *
        #   e all
        if filename_list:  # TODO review
            filename = '"' + '" "'.join(filename_list) + '"'  # each filename wrapped in double quotes
            # TODO password prompt? above is_encrypted() call won't work
            # NOTE under Windows only will work for third party text editor/viewers
            #   notepad will not handle this
            #print('%r' % filename_list)  # DEBUG
            #print('%s %s' % (editor, filename))  # DEBUG
            os.system('%s %s' % (editor, filename))  # already escaped list
        else:
            os.system('%s "%s"' % (editor, filename))
        print('file: %s' % filename)
        print('To display previous results issue: results')
    do_e = do_edit

    if ptpyvim:
        def do_pyvim(self, line=None):
            """Edit using built in (vim-like) ptpyvim editor
Also see `edit`
Aliases; vim, vi
            """
            line = self.validate_result_id(line)
            if line is None:
                return
            in_filename = line
            #import pdb; pdb.set_trace()
            if not self.grep_options.password:
                self.grep_options.password = puren_tonbo.caching_console_password_prompt(filename=in_filename, reset=True)  # TODO not for .txt and .md files
            ptpyvim.edit([in_filename], password=self.grep_options.password)
        do_ptpyvim = do_pyvim
        do_vim = do_pyvim
        do_vi = do_pyvim

    def validate_result_id(self, line=None):
        """validate that either have:
            * a line number (index into previous results) and that it's valid
            * or assume a filename (which is NOT validated)

        Returns path/filename.

        For numbers, 0 (zero) will view last hit.
        """
        if line == '':
            print('no parameter given')
            return None
        try:
            file_number = int(line)
            if not self.file_hits:
                print('no results')
                return None
            if file_number > len(self.file_hits):
                print('result file %d invalid' % file_number)
                return None
            line = self.file_hits[file_number - 1]
        except ValueError:
            # line contains filename, but filename may not exist
            note_encoding = self.pt_config['codec']
            if is_win:
                return line  # skip for now
            # attempt to validate
            if line.startswith('/'):
                return line  # absolute path, for now supported as pass-thru (and skip directory jail)
            # Assume relative path, enforce
            for note_root in self.paths_to_search:
                notes = puren_tonbo.FileSystemNotes(note_root, note_encoding)
                fullpath = notes.native_full_path(line)  # relative2abspath()
                if os.path.exists(fullpath):
                    return fullpath
            # so file does not exist, assume new file in first directory
            note_root = self.paths_to_search[0]
            notes = puren_tonbo.FileSystemNotes(note_root, note_encoding)
            fullpath = notes.native_full_path(line)
            return fullpath
        return line

    def do_opendir(self, line=None):
        """Given a filename (or result index number), open native directory file browser.
For numbers, 0 (zero) will view last hit.
        """
        line = self.validate_result_id(line)
        note_root = os.path.dirname(line)
        print('line: %r' % line)
        print('note_root: %s' % note_root)
        if line is None:
            return

        ret = subprocess.Popen([self.pt_config['ptig']['file_browser'], note_root]).wait()
        #print('ret: %r' % ret)  # always 1?

    do_od = do_opendir

    def do_cat(self, line=None):
        """cat/type/view file. Takes either a number or filename.
For numbers, 0 (zero) will view last hit. See results command.
See use_pager option, e.g. set use_pager=True
Also see `edit`
        """
        line = self.validate_result_id(line)
        if line is None:
            return
        # TODO display file name (head and tail?)
        note_encoding = self.pt_config['codec']
        in_filename = os.path.basename(line)
        note_root = os.path.dirname(line)
        password_func = self.grep_options.password or puren_tonbo.caching_console_password_prompt

        # TODO refactor ptcat
        notes = puren_tonbo.FileSystemNotes(note_root, note_encoding)
        try:
            data = notes.note_contents(in_filename, password_func)
            #print('%r' % data)
            if self.grep_options.use_pager:
                pager(data)  # TODO bytes instead of string?  -- or simply refactor ptcat and call that....
            else:
                print('%s' % data)  # TODO bytes instead of string?  -- or simply refactor ptcat and call that....
        except (puren_tonbo.PurenTonboIO, puren_tonbo.UnsupportedFile) as info:
            message = 'Error opening file %r' % info
            if self.grep_options.use_color:
                message = ptgrep.color_error + message + ptgrep.color_reset
            print('%s' % message)
        except KeyboardInterrupt:
            # TODO color support?
            message = 'search cancelled'
            if self.grep_options.use_color:
                message = ptgrep.color_error + message + ptgrep.color_reset
            print('%s' % message)

    do_c = do_cat  # shortcut to save typing
    do_type = do_cat  # Windows alias

    def default(self, line=None):
        try:
            file_number = int(line)
            self.do_cat(line)
        except ValueError:
            Cmd.default(self, line)  # Super...

    def do_grep(self, line=None, paths_to_search=None):
        # Doc comment updated in code; CommandPrompt.do_grep.__doc__ - TODO list aliases?
        if not line:
            print('Need a search term')  # TODO show help?
            return
        options = copy.copy(self.grep_options)
        if line[0] != '-':
            search_term = line  # TODO option to strip (default) and retain trailing/leading blanks
        else:
            parsed_line = shlex.split(line)
            (grep_parser_options, grep_parser_args) = grep_parser.parse_args(parsed_line)
            if not grep_parser_args:
                print('Need a search term')  # TODO show help?
                return
            if len(grep_parser_args) != 1:
                print('Too many search terms (use quotes)')  # TODO show help?
                return
            search_term = grep_parser_args[0]
            # TODO consider a loop of get /set attr
            options.ignore_case = options.ignore_case or grep_parser_options.ignore_case
            options.find_only_filename = options.find_only_filename or grep_parser_options.find_only_filename
            options.files_with_matches = options.files_with_matches or grep_parser_options.files_with_matches
            options.regex_search = options.regex_search or grep_parser_options.regex_search
            options.search_encrypted = options.search_encrypted or grep_parser_options.search_encrypted
        if not search_term:
            print('Need a search term')  # TODO show help?
            return
        paths_to_search = paths_to_search or self.cache or self.paths_to_search

        note_encoding = self.pt_config['codec']

        line_numbers = options.line_numbers

        password_func = options.password or puren_tonbo.caching_console_password_prompt
        use_color = options.use_color

        self.file_hits = ptgrep.grep(search_term, paths_to_search, options, use_color, password_func, note_encoding)

    do_g = do_grep  # shortcut to save typing
    do_rg = do_grep  # ripgrep alias for convenience

    # TODO refactor to call do_grep() to remove code duplication
    def do_find(self, line=None, paths_to_search=None):
        """find to pathname/filename, same as grep but only matches directory and file names"""
        # TODO -i, and -r (regex) flag support rather than using config variables?
        search_term = line  # TODO option to strip (default) and retain trailing/leading blanks
        paths_to_search = paths_to_search or self.cache or self.paths_to_search
        options = self.grep_options

        note_encoding = self.pt_config['codec']

        line_numbers = options.line_numbers

        password_func = options.password or puren_tonbo.caching_console_password_prompt
        use_color = options.use_color
        grep_options = FakeOptions(options)
        grep_options.find_only_filename = True  # same as grep but filenames only
        grep_options.search_encrypted = True  # TODO review, this seems like a reasonable default and password not needed for name matching

        self.file_hits = ptgrep.grep(search_term, paths_to_search, grep_options, use_color, password_func, note_encoding)
    do_f = do_find  # shortcut to save typing

    def do_config(self, line=None):
        """show puren tonbo config"""
        config_filename = puren_tonbo.get_config_path()
        if os.path.exists(config_filename):
            config_filename_exists = True
        else:
            config_filename_exists = False
        print('config_filename %s (%s)' % (config_filename, 'exists' if config_filename_exists else 'does not exist'))
        print('%s' % json.dumps(self.pt_config, indent=4, sort_keys=True))  # TODO color support
    do_ptconfig = do_config

    def do_version(self, line=None):
        """show version/info"""
        puren_tonbo.print_version_info()
    do_ver = do_version
    do_info = do_version

try:
    CommandPrompt.do_grep.__doc__ = grep_help
except AttributeError:
    # AttributeError: attribute '__doc__' of 'instancemethod' objects is not writable
    pass  # assumue Python 2.7

def main(argv=None):
    if argv is None:
        argv = sys.argv

    usage = "usage: %prog [options] [search_term] [dir_name_or_filename1] [dir_name_or_filename2...]"
    parser = OptionParser(usage=usage, version="%%prog %s" % puren_tonbo.__version__)
    parser.add_option("-c", "--codec", help="Override config file encoding (can be a list TODO format comma?)")
    parser.add_option("--config-file", "--config_file", help="Override config file")
    parser.add_option("--note-root", help="Directory of notes, or dir_name_or_filename1.... will pick up from config file and default to '.'")
    parser.add_option("-p", "--password", help="password, if omitted and OS env PT_PASSWORD is set use that, next checks keyring, if missing prompt")
    parser.add_option("-P", "--password_file", help="file name where password is to be read from, trailing blanks are ignored")

    (options, args) = parser.parse_args(argv[1:])
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

    #import pdb ; pdb.set_trace()
    config = puren_tonbo.get_config(options.config_file)
    if options.note_root:
        relative_paths_to_search = [options.note_root]
    else:
        relative_paths_to_search = args or [config.get('note_root', '.')]
        if not relative_paths_to_search:
            usage_error('ERROR: Missing search path/directory')  # should never happen now, here just-in-case
    paths_to_search = [os.path.abspath(x) for x in relative_paths_to_search]
    config['note_root'] = paths_to_search  # ensure config updated with path(s) override from command line

    if options.codec:
        note_encoding = options.codec
    else:
        note_encoding = config['codec']

    if is_win:
        if ptgrep.colorama:
            # TODO only do below for Windows? looks like it may be a NOOP so may not need a windows check
            try:
                ptgrep.colorama.just_fix_windows_console()
            except AttributeError:
                # older version, for example '0.4.4'
                ptgrep.colorama.init()
            use_color = True
        else:
            use_color = False
    else:
        use_color = True
    options.use_color = use_color
    options.password = password
    grep_options = FakeOptions(options)
    grep_options.use_color = use_color  # redundant?

    ptig_options = config['ptig']
    grep_options.use_pager = ptig_options['use_pager']  # TODO revisit this, should ptig pick this up from pt_config directly instead of grep_options/Fakeoptions - see do_set() comments on grep config versus pt_config

    interpreter = CommandPrompt(paths_to_search=paths_to_search, pt_config=config, grep_options=grep_options)
    interpreter.onecmd('version')
    for command in ptig_options.get('init', []):
        interpreter.onecmd(command)
    interpreter.cmdloop()

    return 0


if __name__ == "__main__":
    sys.exit(main())
