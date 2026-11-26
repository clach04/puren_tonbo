MERGED into hash:10aa0516 on 2026-11-25 and closed. Priority raised with the merge (C -> B).

Reason: the misnomer and the is_encrypted()/needs_key split are the same root cause - SubstitutionCipher(EncryptedFile) is simultaneously 'an EncryptedFile subclass' (what every filter means by encrypted) and needs_key=False (what the load path means by needs a password). Fixing the name without fixing the predicate, or the reverse, just moves the confusion.

Where the content went: the "SubstitutionCipher misnomer (absorbed from hash:fa00c950)" section of .issues/10aa0516/issue.md, plus the comment 20261126_025036.md in this directory (the audit trail: class body, the unencrypted_only hazard at __init__.py:1631, the registry loop at :1248-1260, the VimDecrypt caveat, README.md:624/:642, CONCERNS.md:203, ARCHITECTURE.md:33/:151).

Open items carried across: rename SubstitutionCipher (option a) or reparent / add an explicit capability flag (b/c); make needs_key the documented source of truth with a reachable accessor; add the classification-agreement test; fix the user-facing 'Symmetric Substitution cipher' text.
