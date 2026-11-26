Consider only if the zip-based password tests (hash:a5b3f4d9 / hash:6a77677e) turn out to be unusable. Do NOT implement speculatively.

Why it keeps coming up: PurePyZipAES needs pyzipper/mzipaes and produces a binary container (single entry 'encrypted.md'), which is awkward for manual testing and for old Pythons. A flat XOR cipher with a password would give needs_key=True coverage with no third-party lib and a file you can cat.

Why it is probably a bad idea:
- A new handler is not test-only. file_type_handlers is built by reflection over dir() (__init__.py:1248), so the class is picked up by filename2handler(), ptcipher --list-formats, ptcipher, ptgrep, ptig and pt_open. It ships in a security tool.
- CONCERNS.md already carries "keep insecure handlers clearly labelled" for rot13/47, TomboBlowfish ECB, SubstitutionCipher and VimCrypt; this adds another.
- needs_key=True would need a KDF story (or a documented "key is the password bytes" rule), plus docs and a --list-formats entry someone will eventually use for real notes.

Cheaper alternatives if zip proves painful:
- Use the already-present CcryptExe (.cpt, needs_key=True) for password tests - it is an external exe, but ccrypt is already a documented dependency and is present in CI.
- Use OpenSslEnc10k (.openssl_aes256cbc_pbkdf2_10k) via openssl_enc_compat - pure python, needs_key=True, flat file, wrong password raises BadPassword.
- Keep the bad-password assertion at the handler level (TestBaseEncryptedFileUtil) rather than through ptrecrypt, and let rot13 cover the file-flow tests.

Status: OPEN (deferred, revisit only if zip-based tests fail)