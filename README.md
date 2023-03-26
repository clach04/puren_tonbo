# puren_tonbo

Pure Plain Text Notes... with optional encryption.

https://github.com/clach04/puren_tonbo/

**IMPORTANT** before using the optionally encryption features,
ensure that it is legal in your country to use the specific encryption ciphers.
Some countries have also have restrictions on import, export, and usage see http://www.cryptolaw.org/cls-sum.htm

- [Background](#background)
- [Features](#features)
- [Getting Started](#getting-started)
- [Examples](#examples)
  - [ptcat](#ptcat)
  - [ptgrep](#ptgrep)
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

  * AES-256 ZIP AE-1/AE-2 - AES256 (note can also read but not write the old pkzip encrption format)
  * ccrypt - Rijndael
  * GnuPG (OpenPGP, gpg)
  * Tombo (chi) - blowfish
  * VimCrypt encrypted files READ ONLY - zip, blowfish, and blowfish2

プレーン トンボ
Purēntonbo

 平易 蜻蛉


  * http://tombo.sourceforge.jp/En/
  * https://github.com/clach04/chi_io
  * https://hg.sr.ht/~clach04/pytombo


## Features

None right now!

  * Plain text files notes (potentially with no formatting or in Markdown, reStructuredText, etc.)
  * Nested directories of notes
  * Supports reading and writing from/to encrypted chi files that are compatible with:
      * Tombo Blowfish `*.chi` (note not recommended for new storage)
      * VimCrypt (1-3)
      * AE-1/AE-2 AES-256 encrypted zip files created with WinZIP and WinRAR (does NOT support encrypted 7z files)
          * under Python 3 can also read (but not write) the original ZipCrypto zip format
  * Currently limited to local file system and stdin/out for files.


## Getting Started

### Without a source code checkout

    pip uninstall puren_tonbo ; python -m pip install --upgrade git+https://github.com/clach04/chi_io.git  git+https://github.com/clach04/puren_tonbo.git

NOTE be aware test suite will not pass due to missing data files,
issue https://github.com/clach04/puren_tonbo/issues/38

### From a source code checkout

    # pip uninstall puren_tonbo
    # python -m pip install -r requirements.txt
    # TODO requirements_optional.txt
    python -m pip install -e .


    # sanity check, and dump sample config to stdout
    ptconfig
    python -m puren_tonbo.tools.ptconfig


## Examples

    python -m puren_tonbo.tools.ptconfig


### ptcat

    python -m puren_tonbo.tools.ptcat  puren_tonbo/tests/data/aesop.txt
    python -m puren_tonbo.tools.ptcat -p password puren_tonbo/tests/data/aesop_linux_7z.aes256.zip


### ptgrep

A grep, [ack](https://beyondgrep.com/), [ripgrep](https://github.com/BurntSushi/ripgrep), [silver-searcher](https://geoff.greer.fm/ag/), [pss](https://github.com/eliben/pss) like tool that works on encrypted (and plain text) files.

    python -m puren_tonbo.tools.ptgrep better
    python -m puren_tonbo.tools.ptgrep -e -p password Better
    python -m puren_tonbo.tools.ptgrep -e -p password Better



### ptcipher

Assuming installed:

    ptcipher -h

From source code checkout:

    python -m puren_tonbo.tools.ptcipher -h
    python2 -m puren_tonbo.tools.ptcipher -h
    python3 -m puren_tonbo.tools.ptcipher -h

#### Tombo Blowfish CHI

Symmetric encryption/decryption from passphase.

Compatible with http://tombo.osdn.jp/En/ (and others, for example, Kumagusu on Android).

    ptcipher -e -p test README.md -o README.chi

    ptcipher -v -p test README.chi

The chi file can also be read/written by Tombo http://tombo.sourceforge.jp/En/ and clones


#### ccrypt CPT

Symmetric encryption/decryption from passphase.

Requires a ccrypt binary, download from https://ccrypt.sourceforge.net/ (or debian apt)

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

### vim plugin

See [pt.vim](./pt.vim) - Linux/Unix/Cygwin only for now.

See https://vim.fandom.com/wiki/Encryption for how to configure vim with external tools for (view and edit) of encrypted files with autocmd.
NOTE under Windows buffered IO can interfere with vim interactions.
TODO consider using (OpenSSL) https://www.vim.org/scripts/script.php?script_id=2012 as a model for vim plugin (uses functions), also see:

  * https://aweirdimagination.net/2019/03/24/encrypted-files-in-vim/ https://git.aweirdimagination.net/perelman/openssl.vim
  * https://github.com/MoserMichael/vimcrypt2.
      * https://github.com/MoserMichael/vimcrypt



## Development and testing


### Run test suite

    python -m puren_tonbo.tests.testsuite

### High Level Overview

All encryption/decryption is file based.
Low level routines (EncryptedFile) use file-like objects, for in-memory encryption/decryption use BytesIO
(see test suite, `puren_tonbo/tests/testsuite.py`).

There is also the note abstraction (FileSystemNotes) which is filename based.

## Thanks

Thanks and kudos to:

  * [maxpat78](https://github.com/maxpat78) for the Python 2 (and 3) fall back code for AES zip support, [relicensed with permission](https://github.com/maxpat78/CryptoPad/issues/2) from https://github.com/maxpat78/CryptoPad
  * Noah Spurrier who's Public Domain OpenSSL vim plugin is the inspiration for the PT vim support (using functions) https://www.vim.org/scripts/script.php?script_id=2012
