# test data

Ideally generated with external tools that Puren Tonbo can validate against.

  * aesop.txt - plain text version of shortest Aesop fable there is,
    so suitable for realistic test data.
      * has window newlines
      * us-ascii encoding
      * Contains long lines (one is 1435 bytes)
      * Approx 1.5Kb.

  * aesop.chi -  Tombo Blowfish encrypted from `aesop.txt`
    Created with Windows win32 Tombo http://tombo.sourceforge.jp/En/
      * password is `password`
      * Approx 1.5Kb.

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
  * aesop_linux.vimcrypt3 - Vim Crypt Blowfish2 (VimCrypt~03)  encrypted from
    `aesop.txt`
    Created with ARM Linux vim 8.1.2269 https://www.vim.org/
      * password is `password`
      * Approx 1.5Kb.
      * has unix/linux newlines
      * us-ascii encoding
  * aesop_linux.vimcrypt2 - Vim Crypt Blowfish (VimCrypt~02)  encrypted from
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

Vim Crypt files created via:

    vim -c ":setlocal cm=blowfish2"  puren_tonbo/tests/data/aesop_linux.vimcrypt3
    vim -c ":setlocal cm=blowfish"  puren_tonbo/tests/data/aesop_linux.vimcrypt2
    vim -c ":setlocal cm=zip"  puren_tonbo/tests/data/aesop_linux.vimcrypt1


TODO WinRAR has a command line rar.exe, but it's not clear if AE-1/AE-2 can be generated using it.
