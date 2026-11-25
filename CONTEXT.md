# Puren Tonbo

A grep-like search and note layer over plain text and encrypted notes.

## Language

**Plain note**:
A note stored unencrypted, in a format that needs no password to read.
_Avoid_: raw note, unencrypted note, clear note

**Encrypted note**:
A note whose contents require a password to read.
_Avoid_: cipher note, protected note, secret note

**Search scope**:
Which of the two note kinds a single search covered: plain only, plain and
encrypted, or encrypted only.
_Avoid_: search mode, search type, filter

**Encrypted only**:
The scope that considers encrypted notes and ignores plain ones.
_Avoid_: enc-only, encrypted-exclusive

**Filename search**:
A search that matches note names and never reads note contents.
_Avoid_: name search, find mode