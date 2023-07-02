# scite with python

From https://github.com/moltenform/scite-with-python

Tested with 32-bit Windows binaries https://github.com/moltenform/scite-with-python/releases/tag/v0.7.4

Supports:

  * loading (decrypting) by spawning ptcipher
  * saving (encrypting) by spawning ptcipher

TODO

  * code clean up
      * remove/comment out debug code (replace with logging)
  * look at other ways of passing in password than environment variable
      * prompt in GUI?
      * keyring?
  * try importing puren_tonbo instead of using external binary and pipes
  * find out if there is scite python3?

## Setup

Important to use the scite properties file shipped with scite-with-python, one option:


    (py310venv) C:\code\py\puren_tonbo\scite_with_python_0_7_4_win32>type pyscite.bat
    @echo off
    setlocal

    REM from https://github.com/moltenform/scite-with-python

    REM ensure using correct config location
    REM TODO edit this location to where scite_with_python has been extracted
    set SciTE_HOME=C:\code\py\puren_tonbo\scite_with_python_0_7_4_win32

    REM modifed (or added files)
    rem tools_internal\ptplugin\register.properties tools_internal\ptplugin\__init__.py properties\SciTEGlobal.properties
    REM check  doc\SciTEWithPythonAPIReference.html

    scite %*

    endlocal

Then copy this directory into the scite_with_python root, so end up with:

    C:\....\scite_with_python\pt_scite_with_python

Then edit `properties\SciTEGlobal.properties` and add at the end:

    ## clach04 debug
    # puren_tonbo plugin from
    # for use with https://github.com/moltenform/scite-with-python - tested with scite_with_python_0_7_4_win32
    #import tools_internal/pt_scite_with_python/register
    import pt_scite_with_python/register

Ensure ptcipher is in the path (or set OS environment variable `PTCIPHER_EXE` to path).

Set password using regular os environment variable, `PT_PASSWORD`, There is no prompt (or keyring) support.
