Design only this session; implementation deferred.

Problem: ptrecrypt.process_file() (puren_tonbo/tools/ptrecrypt.py:120-227) writes the new file with write_encrypted_file() -> plain open(filename,'wb') (line 113). No tempfile, no file_replace(), no .bak. Two consequences:

1. Non-atomic: an interruption mid-write leaves a truncated note and the source already overwritten (existing_files_resolution='replace' is the only way to get in-place behaviour at all).
2. Leftover source: the source is removed only when existing_files_resolution == 'delete' (line 219). With 'replace' and a changed extension (the normal case: --cipher .zip on a .txt note) both files remain.

Contrast: the library path note_contents_save_native_filename() (__init__.py:2011) already does tempfile + file_replace() + optional .bak, and file_replace() (__init__.py:1884) is os.replace on py3.

Proposed fix:
- Write to a NamedTemporaryFile in the destination directory, then file_replace(tmp, new_filename).
- When new_filename != filename, remove the source after a successful replace (i.e. make 'replace' mean replace, not write-alongside).
- Keep existing_files_resolution='stop' as the default for the CLI; add .bak via the existing backup flag rather than a new one.
- process_file() currently returns None on skip/unsupported and raises on error; return a per-file result so callers (ptig) can report per-file status.

Decisions from the grilling session (2026-11-25):
- In-place replace is the intended operation; making the user delete the old copy is not acceptable.
- Hard-fail on an existing target unless the user explicitly asks for overwrite.
- Verbose by default (one 'old -> new' line per file, also under --simulate), quiet mode as an option.
- Tests should use rot13/rot47 (SubstitutionCipher, needs_key=False) to avoid password plumbing.

Blocks: ptig recrypt/encrypt command (separate issue), which needs atomic replace before it can default to destructive in-place re-encryption.

Issue 180 (https://github.com/clach04/puren_tonbo/issues/180) is the original ptig request; the todo claiming ptig's command was 'code complete but missing real docs' was wrong - no such command exists in this tree.