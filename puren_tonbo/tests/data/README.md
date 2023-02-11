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
  * aesop_win.vimcrypt3 - Vim Crypt Blowfish2 (VimCrypt~03) encrypted from
    `aesop.txt`
    Created with Windows vim 8.1.1 https://www.vim.org/
      * password is `password`
      * Approx 1.5Kb.
  * aesop_win.vimcrypt2 - Vim Crypt Blowfish (VimCrypt~02) encrypted from
    `aesop.txt`
    Created with Windows vim 8.1.1 https://www.vim.org/
      * password is `password`
      * Approx 1.5Kb.
  * aesop_win.vimcrypt1 - Vim Crypt old PkZip (VimCrypt~01) encrypted from
    `aesop.txt`
    Created with Windows vim 8.1.1 https://www.vim.org/
      * password is `password`
      * Approx 1.5Kb.
