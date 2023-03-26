#!/usr/bin/env python
# -*- coding: us-ascii -*-
# vim:ts=4:sw=4:softtabstop=4:smarttab:expandtab
"""Command line interactive tool to recursively Search Puren Tonbo files (plain text and encrypted notes).
Example encryption file formats; Tombo CHI Blowfish files, VimCrypt, AES-256.zip, etc.

    python -m puren_tonbo.tools.ptig -h
"""

import json
import os
from optparse import OptionParser
import pydoc
import shlex
import sys
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
    files_with_matches = False  # set to True to only search on filename
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


class CommandPrompt(Cmd):
    def __init__(self, paths_to_search=None, pt_config=None, grep_options=None):  # TODO refactorm too many options and search path is also potentially a dupe
        """If paths_to_search is omitted, defaults to current directory
        """
        Cmd.__init__(self)
        self.paths_to_search = paths_to_search or ['.']
        self.pt_config = pt_config
        self.grep_options = grep_options or FakeOptions()
        self.file_hits = []
        #import pdb ; pdb.set_trace()
        if self.pt_config['ptig']['prompt']:
            self.prompt = self.pt_config['ptig']['prompt']
        else:
            self.prompt = 'ptig:' + str(paths_to_search) + ' '  # Almost never going to be seen, unless config file entry is false/null, '' empty string, 0, etc.
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

    def do_set(self, line=None):
        """Set variables/options. No params, show variable settings

Examples

    set ic
    set ignorecase
    set noic
    set noignorecase

"""
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
            for attribute_name in dir(options):
                if not attribute_name.startswith('_'):
                    attribute_value = getattr(options, attribute_name)
                    #print('\t%s=%s' % (attribute_name, attribute_value))  # TODO consider sorted dict?
                    print('\t%s%s%s=%s%s%s' % (name_color, attribute_name, color_reset, value_color, attribute_value, color_reset))  # TODO consider sorted dict?
            return

        # vim-like case insensitive
        if line in ('ic', 'ignorecase'):
            self.grep_options.ignore_case = True
            return
        if line in ('noic', 'noignorecase'):
            self.grep_options.ignore_case = False
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

        # TODO set shoud support prompt change

        print('unsupported set operation')

    def do_results(self, line=None):
        """Redisplay previous filename search results
        """
        if not self.file_hits:
            print('no results')
            return
        for counter, filename in enumerate(self.file_hits):
            print('[%d] %s' % (counter, filename))

    def do_edit(self, line=None):
        """Edit using external $VISUAL or $EDITOR, with fall backs if unset.

Microsoft Windows will use file associations.

Linux/Unix will use editor, which under Debian derivatives like
Ubuntu can be configured via:

    sudo update-alternatives --config editor
    update-alternatives --list editor
        """
        try:
            file_number = int(line)
            if not self.file_hits:
                print('no results')
                return
            if file_number > len(self.file_hits):
                print('result file %d invalid' % file_number)
                return
            line = self.file_hits[file_number - 1]
        except ValueError:
            pass  # line contains filename
        filename = line
        editor = os.environ.get('VISUAL') or os.environ.get('EDITOR')
        if not editor:
            # TODO pickup from config file
            # default a sane editor
            if is_win:
                editor = 'start "ptig"'  # Let Windowsfigure it out based on file extension
            else:
                # Assume Linux
                editor = 'editor' # TODO full path "/usr/bin/editor" -> /etc/alternatives/editor, or xdg-open, jaro, etc.
        # TODO what about password? For now let external tool handle that. To support tools that don't support password, need to pipe in plain text
        print('Using: %s' % editor)
        print('file: %s' % filename)
        os.system('%s "%s"' % (editor, filename))
        print('file: %s' % filename)
        print('To display previous results issue: results')
    do_e = do_edit

    if ptpyvim:
        def do_pyvim(self, line=None):
            """Edit using built in (vim-like) ptpyvim editor
            """
            try:
                file_number = int(line)
                if file_number > len(self.file_hits):
                    print('result file %d invalid' % file_number)
                    return
                line = self.file_hits[file_number - 1]
            except ValueError:
                pass  # line contains filename
            in_filename = line
            #import pdb; pdb.set_trace()
            if not self.grep_options.password:
                self.grep_options.password = puren_tonbo.caching_console_password_prompt(filename=in_filename, reset=True)  # TODO not for .txt and .md files
            ptpyvim.edit([in_filename], password=self.grep_options.password)
        do_ptpyvim = do_pyvim
        do_vim = do_pyvim
        do_vi = do_pyvim

    def do_cat(self, line=None):
        """cat/view file. Takes either a number or filename.
For numbers, 0 (zero) will view last hit.
        """
        try:
            file_number = int(line)
            if file_number > len(self.file_hits):
                print('result file %d invalid' % file_number)
                return
            line = self.file_hits[file_number - 1]
        except ValueError:
            pass  # line contains filename
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
        except KeyboardInterrupt:
            print('search cancelled')

    do_c = do_cat  # shortcut to save typing

    def default(self, line=None):
        try:
            file_number = int(line)
            self.do_cat(line)
        except ValueError:
            Cmd.default(self, line)  # Super...

    def do_grep(self, line=None):
        """ptgrep/search"""
        # TODO -i, -r, and -l (instead of find) flag support rather than using config variables?
        search_term = line  # TODO option to strip (default) and retain trailing/leading blanks
        paths_to_search = self.paths_to_search
        options = self.grep_options

        note_encoding = self.pt_config['codec']

        line_numbers = options.line_numbers

        password_func = options.password or puren_tonbo.caching_console_password_prompt
        use_color = options.use_color

        self.file_hits = ptgrep.grep(search_term, paths_to_search, options, use_color, password_func, note_encoding)

    do_g = do_grep  # shortcut to save typing
    do_rg = do_grep  # ripgrep alias for convenience

    def do_find(self, line=None):
        """find to pathname/filename, same as grep but only matches directory and file names"""
        # TODO -i, and -r (regex) flag support rather than using config variables?
        search_term = line  # TODO option to strip (default) and retain trailing/leading blanks
        paths_to_search = self.paths_to_search
        options = self.grep_options

        note_encoding = self.pt_config['codec']

        line_numbers = options.line_numbers

        password_func = options.password or puren_tonbo.caching_console_password_prompt
        use_color = options.use_color
        grep_options = FakeOptions(options)
        grep_options.files_with_matches = True  # same as grep but filenames only
        grep_options.search_encrypted = True  # TODO review, this seems like a reasonable default and password not needed for name matching

        self.file_hits = ptgrep.grep(search_term, paths_to_search, grep_options, use_color, password_func, note_encoding)
    do_f = do_find  # shortcut to save typing

    def do_config(self, line=None):
        """show puren tonbo config"""
        print('%s' % json.dumps(self.pt_config, indent=4, sort_keys=True))  # TODO color support

    def do_version(self, line=None):
        """show version/info"""
        puren_tonbo.print_version_info()
    do_ver = do_version
    do_info = do_version


