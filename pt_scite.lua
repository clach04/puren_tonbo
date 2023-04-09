-- SciTE Lua Puren Tonbo script for reading encrypted files
-- https://www.scintilla.org/SciTE.html
-- https://github.com/clach04/puren_tonbo
-- Can be used standalone or with ParsKorata (http://lua-users.org/wiki/ParsKorata) mini/simple ExtMan compatible script
-- Untested with ExtMan - http://lua-users.org/wiki/SciteExtMan

-- Only supports Tombo format *.chi files
-- Usage, ensure:
--  1) operating system environment variable PT_PASSWORD is set before loading scite
--  2) that ptcipher is in path or set os env PTCIPHER_EXE to path

-- http://lua-users.org/wiki/StringRecipes
local function starts_with(str, start)
   return str:sub(1, #start) == start
end

local function ends_with(str, ending)
   return ending == "" or str:sub(-#ending) == ending
end



local PTCIPHER_EXE = os.getenv('PTCIPHER_EXE') or 'ptcipher'

local function determine_encrypted_file_extensions()
-- TODO encrypted filename determination PTCIPHER_EXE, '--list-formats', '--no-prompt'
  local file_extensions = {}
  local prog = PTCIPHER_EXE .. ' --list-formats --no-prompt'
  local f = io.popen(prog, 'rb')  -- read
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
            --table.insert(file_extensions, w)
            file_extensions[w] = true
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
  print('determine_encrypted_file_extensions popen_success: ' .. tostring(popen_success))
  return file_extensions
end
enc_types = determine_encrypted_file_extensions()
--print(enc_types)  -- does NOT show table contents

local function IsPurenTonboEncryptedFilename(filename)
  filename_lower = string.lower(filename)
  --if ends_with(filename_lower, '.chi') then -- Tombo file only (working) check
  --if enc_types[filename_lower] ~= nil then -- not working yet
  for k,v in pairs(enc_types) do
    if ends_with(filename_lower, k) then
      return true
    end
  end
  return false
end

-- NOTE SaveEncryptedFile() does not (yet) support saving encrypted files, instead it prevents accidental saving
local function SaveEncryptedFile(filename)
  --print('OnBeforeSave')  -- to output pane
  --print(filename)  -- to output pane
  if IsPurenTonboEncryptedFilename(filename) then
    --print('block CHI save')  -- to output pane
    --print(filename)  -- to output pane
    print('blocked CHI save ' .. filename)  -- to output pane
    --editor:EmptyUndoBuffer()
    --editor.UndoCollection=1

    --editor:SetSavePoint() -- indicate to editor that save happened - whether it really did or not ;-)
    return true -- indicate to editor NOT to save
  end
end

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
    print('DEBUG block CHI load ' .. filename)  -- to output pane
    --editor:EmptyUndoBuffer()
    --editor.UndoCollection=1
    --editor:SetSavePoint() -- indicate to editor that save happened - whether it really did or not ;-)
    --return false  - reverse value compared with before save, false tells editor to NOT load and to NOT open a new pane
    -- either return false and open new tab and populate OR replace content in tab

    -- TODO SciTE 4.4.4 on Windows adds create.hidden.console option to stop console window flashing when Lua script calls os.execute or io.popen.https://groups.google.com/g/scite-interest/c/QOhizNSEejU/m/qXslloxnCgAJ\
    -- getenv works, there is no setenv unless using posix stdlib extension http://luaposix.github.io/luaposix/modules/posix.stdlib.html#setenv
    -- os.environ['PT_PASSWORD'] = 'bad'
    -- NOTE expects PT_PASSWORD to be set, there is no way to set this from lua and do not want to use command line arg to pass password
    local prog = PTCIPHER_EXE .. ' --decrypt "' .. filename .. '" --output=- --no-prompt'
    local f = io.popen(prog, 'rb')  -- read
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
        print('popen_success: ' .. tostring(popen_success))
        -- either nil or false - so far only seen nil for both; failure to launch (missing PTCIPHER_EXE) and also exe launched and returned errors (like bad password)
        -- empty output seen for missing exe and also missing file - TODO consider adding extra output to ptcipher for missing file case
        print('failed to load using '.. prog)
        print('failed to load using '.. PTCIPHER_EXE)
        --editor:AddText('failed to load using '.. PTCIPHER_EXE)
        editor:AppendText('\nfailed to load using '.. prog)
        editor:AppendText('\nSuggestions, check:\n')
        editor:AppendText('  1) file exists\n')
        editor:AppendText('  2) environment variable PTCIPHER_EXE - ptcipher script/executable\n')
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
