-*- coding: utf-8 -*-
# puren_tonbo

Pure Plain Text Notes... with optional encryption.

https://github.com/clach04/puren_tonbo/

**IMPORTANT** before using the optionally encryption features,
ensure that it is legal in your country to use the specific encryption ciphers.
Some countries have also have restrictions on import, export, and usage see http://www.cryptolaw.org/cls-sum.htm

Ensure you have backups, these tools could destroy/delete/corrupt your notes!
NO WARRANTY - see the LICENSE

  * [Background](#background)
  * [Features](#features)
  * [Getting Started](#getting-started)
    + [Regular install](#regular-install)
    + [Without a source code checkout](#without-a-source-code-checkout)
    + [From a source code checkout](#from-a-source-code-checkout)
  * [Microsoft Windows](#microsoft-windows)
    + [Microsoft Windows GUI Alternative Terminals](#microsoft-windows-gui-alternative-terminals)
      - [mintty (recommended)](#mintty--recommended-)
      - [Alacritty](#alacritty)
      - [Windows Terminal](#windows-terminal)
  * [Examples](#examples)
    + [ptcat](#ptcat)
    + [ptgrep](#ptgrep)
    + [ptrecrypt](#ptrecrypt)
    + [ptig](#ptig)
      - [Sample ptig session](#sample-ptig-session)
      - [ptig config](#ptig-config)
    + [pttkview](#pttkview)
    + [ptpyvim](#ptpyvim)
    + [ptdiff3merge](#ptdiff3merge)
    + [ptcipher](#ptcipher)
      - [rot-13](#rot-13)
      - [rot-47](#rot-47)
      - [gzip](#gzip)
      - [jenc / Markor / jpencconverter](#jenc---markor---jpencconverter)
      - [Tombo Blowfish CHI](#tombo-blowfish-chi)
      - [Age encryption](#age-encryption)
      - [ccrypt CPT](#ccrypt-cpt)
      - [OpenPGP - gpg / pgp](#openpgp---gpg---pgp)
      - [OpenSSL 1.1.0 AES](#openssl-110-aes)
      - [AES-256 zip](#aes-256-zip)
      - [VimCrypt](#vimcrypt)
  * [ptcat/ptcipher with text editors like vim](#ptcat-ptcipher-with-text-editors-like-vim)
    + [readonly pipe into editor](#readonly-pipe-into-editor)
    + [SciTE lua plugin](#scite-lua-plugin)
      - [SciTE lua install without extension manager](#scite-lua-install-without-extension-manager)
      - [SciTE lua install with an extension manager](#scite-lua-install-with-an-extension-manager)
    + [SciTE Python plugin](#scite-python-plugin)
    + [vim plugin](#vim-plugin)
      - [vim demo](#vim-demo)
      - [vim plugin install](#vim-plugin-install)
      - [vim plugin install linux/unix](#vim-plugin-install-linux-unix)
      - [vim plugin install Microsoft Windows](#vim-plugin-install-microsoft-windows)
      - [vim config notes](#vim-config-notes)
  * [Development and testing](#development-and-testing)
    + [Run test suite](#run-test-suite)
    + [High Level Overview](#high-level-overview)
  * [Thanks](#thanks)
  * [TODO](#todo)

<small><i><a href='http://ecotrust-canada.github.io/markdown-toc/'>Table of contents generated with markdown-toc</a></i></small>

## Background

Plain text notes search/edit tool that supports encrypted files, formats:

  * [AES-256 ZIP AE-1/AE-2](https://www.winzip.com/en/support/aes-encryption/) created with 7z (does NOT support encrypted 7z files), WinZIP, WinRAR - AES256 (under Python 3 can also read (but not write) the original ZipCrypto zip format)
      * AES-256-CTR PBKDF2 (iterations 1000)
  * [Age](https://github.com/clach04/age/tree/pr520_osenv_password) age passphrase encryption (not key)
  * [jenc / markor](https://github.com/clach04/jenc-py)
  * [ccrypt](https://ccrypt.sourceforge.net/) - Rijndael-256 (no authentication)
  * [GnuPG (OpenPGP, gpg)](https://www.gnupg.org/) - [symmetric](https://www.gnupg.org/gph/en/manual/r656.html) see https://tutonics.com/articles/gpg-encryption-guide-part-4-symmetric-encryption/#:~:text=Another%20type%20of%20cryptographic%20solution,also%20called%20a%20shared%20secret.
  * [OpenSSL 1.1.0 aes-256-cbc](https://github.com/openssl/openssl) - [symmetric](https://www.openssl.org/docs/manmaster/man1/openssl.html) AES-256-CBC encryption with pbkdf2.
  * [Tombo (chi)](https://github.com/clach04/chi_io?tab=readme-ov-file) - blowfish-ECB
  * [vim VimCrypt](https://vimdoc.sourceforge.net/htmldoc/editing.html#encryption) encrypted files READ ONLY - VimCrypt (1-3) zip, blowfish, and blowfish2

プレーン トンボ
Purēntonbo

 平易 蜻蛉


  * http://tombo.sourceforge.jp/En/
  * https://github.com/clach04/chi_io
  * https://hg.sr.ht/~clach04/pytombo - NOTE Puren Tonbo is intended to replace PyTombo


## Features

  * Plain text files notes (potentially with no formatting or in Markdown, reStructuredText, etc.)
  * Nested directories of notes
  * Supports reading and writing from/to encrypted files that are compatible with other formats/tools (there is no intention to create a new crypto format/algorithm in this tool)
  * Currently limited to local file system and stdin/out for files
  * Command line tools; `ptcat` and `ptcipher` to encrypt/decrypt and view plain text files
      * `ptcipher` - process raw binary files, controlled via command line and environment variables
      * `ptcat` - in addition to command line and environment variables, also has an (optional) config file and the concept of a root directory of notes
  * `ptgrep` - a grep, [ack](https://beyondgrep.com/), [ripgrep](https://github.com/BurntSushi/ripgrep), [silver-searcher](https://geoff.greer.fm/ag/), [pss](https://github.com/eliben/pss) like tool that works on encrypted (and plain text) files
  * `ptig` an interactive grep like tool that can also view/edit
  * `ptrecrypt` a TODO
  * `ptpyvim` a vim-like editor that works on encrypted (and plain text) files
  * `ptdiff3merge` 3-way diff/merge too that can works with encrypted (and plain text) files


## Getting Started

    sudo apt-get install python-tk
    sudo apt-get install ccrypt


### Regular install

    pip install "puren_tonbo[all]"

### Without a source code checkout

Picking up the latest version

    pip uninstall puren_tonbo ; python -m pip install --upgrade git+https://github.com/clach04/chi_io.git  git+https://github.com/clach04/puren_tonbo.git

    # sanity check, and dump sample config to stdout
    ptconfig
    python -m puren_tonbo.tools.ptconfig

### From a source code checkout

    # pip uninstall puren_tonbo
    # python -m pip install -r requirements.txt
    # TODO requirements_optional.txt
    python -m pip install -e .
    python -m pip install -e .[all]


    # sanity check, and dump sample config to stdout
    ptconfig
    python -m puren_tonbo.tools.ptconfig


## Microsoft Windows

  * NOTE "start" can help with spawning exes that wait, and do not exit. BUT ensure command being started is in path (do not use full path), causes issues with multiple edit ("en") in ptig.
  * Unicode support, CMD.exe has limited Unicode support, instead use a GUI terminal with Unicode support (see below)

### Microsoft Windows GUI Alternative Terminals

Using an alternative to CMD.exe allows full Unicode support, including Emoji
Recommend mintty (or in a pinch Windows Terminal).

Do NOT recommend Fluent Terminal (FluentTerminal).

Untested alternatives; Windows Terminal 2, ConEMu (https://conemu.github.io/ https://github.com/Maximus5/ConEmu)

#### mintty (recommended)

https://github.com/mintty/mintty

mintty is included with Git for Windows, msys2, cygwin.

Examples:

    mintty --title ptig --hold error --size 120,35 -e python -m puren_tonbo.tools.ptig
    mintty --title ptig --hold error --size 120,35 -e C:\full\path\to\ptig.exe
    mintty --title ptig --hold error --size 120,35 -e ptig.exe
    "C:\Program Files\Git\usr\bin\mintty.exe" --title ptig --hold error --size 120,35 -e python -m puren_tonbo.tools.ptig

Support is excellent, can easily change color theme/scheme without changing ALL terminals. Great control over title name.
Out of the box Emoji (Unicode) font is mono, rather than full color.
To enable full color emoji see https://github.com/mintty/mintty/wiki/Tips#emojis
https://github.com/mintty/mintty/wiki/Tips#quick-guide-to-emoji-installation is the least effort option, but slower than manually downloading and extracting.
One emoji are installed (to `%APPDATA%\mintty\emojis`) open mintty settings "Options...", Text, then edit the Style content to point to the directory of downloaded images for emoji.

Known to work well with mintty; 3.6.4, 3.7.0, 3.7.4, and 3.7.6 as installed by https://github.com/git-for-windows/git (and Python 3.1x).
NOTE odd title (numbers, forward slash, numbers) with mintty 3.7.4 and 3.7.6 (included with Git 2.46.0 and 2.46.2) and Python 3.12.5 - NOT seen with other versions.

Sample config file:

    type "%USERPROFILE%\.minttyrc"
    cat ~/.minttyrc

    ThemeFile=rosipov
    Font=Consolas
    FontHeight=10

"rosipov" is a built in theme (there are others, and custom ones can also be added too).

#### Alacritty

https://github.com/alacritty/alacritty

NOTE no scroll bar, and looks like there is no intention to support?
Great for keyboard only control.

Examples:

    "C:\Program Files\Alacritty\alacritty.exe" --title ptig --hold -e C:\full\path\to\ptig.exe


#### Windows Terminal

https://github.com/microsoft/terminal/ https://aka.ms/terminal

Whilst Windows Terminal looks great (out of box emoji is in full color font), it is limited compared to mintty. For example no control over title and color scheme is global.

Windows Terminal (with Unicode support, including emoji) WindowsTerminal https://github.com/microsoft/terminal/releases/tag/v1.20.11381.0 works great (or from AppStore https://apps.microsoft.com/detail/9n0dx20hk701)

    wt.exe - `%LOCALAPPDATA%\Microsoft\WindowsApps\wt.exe` or from zip (not AppStore) `WindowsTerminal.exe` (multi color emoji) and `OpenConsole.exe` (single color emoji)
        how to get taskbar icon showing up?

Examples:

    %LOCALAPPDATA%\Microsoft\WindowsApps\wt.exe C:\full\path\to\ptig.exe


## Examples

    ptconfig
    python -m puren_tonbo.tools.ptconfig
    ptconfig --list-formats
    ptconfig --list-all-formats


### ptcat

    ptcat  puren_tonbo/tests/data/aesop.txt
    ptcat --list-formats
    python -m puren_tonbo.tools.ptcat --list-formats
    python -m puren_tonbo.tools.ptcat --note-root . puren_tonbo/tests/data/aesop.txt
    python -m puren_tonbo.tools.ptcat --note-root . puren_tonbo/tests/data/aesop.chi
    python -m puren_tonbo.tools.ptcat  puren_tonbo/tests/data/aesop.txt

    ptcat -p password puren_tonbo/tests/data/aesop_linux_7z.aes256.zip
    python -m puren_tonbo.tools.ptcat -p password puren_tonbo/tests/data/aesop_linux_7z.aes256.zip


### ptgrep

A grep, [ack](https://beyondgrep.com/), [ripgrep](https://github.com/BurntSushi/ripgrep), [silver-searcher](https://geoff.greer.fm/ag/), [pss](https://github.com/eliben/pss) like tool that works on encrypted (and plain text) files.

Has similar parameters for ease of switching.

Python 2.7 note for Windows. Non-ascii characters can cause Python exception/crashes UnicodeEncodeError when attempting to print Unicode characters, where as Python 3 does not. ptgrep implements a translation feature/hack which can be disabled (or tweaked) via the Operating System environment variable `PTGREP_STDOUT_MODE. Valid options are `disabled`, `utf8`, and `ascii:backslashreplace`. For Python 2.7 under Microsoft Windows **only** (when neither `PYTHONIOENCODING` nor `PYTHONUTF8` have been set) `ascii:backslashreplace` is the default and works in a similar fashion to `PYTHONIOENCODING`.

    ptgrep better
    ptgrep -i better
    python -m puren_tonbo.tools.ptgrep -i better
    python -m puren_tonbo.tools.ptgrep --note-root=puren_tonbo/tests/data -i better
    python -m puren_tonbo.tools.ptgrep -e -p password Better
    python -m puren_tonbo.tools.ptgrep --note-root=puren_tonbo/tests/data -e -p password Better

Find all instances of "king", case-insensitive (note; matches `taking`):

    python -m puren_tonbo.tools.ptgrep --note-root=puren_tonbo/tests/data -i king

Find all words "king", case-insensitive using a regex:

    python -m puren_tonbo.tools.ptgrep --note-root=puren_tonbo/tests/data -i -r \bking\b

Find all instances of "king" but not "aking", "iking", or "lking", case-insensitive using a regex:

    python -m puren_tonbo.tools.ptgrep --note-root=puren_tonbo/tests/data -i -r [^ail]king

find different words with regex

    python -m puren_tonbo.tools.ptgrep --note-root=puren_tonbo/tests/data    -r "cruel|better"
    python -m puren_tonbo.tools.ptgrep --note-root=puren_tonbo/tests/data -i -r "cruel|better"
    python -m puren_tonbo.tools.ptgrep --note-root=puren_tonbo/tests/data    -r "cru.l|b.tter"

find "-feast" which looks like a command line argument:

    python -m puren_tonbo.tools.ptgrep --note-root=puren_tonbo/tests/data -- -feast

find filenames with regex

    python -m puren_tonbo.tools.ptgrep --note-root=puren_tonbo/tests/data -y -r ^aesop

find filenames that have an ISO date in either dirname or filename

    python -m puren_tonbo.tools.ptgrep --note-root=puren_tonbo/tests/data -y -r "202[0-9]-[0-9][0-9]-[0-9][0-9]"

find filenames encrypted with regex

    python -m puren_tonbo.tools.ptgrep --note-root=puren_tonbo/tests/data -y -e -r ^aesop

find filenames ONLY encrypted with regex

    python -m puren_tonbo.tools.ptgrep --note-root=puren_tonbo/tests/data -y -k -r ^aesop

### ptrecrypt

Help:

    Usage: ptrecrypt [options] file_or_dir_pattern1 [file_or_dir_pattern2...]

    Command line tool to (re-)encrypt files. Any files passed on the command line
    WILL BE encrypted (in the requested format, if none requested original format)
    unless it is the same format and password. Any directories may have some form
    of filtering based on type.

    Options:
      --version             show program's version number and exit
      -h, --help            show this help message and exit
      --list-formats        Which encryption/file formats are available
      --password-prompt=PASSWORD_PROMPT, --password_prompt=PASSWORD_PROMPT
                            Comma seperated list of prompt mechanism to use,
                            options; any,text,gui,win32,tk
      --no-prompt, --no_prompt
                            do not prompt for password
      --cipher=CIPHER       Which encryption mechanism to use (file extension used
                            as hint), use existing cipher if ommited
      --new-password=NEW_PASSWORD, --new_password=NEW_PASSWORD
                            new password to use, if omitted use the existing
                            password
      -E ENVVAR, --envvar=ENVVAR
                            Name of environment variable to get password from
                            (defaults to PT_PASSWORD) - unsafe
      -p PASSWORD, --password=PASSWORD
                            password, if omitted but OS env PT_PASSWORD is set use
                            that, if missing prompt
      -P PASSWORD_FILE, --password_file=PASSWORD_FILE
                            file name where password is to be read from, trailing
                            blanks are ignored
      -v, --verbose
      -s, --silent          if specified do not warn about stdin using
      --force-recrypt-same-format-password, --force_recrypt_same_format_password
                            For re encryption, even if same file format/container
                            and password is to be used
      --destination-directory=DESTINATION_DIRECTORY, --destination_directory=DESTINATION_DIRECTORY
                            If specified where to write to, if ommited uses same
                            directory
      --new-extension=NEW_EXTENSION, --new_extension=NEW_EXTENSION
                            file extension to append for new files; 'default'
                            (default for cipher), 'cipher' (what was passed in on
                            command line), 'retain' (if not changing formats, use
                            the original file extension) - and potentially
                            anything else with a period is the new extension to
                            use, for example '.zip'
      --skip-encrypted, --skip_encrypted
                            For directories, skip already encrypted files
      --skip-unencrypted, --skip_unencrypted
                            For directories, skip files that are not already
                            encrypted
      --existing-files=EXISTING_FILES, --existing_files=EXISTING_FILES
                            How to handle existing files; resolving files that
                            already exist; default error/stop, skip,
                            overwrite/replace/delete (in safe mode - needed for
                            same file type, new password), delete (after
                            successful write)
      --simulate            Do not write/delete/change files

### ptig

Command line interactive search tool, that also supports viewing and editing.
Relies on ptgrep, see `PTGREP_STDOUT_MODE` note.

Also see https://github.com/clach04/puren_tonbo/wiki/tool-ptig

    ptig
    python -m puren_tonbo.tools.ptig

#### Sample ptig session

    $ ptig --note-root=puren_tonbo/tests/data
    3.8.10 (default, Mar 15 2022, 12:22:08)
    [GCC 9.4.0]

    Puren Tonbo puren_tonbo version 0.0.3.git
    Formats:

                  txt - RawFile - Raw file, no encryption support
                   md - RawFile - Raw file, no encryption support
                  chi - TomboBlowfish - Tombo Blowfish ECB (not recommended)
                  gpg - GnuPG - gpg (GnuPG) symmetric 1.x and 2.x, does NOT uses keys
                  asc - GnuPGascii - gpg (GnuPG) symmetric 1.x and 2.x, does NOT uses keys
                  cpt - Ccrypt - ccrypt symmetric Rijndael
              aes.zip - ZipAES - AES-256 ZIP AE-1 DEFLATED (regular compression)
           aes256.zip - ZipAES - AES-256 ZIP AE-1 DEFLATED (regular compression)
               aeszip - ZipAES - AES-256 ZIP AE-1 DEFLATED (regular compression)
              old.zip - ZipAES - AES-256 ZIP AE-1 DEFLATED (regular compression)
    openssl_aes256cbc_pbkdf2_10k - OpenSslEnc10k - OpenSSL 1.1.0 pbkdf2 iterations 10000 aes-256-cbc
     aes256stored.zip - ZipNoCompressionAES - AES-256 ZIP AE-1 STORED (uncompressed)
        oldstored.zip - ZipNoCompressionAES - AES-256 ZIP AE-1 STORED (uncompressed)
       aes256lzma.zip - ZipLzmaAES - AES-256 ZIP AE-1 LZMA
      aes256bzip2.zip - ZipBzip2AES - AES-256 ZIP AE-1 BZIP2
             vimcrypt - VimDecrypt - vimcrypt 1, 2, 3
            vimcrypt1 - VimDecrypt - vimcrypt 1, 2, 3
            vimcrypt2 - VimDecrypt - vimcrypt 1, 2, 3
            vimcrypt3 - VimDecrypt - vimcrypt 1, 2, 3

    Libs:
            chi_io.implementation: using PyCrypto 3.15.0
            python-gnupg version: 0.5.0
            gpg version: (2, 2, 19)
            pyzipper version: 0.3.6

    ptig: 🔎 rg better
    Query time: 0.01 seconds
    ptig: 🔎 set ic
    ptig: 🔎 rg better
    [1] puren_tonbo/tests/data/aesop.txt
    7:Better no rule than cruel rule.
    Query time: 0.01 seconds
    ptig: 🔎 find ccrypt
    [1] puren_tonbo/tests/data/aesop_win_ccrypt.cpt
    Query time: 0.00 seconds
    ptig: 🔎 f ccrypt
    [1] puren_tonbo/tests/data/aesop_win_ccrypt.cpt
    Query time: 0.00 seconds
    ptig: 🔎 cat 0
    Password for file aesop_win_ccrypt.cpt:
    ptig: 🔎 set search_encrypted=True
    ptig: 🔎 rg better
    [1] puren_tonbo/tests/data/aesop.chi
    7:Better no rule than cruel rule.
    ..... Truncated
    [21] puren_tonbo/tests/data/aesop_win_winrar.aes256stored.zip
    7:Better no rule than cruel rule.
    Query time: 0.32 seconds
    ptig: 🔎 help

    Documented commands (type help <topic>):
    ========================================
    EOF  c    config  edit  f     g     help  ptpyvim  quit     rg   ver      vi
    bye  cat  e       exit  find  grep  info  pyvim    results  set  version  vim

    ptig: 🔎 exit
    Quitting...

#### ptig config

Config for ptig is the regular config file `pt.json`, with additional (optional) ptig section:

```json
    {
        "_version_created_with": "0.0.dev3",
        "codec": [
            "utf8",
            "cp1252"
        ],
        "default_encryption_ext": "chi",
        "default_text_ext": "txt",
        "note_root": "C:\\Users\\yourname\\tombo",
        "ptig": {
            "#init": ["set ic", "set enc"],
            "init": ["set ic"],
            "editor": "start scite",
            "editors": {
                "encscite": "C:\\programs\\encscite\\prog\\encscite.bat",
                "pttkview": "pttkview",
                "scite": "scite",
                "gvim": "gvim",
                "vim": "vim"
            },
            "file_browser": "explorer",
            "prompt": "ptig: ? ",
            "use_pager": false
        }
    }
```

NOTE options for editor along with `init` which is a **list** of commands to issue on start up.
For example, enabling case insensitive search. There is a commented out example which enables encrypted file search.


### pttkview

A simple GUI viewer using the tk toolkit:

    python -m puren_tonbo.tools.pttkview -h
    pttkview -h

### ptpyvim

If pyvim is available, ptpyvim wraps encryption/decryption support.

    ptpyvim
    python -m puren_tonbo.tools.ptpyvim

### ptdiff3merge

a 3-way diff and merge tool.
Defaults to outputing plaintext to stdout, can be an encrypted file output.
Each file can be encrypted with differnent methods BUT any encrypted files must all use the same password.

    ptdiff3merge
    python -m puren_tonbo.tools.ptdiff3merge


### ptcipher

ptcipher is a tool for dealing with raw (binary, i.e. bytes rather than characters) files for encryption/decryption.
All options are controlled via command line flag and operating system environment variables.

Assuming installed:

    ptcipher -h

From source code checkout:

    python -m puren_tonbo.tools.ptcipher -h
    python -m puren_tonbo.tools.ptcipher --list-formats
    python2 -m puren_tonbo.tools.ptcipher -h
    python3 -m puren_tonbo.tools.ptcipher -h

Quick demo:

    ptcipher --password password --decrypt puren_tonbo/tests/data/aesop.chi
    ptcipher --password password --decrypt puren_tonbo/tests/data/aesop_linux_7z.aes256.zip
    python -m puren_tonbo.tools.ptcipher --password password --decrypt puren_tonbo/tests/data/aesop.chi


#### rot-13

Symmetric Substitution cipher with no passphrase/password/key support.
Do not use, this is implemented as a demo and for testing code paths when encryption libraries are not available.

https://en.wikipedia.org/wiki/ROT13

    ptcipher -e -p test README.md -o README.rot13

    ptcipher -v -p test README.rot13
    ptcipher -p password_ignored puren_tonbo/tests/data/aesop.rot13
    py -3 -m puren_tonbo.tools.ptcipher puren_tonbo/tests/data/aesop.rot13 -p password_ignored

    echo Why did the chicken cross the road?|ptcipher -p ignored_password  --encrypt --cipher=rot13
    echo Jul qvq gur puvpxra pebff gur ebnq?|ptcipher -p ignored_password  --encrypt --cipher=rot13

If using vim, can also use `g?` to rot-13 text. For example; selected text, whole file, etc.

#### rot-47

Symmetric Substitution cipher with no passphrase/password/key support.
Do not use, this is implemented as a demo and for testing code paths when encryption libraries are not available.

https://en.wikipedia.org/wiki/ROT13#Variants

    ptcipher -p password_ignored puren_tonbo/tests/data/aesop.rot47

    py -3 -m puren_tonbo.tools.ptcipher puren_tonbo/tests/data/aesop.rot47 -p password_ignored

#### gzip

No encryption, gzip compressed files - no passphrase/password/key support.

    ptcipher -p password_ignored puren_tonbo/tests/data/aesop.txt.gz
    py -3 -m puren_tonbo.tools.ptcipher -p password_ignored puren_tonbo/tests/data/aesop.txt.gz

NOTE Python 2 support for gz files is missing do to API differences in zlib.

NOTE files named .tar.gz will be picked up, they are NOT ignored.
TODO feature to ignore tar files (raw, gz, bz2, etc.)

#### jenc / Markor / jpencconverter

Symmetric encryption/decryption from passphase.

Format that [Markor](https://github.com/gsantner/markor) supports [jenc format](https://github.com/opensource21/jpencconverter).

    py -3 -m puren_tonbo.tools.ptcipher -p password puren_tonbo/tests/data/test_winnewlines.v001.jenc
    py -3 -m puren_tonbo.tools.ptcipher -p password puren_tonbo/tests/data/test_winnewlines.u001.jenc  # Old, legacy format

Jenc settings, application.properties contents:

    filesearch.depth=10
    # paths can be unix, i.e. '/'
    # or under Windows, can be either Unix style or Windows. For Windows paths need to escape, for example; 'C:\\some\\\dir'
    filesearch.encdir=C:\\code\\java\\jpencconverter\\bins\\jpenc-converter_0.2.1\\enc
    #filesearch.decdir=C:\\code\\java\\jpencconverter\\bins\\jpenc-converter_0.2.1\\plain
    filesearch.decdir=/code/java/jpencconverter/bins/jpenc-converter_0.2.1/plain
    extension.encrypt=.jenc
    extensions.plainText=md, markdown
    #password=geheim
    password=password
    # For android-devices before Android 8 use U001
    #encryption.version=U001
    encryption.version=V001

Command line, note operates on directories NOT file (names) like most command line crypto tools:

    java.exe -jar jpencconverter-0.2.1.jar encrypt
    java.exe -jar jpencconverter-0.2.1.jar decrypt

#### Tombo Blowfish CHI

Symmetric encryption/decryption from passphase.

Compatible with http://tombo.osdn.jp/En/ (and others, for example, Kumagusu on Android).

    ptcipher -e -p test README.md -o README.chi

    ptcipher -v -p test README.chi

The chi/chs file can also be read/written by Tombo http://tombo.sourceforge.jp/En/ and clones (for example, Kumagusu).


#### Age encryption

NOTE age passphrase encryption, not key.

Can either use Python library or age exe/binary - NOTE binary is signifcantly faster, there are also decryption failures wiht pyage!
Age exe from https://github.com/wj/age recommended which implements support for password from environment variable
For more details see:
  * https://github.com/FiloSottile/age/pull/520
      * https://github.com/FiloSottile/age/pull/520#issuecomment-2760007480
      * https://github.com/FiloSottile/age/pull/520#issuecomment-2993644928
      * https://github.com/clach04/age/tree/pr520_osenv_password - backup of the change that Puren Tonbo expects
      * Related
          * https://github.com/FiloSottile/age/discussions/275
  * Go build notes
      * https://go.dev/doc/tutorial/compile-install
      * https://opensource.com/article/22/4/go-build-options

Problems:

  * Weird characters in place of terminal escape sequences on Windows Console - https://github.com/FiloSottile/age/issues/474
  * pyage notes
      * errors opening an age encrypted file that works fine with age/rage - https://github.com/jojonas/pyage/issues/14

#### ccrypt CPT

Symmetric encryption/decryption from passphase.

Tested with ccrypt 1.11 and 1.10 (32-bit and 64-bit Intel x86/x64 and arm).

Requires a ccrypt binary, download from https://ccrypt.sourceforge.net/
(or debian apt). ccrypt binary/executable needs to be in the path or
the environment variable CCRYPT_EXE needs to have the (full) path.
NOTE Under Microsoft Windows, is the ccrypt.exe is in a path with
spaces, do NOT use double quotes in the SET. Example: `set CCRYPT_EXE=C:\3rd party bins\ccrypt.exe`

    python -m puren_tonbo.tools.ptcipher --password password puren_tonbo/tests/data/aesop_win_ccrypt.cpt
    ptcipher --cipher=cpt -e -p test README.md -o README.cpt
    python -m puren_tonbo.tools.ptcipher --cipher=cpt -e -p test README.md -o README.cpt

    ccrypt -c README.cpt
    ccrypt -c -K test README.cpt

#### OpenPGP - gpg / pgp

Symmetric encryption/decryption from passphase, key support not explictly implemented. RFC-4880 sec 5.13 (Symmetrically Encrypted Integrity Protected Data packet) OCFB-MDC.

Depending on which gpg Python module is installed **might requires** a gpg binary, download from https://gnupg.org/download/ or use one provided by Git For Windows

    set GPG_EXE=C:\Program Files\Git\usr\bin\gpg.exe
    python -m puren_tonbo.tools.ptcipher --cipher=asc -e -p test README.md -o README.asc
    python -m puren_tonbo.tools.ptcipher --cipher=gpg -e -p test README.md -o README.gpg
    ptcipher -p password puren_tonbo/tests/data/aesop_win_encryptpad.asc

    gpg --pinentry-mode=loopback --decrypt  --passphrase test README.gpg
    gpg --pinentry-mode=loopback --no-tty --no-verbose --decrypt  --passphrase password puren_tonbo/tests/data/aesop_win_encryptpad.asc

Also known to work withL


  * EncryptPad (cross platform, QT) from https://github.com/evpo/EncryptPad
      * `EncryptPad` - GUI tool encrypted text editor, with word-wrap, search/find, find and replace
      * `encryptcli` - command line , example usage that prompts for password:

            encryptcli.exe --decrypt aesop_win_encryptpad.asc

  * GpgFrontend (cross platform QT) from https://github.com/saturneric/GpgFrontend/
      * includes gpg command line tools, acts as a GUI front end and offers editing encrypted text files (NOTE EncryptPad easier/faster to use for this)

  * [OpenKeychain (for Android)](https://github.com/open-keychain/open-keychain)
    can encrypt/decrypt files and the clipboard, as well as Share-To Intent.

  * EncryptedNotepad2 (cross platform) from https://github.com/ivoras/EncryptedNotepad2/
      * According to https://github.com/ivoras/EncryptedNotepad2/issues/4 should be compatible.

#### OpenSSL 1.1.0 AES

OpenSSL 1.1.0+ compatible (with a very small subset of options).

    ptcat --note-root=. puren_tonbo/tests/data/aesop_win.openssl_aes256cbc_pbkdf2_10k

Intended to allow decryption of files generated with OpenSSL 1.1.0 and vice-versa. Supported OpenSSL flags/formats, see https://linux.die.net/man/1/openssl:

    openssl enc -e aes-256-cbc -salt -pbkdf2 -iter 10000 -in in_file -base64 -out out_file
    openssl dec -d aes-256-cbc -salt -pbkdf2 -iter 10000 -in in_file -base64 -out out_file

    echo hello| openssl enc -e aes-256-cbc -salt -pbkdf2 -iter 10000 -in - -base64 -out - -pass env:SET_OS_VAR_PASSWORD
    echo hello| openssl enc -e aes-256-cbc -salt -pbkdf2 -iter 10000 -in - -base64 -out - -pass pass:password
    echo hello| openssl enc -e -aes-256-cbc -in - -out - -salt -pbkdf2 -iter 10000  -pass pass:password

NOTE PBKDF2 iteration count of 10,000 is the default in OpenSSL 1.1.1 and is considered too few in 2023.
Older versions of OpenSSL did not support; PBKDF2 (and ergo iterations) and salt and used a much weaker KDF.
See https://www.openssl.org/docs/manmaster/man1/openssl-enc.html for more information.

Supports binary/raw and base64 encoded/ASCII armored files.
ONLY supports aes-256-cbc with salt and pbkdf2 KDF with 10,000 interations.

#### AES-256 zip

Symmetric encryption/decryption from passphase. See https://github.com/clach04/puren_tonbo/wiki/format-zip

    ptcipher -e -p test README.md -o README.aes256.zip

    ptcipher -p test README.aes256.zip

The aes256.zip file can also be read/written by 7-Zip, WinRAR, WinZIP, etc. that support AES zip files.

For example, 7z can read and write AES zip files:

    7z a -tzip -mem=AES256 -ptest README.aes256.zip README.md
    7z x -ptest README.aes256.zip

for more 7z command line options see https://github.com/axelstudios/7z

#### VimCrypt

Symmetric encryption/decryption from passphase.

NOTE not implemented in nvim / neovim.

In vim the easiest way to get the newest encryption mode/format, for a file:

    vim -c ":setlocal cm=blowfish2"  test.vimcrypt3

then issue:

    :X

will be prompted for password, can then edit/save as per normal.

To see encryption mode:

    :setlocal cm?

ptcipher demo:

    python -m puren_tonbo.tools.ptcipher -p test test.vimcrypt3


## ptcat/ptcipher with text editors like vim

### readonly pipe into editor

Quick and easy view/read ONLY of encrypted file with vim, without updating vim config.

NOTE call vim (or neovim) with options to set "private" mode:

  * `-` to read from stdin instead of a filename, avoid plaintext hitting the disk
  * `-n` turns off swap file - use memory only
  * `-i` turns off .viminfo

TODO disable undo file


  1. Use a pipe (cross platform)

            ptcat FILE | vim - -n -i "NONE"

  2. Use bash shell [process substitution](http://www.tldp.org/LDP/abs/html/process-sub.html) feature for editors that don't support stdin (Linux/Unix only, avoids directly calling mkfifo and cleaning up named pipes)

            scite < (ptcat FILE)
            ptcat FILE | scite /dev/stdin
            scite <(python -m puren_tonbo.tools.ptcat  puren_tonbo/tests/data/aesop.txt)

Puren Tonbo will prompt for passwords and the decrypted content should not hit the file system.


Option 1 can be used with other tools that take in stdin, option 2 can be used with any tool that takes in a filename.

Caution!

  * don't save the raw file
  * ensure now backup, swap, undo file, etc.. get created


https://vi.stackexchange.com/questions/6177/the-simplest-way-to-start-vim-in-private-mode

### git diff integration support

Allow diff'ing encrypted or compressed files that have been modified.

  * `git diff` - regular diff
  * `git diff --word-diff` - word based diff
  * with and without password prompt (e.g. mention `PT_PASSWORD` environment variable)

Password will be prompted twice:

  * once for original file
  * second for modified file

See integrations/git/README.md for more details and install/setup instructions.

### SciTE lua plugin

Tested with versions: v4.0.0, 4.1.5, and 5.3.5

See [pt_scite.lua](integrations/scite/pt_scite.lua) - read and write support (tested Windows).
NOTE due to lua popen() any helpful error text/information is missing. Diagnosing failures can be difficult, even for trivial errors like directory/disk does not exist as this is not reported to the lua runtime.
Also see SciTE Python plugin for read and write support with stderror support.

By default uses `ptcipher` in path, override via `PTCIPHER_EXE` environment variable.

Does NOT prompt for password, requires setting `PT_PASSWORD` environment variable or use of keyring.

  * Can be used standalone or with ParsKorata (http://lua-users.org/wiki/ParsKorata) mini/simple ExtMan compatible script
  * Untested with ExtMan - http://lua-users.org/wiki/SciteExtMan

Need to edit SciTEUser.properties:

  * Windows
      * `%USERPROFILE%"\SciTEUser.properties` or `%APPDATA%\scite\SciTEUser.properties`
  * Unix
      * `~/.SciTEUser.properties` or `$HOME/.SciTEUser.properties`

Alternatively, launch scite, then open Options, Open User (or GLobal) Options File.

Windows NOTE to avoid a (typically black) CMD/Command window showing up use SciTE 4.4.4 or later and set `create.hidden.console` in SciTEUser.properties:

    # https://groups.google.com/g/scite-interest/c/QOhizNSEejU/m/qXslloxnCgAJ
    # SciTE 4.4.4 on Windows adds create.hidden.console option to stop console window flashing when Lua script calls os.execute or io.popen.
    create.hidden.console=1
    # TODO see if this can be set in lua code, to make config easier

#### SciTE lua install without extension manager

If not using a plugin extension manager can simply set `pt_scite.lua` as starting lua script.
Edit SciTEUser.properties to set lua script:

    ...
    ext.lua.startup.script=C:\code\py\puren_tonbo\pt_scite.lua
    create.hidden.console=1
    ...

#### SciTE lua install with an extension manager

If using an extman like system:

    ...
    # This is a simplified ExtMan
    # requires each plugin/add-on to be "registered" or declared, white listed, etc.
    ext.lua.startup.script=C:\code\scite\extman\parskorata_extman.lua
    ...

Then edit `parskorata_extman.lua` to add to end:

    mgr:load_files{'pt_scite.lua'}

NOTE not needed with original full ExtMan.


### SciTE Python plugin

See [scite with Python README](integrations/pt_scite_with_python/README.md) - read and write support, Windows only (needs polishing).

By default uses `ptcipher` in path, override via `PTCIPHER_EXE` environment variable.

Does NOT prompt for password, requires setting `PT_PASSWORD` environment variable.


### vim plugin

Tested under Linux with vim 8.0 and 8.1. under x86, x64, and arm 32-bit.

See [pt.vim](integrations/vim/pt.vim) - Linux/Unix/Cygwin only for now.

By default uses `ptcipher` in path, override via `PTCIPHER_EXE` environment variable.

Will prompt for password, which can be skipped by setting `PT_PASSWORD` environment variable.

#### vim demo

Assuming puren_tonbo has been installed and `ptcipher` is in the
path (and in source code checkout):

    vim -u pt.vim  puren_tonbo/tests/data/aesop.chi

And enter in the test password, `password`.

#### vim plugin install

As per example above, can use the `-u` parameter but this overrides existing settings.

Vim 8 supports plugins packs, to install:

#### vim plugin install linux/unix

If you do not already have any plugin packs, need to create directory, e.g.:

    mkdir -p ~/.vim/pack/bundle/start/

Where `bundle` is user decided. For the rest of the documentation replace `bundle` with your directory name.

Install from checkout:

    mkdir -p ~/.vim/pack/bundle/start/puren_tonbo/plugin/
    cp pt.vim ~/.vim/pack/bundle/start/puren_tonbo/plugin/

Then can call vim without `-u`:

    vim puren_tonbo/tests/data/aesop.chi
    gvim puren_tonbo/tests/data/aesop.chi


#### vim plugin install Microsoft Windows

NOTE not working under Windows :-(
Appear to be buffered files issues with vim/python interaction.

See linux notes, instead of `~/.vim` use %USERPROFILE%\vimfiles (or `$VIM_INSTALLATION_FOLDER\vimfiles`)

    mkdir %USERPROFILE%\vimfiles\pack\bundle\start\puren_tonbo\plugin
    copy pt.vim %USERPROFILE%\vimfiles\pack\bundle\start\puren_tonbo\plugin


#### vim config notes

See https://vim.fandom.com/wiki/Encryption for how to configure vim with external tools for (view and edit) of encrypted files with autocmd.
NOTE under Windows buffered IO can interfere with vim interactions.
TODO consider using (OpenSSL) https://www.vim.org/scripts/script.php?script_id=2012 as a model for vim plugin (uses functions), also see:

  * https://aweirdimagination.net/2019/03/24/encrypted-files-in-vim/ https://git.aweirdimagination.net/perelman/openssl.vim
  * https://github.com/MoserMichael/vimcrypt2.
      * https://github.com/MoserMichael/vimcrypt



## Development and testing

Puren Tonbo is implemented in Python, with support for Python 3.x and 2.7.


### Run test suite

    python -m puren_tonbo.tests.testsuite
    python -m puren_tonbo.tests.testsuite -v 2>&1 |grep -i skipped

### High Level Overview

All encryption/decryption is file object based.
Low level routines (EncryptedFile) use file-like objects, for in-memory encryption/decryption use BytesIO
(see test suite, `puren_tonbo/tests/testsuite.py`).

There is also the note abstraction (FileSystemNotes) which is filename based.

Simple file-like API available with:

  * `FileLike` class which wraps a file object using a Puren Tonbo file (encryption) object
  * `pt_open()` which is similar to the regular Python open() function but will read/write encrypted files. File type is determined by file extension. Unrecognized file extension treated as raw (text).

Quick demo:

    import os

    import puren_tonbo

    # read
    pt_root_dir = os.path.dirname(puren_tonbo.__file__)
    test_filename = os.path.join(pt_root_dir, 'tests', 'data', 'aesop.chi')
    print(test_filename)

    open = puren_tonbo.pt_open  # monkey patch time!
    with open(test_filename) as f:
        print('%r' % f.read())

    f = open(test_filename)
    print('%r' % f.read())
    f.close()


    # write
    test_filename = 'test.zip'
    f = open(test_filename, 'w')
    f.write('hello')
    f.close()


## Thanks

Thanks and kudos to:

  * Tomohisa Hirami - the original creator of Tombo
  * [maxpat78](https://github.com/maxpat78) for the Python 2 (and 3) fall back code for AES zip support, [relicensed with permission](https://github.com/maxpat78/CryptoPad/issues/2) from https://github.com/maxpat78/CryptoPad
  * Noah Spurrier who's Public Domain OpenSSL vim plugin is the inspiration for the PT vim support (using functions) https://www.vim.org/scripts/script.php?script_id=2012

## TODO

TODO padlock and case insensitive ic in prompt - Windows terminal 2, ConEMu (https://conemu.github.io/ https://github.com/Maximus5/ConEmu) etc.?
    unlocked padlock for password present?
    key for searching for encrypted files?
    padlock for NOT searching for crypted files (or reverse?)
scite refuses to create new chi files if file was originally missing on open
    new window/instnace (not tab), copy/paste and then close orig ad save as workaround seems to work
    if file gets creted and scite reloads, still fails to save - trigger for successful load didn't reset trigger variable
ptig - with list of dirs, set shows note_root=None (ptconfig works fine)
stripe colors ptgrep/ptig
