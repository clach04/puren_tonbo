#!/usr/bin/env python
# -*- coding: us-ascii -*-
# vim:ts=4:sw=4:softtabstop=4:smarttab:expandtab
"""Command line interactive tool to recursively Search Puren Tonbo files (plain text and encrypted notes).
Example encryption file formats; Tombo CHI Blowfish files, VimCrypt, AES-256.zip, etc.

    python -m puren_tonbo.tools.ptig -h

TODO delete support (with confirmation)
"""

import copy
import datetime
import json
import os
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

try:
    import percol  # percolator https://github.com/clach04/percolator/
    import percol.actions
    import percol.command
    import percol.finder
except ImportError:
    percol = None

import puren_tonbo
from puren_tonbo import SearchCancelled
from puren_tonbo.tools import ptcat, ptgrep  # FIXME TODO actually use these


is_py3 = sys.version_info >= (3,)
is_win = sys.platform.startswith('win')

# Python pager, do NOT use temporary files - could be used to monkey patch pydoc.pager
def getpager_no_temp_files():
    """Decide what method to use for paging through text.
    Extracted and modified from pydoc.getpager()
    Under Windows have to issue: space then enter which is less than ideal. Consider  https://pypi.org/project/pypager/ https://pypi.org/project/PrintWithPager/ https://github.com/zaneb/autopage
    """
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
    zebra_color_filenames = True  # (note, use_color=True) every other filename in search results use a different background color. Control: set no zebra_color_filenames / set zebra_color_filenames
    ignore_case = False
    regex_search = False
    line_numbers = True
    grep = False  # i.e ripgrep=True
    find_only_filename = False  # set to True to only search on filename
    files_with_matches = False  # set to True to only list filenames (not lines/hits)
    search_encrypted = False  # TODO add away to change this (set...
    search_is_regex = False
    time = True
    use_color = True  # TODO NO_COLOR https://no-color.org/ (also initial config creation)
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
# FIXME refactor ptgrep to have a shared, reusable parser and use here. E.g. would add support for -t
grep_parser = ptgrep.MyParser(usage='usage: %prog [options] [search_term]',
                        prog='grep',
                        description=ptgrep.ptgrep_description,
                        epilog =ptgrep.ptgrep_examples
                    )
grep_parser.add_option("-i", "--ignore_case", help="Case insensitive search", action="store_true")
grep_parser.add_option("-y", "--find-only-filename", "--find_only_filename", help="Only search filenames, do not search file content", action="store_true")
grep_parser.add_option("-l", "--files-with-matches", "--files_with_matches", help="Only print filenames that contain matches", action="store_true")
grep_parser.add_option("-r", "--regex_search", help="Treat search term as a regex (default is to treat as literal word/phrase)", action="store_true")
grep_parser.add_option("-e", "--search_encrypted", help='Search encrypted files (default false)', action="store_true")
grep_parser.add_option("-k", "--search_encrypted_only", help='Search encrypted files (default false)', action="store_const", const='only', dest='search_encrypted')
grep_help = grep_parser.format_help()

class FakeMethodEdit(object):
    def __init__(self, name, parent):
        self.name = name
        self.parent = parent

    def __call__(self, *args, **kwargs):
        line = args[0]
        editor = self.parent.pt_config['ptig']['editors'][self.name]
        self.parent.do_edit(line, editor=editor)

def zebra_stripe(line, use_color=False, use_zebra_color_filenames=False, line_counter=1, color_filename=ptgrep.color_filename, color_filename_zebra=ptgrep.color_filename_zebra, color_reset=ptgrep.color_reset):  # FIXME rename
    """Optionally zebra-stripe alternative lines
    """
    if use_color:
        if use_zebra_color_filenames and line_counter % 2:
            color_prefix = color_filename_zebra
        else:
            color_prefix = color_filename
        line = color_prefix + str(line) + color_reset
    else:
        line = str(line)
    return line

