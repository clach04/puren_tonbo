Design only this session; implementation deferred. Depends on the ptrecrypt atomic-save issue (hash:a5b3f4d9).

Origin: todo entry 'ptig needs ptrecrypt, recrypt, encrypt command support https://github.com/clach04/puren_tonbo/issues/180 , command line code complete but missing real docs'. Reading (corrected 2026-11-25): the todo meant puren_tonbo (the project) already has the tools - ptrecrypt.py, ptcipher.py - that code is complete, and what is missing is real docs; the ptig command is the missing integration. NOT a claim that ptig already had recrypt support (an earlier revision of this issue said the todo was 'verified wrong'; that was an over-read). ptig has no recrypt/encrypt command (do_* ends at do_version); its only write paths are do_new and do_edit. So: implement the command, then document.

Decisions (grilling session, 2026-11-25):
- One command, do_recrypt, with do_encrypt as an alias (same code path; 'encrypt' is the discoverable verb, not a second implementation).
- Targets: reuse validate_result_id() - comma/space separated result numbers ('1,3,5') and plain paths. A path that is a directory walks it (recurse_notes + supported_filename_filter, like ptrecrypt's directory branch). Bare 'recrypt' with no argument is an error, never 'all results'.
- In place by default: the original is replaced. Rationale: making the user delete the old copy is not acceptable; the command is destructive and the mitigation is confirmation, not a second file.
- Hard-fail when the target already exists unless the user explicitly requests overwrite.
- Flags via a PtigParser like fts_index (pending final confirmation): --cipher, --new-password, --simulate, --force-newline, --existing-files.
- Output verbose by default: one 'old -> new' line per file, plus a summary ('3 recrypted, 1 skipped, 0 failed'); quiet mode as an option.
- file_hits is cleared after a recrypt with the message 'results cleared, search again' - the old names may no longer exist.
- FTS: never re-index automatically (potentially costly). Print a warning that fts_index should be re-issued; the user decides.
- No new session-password command; 'set enc' already covers it.

Open: exact flag set, whether do_encrypt's docstring differs, and whether --cipher is required for a plain source.

Blocks on: hash:a5b3f4d9 (atomic save) - ptig must not inherit the non-atomic overwrite.