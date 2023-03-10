#!/usr/bin/env python
# -*- coding: us-ascii -*-
# vim:ts=4:sw=4:softtabstop=4:smarttab:expandtab
"""Test suite for Puren Tonbo

Sample usage:

    python -m puren_tonbo.tests.testsuite -v
    python -m puren_tonbo.tests.testsuite -v TestIO

"""

import os
import sys

from io import BytesIO as FakeFile  # py3

try:
    if sys.version_info < (2, 3):
        raise ImportError
    import unittest2
    unittest = unittest2
except ImportError:
    import unittest
    unittest2 = None

import puren_tonbo


is_py3 = sys.version_info >= (3,)
is_win = sys.platform.startswith('win')


class TestUtil(unittest.TestCase):
    def skip(self, reason):
        """Skip current test because of `reason`.

        NOTE currently expects unittest2, and defaults to "pass" if not available.

        unittest2 does NOT work under Python 2.2.
        Could potentially use nose or py.test which has (previously) supported Python 2.2
          * nose http://python-nose.googlecode.com/svn/wiki/NoseWithPython2_2.wiki
          * py.test http://codespeak.net/pipermail/py-dev/2005-February/000203.html
        """
        #self.assertEqual(1, 0)
        if unittest2:
            raise unittest2.SkipTest(reason)
        else:
            raise self.skipTest(reason)  # py3 and 2.7 have this
            """
            print(reason)
            self.fail('SKIP THIS TEST: ' + reason)
            #self.assertTrue(False, reason)
            #raise Exception(reason)
            """



class TestBaseEncryptedFileUtilBase(TestUtil):
    def check_get_what_you_put_in(self, test_data_bytes, test_password_bytes, encrypt_pt_handler_class, decrypt_pt_handler_class=None):
        if hasattr(self, 'pt_handler_class_conditional'):
            pt_handler_class_conditional = self.pt_handler_class_conditional
            if not getattr(puren_tonbo, pt_handler_class_conditional, True):
                self.skip('%r pt_handler_class_conditional not available' % pt_handler_class_conditional)

        decrypt_pt_handler_class = decrypt_pt_handler_class or encrypt_pt_handler_class

        #import pdb ; pdb.set_trace()  # DEBUG
        plain_text = test_data_bytes

        fileptr1 = FakeFile()
        handler = encrypt_pt_handler_class(key=test_password_bytes)
        handler.write_to(fileptr1, plain_text)
        crypted_data = fileptr1.getvalue()
        #print repr(crypted_data)

        fileptr2 = FakeFile(crypted_data)
        handler = decrypt_pt_handler_class(key=test_password_bytes)
        result_data = handler.read_from(fileptr2)
        #print repr(result_data)
        self.assertEqual(plain_text, result_data)

class TestBaseEncryptedFileUtil(TestBaseEncryptedFileUtilBase):
    def check_same_input_different_crypted_text(self, test_data_bytes, test_password_bytes, pt_handler_class):
        if hasattr(self, 'pt_handler_class_conditional'):
            pt_handler_class_conditional = self.pt_handler_class_conditional
            if not getattr(puren_tonbo, pt_handler_class_conditional, True):
                self.skip('%r dependency (pt_handler_class_conditional) not available' % pt_handler_class_conditional)

        plain_text = test_data_bytes

        fileptr1 = FakeFile()
        handler = pt_handler_class(key=test_password_bytes)
        handler.write_to(fileptr1, plain_text)
        crypted_data1 = fileptr1.getvalue()
        #print repr(crypted_data1)

        fileptr2 = FakeFile()
        handler = pt_handler_class(key=test_password_bytes)
        handler.write_to(fileptr2, plain_text)
        crypted_data2 = fileptr2.getvalue()
        #print repr(crypted_data2)

        # NOTE does not attempt to decrypt both.. yet. TODO
        self.assertNotEqual(crypted_data1, crypted_data2)



