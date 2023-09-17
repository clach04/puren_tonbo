#!/usr/bin/env python
# -*- coding: us-ascii -*-
# vim:ts=4:sw=4:softtabstop=4:smarttab:expandtab
"""Test data generator for Puren Tonbo

Sample usage:

    python -m puren_tonbo.tests.generate_data
TODO dir as param?
"""

import copy
import os
import sys

import puren_tonbo


is_py3 = sys.version_info >= (3,)
is_win = sys.platform.startswith('win')


def int2singlebyte(in_number):
    if is_py3:
        return in_number.to_bytes(1, 'little')
    else:
        return chr(in_number)


def safe_mkdir(newdir):
    result_dir = os.path.abspath(newdir)
    try:
        os.makedirs(result_dir)
    except OSError as info:
        if info.errno == 17 and os.path.isdir(result_dir):
            pass
        else:
            raise

def generate_cp1252_extended_ascii_table():
    single_byte_encoding = 'cp1252'
    result = []
    result.append(u'See https://en.wikipedia.org/wiki/Windows-1252')
    result.append(u'NOTE there are some MISSING holes.')
    result.append(u'')
    result.append(u'')
    # expect cp1252 Latin15 output
    #for counter in range(255):
    for counter in range(1, 255):
        if counter == 0x0a:
            single_char = 'NEWLINE'
        else:
            try:
                bytes_rep = int2singlebyte(counter)
                single_char = bytes_rep.decode(single_byte_encoding)
            except UnicodeDecodeError:
                single_char = 'MISSING'
        #print(u'%3d  0x%02x  %s' % (counter, counter, single_char))
        result.append(u'%3d  0x%02x  %s' % (counter, counter, single_char))
    return u'\n'.join(result)


print('Python %s on %s' % (sys.version, sys.platform))

data_folder = os.path.join(
                os.path.dirname(puren_tonbo.tests.__file__),
                'tempdata'
)
safe_mkdir(data_folder)

test_table = generate_cp1252_extended_ascii_table()


note_encoding = ('utf8', 'cp1252')
note_root = puren_tonbo.FileSystemNotes(data_folder, note_encoding)
handler_class = puren_tonbo.RawFile
handler = handler_class()

# no handler
#puren_tonbo.note_contents_save_filename(note_text = u'table cp1252 encoded in cp1252' + u'\n' + test_table, filename=u'1.txt', backup=False, use_tempfile=False, note_encoding='cp1252')
#puren_tonbo.note_contents_save_filename(note_text = u'table cp1252 encoded in utf8' + u'\n' + test_table,   filename=u'2.txt', backup=False, use_tempfile=False, note_encoding='utf-8')

#puren_tonbo.note_contents_save_filename(note_text = u'table cp1252 encoded in cp1252' + u'\n' + test_table, filename=u'1.txt', handler=handler, backup=False, use_tempfile=False, note_encoding='cp1252')
#puren_tonbo.note_contents_save_filename(note_text = u'table cp1252 encoded in utf8' + u'\n' + test_table,   filename=u'2.txt', handler=handler, backup=False, use_tempfile=False, note_encoding='utf-8')


backup_note_encoding = copy.copy(note_root.note_encoding)
print(backup_note_encoding, note_root.note_encoding)
note_root.note_encoding = 'cp1252'
print(backup_note_encoding, note_root.note_encoding)
note_root.note_contents_save(note_text = u'table cp1252 encoded in cp1252' + u'\n' + test_table, filename=u'1.txt', backup=False, handler_class=handler_class)  # guess encoding.. so it tries utf8 which of course works fine, both files end up as utf8

# restore
note_root.note_encoding = backup_note_encoding
print(backup_note_encoding, note_root.note_encoding)
note_root.note_contents_save(note_text = u'table cp1252 encoded in utf8' + u'\n' + test_table,   filename=u'2.txt', backup=False, handler_class=handler_class)  # guess encoding

note_root.note_contents_save(note_text = u'table cp1252 encoded in utf8' + u'\n' + test_table,   filename=None, backup=False, handler_class=handler_class, filename_generator=puren_tonbo.FILENAME_TIMESTAMP)  # guess filename
note_root.note_contents_save(note_text = u'table cp1252 encoded in utf8' + u'\n' + test_table,   filename=None, backup=False, handler_class=handler_class)  # guess filename
note_root.note_contents_save(note_text = u'table cp1252 encoded in utf8' + u'\n' + test_table,   filename=None, backup=False, handler_class=handler_class, filename_generator=puren_tonbo.FILENAME_FIRSTLINE_CLEAN)  # guess filename
note_root.note_contents_save(note_text = u'table cp1252 encoded in utf8' + u'\n' + test_table,   filename=None, backup=False, handler_class=handler_class, filename_generator=puren_tonbo.FILENAME_FIRSTLINE_KEBAB_CASE)  # guess filename
note_root.note_contents_save(note_text = u'' + u'\n' + test_table,   filename=None, backup=False, handler_class=handler_class)  # empty first line; guess filename


