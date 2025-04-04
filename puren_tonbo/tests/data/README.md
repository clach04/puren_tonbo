# test data

Ideally generated with external tools that Puren Tonbo can validate against.

  * aesop.txt - plain text version of shortest Aesop fable there is,
    so suitable for realistic test data.
      * has window newlines
      * us-ascii encoding
      * Contains long lines (one is 1435 bytes)
      * Approx 1.5Kb.

  * aesop.rot13 - rot-13 version
    so suitable for realistic test data. Does NOT require any encryption libaries present, supported by vim with `g?`
      * has window newlines
      * us-ascii encoding
      * Contains long lines (one is 1435 bytes)
      * Approx 1.5Kb.

  * aesop.rot47 - rot-47 version
    so suitable for realistic test data. Does NOT require any encryption libaries present
      * has window newlines
      * us-ascii encoding
      * Contains long lines (one is 1435 bytes)
      * Approx 1.5Kb.

  * aesop.txt.gz - Compress gZip text file
    so suitable for realistic test data. Does NOT require any encryption libaries present. Can be read with `gzip` (and modern versions of `zcat`)
      * has window newlines
      * us-ascii encoding
      * Contains long lines (one is 1435 bytes)
      * Approx 1.5Kb.

  * aesop.chi -  Tombo Blowfish encrypted from `aesop.txt`
    Created with Windows win32 Tombo http://tombo.sourceforge.jp/En/
      * password is `password`
      * Approx 1.5Kb.

  * aesop_win_ccrypt.cpt - ccrypt encrypted from `aesop.txt`
    Created with Windows win32 ccrypt 1.11 https://ccrypt.sourceforge.net/
      * password is `password`
      * Approx 1.5Kb.
      * Command: type aesop.txt | ccrypt -e > aesop_win_ccrypt.cpt

  * aesop_linux.openssl_aes256cbc_pbkdf2_10k - OpenSSL aes-256-cbc pbkdf2 encrypted from `aesop.txt`
    Created with Linux arm OpenSSL 1.1.1f  31 Mar 2020, `openssl enc -e -aes-256-cbc -in aesop.txt -out aesop_lin.openssl_aes256cbc_pbkdf2_10k -salt -pbkdf2 -iter 10000 -pass pass:password`
      * password is `password`
      * Approx 1.5Kb.

  * aesop_win.openssl_aes256cbc_pbkdf2_10k - OpenSSL aes-256-cbc pbkdf2 encrypted from `aesop.txt`
    Created with Windows win64 with windows-git openssl.exe - `"C:\Program Files\Git\mingw64\bin\openssl.exe" enc -e -aes-256-cbc -in aesop.txt -out aesop_win.openssl_aes256cbc_pbkdf2_10k -salt -pbkdf2 -iter 10000 -pass pass:password`
      * password is `password`
      * Approx 1.5Kb.

  * aesop_win_encryptpad.asc - gpg (GnuPG) encrypted from `aesop.txt`
    Created with Windows win32 encryptpad 0.5.0.2 beta https://github.com/evpo/EncryptPad/
      * password is `password`
      * Approx 1.1Kb.

  * aesop_win_encryptpad.gpg - gpg (GnuPG) encrypted from `aesop.txt`
    Created with Windows win32 encryptpad 0.5.0.2 beta https://github.com/evpo/EncryptPad/
      * password is `password`
      * Approx 0.8Kb.

  * aesop_win_winrar.aes256.zip - default AES-256 zip AE-1 encrypted from
    `aesop.txt` on Windows
    Created with Windows WinRAR 5.00 (32-bit)
      * password is `password`
      * Approx 0.8Kb.
      * has window newlines
      * us-ascii encoding
      * created using GUI
  * aesop_win_winrar.aes256stored.zip - uncompressed AES-256 zip AE-1 encrypted from
    `aesop.txt` on Windows
    Created with Windows WinRAR 5.00 (32-bit)
      * password is `password`
      * Approx 1.6Kb.
      * has window newlines
      * us-ascii encoding
      * created using GUI

  * aesop_linux_7z.aes256.zip - AE-2 AES-256 zip encrypted from
    `aesop.txt` on Windows
    Created with ARM Linux p7zip Version 16.02 (32-bit) https://www.7-zip.org/
      * password is `password`
      * Approx 0.9Kb.
      * has window newlines
      * us-ascii encoding
      * `7z a -tzip -mem=AES256 -ppassword aesop_linux_7z.aes256.zip encrypted.md`
  * aesop_linux_7z.aes256stored.zip - AE-2 uncompressed AES-256 zip encrypted from
    `aesop.txt` on Windows
    Created with ARM Linux p7zip Version 16.02 (32-bit) https://www.7-zip.org/
      * password is `password`
      * Approx 1.7Kb.
      * has window newlines
      * us-ascii encoding
      * `7z a -tzip -mem=AES256 -mx0 -ppassword aesop_linux_7z.aes256stored.zip encrypted.md`
  * aesop_win_7z.aes256.zip - AE-2 AES-256 zip encrypted from
    `aesop.txt` on Windows
    Created with Windows 7-Zip 19.00 (x64) https://www.7-zip.org/
      * password is `password`
      * Approx 0.9Kb.
      * has window newlines
      * us-ascii encoding
      * `7z a -tzip -mem=AES256 -ppassword aesop_win_7z.aes256.zip encrypted.md`
  * aesop_win_7z.aes256stored.zip - AE-2 uncompressed AES-256 zip encrypted from
    `aesop.txt` on Windows
    Created with Windows 7-Zip 19.00 (x64) https://www.7-zip.org/
      * password is `password`
      * Approx 1.7Kb.
      * has window newlines
      * us-ascii encoding
      * `7z a -tzip -mem=AES256 -mx0 -ppassword aesop_win_7z.aes256stored.zip encrypted.md`

  * aesop_linux_7z.old.zip - default old ZipCrypto zip encrypted from
    `aesop.txt` on Windows
    Created with ARM Linux p7zip Version 16.02 (32-bit) https://www.7-zip.org/
      * password is `password`
      * Approx 0.8Kb.
      * has window newlines
      * us-ascii encoding
      * `7z a -ppassword aesop_linux_7z.old.zip encrypted.md`
  * aesop_linux_7z.oldstored.zip - uncompressed old ZipCrypto zip encrypted from
    `aesop.txt` on Windows
    Created with ARM Linux p7zip Version 16.02 (32-bit) https://www.7-zip.org/
      * password is `password`
      * Approx 1.6Kb.
      * has window newlines
      * us-ascii encoding
      * `7z a -mx0 -ppassword aesop_linux_7z.oldstored.zip encrypted.md`

  * aesop_win_7z.old.zip - default old ZipCrypto zip encrypted from
    `aesop.txt` on Windows
    Created with Windows 7-Zip 19.00 (x64) https://www.7-zip.org/
      * password is `password`
      * Approx 0.8Kb.
      * has window newlines
      * us-ascii encoding
      * `7z a -ppassword aesop_win_7z.old.zip encrypted.md`
  * aesop_win_7z.oldstored.zip - uncompressed old ZipCrypto zip encrypted from
    `aesop.txt` on Windows
    Created with Windows 7-Zip 19.00 (x64) https://www.7-zip.org/
      * password is `password`
      * Approx 1.6Kb.
      * has window newlines
      * us-ascii encoding
      * `7z a -mx0 -ppassword aesop_win_7z.oldstored.zip encrypted.md`

  * aesop_win.vimcrypt3 - Vim Crypt Blowfish2 (VimCrypt~03) encrypted from
    `aesop.txt`
    Created with Windows vim 8.1.1 https://www.vim.org/
      * password is `password`
      * Approx 1.6Kb.
      * has window newlines
      * us-ascii encoding
  * aesop_win.vimcrypt2 - Vim Crypt Blowfish (VimCrypt~02) encrypted from
    `aesop.txt`
    Created with Windows vim 8.1.1 https://www.vim.org/
      * password is `password`
      * Approx 1.6Kb.
      * has window newlines
      * us-ascii encoding
  * aesop_win.vimcrypt1 - Vim Crypt old PkZip (VimCrypt~01) encrypted from
    `aesop.txt`
    Created with Windows vim 8.1.1 https://www.vim.org/
      * password is `password`
      * Approx 1.5Kb.
      * has unix/linux newlines
      * us-ascii encoding
  * aesop_linux.vimcrypt3 - Vim Crypt Blowfish2 (VimCrypt~03) encrypted from
    `aesop.txt`
    Created with ARM Linux vim 8.1.2269 https://www.vim.org/
      * password is `password`
      * Approx 1.5Kb.
      * has unix/linux newlines
      * us-ascii encoding
  * aesop_linux.vimcrypt2 - Vim Crypt Blowfish (VimCrypt~02) encrypted from
    `aesop.txt`
    Created with ARM Linux vim 8.1.2269 https://www.vim.org/
      * password is `password`
      * Approx 1.5Kb.
      * has unix/linux newlines
      * us-ascii encoding
  * aesop_linux.vimcrypt1 - Vim Crypt old PkZip (VimCrypt~01) encrypted from
    `aesop.txt`
    Created with ARM Linux vim 8.1.2269 https://www.vim.org/
      * password is `password`
      * Approx 1.5Kb.
      * has unix/linux newlines
      * us-ascii encoding
  * latin.txt - plain text file, single byte encoding
      * Approx 3.2Kb.
      * ISO-8859-1/Windows-1252 encoding
  * pg28_the_fables_of_aesop_utf8.txt - plain text file, utf-8 multi byte encoding
      * Approx 100Kb.
      * utf-8 encoding
      * From https://www.gutenberg.org/ebooks/28 - larger than 64Kb, yet not too big
      * NOTE includes BOM at start of file
      * compatabilty notes
        * Tombo 1.17 - Windows
          * will load BUT will display question mark for the BOM that is present (even when utf-8 is the encoding option)
          * will save cleanly - not sure how with 30Kb limits seen when copy/pasting
        * Tombo 2.0 beta 5 - Windows
          * will load BUT will display question mark for the BOM that is present (even when utf-8 is the encoding option)
          * will save cleanly
        * Kumagusu 1.21 - Android
          * will load, no BOM issues
  * pg28_the_fables_of_aesop_utf8.chi - Tombo Blowfish encrypted from `pg28_the_fables_of_aesop_utf8.txt`
      * Approx 100Kb.
      * utf-8 encoding
      * NOTE includes BOM at start of file
      * Created with `TomboCrypt.exe enc pg28_the_fables_of_aesop_utf8.chi password<pg28_the_fables_of_aesop_utf8.txt` from Tombo https://github.com/clach04/tombo
      * compatabilty notes
        * Tombo 1.17 - Windows
          * similar to the text file will load BUT will display question mark for the BOM that is present (even when utf-8 is the encoding option)
          * new lines missing, not a problem with text file (or Tombo 2.0 beta 5)
        * Tombo 2.0 beta 5 - Windows
          * will load BUT will display question mark for the BOM that is present (even when utf-8 is the encoding option)
          * no new line issues, that 1.17 has
          * will save cleanly
        * Kumagusu 1.21 - Android
          * will load, no BOM issues
          * will save cleanly
  * test_winnewlines.u001.jenc - U001 jenc, us-ascii encoding
  * test_winnewlines.v001.jenc - V001 jenc, us-ascii encoding
  * utf8_latin.txt - plain text file, utf-8 multi byte encoding
      * Approx 3.4Kb.
      * utf-8 encoding

Vim Crypt files created via:

    vim -c ":setlocal cm=blowfish2"  puren_tonbo/tests/data/aesop_linux.vimcrypt3
    vim -c ":setlocal cm=blowfish"  puren_tonbo/tests/data/aesop_linux.vimcrypt2
    vim -c ":setlocal cm=zip"  puren_tonbo/tests/data/aesop_linux.vimcrypt1


TODO WinRAR has a command line rar.exe, but it's not clear if AE-1/AE-2 can be generated using it.
