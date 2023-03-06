# puren_tonbo

Pure Plain Text Notes... with optional encryption.

https://github.com/clach04/puren_tonbo/

**IMPORTANT** before using the optionally encryption features,
ensure that it is legal in your country to use the specific encryption ciphers.
Some countries have also have restrictions on import, export, and usage see http://www.cryptolaw.org/cls-sum.htm

* [Features](#Features)
* [Background](#Background)
* [Getting Started](#Getting-Started)
* [Examples](#Examples)
    * [ptcipher](#ptcipher)


## Background

Plain text notes Tombo (chi) alternative, also supports AES-256 ZIP AE-1/AE-2 and VimCrypt encrypted files. Work-In-Progress (WIP)!

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

    # python -m pip install -r requirements.txt
    # TODO requirements_optional.txt
    python -m pip install -e .

## Examples

    python -m puren_tonbo.tools.ptconfig


### ptcat

    python -m puren_tonbo.tools.ptcat  puren_tonbo/tests/data/aesop.txt
    python -m puren_tonbo.tools.ptcat -p password puren_tonbo/tests/data/aesop_linux_7z.aes256.zip


### ptgrep

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

    ptcipher -e -p test README.md -o README.chi

    ptcipher -v -p test README.chi

The chi file can also be read/written by Tombo http://tombo.sourceforge.jp/En/ and clones


#### OpenPGP - gpg / pgp

Symmetric encryption/decryption, no explict key support.

Requires a gpg binary, download from https://gnupg.org/download/

    python -m puren_tonbo.tools.ptcipher --cipher=asc -e -p test README.md -o README.asc
    python -m puren_tonbo.tools.ptcipher --cipher=gpg -e -p test README.md -o README.gpg

    gpg  --pinentry-mode=loopback --decrypt  --passphrase test README.gpg

Also see `encryptcli` from https://github.com/evpo/EncryptPad/


#### AES-256 zip

    ptcipher -e -p test README.md -o README.aes256.zip

    ptcipher -p test README.aes256.zip

The aes256.zip file can also be read/written by 7-Zip, WinRAR, WinZIP, etc. that support AES zip files.

For example, 7z can read and write AES zip files:

    7z a -tzip -mem=AES256 -ptest README.aes256.zip README.md
    7z x -ptest README.aes256.zip


#### VimCrypt

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

Quick and easy view/read ONLY of encrypted file with vim, without updating vim config.

NOTE call vim (or neovim) with options to set "private" mode:

  * - to read from stdin instead of a filename, avoid plaintext hitting the disk
  * -n turns off swap file - use memory only
  * -i turns off .viminfo

TODO disable undo file


  1. Use a pipe (cross platform)

        ptcat FILE | vim - -n -i "NONE"

  2. Use bash shell command substitution feature for editors that don't support stdin (Linux/Unix only, avoids directly calling mkfifo and cleaning up named pipes)

        scite < (ptcat FILE)
        ptcat FILE | scite /dev/stdin
        scite <(python -m puren_tonbo.tools.ptcat  puren_tonbo/tests/data/aesop.txt)

Puren Tonbo will prompt for passwords and the decrypted content should not hit the file system.


Option 1 can be used with other tools that take in stdin, option 2 can be used with any tool that takes in a filename.

Caution!

  * don't save the raw file
  * ensure now backup, swap, undo file, etc.. get created


https://vi.stackexchange.com/questions/6177/the-simplest-way-to-start-vim-in-private-mode


See https://vim.fandom.com/wiki/Encryption for how to configure vim with external tools for (view and edit) of encrypted files with autocmd.
NOTE under Windows buffered IO can interfere with vim interactions.
TODO consider using (OpenSSL) https://www.vim.org/scripts/script.php?script_id=2012 as a model for vim plugin (uses functions), also see:

  * https://aweirdimagination.net/2019/03/24/encrypted-files-in-vim/ https://git.aweirdimagination.net/perelman/openssl.vim
  * https://github.com/MoserMichael/vimcrypt2.
      * https://github.com/MoserMichael/vimcrypt



## Developement and testing


### Run test suite

    python -m puren_tonbo.tests.testsuite

### High Level Overview

All encryption/decryption is file based.
Low level routines (EncryptedFile) use file-like objects, for in-memory encryption/decryption use BytesIO
(see test suite, `puren_tonbo/tests/testsuite.py`).

There is also the note abstraction (FileSystemNotes) which is filename based.
