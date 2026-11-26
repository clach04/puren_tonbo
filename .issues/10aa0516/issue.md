Merged 2026-11-25: this issue absorbs hash:fa00c950 (rot13/47 are not substitution ciphers; the SubstitutionCipher marker class is a misnomer doing double duty). Raised B -> B (was C) because the failure is user-visible today, not cosmetic: four call sites prompt for a password that is ignored. fa00c950's audit trail is reproduced in the "SubstitutionCipher misnomer" section below and in comments.

Symptom: puren_tonbo.is_encrypted('note.rot13') is True, but Rot13.needs_key is False and Rot13.__init__ ignores the key entirely (SubstitutionCipher, __init__.py:381-388). So any caller that branches on is_encrypted() instead of needs_key prompts for a password that cannot be used. Verified user-visible today:
- ptcipher on a rot13 note prompts for a password, then ignores it (ptcipher.py:186).
- ptig do_edit on a rot13 note prompts, then exports the ignored password as PT_PASSWORD (ptig.py:1302).
- ptnewline_check.py:105 and pttkview.py:177 same shape.
- ptgrep -k / fts "encrypted only" scope includes rot13/47 (encrypted_filename_filter at __init__.py:3118, :3241), so one flag conflates "encrypted" with "needs a key".

Callers that already do it right: ptig.py:1139 (do_new) and note_contents_load_filename() (__init__.py:1948) both use handler_class.needs_key. ptrecrypt.py:144 does no check at all (harmless for rot13, correct by accident for zip).

Root cause, from the commits:
- 483ccdd (2024-09-07, "Implement #157 - rot13 support and improve testing") added needs_key (BaseFile True, RawFile False, SubstitutionCipher False) and switched note_contents_load_filename() from "is RawFile" to "not needs_key". It did NOT touch the extension-based encrypted/plain filters.
- 1203fe2 (2023-04-23, "Filename extension filters - encrypted and plain text") created encrypted_filename_filter() predating rot13; its rule was "not RawFile.extensions" - i.e. a denylist, so anything new counted as encrypted.
- 657a34a (2024-11-02) rewrote the rule to issubclass(handler_class, EncryptedFile), which still includes SubstitutionCipher.
- 78f66e2 (2024-10-04) changed isinstance -> issubclass in the same predicate (a real fix, unrelated).

So "encrypted" has meant two different things since 2024-09: "is an EncryptedFile subclass" (filters) and "needs a key" (load path). rot13/47 are the only handlers where they disagree (verified: the only extensions flagged encrypted with needs_key=False are .rot13 and .rot47; .gz/.Z are CompressedFile, not EncryptedFile).

Why it is not as bad as it could be: SubstitutionCipher is not a CompressedFile, so plaintext_filename_filter() correctly reports a .rot13 as not-plain; only the "does this need a password" question is wrong. Defence-in-depth reading (treat anything not-plain as encrypted) is defensible, but then the prompt is misleading and needs_key should be the documented source of truth.

## SubstitutionCipher misnomer (absorbed from hash:fa00c950)

rot13/rot47 are NOT substitution ciphers and the class hierarchy says they are. SubstitutionCipher(EncryptedFile) (__init__.py:381) is a marker base class whose only job is needs_key=False plus a no-op __init__; Rot13/Rot47 subclass it (:389, :412). rot13 is a fixed Caesar shift, rot47 a printable-ASCII rotation - neither is keyed, neither is a cipher in any meaningful sense. A substitution cipher is keyed.

The class does double duty: (a) 'is an EncryptedFile subclass', which is what 'encrypted' means to every filter, and (b) 'needs no key', which is what 'needs a password' means to the load path. That is this issue.

Constraints (do NOT do the naive thing):
- supported_filetypes_info(unencrypted_only=True) (__init__.py:1631) skips only EncryptedFile subclasses. If SubstitutionCipher stops being an EncryptedFile, .rot13/.rot47 fall into the PLAIN list and plaintext_filename_filter('a.rot13') becomes True - verified by simulation - which changes default search scope (__init__.py:3118, :3241).
- The registry loop at :1248-1260 registers RawFile/SubstitutionCipher/CompressedFile subclasses into file_type_handlers. Renaming without updating that loop, or reparenting without adding the new base, silently drops .rot13/.rot47 and filename2handler raises UnsupportedFile. all_file_type_handlers (:1236-1246) only excludes RawFile, so it is unaffected either way.
- VimDecrypt is needs_key=True but only registered when the vimdecrypt lib is present, so the agreement test must not assume it.

Options (naming + semantics, decided together):
a) Rename only: SubstitutionCipher -> KeylessObfuscation (or UnkeyedTransform), same base (EncryptedFile), needs_key=False. Smallest, fixes the naming lie, no behaviour change.
b) Reparent to BaseFile and add a third state to the filters so 'encrypted' means needs_key. Cleaner model, touches every filter and the registry loop.
c) Make the marker honest with an explicit capability flag (e.g. is_encryption=False) so filters stop overloading the class hierarchy. Most explicit, most churn.
Whichever is chosen, needs_key becomes the documented source of truth, reachable without importing the class (no public needs_key(filename) accessor exists today - is_encrypted() is the only public predicate, which is why the proxy got used).

Fix options for the predicate/callers:
x) Make encrypted_filename_filter() exclude handlers with needs_key=False (filters then mean "needs a key").
y) Change the four callers to handler_class.needs_key and document needs_key as the source of truth.
z) Both: (x) for the filters, (y) where a prompt is involved.
Plus: a test asserting is_encrypted()/needs_key agree (or that the classification is explicit) for every registered handler, so a future handler cannot reintroduce the split.

Also fix the user-facing text in the same pass: README.md:624 and :642 call rot13/rot47 'Symmetric Substitution cipher with no passphrase/password/key support' ('symmetric' and 'cipher' are both wrong), CONCERNS.md:203, ARCHITECTURE.md:33 and :151.

Recommendation: (a) rename now, fold (b)/(c) into the predicate decision here, then (z). One coherent change, not two half-fixes.