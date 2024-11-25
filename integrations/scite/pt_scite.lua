-- SciTE Lua Puren Tonbo script for reading encrypted files
-- https://www.scintilla.org/SciTE.html
--   - see API docs https://www.scintilla.org/PaneAPI.html
--   - see API docs http://lua-users.org/wiki/UsingLuaWithScite
-- https://github.com/clach04/puren_tonbo
--
-- Can be used standalone or with ParsKorata (http://lua-users.org/wiki/ParsKorata) mini/simple ExtMan compatible script
-- Untested with ExtMan - http://lua-users.org/wiki/SciteExtMan

-- Only supports Tombo format *.chi files
-- Usage, ensure:
--  1) operating system environment variable PT_PASSWORD is set before loading scite (or that ptcipher has GUI password prompt support)
--  2) that ptcipher specified is set or in the path, i.e. one of:
--      a) ptcipher exe is in path
--      b) set OS env PTCIPHER_EXE to fully qualitied path to exe
--      c) scite variable/property set to path, for example; props['clach04.puren_tonbo.ptcipher'] = 'C:\\code\\puren_tonbo\\py3.12.5venv\\Scripts\\ptcipher.exe'

-- TODO
--  * write support - file that was loaded
--  * write support - file that was loaded - missing exe, password, unsupported extension (maybe lib missing)
--  * write support - new file
--  * test utf8 read/write
--  * test cp1252/latin1 read/write

local is_win = props['PLAT_WIN']=="1"
local disable_save = false

