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

def main(argv=None):
    if argv is None:
        argv = sys.argv

    puren_tonbo.print_version_info()
    #print('Python %s on %s' % (sys.version, sys.platform))

    try:
        data_folder = argv[1]
    except IndexError:
        data_folder = os.path.join(
                        os.path.dirname(puren_tonbo.tests.__file__),
                        'tempdata'
        )
    safe_mkdir(data_folder)

    test_table = generate_cp1252_extended_ascii_table()
    three_lines = '\n' + 'line 1\nline 2\nline 3\n'
    aesop_frog_king = \
'''\n\nThe Frogs Desiring a King\n\nThe Frogs were l\
iving as happy as could be in a marshy swamp that just suited the\
m; they went splashing about caring for nobody and nobody troubli\
ng with them. But some of them thought that this was not right, t\
hat they should have a king and a proper constitution, so they de\
termined to send up a petition to Jove to give them what they wan\
ted. "Mighty Jove," they cried, "send unto us a king that will ru\
le over us and keep us in order." Jove laughed at their croaking,\
 and threw down into the swamp a huge Log, which came down splash\
ing into the swamp. The Frogs were frightened out of their lives \
by the commotion made in their midst, and all rushed to the bank \
to look at the horrible monster; but after a time, seeing that it\
 did not move, one or two of the boldest of them ventured out tow\
ards the Log, and even dared to touch it; still it did not move. \
Then the greatest hero of the Frogs jumped upon the Log and comme\
nced dancing up and down upon it, thereupon all the Frogs came an\
d did the same; and for some time the Frogs went about their busi\
ness every day without taking the slightest notice of their new K\
ing Log lying in their midst. But this did not suit them, so they\
 sent another petition to Jove, and said to him, "We want a real \
king; one that will really rule over us." Now this made Jove angr\
y, so he sent among them a big Stork that soon set to work gobbli\
ng them all up. Then the Frogs repented when too late.\n\nBet\
ter no rule than cruel rule.\n'''


    note_encoding = ('utf8', 'cp1252')
    note_root = puren_tonbo.FileSystemNotes(data_folder, note_encoding)
    handler_class = puren_tonbo.RawFile
    handler = handler_class()

    def create_file(first_line, note_content=three_lines, file_extension='.txt'):
        # FIXME `file_extension` currently a NOOP and ignored!
        note_root.note_contents_save(note_text=first_line + note_content, filename=None, backup=False, handler_class=handler_class, filename_generator=puren_tonbo.FILENAME_FIRSTLINE_CLEAN)

    create_file('001')
    create_file('002')
    create_file('lower_text', file_extension='.txt')
    create_file('upper_text', file_extension='.TXT')  # NOT working/implemented yet
    create_file('lower_markdown', file_extension='.md')  # NOT working/implemented yet
    create_file('upper_markdown', file_extension='.MD')  # NOT working/implemented yet
    create_file('aesop', note_content=aesop_frog_king)
    create_file('')  # empty, memo
    create_file('')  # repeat empty, memo(1)
    #create_file('003.chi')  # TODO

    backup_note_encoding = copy.copy(note_root.note_encoding)
    note_root.note_encoding = 'cp1252'
    create_file(u'table cp1252 encoded in cp1252' + u'\n' + test_table, note_content=test_table)
    # restore
    note_root.note_encoding = backup_note_encoding
    create_file(u'table cp1252 encoded in utf8' + u'\n' + test_table, note_content=test_table)

    safe_mkdir(os.path.join(data_folder, 'dir01'))  # note_root.note_contents_save() willl fail if directory does not aready exist
    safe_mkdir(os.path.join(data_folder, 'dir02'))
    note_root.note_contents_save(note_text=u'test different styles' + u'\n' + three_lines, filename=None, backup=False, handler_class=handler_class)  # guess filename
    note_root.note_contents_save(note_text=u'test different styles' + u'\n' + three_lines, filename=None, backup=False, handler_class=handler_class, filename_generator=puren_tonbo.FILENAME_FIRSTLINE_CLEAN)  # guess filename
    note_root.note_contents_save(note_text=u'test different styles' + u'\n' + three_lines, filename=None, backup=False, handler_class=handler_class, filename_generator=puren_tonbo.FILENAME_FIRSTLINE_SNAKE_CASE)  # guess filename
    note_root.note_contents_save(note_text=u'test different styles' + u'\n' + three_lines, filename=None, backup=False, handler_class=handler_class, filename_generator=puren_tonbo.FILENAME_FIRSTLINE_KEBAB_CASE)  # guess filename

    #import pdb ; pdb.set_trace()
    note_root.note_contents_save(note_text=u'test different styles' + u'\n' + three_lines, filename=os.path.join('dir01', '001.txt'), backup=False, handler_class=handler_class)
    note_root.note_contents_save(note_text=u'test different styles' + u'\n' + three_lines, filename=os.path.join('dir01', '002.txt'), backup=False, handler_class=handler_class)
    note_root.note_contents_save(note_text=u'test different styles' + u'\n' + three_lines, filename=os.path.join('dir02', '001.txt'), backup=False, handler_class=handler_class)
    note_root.note_contents_save(note_text=u'test different styles' + u'\n' + three_lines, filename=os.path.join('dir02', '002.txt'), backup=False, handler_class=handler_class)
    # TODO additional nested directory with content
    safe_mkdir(os.path.join(data_folder, 'Refreshments', 'food'))
    safe_mkdir(os.path.join(data_folder, 'Refreshments', 'drink'))
    note_root.note_contents_save(note_text=u'sandwich' + u'\n' + u'', folder=os.path.join('Refreshments', 'food'), backup=False, handler_class=handler_class)
    note_root.note_contents_save(note_text=u'fries' + u'\n' + u'', folder=os.path.join('Refreshments', 'food'), backup=False, handler_class=handler_class)
    note_root.note_contents_save(note_text=u'cola' + u'\n' + u'', folder=os.path.join('Refreshments', 'drink'), backup=False, handler_class=handler_class)
    note_root.note_contents_save(note_text=u'liquor' + u'\n' + u'', folder=os.path.join('Refreshments', 'drink'), backup=False, handler_class=handler_class)
    note_root.note_contents_save(note_text=u'tea' + u'\n' + u'', folder=os.path.join('Refreshments', 'drink'), backup=False, handler_class=handler_class)
    note_root.note_contents_save(note_text=u'\u9152' + u'\n' + u'', folder=os.path.join('Refreshments', 'drink'), backup=False, handler_class=handler_class)

    note_root.note_contents_save(note_text=u'test different styles' + u'\n' + three_lines, filename=os.path.join('real_lower_text.txt'), backup=False, handler_class=handler_class)
    note_root.note_contents_save(note_text=u'test different styles' + u'\n' + three_lines, filename=os.path.join('real_upper_text.TXT'), backup=False, handler_class=handler_class)
    note_root.note_contents_save(note_text=u'test different styles' + u'\n' + three_lines, filename=os.path.join('real_lower_markdown.md'), backup=False, handler_class=handler_class)
    note_root.note_contents_save(note_text=u'test different styles' + u'\n' + three_lines, filename=os.path.join('real_upper_markdown.MD'), backup=False, handler_class=handler_class)


    # create some empty directory trees
    safe_mkdir(os.path.join(data_folder, 'a', 'b', 'c'))
    safe_mkdir(os.path.join(data_folder, 'a', 'b', 'a'))
    safe_mkdir(os.path.join(data_folder, 'a', 'd'))

    """
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

    note_root.note_contents_save(note_text = u'table cp1252 encoded in utf8' + u'\n' + test_table,   filename=None, backup=False, handler_class=handler_class)  # guess filename
    note_root.note_contents_save(note_text = u'table cp1252 encoded in utf8' + u'\n' + test_table,   filename=None, backup=False, handler_class=handler_class, filename_generator=puren_tonbo.FILENAME_FIRSTLINE_CLEAN)  # guess filename
    note_root.note_contents_save(note_text = u'table cp1252 encoded in utf8' + u'\n' + test_table,   filename=None, backup=False, handler_class=handler_class, filename_generator=puren_tonbo.FILENAME_FIRSTLINE_SNAKE_CASE)  # guess filename
    note_root.note_contents_save(note_text = u'table cp1252 encoded in utf8' + u'\n' + test_table,   filename=None, backup=False, handler_class=handler_class, filename_generator=puren_tonbo.FILENAME_FIRSTLINE_KEBAB_CASE)  # guess filename
    note_root.note_contents_save(note_text = u'' + u'\n' + test_table,   filename=None, backup=False, handler_class=handler_class)  # empty first line; guess filename


    # different each run
    note_root.note_contents_save(note_text = u'table cp1252 encoded in utf8' + u'\n' + test_table,   filename=None, backup=False, handler_class=handler_class, filename_generator=puren_tonbo.FILENAME_TIMESTAMP)  # guess filename
    note_root.note_contents_save(note_text = u'table cp1252 encoded in utf8' + u'\n' + test_table,   filename=None, backup=False, handler_class=handler_class, filename_generator=puren_tonbo.FILENAME_UUID4)  # guess filename
    """

    return 0


if __name__ == "__main__":
    sys.exit(main())