class TestBaseEncryptedFileBase():  # mix-in with TestBaseEncryptedFileUtil
    """
    test_data_bytes = b"this is just a small piece of text."
    test_password_bytes = b'mypassword'
    pt_handler_class = puren_tonbo.VimDecrypt
    #pt_handler_class_conditional = puren_tonbo.vimdecrypt  # TODO string instead and lookup the attribute name?
    pt_handler_class_conditional = 'vimdecrypt ' # name of conditional in puren_tonbo to check, if false skip tests. if true or conditional not specified run the test(s)
    """

    def test_get_what_you_put_in(self):
        if hasattr(self, 'decrypt_pt_handler_class'):
            decrypt_pt_handler_class = self.decrypt_pt_handler_class
        else:
            decrypt_pt_handler_class = None

        self.check_get_what_you_put_in(self.test_data_bytes, self.test_password_bytes, self.pt_handler_class, decrypt_pt_handler_class)


class TestBaseEncryptedFile(TestBaseEncryptedFileBase):  # mix-in with TestBaseEncryptedFileUtil
    def test_same_input_different_crypted_text(self):
        self.check_same_input_different_crypted_text(self.test_data_bytes, self.test_password_bytes, self.pt_handler_class)


class TestBaseEncryptedPurePyZipAES(TestBaseEncryptedFileUtil, TestBaseEncryptedFile):
    test_data_bytes = b"this is just a small piece of text."
    test_password_bytes = b'mypassword'
    pt_handler_class = puren_tonbo.PurePyZipAES

class TestBaseEncryptedZipNoCompressionPurePyZipAES(TestBaseEncryptedFileUtil, TestBaseEncryptedFile):
    test_data_bytes = b"this is just a small piece of text."
    test_password_bytes = b'mypassword'
    pt_handler_class = puren_tonbo.ZipNoCompressionPurePyZipAES

class TestBaseEncryptedZipAES(TestBaseEncryptedFileUtil, TestBaseEncryptedFile):
    test_data_bytes = b"this is just a small piece of text."
    test_password_bytes = b'mypassword'
    pt_handler_class = puren_tonbo.ZipAES
    pt_handler_class_conditional = 'pyzipper'

class TestBaseEncryptedZipNoCompressionAES(TestBaseEncryptedZipAES):
    pt_handler_class = puren_tonbo.ZipNoCompressionAES

class TestBaseEncryptedZipLzmaAES(TestBaseEncryptedZipAES):
    pt_handler_class = puren_tonbo.ZipLzmaAES

class TestBaseEncryptedZipBzip2AES(TestBaseEncryptedZipAES):
    pt_handler_class = puren_tonbo.ZipBzip2AES


class TestBaseEncryptedFileCompat(TestBaseEncryptedFileBase):
    def test_get_what_you_put_in_reverse(self):
        decrypt_pt_handler_class = self.decrypt_pt_handler_class

        #self.check_get_what_you_put_in(self.test_data_bytes, self.test_password_bytes, self.pt_handler_class, decrypt_pt_handler_class)
        self.check_get_what_you_put_in(self.test_data_bytes, self.test_password_bytes, decrypt_pt_handler_class, self.pt_handler_class)

class TestBaseEncryptedFileCompatPurePyZipAESandZipAES(TestBaseEncryptedFileCompat, TestBaseEncryptedFileUtilBase):
    test_data_bytes = b"this is just a small piece of text."
    test_password_bytes = b'mypassword'
    encrypt_pt_handler_class = puren_tonbo.PurePyZipAES
    decrypt_pt_handler_class = puren_tonbo.ZipAES
    pt_handler_class = encrypt_pt_handler_class
    pt_handler_class_conditional = 'pyzipper'


class TestBaseEncryptedFileCompatZipNoCompressionPurePyZipAESandZipNoCompressionAES(TestBaseEncryptedFileCompatPurePyZipAESandZipAES):
    encrypt_pt_handler_class = puren_tonbo.ZipNoCompressionPurePyZipAES
    decrypt_pt_handler_class = puren_tonbo.ZipNoCompressionAES
    pt_handler_class = encrypt_pt_handler_class


class TestBaseEncryptedTomboBlowfish(TestBaseEncryptedFileUtil, TestBaseEncryptedFile):
    test_data_bytes = b"this is just a small piece of text."
    test_password_bytes = b'mypassword'
    pt_handler_class = puren_tonbo.TomboBlowfish
    pt_handler_class_conditional = 'chi_io'

class TestBaseEncryptedFileVimDecrypt(TestBaseEncryptedFileUtil, TestBaseEncryptedFile):
    test_data_bytes = b"this is just a small piece of text."
    test_password_bytes = b'mypassword'
    pt_handler_class = puren_tonbo.VimDecrypt

    def test_get_what_you_put_in(self):
        self.skip('VimCrypt encryption not implemented yet')

    def test_same_input_different_crypted_text(self):
        self.skip('VimCrypt encryption not implemented yet')


