augroup PurenTonbo_encrypted
autocmd!

function! s:PurenTonboReadPre()
    set cmdheight=3
    set viminfo=
    set noswapfile
    set shell=/bin/sh
    set bin
endfunction

function! s:WorksErrorsToBufferPurenTonboReadPost()

    " using filename <afile> rather than stdin to tool due to unbuffered issues with python (bins and __main__) and Windows
    " 0 and 1 both work so far under Linux

    " experiment hard coded password
    "silent 1,$!ptcipher -d -p password <afile>
    "silent 0,$!ptcipher -d -p password <afile>

    " ptcipher prompts for password
    " on error bugfer fills with error text
    "silent 1,$!ptcipher -d <afile>

    " vim prompts for password, put into OS env PT_PASSWORD which ptcipher picks up automatically
    let $PT_PASSWORD = inputsecret("ptcipher Password: ")
    silent 1,$!ptcipher -d <afile>

    set nobin
    set cmdheight&
    set shell&
    execute ":doautocmd BufReadPost ".expand("%:r")
    redraw!
endfunction

function! s:PurenTonboReadPost()

    " using filename <afile> rather than stdin to tool due to unbuffered issues with python (bins and __main__) and Windows
    " 0 and 1 both work so far under Linux

    " vim prompts for password, put into OS env PT_PASSWORD which ptcipher picks up automatically
    " error message that requires dismisal displayed, then raw file loaded/displayed in buffer
    let $PT_PASSWORD = inputsecret("ptcipher Password: ")
    let l:expr = "1,$!ptcipher -d <afile>"
    silent! execute l:expr
    if v:shell_error
        silent! 0,$y
        silent! undo
        echo "COULD NOT DECRYPT USING EXPRESSION: " . expr
        echo "ERROR FROM Puren Tonbo:"
        echo @"
        echo "COULD NOT DECRYPT"
        return
    endif

    set nobin
    set cmdheight&
    set shell&
    execute ":doautocmd BufReadPost ".expand("%:r")
    redraw!
endfunction

autocmd BufReadPre,FileReadPre     *.chi,*.asc,*.gpg,*aeszip call s:PurenTonboReadPre()
autocmd BufReadPost,FileReadPost   *.chi,*.asc,*.gpg,*aeszip call s:PurenTonboReadPost()
" TODO write not implemented!
" WARNING writing with this config will write plain text content, withOUT encryption!
autocmd BufWritePre,FileWritePre   *.chi,*.asc,*.gpg call s:PurenTonboWritePre()
autocmd BufWritePost,FileWritePost *.chi,*.asc,*.gpg call s:PurenTonboWritePost()

augroup END