def main(argv=None):
    if argv is None:
        argv = sys.argv

    usage = "usage: %prog [options] [search_term] [dir_name_or_filename1] [dir_name_or_filename2...]"
    parser = OptionParser(usage=usage, version="%%prog %s" % puren_tonbo.__version__)
    parser.add_option("-c", "--codec", help="Override config file encoding (can be a list TODO format comma?)")
    parser.add_option("--config-file", help="Override config file")
    parser.add_option("--note-root", help="Directory of notes, or dir_name_or_filename1.... will pick up from config file and default to '.'")
    parser.add_option("-p", "--password", help="password, if omitted and OS env PT_PASSWORD is set use that, if missing prompt")  # TODO keyring support
    parser.add_option("-P", "--password_file", help="file name where password is to be read from, trailing blanks are ignored")

    (options, args) = parser.parse_args(argv[1:])
    if options.password_file:
        f = open(options.password_file, 'rb')
        password_file = f.read()
        f.close()
        password_file = password_file.strip()
    else:
        password_file = None

    password = options.password or password_file or os.environ.get('PT_PASSWORD') or puren_tonbo.caching_console_password_prompt  # TODO keyring support
    if password and not callable(password) and not isinstance(password, bytes):
        password = password.encode('us-ascii')

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
    options.password = password
    grep_options = FakeOptions(options)
    grep_options.use_color = use_color

    ptig_options = config['ptig']
    grep_options.use_pager = ptig_options['use_pager']  # TODO revisit this, should ptig pick this up from pt_config directly instead of grep_options/Fakeoptions - see do_set() comments on grep config versus pt_config

    interpreter = CommandPrompt(paths_to_search=paths_to_search, pt_config=config, grep_options=grep_options)
    interpreter.onecmd('version')
    interpreter.cmdloop()

    return 0


if __name__ == "__main__":
    sys.exit(main())