class TestFileSystemNotes(TestUtil):
    data_folder = os.path.join(
                    os.path.dirname(puren_tonbo.tests.__file__),
                    'data'
    )
    test_password_bytes = b'password'
    note_encoding = 'us-ascii'

    plain_text_data_windows_newlines = \
'''aesop\r\n\r\nThe Frogs Desiring a King\r\n\r\nThe Frogs were l\
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
ng them all up. Then the Frogs repented when too late.\r\n\r\nBet\
ter no rule than cruel rule.\r\n'''

    plain_text_data_linux_newlines = \
'''aesop\n\nThe Frogs Desiring a King\n\nThe Frogs were l\
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

    #C:\code\py\puren_tonbo\puren_tonbo\tests\data\README.md
    def test_aesop_txt(self):
        #print(self.data_folder)
        note_root = puren_tonbo.FileSystemNotes(self.data_folder, self.note_encoding)
        password = self.test_password_bytes
        test_note_filename = 'aesop.txt'
        data = note_root.note_contents(test_note_filename, password)
        #print('%r' % self.plain_text_data_windows_newlines)
        #print('%r' % data)
        if is_win:
            self.assertEqual(self.plain_text_data_windows_newlines, data)
        else:
            self.assertEqual(self.plain_text_data_linux_newlines, data)

    def test_aesop_chi(self):
        note_root = puren_tonbo.FileSystemNotes(self.data_folder, self.note_encoding)
        password = self.test_password_bytes
        test_note_filename = 'aesop.chi'
        data = note_root.note_contents(test_note_filename, password)
        self.assertEqual(self.plain_text_data_windows_newlines, data)

    # TODO skip if gpg missing
    def test_aesop_win_encryptpad_asc(self):
        if not puren_tonbo.gpg:
            self.skip('gpg not available')

        note_root = puren_tonbo.FileSystemNotes(self.data_folder, self.note_encoding)
        password = self.test_password_bytes
        test_note_filename = 'aesop_win_encryptpad.asc'
        data = note_root.note_contents(test_note_filename, password)
        if is_win:
            canon = self.plain_text_data_windows_newlines
        else:
            canon = self.plain_text_data_linux_newlines
        #self.assertEqual(canon, data)  # FIXME works with gpg versions; 1.4.23, 2.2.19, 2.4.0 (windows and linux) BUT fails under GitHub Actions with (Chocolatey?) 2.2.29 (windows ONLY) with double \n instead of \r\n
        self.assertTrue(data == self.plain_text_data_windows_newlines or data == self.plain_text_data_linux_newlines)

    def test_aesop_win_encryptpad_gpg(self):
        if not puren_tonbo.gpg:
            self.skip('gpg not available')

        note_root = puren_tonbo.FileSystemNotes(self.data_folder, self.note_encoding)
        password = self.test_password_bytes
        test_note_filename = 'aesop_win_encryptpad.gpg'
        data = note_root.note_contents(test_note_filename, password)
        if is_win:
            canon = self.plain_text_data_windows_newlines
        else:
            canon = self.plain_text_data_linux_newlines
        #self.assertEqual(canon, data)  # FIXME works with gpg versions; 1.4.23, 2.2.19, 2.4.0 (windows and linux) BUT fails under GitHub Actions with (Chocolatey?) 2.2.29 (windows ONLY) with double \n instead of \r\n
        self.assertTrue(data == self.plain_text_data_windows_newlines or data == self.plain_text_data_linux_newlines)


    def test_aesop_win_encryptpad_gpg_string_password(self):
        if not puren_tonbo.gpg:
            self.skip('gpg not available')

        note_root = puren_tonbo.FileSystemNotes(self.data_folder, self.note_encoding)
        password = self.test_password_bytes.decode('us-ascii')
        test_note_filename = 'aesop_win_encryptpad.gpg'
        data = note_root.note_contents(test_note_filename, password)
        if is_win:
            canon = self.plain_text_data_windows_newlines
        else:
            canon = self.plain_text_data_linux_newlines
        #self.assertEqual(canon, data)  # FIXME works with gpg versions; 1.4.23, 2.2.19, 2.4.0 (windows and linux) BUT fails under GitHub Actions with (Chocolatey?) 2.2.29 (windows ONLY) with double \n instead of \r\n
        self.assertTrue(data == self.plain_text_data_windows_newlines or data == self.plain_text_data_linux_newlines)

    def test_aesop_win_encryptpad_gpg_bad_password(self):
        if not puren_tonbo.gpg:
            self.skip('gpg not available')

        note_root = puren_tonbo.FileSystemNotes(self.data_folder, self.note_encoding)
        password = 'bad'
        test_note_filename = 'aesop_win_encryptpad.gpg'
        self.assertRaises(puren_tonbo.BadPassword, note_root.note_contents, test_note_filename, password)

    def test_aesop_linux_7z_old_zip(self):
        note_root = puren_tonbo.FileSystemNotes(self.data_folder, self.note_encoding)
        password = self.test_password_bytes
        test_note_filename = 'aesop_linux_7z.old.zip'
        if puren_tonbo.pyzipper:
            data = note_root.note_contents(test_note_filename, password)
            self.assertEqual(self.plain_text_data_linux_newlines, data)
        else:
            self.assertRaises(puren_tonbo.UnsupportedFile, note_root.note_contents, test_note_filename, password)

    def test_aesop_linux_7z_oldstored_zip(self):
        note_root = puren_tonbo.FileSystemNotes(self.data_folder, self.note_encoding)
        password = self.test_password_bytes
        test_note_filename = 'aesop_linux_7z.oldstored.zip'
        if puren_tonbo.pyzipper:
            data = note_root.note_contents(test_note_filename, password)
            self.assertEqual(self.plain_text_data_linux_newlines, data)
        else:
            self.assertRaises(puren_tonbo.UnsupportedFile, note_root.note_contents, test_note_filename, password)

    def test_aesop_win_7z_old_zip_using_purepyzipaes(self):
        note_root = puren_tonbo.FileSystemNotes(self.data_folder, self.note_encoding)
        password = self.test_password_bytes
        test_note_filename = 'aesop_win_7z.old.zip'
        # this file format is not supported by PurePyZipAES
        self.assertRaises(puren_tonbo.UnsupportedFile, note_root.note_contents, test_note_filename, password, handler_class=puren_tonbo.PurePyZipAES)

    def test_aesop_win_7z_old_zip(self):
        note_root = puren_tonbo.FileSystemNotes(self.data_folder, self.note_encoding)
        password = self.test_password_bytes
        test_note_filename = 'aesop_win_7z.old.zip'
        if puren_tonbo.pyzipper:
            data = note_root.note_contents(test_note_filename, password)
            self.assertEqual(self.plain_text_data_windows_newlines, data)
        else:
            self.assertRaises(puren_tonbo.UnsupportedFile, note_root.note_contents, test_note_filename, password)

    def test_aesop_win_7z_oldstored_zip(self):
        note_root = puren_tonbo.FileSystemNotes(self.data_folder, self.note_encoding)
        password = self.test_password_bytes
        test_note_filename = 'aesop_win_7z.oldstored.zip'
        if puren_tonbo.pyzipper:
            data = note_root.note_contents(test_note_filename, password)
            self.assertEqual(self.plain_text_data_windows_newlines, data)
        else:
            self.assertRaises(puren_tonbo.UnsupportedFile, note_root.note_contents, test_note_filename, password)

    def test_aesop_win_winrar_aes256_zip(self):
        note_root = puren_tonbo.FileSystemNotes(self.data_folder, self.note_encoding)
        password = self.test_password_bytes
        test_note_filename = 'aesop_win_winrar.aes256.zip'
        data = note_root.note_contents(test_note_filename, password)
        self.assertEqual(self.plain_text_data_windows_newlines, data)

    def test_aesop_win_winrar_aes256stored_zip(self):
        note_root = puren_tonbo.FileSystemNotes(self.data_folder, self.note_encoding)
        password = self.test_password_bytes
        test_note_filename = 'aesop_win_winrar.aes256stored.zip'
        data = note_root.note_contents(test_note_filename, password)
        self.assertEqual(self.plain_text_data_windows_newlines, data)

    def test_aesop_linux_7z_aes256_zip(self):
        note_root = puren_tonbo.FileSystemNotes(self.data_folder, self.note_encoding)
        password = self.test_password_bytes
        test_note_filename = 'aesop_linux_7z.aes256.zip'
        data = note_root.note_contents(test_note_filename, password)
        self.assertEqual(self.plain_text_data_linux_newlines, data)

    def test_aesop_linux_7z_aes256stored_zip(self):
        note_root = puren_tonbo.FileSystemNotes(self.data_folder, self.note_encoding)
        password = self.test_password_bytes
        test_note_filename = 'aesop_linux_7z.aes256stored.zip'
        data = note_root.note_contents(test_note_filename, password)
        self.assertEqual(self.plain_text_data_linux_newlines, data)

    def test_aesop_win_7z_aes256_zip(self):
        note_root = puren_tonbo.FileSystemNotes(self.data_folder, self.note_encoding)
        password = self.test_password_bytes
        test_note_filename = 'aesop_win_7z.aes256.zip'
        data = note_root.note_contents(test_note_filename, password)
        self.assertEqual(self.plain_text_data_windows_newlines, data)

    def test_aesop_win_7z_aes256stored_zip(self):
        note_root = puren_tonbo.FileSystemNotes(self.data_folder, self.note_encoding)
        password = self.test_password_bytes
        test_note_filename = 'aesop_win_7z.aes256stored.zip'
        data = note_root.note_contents(test_note_filename, password)
        self.assertEqual(self.plain_text_data_windows_newlines, data)

    def test_aesop_win_7z_aes256_zip_using_purepyzipaes(self):
        note_root = puren_tonbo.FileSystemNotes(self.data_folder, self.note_encoding)
        password = self.test_password_bytes
        test_note_filename = 'aesop_win_7z.aes256.zip'
        data = note_root.note_contents(test_note_filename, password, handler_class=puren_tonbo.PurePyZipAES)  # force usage of PurePyZipAES, for when pyzipper is available and the default
        self.assertEqual(self.plain_text_data_windows_newlines, data)

    def test_aesop_win_vimcrypt3(self):
        note_root = puren_tonbo.FileSystemNotes(self.data_folder, self.note_encoding)
        password = self.test_password_bytes
        test_note_filename = 'aesop_win.vimcrypt3'
        data = note_root.note_contents(test_note_filename, password)
        self.assertEqual(self.plain_text_data_windows_newlines, data)

    def test_aesop_win_vimcrypt2(self):
        note_root = puren_tonbo.FileSystemNotes(self.data_folder, self.note_encoding)
        password = self.test_password_bytes
        test_note_filename = 'aesop_win.vimcrypt2'
        data = note_root.note_contents(test_note_filename, password)
        self.assertEqual(self.plain_text_data_windows_newlines, data)

    def test_aesop_win_vimcrypt1(self):
        note_root = puren_tonbo.FileSystemNotes(self.data_folder, self.note_encoding)
        password = self.test_password_bytes
        test_note_filename = 'aesop_win.vimcrypt1'
        data = note_root.note_contents(test_note_filename, password)
        self.assertEqual(self.plain_text_data_windows_newlines, data)

    def test_aesop_linux_vimcrypt3(self):
        note_root = puren_tonbo.FileSystemNotes(self.data_folder, self.note_encoding)
        password = self.test_password_bytes
        test_note_filename = 'aesop_linux.vimcrypt3'
        data = note_root.note_contents(test_note_filename, password)
        self.assertEqual(self.plain_text_data_linux_newlines, data)

    def test_aesop_linux_vimcrypt2(self):
        note_root = puren_tonbo.FileSystemNotes(self.data_folder, self.note_encoding)
        password = self.test_password_bytes
        test_note_filename = 'aesop_linux.vimcrypt2'
        data = note_root.note_contents(test_note_filename, password)
        self.assertEqual(self.plain_text_data_linux_newlines, data)

    def test_aesop_linux_vimcrypt1(self):
        note_root = puren_tonbo.FileSystemNotes(self.data_folder, self.note_encoding)
        password = self.test_password_bytes
        test_note_filename = 'aesop_linux.vimcrypt1'
        data = note_root.note_contents(test_note_filename, password)
        self.assertEqual(self.plain_text_data_linux_newlines, data)



def main():
    puren_tonbo.print_version_info()
    unittest.main()

if __name__ == '__main__':
    main()
