-*- coding: utf-8 -*-
# puren_tonbo

Pure Plain Text Notes... with optional encryption.

https://github.com/clach04/puren_tonbo/

**IMPORTANT** before using the optionally encryption features,
ensure that it is legal in your country to use the specific encryption ciphers.
Some countries have also have restrictions on import, export, and usage see http://www.cryptolaw.org/cls-sum.htm

- [Background](#background)
- [Features](#features)
- [Getting Started](#getting-started)
  - [Without a source code checkout](#without-a-source-code-checkout)
  - [From a source code checkout](#from-a-source-code-checkout)
- [Examples](#examples)
  - [ptcat](#ptcat)
  - [ptgrep](#ptgrep)
  - [ptig](#ptig)
  - [pttkview](#pttkview)
  - [ptpyvim](#ptpyvim)
  - [ptcipher](#ptcipher)
- [ptcat/ptcipher with text editors like vim](#ptcatptcipher-with-text-editors-like-vim)
  - [readonly pipe into editor](#readonly-pipe-into-editor)
  - [vim plugin](#vim-plugin)
- [Development and testing](#development-and-testing)
  - [Run test suite](#run-test-suite)
  - [High Level Overview](#high-level-overview)
- [Thanks](#thanks)


## Background

Plain text notes search/edit tool that supports encrypted files, formats:

  * AES-256 ZIP AE-1/AE-2 created with 7z (does NOT support encrypted 7z files), WinZIP, WinRAR - AES256 (under Python 3 can also read (but not write) the original ZipCrypto zip format)
  * ccrypt - Rijndael
  * GnuPG (OpenPGP, gpg)
  * Tombo (chi) - blowfish
  * VimCrypt encrypted files READ ONLY - VimCrypt (1-3) zip, blowfish, and blowfish2

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
  * `ptpyvim` a vim-like editor that works on encrypted (and plain text) files


## Getting Started

### Without a source code checkout

    pip uninstall puren_tonbo ; python -m pip install --upgrade git+https://github.com/clach04/chi_io.git  git+https://github.com/clach04/puren_tonbo.git

    # sanity check, and dump sample config to stdout
    ptconfig
    python -m puren_tonbo.tools.ptconfig

### From a source code checkout

    # pip uninstall puren_tonbo
    # python -m pip install -r requirements.txt
    # TODO requirements_optional.txt
    python -m pip install -e .


    # sanity check, and dump sample config to stdout
    ptconfig
    python -m puren_tonbo.tools.ptconfig


## Examples

    ptconfig
    python -m puren_tonbo.tools.ptconfig


### ptcat

    ptcat  puren_tonbo/tests/data/aesop.txt
    python -m puren_tonbo.tools.ptcat --note-root . puren_tonbo/tests/data/aesop.txt
    python -m puren_tonbo.tools.ptcat --note-root . puren_tonbo/tests/data/aesop.chi
    python -m puren_tonbo.tools.ptcat  puren_tonbo/tests/data/aesop.txt

    ptcat -p password puren_tonbo/tests/data/aesop_linux_7z.aes256.zip
    python -m puren_tonbo.tools.ptcat -p password puren_tonbo/tests/data/aesop_linux_7z.aes256.zip


### ptgrep

A grep, [ack](https://beyondgrep.com/), [ripgrep](https://github.com/BurntSushi/ripgrep), [silver-searcher](https://geoff.greer.fm/ag/), [pss](https://github.com/eliben/pss) like tool that works on encrypted (and plain text) files.

    ptgrep better
    ptgrep -i better
    python -m puren_tonbo.tools.ptgrep better
    python -m puren_tonbo.tools.ptgrep -e -p password Better
    python -m puren_tonbo.tools.ptgrep -e -p password Better

### ptig

Command line interactive search tool, that also supports viewing and editing.

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

### pttkview

A simple GUI viewer using the tk toolkit:

    python -m puren_tonbo.tools.pttkview -h
    pttkview -h

### ptpyvim

If pyvim is available, ptpyvim wraps encryption/decryption support.

    ptpyvim
    python -m puren_tonbo.tools.ptpyvim


### ptcipher

ptcipher is a tool for dealing with raw (binary, i.e. bytes rather than characters) files for encryption/decryption.
All options are controlled via command line flag and operating system environment variables.

Assuming installed:

    ptcipher -h

From source code checkout:

    python -m puren_tonbo.tools.ptcipher -h
    python2 -m puren_tonbo.tools.ptcipher -h
    python3 -m puren_tonbo.tools.ptcipher -h

Quick demo:

    ptcipher --password password --decrypt puren_tonbo/tests/data/aesop.chi
    ptcipher --password password --decrypt puren_tonbo/tests/data/aesop_linux_7z.aes256.zip

#### Tombo Blowfish CHI

Symmetric encryption/decryption from passphase.

Compatible with http://tombo.osdn.jp/En/ (and others, for example, Kumagusu on Android).

    ptcipher -e -p test README.md -o README.chi

    ptcipher -v -p test README.chi

The chi file can also be read/written by Tombo http://tombo.sourceforge.jp/En/ and clones


#### ccrypt CPT

Symmetric encryption/decryption from passphase.

Tested with ccrypt 1.11 and 1.10 (32-bit and 64-bit Intel x86/x64 and arm).

Requires a ccrypt binary, download from https://ccrypt.sourceforge.net/
(or debian apt). ccrypt binary/executable needs to be in the path or
the environment variable CCRYPT_EXE needs to have the (full) path.

    ptcipher --cipher=cpt -e -p test README.md -o README.cpt
    python -m puren_tonbo.tools.ptcipher --cipher=cpt -e -p test README.md -o README.cpt

    ccrypt -c README.cpt
    ccrypt -c -K test README.cpt

#### OpenPGP - gpg / pgp

Symmetric encryption/decryption from passphase, key support not explictly implemented.

Requires a gpg binary, download from https://gnupg.org/download/

    python -m puren_tonbo.tools.ptcipher --cipher=asc -e -p test README.md -o README.asc
    python -m puren_tonbo.tools.ptcipher --cipher=gpg -e -p test README.md -o README.gpg

    gpg  --pinentry-mode=loopback --decrypt  --passphrase test README.gpg

Also see `encryptcli` from https://github.com/evpo/EncryptPad/


#### AES-256 zip

Symmetric encryption/decryption from passphase.

    ptcipher -e -p test README.md -o README.aes256.zip

    ptcipher -p test README.aes256.zip

The aes256.zip file can also be read/written by 7-Zip, WinRAR, WinZIP, etc. that support AES zip files.

For example, 7z can read and write AES zip files:

    7z a -tzip -mem=AES256 -ptest README.aes256.zip README.md
    7z x -ptest README.aes256.zip


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

### SciTE lua plugin

See [pt_scite.lua](./pt_scite.lua) - read and write support (tested Windows).
NOTE due to lua popen() any helpful error text/information is missing. Diagnosing failures can be difficult, even for trivial errors like directory/disk does not exist as this is not reported to the lua runtime.
Also see SciTE Python plugin for read and write support with stderror support.

By default uses `ptcipher` in path, override via `PTCIPHER_EXE` environment variable.

Does NOT prompt for password, requires setting `PT_PASSWORD` environment variable.

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

See [pt.vim](./pt.vim) - Linux/Unix/Cygwin only for now.

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

### High Level Overview

All encryption/decryption is file object based.
Low level routines (EncryptedFile) use file-like objects, for in-memory encryption/decryption use BytesIO
(see test suite, `puren_tonbo/tests/testsuite.py`).

There is also the note abstraction (FileSystemNotes) which is filename based.

## Thanks

Thanks and kudos to:

  * Tomohisa Hirami - the original creator of Tombo
  * [maxpat78](https://github.com/maxpat78) for the Python 2 (and 3) fall back code for AES zip support, [relicensed with permission](https://github.com/maxpat78/CryptoPad/issues/2) from https://github.com/maxpat78/CryptoPad
  * Noah Spurrier who's Public Domain OpenSSL vim plugin is the inspiration for the PT vim support (using functions) https://www.vim.org/scripts/script.php?script_id=2012