class CommandPrompt(Cmd):
    def __init__(self, paths_to_search=None, pt_config=None, grep_options=None):  # TODO refactorm too many options and search path is also potentially a dupe
        """If paths_to_search is omitted, defaults to current directory
        """
        Cmd.__init__(self)
        self.bookmarks = {}
        self.cache = None
        self.paths_to_search = []
        self.paths_to_search_instances = []
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

    def do_crash_debug(self, line=None):
        """Force a crash for debugging"""
        0 / 0

    def do_exit(self, line=None):
        """Quit/Exit"""
        print("Quitting...")
        return 1
    do_quit = do_exit
    do_bye = do_exit
    do_EOF = do_exit

    def do_fts_index(self, line=None):
        """Created index for full text search FTS
            fts_index [enc]
        """
        if line:
            if line != 'enc':
                print('Parameters not supported')  # TODO handle and also cwd support
                return
        note_encoding = self.pt_config['codec']
        password_func = None  # no password, will not attempt to index files that need passwords    #FIXME include encrypted option
        if line == 'enc':
            # index files that need passwords, using regular password prompt/caching
            # NOTE CRTL-c is not handled the same way for index as it is for cat/grep-searching
            password_func = self.grep_options.password or puren_tonbo.caching_console_password_prompt

        self.paths_to_search_instances = []
        for note_root in self.paths_to_search:
            notes = puren_tonbo.FileSystemNotes(note_root, note_encoding)
            # FIXME handle password from environment, e.g. env PT_PASSWORD=password (keyring)
            # FIXME handle cancel from password prompt
            notes.fts_index(get_password_callback=password_func)
            self.paths_to_search_instances.append(notes)

    def do_fts_search(self, line=None):
        """Perform a Full Text Search (fts), using sqlite3 FTS syntax
Usage:
    fts_search TERM_OR_QUERY
    fts_search king OR frog OR hares
    fts_search frog AND king
    fts_search frog NOT king
    fts_search filename:frog
    fts_search filename:frog AND constitution

NOTE requires fts_index to have been issued.
"""
        # this is temporary, ideally fts should be callable from the regular search interface - self.file_hits needs setting up
        if self.grep_options.use_color:
            highlight_text_start, highlight_text_stop = ptgrep.color_linenum, ptgrep.color_reset
            highlight_text_start, highlight_text_stop = ptgrep.color_searchhit, ptgrep.color_reset
        else:
            highlight_text_start, highlight_text_stop = None, None  # revisit this

        if not line:
            error_message = '\nNeed a search term!\n'
            if highlight_text_start:
                error_message = highlight_text_start + error_message + highlight_text_stop
            print(error_message)
            print('%s' % self.do_fts_search.__doc__)
            return

        if not self.paths_to_search_instances:
            error_message = '\nNo FTS index, issue: fts_index\n'
            if highlight_text_start:
                error_message = highlight_text_start + error_message + highlight_text_stop
            print(error_message)
            print('%s' % self.do_fts_search.__doc__)
            return


        if ' and ' in line or ' or 'in line or ' not ' in line:
            if highlight_text_start:
                and_or_warning_message = highlight_text_start + 'WARNING' + highlight_text_stop + ' or/and/not detected, SQLite3 FTS5 expects upper case'
            else:
                and_or_warning_message = 'WARNING or/and/not detected, SQLite3 FTS5 expects upper case'
        else:
            and_or_warning_message = None
        # warn at start and end
        if and_or_warning_message:
            print(and_or_warning_message)

        # TODO time and report, counts and elapsed time
        ripgrep_outout_style = False  # file, newline, line_number:hit
        ripgrep_outout_style = True  # grep-style; filename:line_number:hit  # FIXME / TODO config option needed
        self.file_hits = []
        for notes in self.paths_to_search_instances:
            index_lines = notes.fts_instance.index_lines
            for counter, hit in enumerate(notes.fts_search(line, highlight_text_start=highlight_text_start, highlight_text_stop=highlight_text_stop), start=1):
                #print('hit %r' % (hit,) )
                #print('%s:%s' % hit)
                filename, filename_highlighted, note_text, size = hit
                """
                # display_full_path - assume True
                if len(self.paths_to_search) == 1:
                    filename = os.path.join(self.paths_to_search[0], filename)  # or store full pathname in database at index time...
                """
                self.file_hits.append(filename)  # not sure how this can work for multi dir search - nor for "results" directive as parent dir is lost
                if self.grep_options.use_color:
                    filename = ptgrep.color_filename + filename + ptgrep.color_reset

                note_text = note_text.replace('\n', ' ')  # TODO consider using .. or some user configurable replacement
                # NOTE filename_highlighted unused
                size_str = '%dKb' % (size / 1024,)  # FIXME human readable size conversion
                if ripgrep_outout_style:
                    print('[%d] %s %s' % (counter, filename, size_str))
                    if index_lines:
                        print('%s' % (note_text,))  # FIXME color support
                    else:
                        print('??:%s' % (note_text,))
                else:
                    # grep-style
                    print('[%d] %s:%s -- %s' % (counter, filename, note_text, size_str))  # unknown line number - depending on index_lines
        if and_or_warning_message:
            print(and_or_warning_message)
    do_fts = do_fts_search

    def do_ls(self, line=None):
        # TODO autocomplete
        # TODO cwd/chdir support
        # TODO show file size and timestamps
        #import pdb; pdb.set_trace()
        if line != '.':
            line = self.validate_result_id(line)
        if line is None:
            # assume current directory (for now, that means root directory)
            line = '.'

        #sub_dir = os.path.dirname(line)  # similar open to opendir - but for directory listings, i.e. can NOT ls/dir a single file (future TODO?)
        sub_dir = line
        note_encoding = self.pt_config['codec']
        note_root = self.paths_to_search[0]  # FIXME handle multiple note dirs, read and new do. TODO just pick the first one, ignore everthing else
        notes = puren_tonbo.FileSystemNotes(note_root, note_encoding)
        # TODO handle; puren_tonbo.PurenTonboIO: outside of note tree root? no need, handled by validate_result_id()
        # FIXME/TODO results list with numbers?
        dir_list, file_list = notes.directory_contents(sub_dir=sub_dir)
        # TODO color options for:
        #   directories
        #   plain text / raw notes
        #   encrypted
        #   optionally show unsupported files?
        # TODO multi-column results
        for x in dir_list:
            x = os.path.join(sub_dir, x)  # TODO notes API call instead?
            print('%s/' % x)
        for x in file_list:
            x = os.path.join(sub_dir, x)  # TODO notes API call instead?
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
        use_zebra_color_filenames = self.grep_options.zebra_color_filenames
        color_filename_zebra = ptgrep.color_filename_zebra
        color_reset = ptgrep.color_reset
        color_filename = ptgrep.color_filename
        for counter, filename in enumerate(notes.recent_notes(number_of_files=number_of_files, order=puren_tonbo.ORDER_DESCENDING, ignore_folders=ignore_folders), start=1):
            hits.append(filename)
            result_hit_line = '[%d] %s' % (counter, filename)
            result_hit_line = zebra_stripe(result_hit_line, use_color=use_color, color_filename=color_filename, use_zebra_color_filenames=use_zebra_color_filenames, line_counter=counter, color_filename_zebra=color_filename_zebra, color_reset=color_reset)  # FIXME param names
            print('%s' % (result_hit_line,))

        # TODO catch SearchCancelled, KeyboardInterrupt
        self.file_hits = hits
    do_mru = do_recent  # Most Recently Used

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
                    attribute_value = repr(attribute_value)  # DEBUG, alternative hack stdout like in ptgrep()
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
        use_color = self.grep_options.use_color
        use_zebra_color_filenames = self.grep_options.zebra_color_filenames
        color_filename_zebra = ptgrep.color_filename_zebra
        color_reset = ptgrep.color_reset
        color_filename = ptgrep.color_filename
        for counter, filename in enumerate(self.file_hits, start=1):
            result_hit_line = '[%d] %s' % (counter, filename)
            result_hit_line = zebra_stripe(result_hit_line, use_color=use_color, color_filename=color_filename, use_zebra_color_filenames=use_zebra_color_filenames, line_counter=counter, color_filename_zebra=color_filename_zebra, color_reset=color_reset)  # FIXME param names
            print('%s' % (result_hit_line,))
    do_res = do_results
    do_r = do_results

    def do_fzf(self, line=None):
        # TODO docs, Windows testing, help (multi-select)
        # Windows works with windows-curses installed and percol syslog "fix"
        # TODO Selecting multiple candidates options. Ctrl-Space does not work out of box (under Windows) percol.command.toggle_mark_and_next()
        # checkout keymap- what other key bindings are there
        # ctrl-t works great for toggle if manually declared
        # TODO regex option for this
        # TODO cancel - ctrl-c doesn't abort it picks selected
        if not percol:
            print('percol missing, required for fuzzy fine')
            return

        file_and_path_names = self.file_hits
        if not file_and_path_names:
            print('no results')
            return

        with percol.Percol(
                finder=percol.finder.FinderMultiQueryString,  # what's the difference between finder and action_finder? I think this is a no-op
                actions=[percol.actions.no_output],
                descriptors={'stdin': None, 'stdout': None, 'stderr': None},
                candidates=iter(file_and_path_names)) as p:
            p.import_keymap({
                'C-a': lambda percol: percol.command.toggle_mark_all(),  # invert selection on screen
                'C-c': lambda percol: percol.cancel(),  # NOTE need to check exit/result code - same as built-in support
                #'Escape': lambda percol: percol.cancel(),  # NOTE need to check exit/result code - Esc/Escape does NOT work bug https://github.com/mooz/percol/issues/56

                'C-t': lambda percol: percol.command.toggle_mark_and_next(),  # works great, Ctrl-t now togles multi-select - same as Midnight Commander
                #'C-SPACE': lambda percol: percol.command.toggle_mark_and_next(),  # nope, built in (expected) C-SPC also does not work under Windows. TODO debug Percol bug https://github.com/mooz/percol/issues/120
                })
            # NOTE do not attempt any stdio in this block
            exit_code = p.loop()  # cancel causes failure on later calls - see bug https://github.com/mooz/percol/issues/122
            #exit_code = p.cancel_with_exit_code()  # straight up fails first time
            #exit_code = p.finish_with_exit_code(1)  # straight up fails first time
        results = p.model_candidate.get_selected_results_with_index()
        if exit_code == 0:
            self.file_hits = [r[0] for r in results]
            self.do_results()
        else:
            print('fzf interactive filter cancelled')

    def do_new(self, line=None):
        """create a new note/file

            new filename
            new filename.txt
        """
        # TODO check for same filename, different file type
        # TODO check for similar filenames and offer confirmation/file-selection
        # TODO off fzf directory name location selection
        if not line:
            print('Missing parameter')  # TODO include/dump __doc__
            return
        filename = line.strip()  # assume a single path/filename

        # first existence check
        if os.path.exists(filename):  # FIXME this is limited to native file system
            print('%s already exists' % filename)
            return

        note_encoding = self.pt_config['codec']
        password_or_password_func = self.grep_options.password or puren_tonbo.caching_console_password_prompt

        base_filename = os.path.basename(filename)  # FIXME this is **probably** limited to native file system

        # TODO refactor and add explict support to validate_result_id() to validate path for new files (i.e. path should exist)
        #import pdb; pdb.set_trace()
        validated_filename = self.validate_result_id(filename)
        #print(validated_filename)  # TODO log.debug
        if not validated_filename:
            return

        # second existence check
        if os.path.exists(validated_filename):  # FIXME this is limited to native file system
            print('%s already exists' % validated_filename)
            return

        handler_class = puren_tonbo.filename2handler(base_filename, default_handler=puren_tonbo.RawFile)

        #if password is None and puren_tonbo.is_encrypted(base_filename):
        if handler_class.needs_key:  # puren_tonbo.is_encrypted(base_filename)
            # code not needed if calling note_contents_save() instead
            #print('DEBUG will need password')  # TODO log.debug
            if callable(password_or_password_func):
                password_or_password_func = password_or_password_func(filename=validated_filename, reset=False)  # TODO want get password with validation (double entry for confirmation)

        handler = handler_class(key=password_or_password_func)
        file_extension = ''
        for extension in handler_class.extensions:
            if base_filename.endswith(extension):
                base_filename = base_filename[:-len(extension)]
                file_extension = extension
                break
        #print('file_extension %s' % file_extension)  # TODO log.debug
        if not file_extension:
            file_extension = handler_class.extensions[0]
            validated_filename = validated_filename + file_extension
        # print('file_extension %s' % file_extension)  # TODO log.debug
        # print('handler_class %r' % handler_class)  # TODO log.debug
        # print('handler %r' % handler)  # TODO log.debug

        # third existence check, with potentially added on file extension
        #import pdb; pdb.set_trace()
        if os.path.exists(validated_filename):  # FIXME this is limited to native file system
            print('%s already exists' % validated_filename)
            return

        plain_str = '%s\n\n%s\n' % (base_filename, datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
        #print('DEBUG %s contents: %s' % (validated_filename, plain_str))  # TODO log.debug
        # note_contents_save_native_filename()
        # note_contents_save_filename(note_text, filename=None, original_filename=None, folder=None, handler=None, dos_newlines=True, backup=True, use_tempfile=True, note_encoding='utf-8', filename_generator=FILENAME_FIRSTLINE):
        #notes = puren_tonbo.FileSystemNotes(note_root, note_encoding)
        #data = notes.note_contents(in_filename, password_func)
        # def note_contents_save(self, note_text, sub_dir=None, filename=None, original_full_filename=None, get_pass=None, dos_newlines=True, backup=True):

        final_filename = puren_tonbo.note_contents_save_filename(plain_str, filename=validated_filename, handler=handler)  # TODO note_encoding missing, filename_generator=None?  # FIXME native only
        self.file_hits = [final_filename]
        self.do_results()  # display
        # TODO add single filename into result list so it can be used in recent/edit 1 command


    def do_edit_multiple(self, line=None):
        """edit multiple files from numbers. Also see `edit`. Alias `en`
            en 1,3
            en 1 3
        would send all two files (assuming there are at least 3 hits) to editor
        NOTE can potentially include filenames (assuming no spaces, there is no lexing going on [yet])
        More control than `edit !`
        """
        if not line:
            return
        #import pdb; pdb.set_trace()
        line = line.replace(',', ' ')  # FIXME TODO this will NOT handle paths with spaces :-(
        filename_list = []
        for entry in line.split():
            validated_entry = self.validate_result_id(entry)
            if validated_entry:
                filename_list.append(validated_entry)
            else:
                print('Ignoring invalid %r' % entry)
        if filename_list:
            self.do_edit(line=None, filename_list=filename_list)
        else:
            print('no results')
            return None

    do_en = do_em = do_editmultiple = do_edit_multiple

    """
    # does not work
    def do_customedit(self, line=None):
        import pdb; pdb.set_trace()
        f_code = sys._getframe().f_code
        this_function_name = sys._getframe().f_code.co_name  # this is always do_customedit() :-(
        print(this_function_name)
        print(sys._getframe().f_code)
        # idea is to then pass in editor
        editor = None
        self.do_edit(line, editor=editor)
    """

    def do_edit(self, line=None, filename_list=None, editor=None):
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
            #print('DEBUG line %r' % line)
            line = self.validate_result_id(line)
            if line is None and not filename_list:  # NOTE filename_list check redundant here in this block
                return
            filename = line
            if filename == '!':
                filename_list = filename_list or self.file_hits
        else:
            filename = None  # ignore filename if a filename_list is passed in
        #import pdb; pdb.set_trace()
        # TODO debug "e `" editor got opened, not a valid file should this be caught? see validate_result_id() which currently does NOT validate filenames (callers do that later)
        editor = editor or os.environ.get('PT_VISUAL') or os.environ.get('VISUAL') or os.environ.get('EDITOR') or self.pt_config['ptig'].get('editor')
        # NOTE no attempt to use note_root, uses path as-is.
        # NOTE no need to double quote for spaces, if spaces are present will have problems - TODO add double quote removal
        # FIXME validate_result_id() needed - alternatives either implement from scratch or use FileSystemNotes.abspath2relative() / FileSystemNotes.native_full_path()
        if not filename_list:
            if puren_tonbo.is_encrypted(filename):
                # Prompt for password for editors that won't prompt
                # TODO how to indicate whether ptig should prompt (and set environment variable)?
                # FIXME if a bad password is used, the same bad password will be used on next edit (unless cat is issued first)
                password_func = self.grep_options.password or puren_tonbo.caching_console_password_prompt
                if callable(password_func):
                    password = password_func('Password for %s' % filename, for_decrypt=True)
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
            command_to_run = '%s "%s"' % (editor, filename)
            #print('DEBUG system: %r' % command_to_run)  # TODO debug log
            #print('DEBUG system: %s' % command_to_run)
            os.system(command_to_run)  # TODO see TODO earlier in file
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
        """validate a line, one of:
            1. a line number (index into previous results) and that it's valid
            2. or assume a filename (which is NOT validated)
            3. pass through value for multi/"all", one of; !, *, all

        TODO add calling option to raise error (or be silent, current behavior)
        TODO consider list of filenames support? See do_edit_multiple()
        Returns path/filename.

        For numbers, 0 (zero) will view last hit.
        """
        if line == '':
            print('no parameter given')
            return None
        elif line in ('!', '*', 'all'):
            return line
        try:
            file_number = int(line)
            if not self.file_hits:
                print('no results')  # TODO add silent parameter to validate_result_id()
                return None
            if file_number > len(self.file_hits):
                print('result file %d invalid' % file_number)
                return None
            line = self.file_hits[file_number - 1]
        except ValueError:
            # line contains filename, but filename may not exist
            note_encoding = self.pt_config['codec']
            # FIXME do not allow access to files outside of the jail directory/directories
            """
            if is_win:  # FIXME TODO remove this!
                return line  # skip for now
            # attempt to validate
            if line.startswith('/'):  # TODO handle '\' IF and only IF windows (which will handle network drives '\\' and '\\?\'), also 'x:' (drive letter, which handles 'x:\')
                return line  # absolute path, for now supported as pass-thru (and skip directory jail)
            #elif windows.. additional checks from above
            """

            # deal with delimited filenames (only, i.e. don't bother to attempt to handle single/stray [double]quotes)
            if line.startswith('"') and line.endswith('"'):  # TODO single quotes too for Linux/Unix?
                line = line[1:-1]  # top and tail
            # Assume relative path, enforce - loop through notes directory list
            is_valid_path_in_note_root = False  # pessimistic
            for note_root in self.paths_to_search:
                notes = puren_tonbo.FileSystemNotes(note_root, note_encoding)
                try:
                    fullpath = notes.native_full_path(line)  # relative2abspath()  # todo handle failures for one dir not bot other
                    is_valid_path_in_note_root = True
                except puren_tonbo.PurenTonboException:
                    continue  # maybe it's a full/abs path to a note in a different note root directory
                if os.path.exists(fullpath):  # prioritize files that exist for relative paths
                    return fullpath
            if is_valid_path_in_note_root == False:
                print('Filename %r is outside note root(s) %r' % (line, self.paths_to_search))  # TODO add calling option to raise error (or be silent, current behavior)
                return None
            # so file does not exist, assume new file in **first** directory
            note_root = self.paths_to_search[0]
            notes = puren_tonbo.FileSystemNotes(note_root, note_encoding)
            #import pdb; pdb.set_trace()
            fullpath = notes.native_full_path(line)
            return fullpath
        return line

    def do_opendir(self, line=None):
        """Given a filename (or result index number), open native directory file browser.
For numbers, 0 (zero) will view last hit.
        """
        line = self.validate_result_id(line)
        if line is None:
            return
        # FIXME if not line, just open (first) note dir (root) - handle no params
        note_root = os.path.dirname(line)
        print('line: %r' % line)
        print('note_root: %s' % note_root)

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
        if line.strip() in ('-h', '--help'):  # Quick and dirty https://github.com/clach04/puren_tonbo/issues/139 workaround/fix
            print('%s' % grep_help)
            return
            # TODO look at how to intercept help command in optparse.OptionParser

        options = copy.copy(self.grep_options)
        if line[0] != '-':
            search_term = line  # TODO option to strip (default) and retain trailing/leading blanks
        else:
            parsed_line = shlex.split(line)
            (grep_parser_options, grep_parser_args) = grep_parser.parse_args(parsed_line)  # FIXME ptig can exit with bad (ptig) ptgrep params
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

    do_ptgrep = do_grep  # shortcut to save typing
    do_g = do_grep  # shortcut to save typing
    do_ack = do_grep  # ack alias for convenience
    do_ag = do_grep  # silver searcher alias for convenience
    do_rg = do_grep  # ripgrep alias for convenience
    do_ugrep = do_grep  # ugrep alias for convenience

    # TODO refactor to call do_grep() to remove code duplication
    def do_find(self, line=None, paths_to_search=None):
        """find to pathname/filename, same as grep but only matches directory and file names

              -i, --ignore_case     Case insensitive search
              -r, --regex_search    Treat search term as a regex (default is to treat as
                                    literal word/phrase)
              -k, --search_encrypted_only
                        Search encrypted files (default false)
              -t, --time
        """
        # TODO -i, and -r (regex) flag support rather than using config variables?
        search_term = line  # TODO option to strip (default) and retain trailing/leading blanks
        paths_to_search = paths_to_search or self.cache or self.paths_to_search

        line = '--find-only-filename ' + line  # -y
        if self.grep_options.search_encrypted:
            line = '--ignore_case ' + line  # -e
        if self.grep_options.ignore_case:
            line = '--ignore_case ' + line  # -i
        return self.do_grep(line=line, paths_to_search=paths_to_search)
    do_f = do_find  # shortcut to save typing
    do_fd = do_find  # fd alias for convenience

    def do_config(self, line=None):
        """show puren tonbo config"""
        config_filename_exists = False
        #config_filename = self.pt_config.get('config_file', puren_tonbo.get_config_path())  # if config_file exists BUT is None, still get None
        config_filename = self.pt_config.get('config_file') or puren_tonbo.get_config_path()
        if config_filename and os.path.exists(config_filename):
            config_filename_exists = True
        print('config_filename %s (%s)' % (config_filename, 'exists' if config_filename_exists else 'does not exist'))
        print('%s' % json.dumps(self.pt_config, indent=4, sort_keys=True))  # TODO color support
    do_ptconfig = do_config

    def do_types(self, line=None):
        """show all suported types (except raw) along with version/info
        Also see command: types"""
        puren_tonbo.print_version_info(list_all=True)

    def do_version(self, line=None):
        """show version/info
        Also see command: version"""
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
    parser = ptgrep.MyParser(usage=usage, version="%%prog %s" % puren_tonbo.__version__)
    parser.add_option("-c", "--codec", help="Override config file encoding (can be a list TODO format comma?)")
    parser.add_option("--config-file", "--config_file", help="Override config file")
    parser.add_option("--note-root", help="Directory of notes, or dir_name_or_filename1.... will pick up from config file and default to '.'")
    parser.add_option("-e", "--exec", help="Command to issue after initialization (init config section), then exit")
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
    config['config_file'] = options.config_file  # set config filename
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

    use_color = False
    if ptgrep.guess_color_available:
        use_color = True
    if is_win:
        if ptgrep.colorama:
            # TODO only do below for Windows? looks like it may be a NOOP so may not need a windows check
            try:
                ptgrep.colorama.just_fix_windows_console()
            except AttributeError:
                # older version, for example '0.4.4'
                ptgrep.colorama.init()
            use_color = True

    options.use_color = use_color
    options.password = password
    grep_options = FakeOptions(options)
    grep_options.use_color = use_color  # redundant?

    ptig_options = config['ptig']
    grep_options.use_pager = ptig_options['use_pager']  # TODO revisit this, should ptig pick this up from pt_config directly instead of grep_options/Fakeoptions - see do_set() comments on grep config versus pt_config

    interpreter = CommandPrompt(paths_to_search=paths_to_search, pt_config=config, grep_options=grep_options)
    interpreter.onecmd('version')
    """Look for (optional) editors dictionary, to support multiple external editors
        "ptig": {
            ...
            # TODO review, may want to change the way external editors are specified, right now assumes single call with single parameter
            "editors": {
                "encscite": "C:\\programs\\encscite\\prog\\encscite.bat",
                "scite": "scite",
                "gvim": "gvim"
            },
            ...
    Dynamically add them, can not use reflection; sys._getframe().f_code.co_name, to determine method name, have to pass it in.
    """
    for editor in ptig_options.get('editors', []):
        print(editor)
        #setattr(interpreter, 'do_' + editor, interpreter.do_edit)  # or pass in and have it self modigy
        #setattr(interpreter, 'do_' + editor, interpreter.do_customedit)  # or pass in and have it self modigy
        setattr(interpreter, 'do_' + editor, FakeMethodEdit(editor, interpreter))
    for command in ptig_options.get('init', []):
        interpreter.onecmd(command)
    if options.exec:
        interpreter.onecmd(options.exec)
        return
    interpreter.cmdloop()

    return 0


if __name__ == "__main__":
    sys.exit(main())
