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
    if $PT_PASSWORD == ""
        let $PT_PASSWORD = inputsecret("ptcipher Password: ")
    endif
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
    if $PT_PASSWORD == ""
        " TODO refactor into a function for password prompt
        let $PT_PASSWORD = inputsecret("ptcipher Password: ")
    endif
    let l:expr = "1,$!ptcipher -d <afile>"
    silent! execute l:expr
    if v:shell_error
        silent! 0,$y
        silent! undo
        echo "COULD NOT DECRYPT USING EXPRESSION: " . expr
        echo "ERROR FROM Puren Tonbo:"
        echo @"
        echo "COULD NOT DECRYPT"
        echo "Unsetting local OS env PT_PASSWORD"
        let $PT_PASSWORD = ""
        return
    endif

    set nobin
    set cmdheight&
    set shell&
    execute ":doautocmd BufReadPost ".expand("%:r")
    redraw!
endfunction

function! s:PurenTonboWritePre()
    " Likely Linux/Unix only due to Windows buffered IO issues (and use of /bin/sh)
    " did experiment with using <afile> and having ptcipher write directly
    " that write/save works, but then get prompt from vim:
    "   WARNING: The file has been changed since reading it!!!
    "   Do you really want to write to it (y/n)?
    " Say no, ptcipher had already written to file
    " Saying yes, outputs the stdout/stderror from ptcipher into file, e.g.:
    "   Read in from stdin...DEBUG tmp_out_filename '/..../puren_tonbo/write.aeszip20230311_170505e0grbho9'

    set cmdheight=3
    set shell=/bin/sh
    set bin

    " 0 and 1 both work so far under Linux

    " vim prompts for password, put into OS env PT_PASSWORD which ptcipher picks up automatically
    " error message that requires dismisal displayed, then raw file loaded/displayed in buffer
    " if using stdout for encryption, ptcipher needs to be told which scheme/file type to use
    " use the file extension as the format/encryption cipher
    let l:file_extension = expand("<afile>:e")
    if $PT_PASSWORD == ""
        let $PT_PASSWORD = inputsecret("ptcipher Password: ")
    endif
    " TODO prompt twice to avoid incorrect passwords? and/or only prompt if PT_PASSWORD is not set
    " WARNING! end up with "Read in from stdin..." as prefix in file without --silent flag, even though that was sent to stderr
    "let l:expr = "1,$!ptcipher --cipher " . l:file_extension . " -e -o -"
    let l:expr = "1,$!ptcipher --silent --cipher " . l:file_extension . " -e -o -"
    silent! execute l:expr
    if v:shell_error
        silent! 0,$y
        silent! undo
        echo "COULD NOT ENCRYPT USING EXPRESSION: " . expr
        echo "ERROR FROM Puren Tonbo:"
        echo @"
        echo "COULD NOT ENCRYPT"
        return
    endif

    set nobin
    set cmdheight&
    set shell&
    execute ":doautocmd BufReadPost ".expand("%:r")
    redraw!
endfunction

function! s:PurenTonboWritePost()
    silent! undo
    set nobin
    set shell&
    set cmdheight&
    redraw!
endfunction


autocmd BufReadPre,FileReadPre     *.chi,*.asc,*.gpg,*aeszip call s:PurenTonboReadPre()
autocmd BufReadPost,FileReadPost   *.chi,*.asc,*.gpg,*aeszip call s:PurenTonboReadPost()
autocmd BufWritePre,FileWritePre   *.chi,*.asc,*.gpg,*aeszip call s:PurenTonboWritePre()
autocmd BufWritePost,FileWritePost *.chi,*.asc,*.gpg,*aeszip call s:PurenTonboWritePost()

augroup END

