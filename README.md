# puren_tonbo

Pure Plain Text Notes... with optional encryption.

https://github.com/clach04/puren_tonbo/

* [Features](#Features)
* [Background](#Background)
* [Getting Started](#Getting-Started)
* [Examples](#Examples)
    * [ptcipher](#ptcipher)


## Background

Tombo alternative, Work-In-Progress (WIP)!

プレーン トンボ
Purēntonbo

 平易 蜻蛉


  * http://tombo.sourceforge.jp/En/
  * https://github.com/clach04/chi_io
  * https://hg.sr.ht/~clach04/pytombo


## Features

None right now!

  * Currently limited to local file system and stdin/out for files.
  * Supports reading and writing from/to encrypted chi files that are compatible with Tombo Blowfish (note not recommended for new storage)
  * Supports reading and writing from/to encrypted zip files that are compatible with AES-256 encrypted zip files created with 7z and WinZIP (does NOT support encrypted 7z files)
  * Plain text files notes (potentially with no formatting or in Markdown, reStructuredText, etc.)
  * Nested directories of notes


## Getting Started

    # python -m pip install -r requirements.txt
    # TODO requirements_optional.txt
    python -m pip install -e .

## Examples

### ptcipher

Assuming installed:

    ptcipher -h

From source code checkout:

    python2 -m puren_tonbo.tools.ptcipher -h
    python3 -m puren_tonbo.tools.ptcipher -h

#### Tombo Blowfish CHI

    ptcipher -e -p test README.md -o README.chi

    ptcipher -v -p test README.chi

The chi file can also be read/written by Tombo http://tombo.sourceforge.jp/En/ and clones


#### AES-256 zip

    ptcipher -e -p test README.md -o README.aes256.zip

    ptcipher -p test README.aes256.zip

The aes256.zip file can also be read/written by 7z, WinZIP, etc that support AES zip files.
For example:

    7z x -ptest README.aes256.zip

or create with 7z:

    7z a -ptest test.aes256.zip encrypted.md

#### VimCrypt

NOTE not implemented in nvim / newovim.

In vim the easiest way to get the newest encryption mode/format, for a file:

    vim -c ":setlocal cm=blowfish2"  test.vimcrypt3

then issue:

    :X

will be prompted for password, can then edit/save as per normal.

To see encryption mode:

    :setlocal cm?

ptcipher demo:

    python3 -m puren_tonbo.tools.ptcipher -p test test.vimcrypt3


## Developement and testing

Python 2.x ONLY:

    pip install unittest2
    # TODO requirements.dev?

### Run test suite

    python -m puren_tonbo.tests.testsuite