-- http://lua-users.org/wiki/StringRecipes
local function starts_with(str, start)
   return str:sub(1, #start) == start
end

local function ends_with(str, ending)
   return ending == "" or str:sub(-#ending) == ending
end


local PTCIPHER_EXE = os.getenv('PTCIPHER_EXE') or props['clach04.puren_tonbo.ptcipher'] --  or 'ptcipher'
if PTCIPHER_EXE then
    if PTCIPHER_EXE == '' then
        PTCIPHER_EXE = 'ptcipher'  -- assume in path
    end
end
--print('DEBUG PTCIPHER_EXE: >' .. PTCIPHER_EXE .. '<')

local function determine_encrypted_file_extensions()
  local hard_coded_file_extensions = true
  local hard_coded_file_extensions = false
  if hard_coded_file_extensions == true then
    -- avoids process spawning unless an actual encrypted file is loaded
    return {
        'gz', 'Z',  -- no password needed, no encryption
        'chi', 'chs', 'aes.zip', 'aes256.zip', 'aeszip', 'old.zip', 'aes256stored.zip', 'oldstored.zip', 'aes256lzma.zip', 'aes256bzip2.zip', 'vimcrypt', 'vimcrypt1', 'vimcrypt2', 'vimcrypt3'
    }
  end
  local file_extensions = {}
  local prog = PTCIPHER_EXE .. ' --list-formats --no-prompt'
  local f
  if is_win then
      f = io.popen(prog, 'rb')  -- read
      -- binary under Linux read fails with; attempt to index a nil value (local 'f')
  else
      f = io.popen(prog, 'r')  -- read
      --works for Linux with scite v4.0.0
  end
  -- line at a time processing
  local look_for_file_types=false
  for line in f:lines() do
      if starts_with(line, 'Libs:') then
        look_for_file_types = false
      end
      if look_for_file_types then
        --print(line)
        for w in line:gmatch("%S+") do
          --print(w);
          if (w ~= 'txt') and (w ~= 'md') then
            table.insert(file_extensions, w)
            --file_extensions[w] = true
          end
          break
        end
        -- https://stackoverflow.com/questions/1426954/split-string-in-lua
        -- http://lua-users.org/wiki/StringTrim
      end
      if starts_with(line, 'Formats:') then
        look_for_file_types = true
      end
  end -- for loop

  local popen_success = f:close()  -- this is nil or boolean, not integer  Lua 5.2 feature?
  if popen_success ~= true then
    print('determine_encrypted_file_extensions popen_success: ' .. tostring(popen_success))
  end
  return file_extensions
end
enc_types = determine_encrypted_file_extensions()
--print(enc_types)  -- does NOT show table contents

local function IsPurenTonboEncryptedFilename(filename)
  filename_lower = string.lower(filename)
  --if ends_with(filename_lower, '.chi') then -- Tombo file only (working) check
  for k,v in pairs(enc_types) do
    --if ends_with(filename_lower, k) then
    if ends_with(filename_lower, v) then
      return true
    end
  end
  return false
end

local function SaveEncryptedFile(filename)
  --print('OnBeforeSave')  -- to output pane
  --print(filename)  -- to output pane
  if IsPurenTonboEncryptedFilename(filename) then
    --print('block CHI save')  -- to output pane
    --print(filename)  -- to output pane
    if disable_save then
        print('Refusing to save, saving disabled (probably due to failed decryption/load)')
        return true -- indicate to editor NOT to save
    end -- if disable_save
    -- consider setting editor.ReadOnly to true? But only for files that failed to load, not non-existing (i.e. new) files
    --editor:EmptyUndoBuffer()
    --editor.UndoCollection=1
    --return true -- indicate to editor NOT to save
    plain_text = editor:GetText()
    --print('-------------')  -- to output pane
    --print(plain_text)  -- to output pane
    --print('-------------')  -- to output pane
    -- default encryption type based on file extension
    local prog = PTCIPHER_EXE .. ' --silent --password-prompt=gui --encrypt --output "' .. filename .. '"'
    --print(prog)

    if is_win then
        -- https://www.lua.org/manual/5.1/manual.html#pdf-io.popen
        -- > This function is system dependent and is not available on all platforms.
        f = io.popen(prog, 'wb')  -- write
        -- binary under Linux read fails with; attempt to index a nil value (local 'f')
    else
        f = io.popen(prog, 'w')  -- write
        --works for Linux with scite v4.0.0
    end -- is win
    write_result = f:write(plain_text)  -- write entire file, write_result is file pointer/handle?
    local popen_success = f:close()  -- saw nil on failure and true on success
    if popen_success == true then
        -- if no error
        editor:SetSavePoint()  -- indicate to editor that save happened and file is unchanged - whether it really did or not ;-)
    else
        -- error handling
        print('Error Encrypt write/save ' .. filename)  -- to output pane
        print('PTCIPHER_EXE ' .. PTCIPHER_EXE)  -- to output pane
        print('popen_success: ' .. tostring(popen_success))
        -- either nil or false - so far only seen nil for both; failure to launch (missing PTCIPHER_EXE) and also exe launched and returned errors (like bad password)
        -- empty output seen for missing exe and also missing file - TODO consider adding extra output to ptcipher for missing file case
        print('failed to save using '.. prog)
        print('failed to save using '.. PTCIPHER_EXE)
        --editor:AddText('failed to load using '.. PTCIPHER_EXE)
        editor:AppendText('\nfailed to load using '.. prog)
        editor:AppendText('\nSuggestions, check:\n')
        editor:AppendText('  1) file exists\n')
        editor:AppendText('  2) environment variable PTCIPHER_EXE / property clach04.puren_tonbo.ptcipher - ptcipher script/executable\n')
        editor:AppendText('  3) environment variable PT_PASSWORD - password\n')
    end  -- error handling

    return true -- indicate to editor NOT to save
  end  -- IsPurenTonboEncryptedFilename
end  -- SaveEncryptedFile

-- parskorata_extman.lua does NOT have scite_OnBeforeSave()
if scite_OnBeforeSave~=nil then
  scite_OnBeforeSave(SaveEncryptedFile)
else
    -- avoid: attempt to call a nil value (global 'scite_OnBeforeSave')
    function OnBeforeSave(filename)
      return SaveEncryptedFile(filename)
    end  -- OnBeforeSave
end

local function LoadEncryptedFile(filename)
  --print('OnOpen')  -- to output pane
  --print(filename)  -- to output pane
  if IsPurenTonboEncryptedFilename(filename) then
    --print('DEBUG block CHI load ' .. filename)  -- to output pane
    --editor:EmptyUndoBuffer()
    --editor.UndoCollection=1
    --editor:SetSavePoint() -- indicate to editor that save happened - whether it really did or not ;-)
    --return false  - reverse value compared with before save, false tells editor to NOT load and to NOT open a new pane
    -- either return false and open new tab and populate OR replace content in tab
    --  right now current implementation has 2 file reads, once for scite which is thrown away and another for ptcipher so slightly inefficient

    -- TODO SciTE 4.4.4 on Windows adds create.hidden.console=1 option to stop console window flashing when Lua script calls os.execute or io.popen.https://groups.google.com/g/scite-interest/c/QOhizNSEejU/m/qXslloxnCgAJ\
    -- getenv works, there is no setenv unless using posix stdlib extension http://luaposix.github.io/luaposix/modules/posix.stdlib.html#setenv
    -- os.environ['PT_PASSWORD'] = 'bad'
    -- NOTE expects PT_PASSWORD to be set, there is no way to set this from lua and do not want to use command line arg to pass password
    local PT_PASSWORD = os.getenv('PT_PASSWORD')
    if PT_PASSWORD==nil then
        print('WARNING: PT_PASSWORD has not been set')
    end
    local prog = PTCIPHER_EXE .. ' --decrypt "' .. filename .. '" --output=- --password-prompt=gui'
    --print(prog)
    local f
    if is_win then
        f = io.popen(prog, 'rb')  -- read
        -- binary under Linux read fails with; attempt to index a nil value (local 'f')
    else
        f = io.popen(prog, 'r')  -- read
        --works for Linux with scite v4.0.0
    end
    program_output = f:read('*a')  -- read entire file
    -- TODO FIXME if program_output is empty treat as an error
    --print(program_output)
    local popen_success = f:close()  -- this is nil or boolean, not integer  Lua 5.2 feature?
    editor:SetText(program_output)  -- this may be real content (decrypted text) or error text (e.g. bad password), check popen_success to determine
    if popen_success == true then
        -- if no error
        editor:SetSavePoint()  -- indicate to editor that save happened and file is unchanged - whether it really did or not ;-)
    else
        -- error handling
        disable_save = true  -- don't allow accidental saving, this impacts all tabs for safety
        -- https://github.com/clach04/puren_tonbo/issues/73 - scite lua integration will allow user to accidentally overrwrite encrypted files with error messages

        print('Error Decrypt loading ' .. filename)  -- to output pane
        print('PTCIPHER_EXE ' .. PTCIPHER_EXE)  -- to output pane
        print('popen_success: ' .. tostring(popen_success))
        -- either nil or false - so far only seen nil for both; failure to launch (missing PTCIPHER_EXE) and also exe launched and returned errors (like bad password)
        -- empty output seen for missing exe and also missing file - TODO consider adding extra output to ptcipher for missing file case
        print('failed to load using '.. prog)
        print('failed to load using '.. PTCIPHER_EXE)
        --editor:AddText('failed to load using '.. PTCIPHER_EXE)
        editor:AppendText('\nfailed to load using '.. prog)
        editor:AppendText('\nSuggestions, check:\n')
        editor:AppendText('  1) file exists\n')
        editor:AppendText('  2) environment variable PTCIPHER_EXE / property clach04.puren_tonbo.ptcipher - ptcipher script/executable\n')
        editor:AppendText('  3) environment variable PT_PASSWORD - password\n')
    end  -- error handling
  end  -- encrypted file
end  -- LoadEncryptedFile

-- parskorata_extman.lua does NOT have scite_OnBeforeSave()
if scite_OnOpen ~= nil then
  scite_OnOpen(LoadEncryptedFile)
else
    -- avoid: attempt to call a nil value (global 'scite_OnOpen')
    function OnOpen(filename)
      return LoadEncryptedFile(filename)
    end  -- OnOpen
end
