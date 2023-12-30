#!/usr/bin/env python
# -*- coding: us-ascii -*-
# vim:ts=4:sw=4:softtabstop=4:smarttab:expandtab
"""Test suite for Puren Tonbo

Sample usage:

    python -m puren_tonbo.tests.testsuite -v
    python -m puren_tonbo.tests.testsuite -v TestIO

"""

import glob
import os
import pdb
import sys
import shutil
import tempfile
import traceback

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

    # this maybe better off in a different class
    def skip_if_missing_handler(self, handler_class):
        if handler_class not in puren_tonbo.supported_handlers:
            self.skip('%r not available (likely missing dependencies)' % handler_class)

    def skip_if_missing_handlers(self, *handler_class_list):
        for handler_class in handler_class_list:
            if handler_class in puren_tonbo.supported_handlers:
                return
        self.skip('One or more of %r not available (likely missing dependencies)' % (handler_class_list, ))


# (In Memory) encrypt/decryption tests for handlers

class TestBaseEncryptedFileUtilBase(TestUtil):
    def check_get_what_you_put_in(self, test_data_bytes, test_password_bytes, encrypt_pt_handler_class, decrypt_pt_handler_class=None):
        self.skip_if_missing_handler(encrypt_pt_handler_class)
        if decrypt_pt_handler_class:
            self.skip_if_missing_handler(decrypt_pt_handler_class)
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
        self.skip_if_missing_handler(pt_handler_class)
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


class TestBaseEncryptedCrypt(TestBaseEncryptedFileUtil, TestBaseEncryptedFile):
    test_data_bytes = b"this is just a small piece of text."
    test_password_bytes = b'mypassword'
    pt_handler_class = puren_tonbo.Ccrypt

    if not puren_tonbo.ccrypt:
        def test_get_what_you_put_in(self):
            self.skip('ccrypt not available')
        def test_same_input_different_crypted_text(self):
            self.skip('ccrypt not available')


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
    def test_get_what_you_put_in_reverse(self):  # TODO test do not get the same crypted bytes for 2 runs with same parameters, see test_same_input_different_crypted_text()
        decrypt_pt_handler_class = self.decrypt_pt_handler_class

        #self.check_get_what_you_put_in(self.test_data_bytes, self.test_password_bytes, self.pt_handler_class, decrypt_pt_handler_class)
        self.check_get_what_you_put_in(self.test_data_bytes, self.test_password_bytes, decrypt_pt_handler_class, self.pt_handler_class)

class TestBaseEncryptedOpenSsl10k(TestBaseEncryptedFile, TestBaseEncryptedFileCompat, TestBaseEncryptedFileUtil):
    test_data_bytes = b"this is just a small piece of text."
    test_password_bytes = b'mypassword'
    pt_handler_class = puren_tonbo.OpenSslEnc10k
    encrypt_pt_handler_class = decrypt_pt_handler_class = puren_tonbo.OpenSslEnc10k  # TODO review this
    pt_handler_class_conditional = 'OpenSslEncDecCompat'

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


class TestBaseEncryptedTomboBlowfish(TestBaseEncryptedFileUtil, TestBaseEncryptedFile):  # TODO TestBaseEncryptedFileCompat
    test_data_bytes = b"this is just a small piece of text."
    test_password_bytes = b'mypassword'
    pt_handler_class = puren_tonbo.TomboBlowfish
    pt_handler_class_conditional = 'chi_io'

class TestBaseEncryptedFileVimDecrypt(TestBaseEncryptedFileUtil, TestBaseEncryptedFile):
    test_data_bytes = b"this is just a small piece of text."
    test_password_bytes = b'mypassword'
    pt_handler_class = puren_tonbo.VimDecrypt

    def test_get_what_you_put_in(self):
        return  # not expected to be implemented
        self.skip('VimCrypt encryption not implemented yet')

    def test_same_input_different_crypted_text(self):
        return  # not expected to be implemented
        self.skip('VimCrypt encryption not implemented yet')


# Tests decryption (read ONLY) of sample test data

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
    # TODO refactor to use (more) shared code
    def test_aesop_txt(self):
        #print(self.data_folder)
        note_root = puren_tonbo.FileSystemNotes(self.data_folder, self.note_encoding)
        password = self.test_password_bytes
        test_note_filename = 'aesop.txt'
        data = note_root.note_contents(test_note_filename, password, dos_newlines=False)  # TODO same test but False and single canon
        #print('%r' % self.plain_text_data_windows_newlines)
        #print('%r' % data)
        if is_win:
            self.assertEqual(self.plain_text_data_windows_newlines, data)
        else:
            self.assertEqual(self.plain_text_data_linux_newlines, data)

    def test_aesop_chi(self):
        self.skip_if_missing_handler(puren_tonbo.TomboBlowfish)  # Tombo chi
        note_root = puren_tonbo.FileSystemNotes(self.data_folder, self.note_encoding)
        password = self.test_password_bytes
        test_note_filename = 'aesop.chi'
        data = note_root.note_contents(test_note_filename, password, dos_newlines=False)  # TODO same test but False and single canon
        self.assertEqual(self.plain_text_data_windows_newlines, data)

    def test_aesop_win_ccrypt_cpt(self):
        if not puren_tonbo.ccrypt:  # TODO replace with calls to skip_if_missing_handler()
            self.skip('ccrypt not available')

        note_root = puren_tonbo.FileSystemNotes(self.data_folder, self.note_encoding)
        password = self.test_password_bytes
        test_note_filename = 'aesop_win_ccrypt.cpt'
        data = note_root.note_contents(test_note_filename, password, dos_newlines=False)  # TODO same test but False and single canon
        if is_win:
            canon = self.plain_text_data_windows_newlines
        else:
            canon = self.plain_text_data_linux_newlines
        self.assertTrue(data == self.plain_text_data_windows_newlines or data == self.plain_text_data_linux_newlines)

    def test_aesop_win_ccrypt_cpt_bad_password(self):
        if not puren_tonbo.ccrypt:
            self.skip('ccrypt not available')

        note_root = puren_tonbo.FileSystemNotes(self.data_folder, self.note_encoding)
        password = 'bad'
        test_note_filename = 'aesop_win_ccrypt.cpt'
        self.assertRaises(puren_tonbo.BadPassword, note_root.note_contents, test_note_filename, password)

    def test_aesop_win_encryptpad_asc(self):
        if not puren_tonbo.gpg:  # TODO replace with calls to skip_if_missing_handler()
            self.skip('gpg not available')

        note_root = puren_tonbo.FileSystemNotes(self.data_folder, self.note_encoding)
        password = self.test_password_bytes
        test_note_filename = 'aesop_win_encryptpad.asc'
        data = note_root.note_contents(test_note_filename, password, dos_newlines=False)  # TODO same test but False and single canon
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
        data = note_root.note_contents(test_note_filename, password, dos_newlines=False)  # TODO same test but False and single canon
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
        data = note_root.note_contents(test_note_filename, password, dos_newlines=False)  # TODO same test but False and single canon
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
            data = note_root.note_contents(test_note_filename, password, dos_newlines=False)  # TODO same test but False and single canon
            self.assertEqual(self.plain_text_data_linux_newlines, data)
        else:
            self.assertRaises(puren_tonbo.UnsupportedFile, note_root.note_contents, test_note_filename, password)

    def test_aesop_linux_7z_oldstored_zip(self):
        note_root = puren_tonbo.FileSystemNotes(self.data_folder, self.note_encoding)
        password = self.test_password_bytes
        test_note_filename = 'aesop_linux_7z.oldstored.zip'
        if puren_tonbo.pyzipper:
            data = note_root.note_contents(test_note_filename, password, dos_newlines=False)  # TODO same test but False and single canon
            self.assertEqual(self.plain_text_data_linux_newlines, data)
        else:
            self.assertRaises(puren_tonbo.UnsupportedFile, note_root.note_contents, test_note_filename, password)

    def test_aesop_win_7z_old_zip_using_purepyzipaes(self):
        self.skip_if_missing_handler(puren_tonbo.PurePyZipAES)
        note_root = puren_tonbo.FileSystemNotes(self.data_folder, self.note_encoding)
        password = self.test_password_bytes
        test_note_filename = 'aesop_win_7z.old.zip'
        # this file format is not supported by PurePyZipAES
        self.assertRaises(puren_tonbo.UnsupportedFile, note_root.note_contents, test_note_filename, password, handler_class=puren_tonbo.PurePyZipAES)

    def test_aesop_win_7z_old_zip(self):
        self.skip_if_missing_handlers(puren_tonbo.PurePyZipAES, puren_tonbo.ZipAES)
        note_root = puren_tonbo.FileSystemNotes(self.data_folder, self.note_encoding)
        password = self.test_password_bytes
        test_note_filename = 'aesop_win_7z.old.zip'
        if puren_tonbo.pyzipper:
            data = note_root.note_contents(test_note_filename, password, dos_newlines=False)  # TODO same test but False and single canon
            self.assertEqual(self.plain_text_data_windows_newlines, data)
        else:
            self.assertRaises(puren_tonbo.UnsupportedFile, note_root.note_contents, test_note_filename, password)

    def test_aesop_win_7z_oldstored_zip(self):
        self.skip_if_missing_handlers(puren_tonbo.PurePyZipAES, puren_tonbo.ZipAES)
        note_root = puren_tonbo.FileSystemNotes(self.data_folder, self.note_encoding)
        password = self.test_password_bytes
        test_note_filename = 'aesop_win_7z.oldstored.zip'
        if puren_tonbo.pyzipper:
            data = note_root.note_contents(test_note_filename, password, dos_newlines=False)  # TODO same test but False and single canon
            self.assertEqual(self.plain_text_data_windows_newlines, data)
        else:
            self.assertRaises(puren_tonbo.UnsupportedFile, note_root.note_contents, test_note_filename, password)

    def test_aesop_win_winrar_aes256_zip(self):
        self.skip_if_missing_handlers(puren_tonbo.PurePyZipAES, puren_tonbo.ZipAES)
        note_root = puren_tonbo.FileSystemNotes(self.data_folder, self.note_encoding)
        password = self.test_password_bytes
        test_note_filename = 'aesop_win_winrar.aes256.zip'
        data = note_root.note_contents(test_note_filename, password, dos_newlines=False)  # TODO same test but False and single canon
        self.assertEqual(self.plain_text_data_windows_newlines, data)

    def test_aesop_win_winrar_aes256stored_zip(self):
        self.skip_if_missing_handlers(puren_tonbo.PurePyZipAES, puren_tonbo.ZipAES)
        note_root = puren_tonbo.FileSystemNotes(self.data_folder, self.note_encoding)
        password = self.test_password_bytes
        test_note_filename = 'aesop_win_winrar.aes256stored.zip'
        data = note_root.note_contents(test_note_filename, password, dos_newlines=False)  # TODO same test but False and single canon
        self.assertEqual(self.plain_text_data_windows_newlines, data)

    def test_aesop_linux_7z_aes256_zip(self):
        self.skip_if_missing_handlers(puren_tonbo.PurePyZipAES, puren_tonbo.ZipAES)
        note_root = puren_tonbo.FileSystemNotes(self.data_folder, self.note_encoding)
        password = self.test_password_bytes
        test_note_filename = 'aesop_linux_7z.aes256.zip'
        data = note_root.note_contents(test_note_filename, password, dos_newlines=False)  # TODO same test but False and single canon
        self.assertEqual(self.plain_text_data_linux_newlines, data)

    def test_aesop_linux_7z_aes256stored_zip(self):
        self.skip_if_missing_handlers(puren_tonbo.PurePyZipAES, puren_tonbo.ZipAES)  # TODO stored check instead?
        note_root = puren_tonbo.FileSystemNotes(self.data_folder, self.note_encoding)
        password = self.test_password_bytes
        test_note_filename = 'aesop_linux_7z.aes256stored.zip'
        data = note_root.note_contents(test_note_filename, password, dos_newlines=False)  # TODO same test but False and single canon
        self.assertEqual(self.plain_text_data_linux_newlines, data)

    def test_aesop_win_7z_aes256_zip(self):
        self.skip_if_missing_handlers(puren_tonbo.PurePyZipAES, puren_tonbo.ZipAES)
        note_root = puren_tonbo.FileSystemNotes(self.data_folder, self.note_encoding)
        password = self.test_password_bytes
        test_note_filename = 'aesop_win_7z.aes256.zip'
        data = note_root.note_contents(test_note_filename, password, dos_newlines=False)  # TODO same test but False and single canon
        self.assertEqual(self.plain_text_data_windows_newlines, data)

    def test_aesop_win_7z_aes256stored_zip(self):
        self.skip_if_missing_handlers(puren_tonbo.PurePyZipAES, puren_tonbo.ZipAES)  # TODO stored check instead?
        note_root = puren_tonbo.FileSystemNotes(self.data_folder, self.note_encoding)
        password = self.test_password_bytes
        test_note_filename = 'aesop_win_7z.aes256stored.zip'
        data = note_root.note_contents(test_note_filename, password, dos_newlines=False)  # TODO same test but False and single canon
        self.assertEqual(self.plain_text_data_windows_newlines, data)

    def test_aesop_win_7z_aes256_zip_using_purepyzipaes(self):
        self.skip_if_missing_handler(puren_tonbo.PurePyZipAES)
        note_root = puren_tonbo.FileSystemNotes(self.data_folder, self.note_encoding)
        password = self.test_password_bytes
        test_note_filename = 'aesop_win_7z.aes256.zip'
        data = note_root.note_contents(test_note_filename, password, handler_class=puren_tonbo.PurePyZipAES, dos_newlines=False)  # force usage of PurePyZipAES, for when pyzipper is available and the default
        self.assertEqual(self.plain_text_data_windows_newlines, data)

    def test_aesop_win_vimcrypt3(self):
        self.skip_if_missing_handler(puren_tonbo.VimDecrypt)
        note_root = puren_tonbo.FileSystemNotes(self.data_folder, self.note_encoding)
        password = self.test_password_bytes
        test_note_filename = 'aesop_win.vimcrypt3'
        data = note_root.note_contents(test_note_filename, password, dos_newlines=False)  # TODO same test but False and single canon
        self.assertEqual(self.plain_text_data_windows_newlines, data)

    def test_aesop_win_vimcrypt2(self):
        self.skip_if_missing_handler(puren_tonbo.VimDecrypt)
        note_root = puren_tonbo.FileSystemNotes(self.data_folder, self.note_encoding)
        password = self.test_password_bytes
        test_note_filename = 'aesop_win.vimcrypt2'
        data = note_root.note_contents(test_note_filename, password, dos_newlines=False)  # TODO same test but False and single canon
        self.assertEqual(self.plain_text_data_windows_newlines, data)

    def test_aesop_win_vimcrypt1(self):
        self.skip_if_missing_handler(puren_tonbo.VimDecrypt)
        note_root = puren_tonbo.FileSystemNotes(self.data_folder, self.note_encoding)
        password = self.test_password_bytes
        test_note_filename = 'aesop_win.vimcrypt1'
        data = note_root.note_contents(test_note_filename, password, dos_newlines=False)  # TODO same test but False and single canon
        self.assertEqual(self.plain_text_data_windows_newlines, data)

    def test_aesop_linux_vimcrypt3(self):
        self.skip_if_missing_handler(puren_tonbo.VimDecrypt)
        note_root = puren_tonbo.FileSystemNotes(self.data_folder, self.note_encoding)
        password = self.test_password_bytes
        test_note_filename = 'aesop_linux.vimcrypt3'
        data = note_root.note_contents(test_note_filename, password)
        self.assertEqual(self.plain_text_data_linux_newlines, data)

    def test_aesop_linux_vimcrypt2(self):
        self.skip_if_missing_handler(puren_tonbo.VimDecrypt)
        note_root = puren_tonbo.FileSystemNotes(self.data_folder, self.note_encoding)
        password = self.test_password_bytes
        test_note_filename = 'aesop_linux.vimcrypt2'
        data = note_root.note_contents(test_note_filename, password)
        self.assertEqual(self.plain_text_data_linux_newlines, data)

    def test_aesop_linux_vimcrypt1(self):
        self.skip_if_missing_handler(puren_tonbo.VimDecrypt)
        note_root = puren_tonbo.FileSystemNotes(self.data_folder, self.note_encoding)
        password = self.test_password_bytes
        test_note_filename = 'aesop_linux.vimcrypt1'
        data = note_root.note_contents(test_note_filename, password)
        self.assertEqual(self.plain_text_data_linux_newlines, data)

# TODO test openssl_aes256cbc_pbkdf2_10k
# TODO test aesop_linux.openssl_aes256cbc_pbkdf2_10k

# Tests write/encryption to disk

class TestFileSystemNotesWrite(TestUtil):
    # data_folder setup in setUpClass()
    test_password_bytes = b'password'
    note_encoding = 'us-ascii'

    @classmethod
    def setUpClass(self):
        self.data_folder = tempfile.mkdtemp(prefix='TestFileSystemNotesWrite_tmp')
        #print('self.data_folder %s' % self.data_folder)

    @classmethod
    def tearDownClass(self):
        shutil.rmtree(self.data_folder)

    # TODO new test without password
    def do_one_test_simple(self, in_filename, buffer_plain_str, dos_newlines=None, test_password_bytes=None):
        filename_no_path = in_filename
        folder = self.data_folder
        in_filename = os.path.join(folder, in_filename)
        try:
            handler_class = puren_tonbo.filename2handler(in_filename, default_handler=puren_tonbo.RawFile)
            password = self.test_password_bytes
            handler = handler_class(key=password)

            if dos_newlines is None:
                # tests with default newline setting
                puren_tonbo.note_contents_save_filename(buffer_plain_str, filename=in_filename, handler=handler)
            else:
                puren_tonbo.note_contents_save_filename(buffer_plain_str, filename=in_filename, handler=handler, dos_newlines=dos_newlines)
            # TODO with and without filename_generatordos newlines
            # TODO with and without filename_generator
            # TODO handler is currently required, support NOT passing it in? see class method version

            note_root = puren_tonbo.FileSystemNotes(folder, self.note_encoding)
            test_note_filename = in_filename
            #import pdb ; pdb.set_trace()
            if dos_newlines is None:
                # tests with default newline setting
                data = note_root.note_contents(test_note_filename, password)
            else:
                data = note_root.note_contents(test_note_filename, password, dos_newlines=dos_newlines)
            self.assertEqual(buffer_plain_str, data)
            # TODO manually read file (for local native filesystem( and perform validation checks; 1. matches input 2. \r (DOS) present/not-present as per dos_newlines expected setting
            #glob
            #import pdb ; pdb.set_trace()
            #print('')
            expected_filenames = [filename_no_path]
            expected_filenames.sort()
            for (dirname, dirnames, filenames) in os.walk(folder):
                filenames.sort()
                #print(dirname, dirnames, filenames)
                self.assertEqual((folder, [], expected_filenames), (dirname, dirnames, filenames))
        finally:
            os.remove(in_filename) # TODO ignore does not exist errors (only)

    def test_file_one_with_dos_newlines(self):
        in_filename = 'one.txt'
        dos_newlines = True
        buffer_plain_str = '''one

file one.

'''
        self.do_one_test_simple(in_filename, buffer_plain_str, dos_newlines=dos_newlines, test_password_bytes=self.test_password_bytes)

    def test_file_one_without_dos_newlines(self):
        in_filename = 'one.txt'
        dos_newlines = False
        buffer_plain_str = '''one

file one.

'''
        self.do_one_test_simple(in_filename, buffer_plain_str, dos_newlines=dos_newlines, test_password_bytes=self.test_password_bytes)

    def test_file_one_with_default_dos_newlines(self):
        in_filename = 'one.txt'
        dos_newlines = None
        buffer_plain_str = '''one

file one.

'''
        self.do_one_test_simple(in_filename, buffer_plain_str, dos_newlines=dos_newlines, test_password_bytes=self.test_password_bytes)


# Filename generation (rename) tests
class TestFileSystemNotesWriteFunctionSaveRawPlainText(TestUtil):
    # data_folder setup in setUpClass()
    test_password_bytes = b'password'
    note_encoding = 'us-ascii'
    handler_class = puren_tonbo.RawFile  # text / txt

    @classmethod
    def setUpClass(self):
        self.data_folder = tempfile.mkdtemp(prefix='TestFileSystemNotesWrite_tmp')
        #print('self.data_folder %s' % self.data_folder)

    @classmethod
    def tearDownClass(self):
        shutil.rmtree(self.data_folder)

    def check_skip(self):
        if self.handler_class not in puren_tonbo.supported_handlers:
            self.skip('%r not available (likely missing dependencies)' % self.handler_class)

    def do_one_test(self, buffer_plain_str, new_filename=None, original_filename=None, folder=None, dos_newlines=None, test_password_bytes=None, backup=True, use_tempfile=True, filename_generator=puren_tonbo.FILENAME_FIRSTLINE, expected_filenames=None):
        self.check_skip()
        if not expected_filenames:
            self.assertTrue(False, 'expected_filenames required... not implemented')
        test_note_filename = new_filename or expected_filenames[0]
        folder = folder or self.data_folder
        try:

            # TODO test withOUT handler
            handler_class = self.handler_class
            password = test_password_bytes
            handler = handler_class(key=password)

            kwargs = dict(
                filename_generator=filename_generator,
                backup=backup,
                use_tempfile=use_tempfile,
            )
            if dos_newlines is not None:
                kwargs['dos_newlines'] = dos_newlines
            if new_filename:
                kwargs['filename'] = new_filename
            if original_filename:
                kwargs['original_filename'] = original_filename
            if folder:
                kwargs['folder'] = folder
            if handler:
                kwargs['handler'] = handler

            #pdb.set_trace()
            puren_tonbo.note_contents_save_filename(buffer_plain_str, **kwargs)

            # load / decrypt / validation
            note_root = puren_tonbo.FileSystemNotes(folder, self.note_encoding)
            # TODO kwargs params
            if dos_newlines is None:
                # tests with default newline setting
                data = note_root.note_contents(test_note_filename, password)
            else:
                data = note_root.note_contents(test_note_filename, password, dos_newlines=dos_newlines)
            self.assertEqual(buffer_plain_str, data)

            expected_filenames.sort()
            for (dirname, dirnames, filenames) in os.walk(folder):
                filenames.sort()
                #print(dirname, dirnames, filenames)
                self.assertEqual((folder, [], expected_filenames), (dirname, dirnames, filenames))

        finally:
            # cleanup file(s)
            for filename in expected_filenames:
                full_pathname = os.path.join(folder, filename)
                if os.path.exists(full_pathname):
                    os.remove(full_pathname) # TODO ignore does not exist errors (only), for now skip attempt

            # simple, flat, non-nested cleanup
            for filename in glob.glob(os.path.join(folder, '*')):
                os.remove(filename)

    def test_filename_gen_one_rename_two_with_password_with_backup(self):
        self.check_skip()
        buffer_plain_str = '''two

file WAS one.

'''
        #pdb.set_trace()
        file_extension = self.handler_class.extensions[0]  # pick the first one
        folder = self.data_folder
        note_root = puren_tonbo.FileSystemNotes(folder, self.note_encoding)
        note_root.note_contents_save('junk', filename='one' + file_extension, filename_generator=None, get_pass=self.test_password_bytes)

        # NOTE implicit backup
        self.do_one_test(buffer_plain_str, original_filename='one' + file_extension, dos_newlines=False, test_password_bytes=self.test_password_bytes, expected_filenames=['two' + file_extension, 'one' + file_extension + '.bak'])

    def test_filename_gen_one_rename_two_with_password_with_nobackup(self):
        self.check_skip()
        buffer_plain_str = '''two

file WAS one.

'''
        #pdb.set_trace()
        file_extension = self.handler_class.extensions[0]  # pick the first one
        folder = self.data_folder
        note_root = puren_tonbo.FileSystemNotes(folder, self.note_encoding)
        note_root.note_contents_save('junk', filename='one' + file_extension, filename_generator=None, get_pass=self.test_password_bytes)

        self.do_one_test(buffer_plain_str, original_filename='one' + file_extension, dos_newlines=False, test_password_bytes=self.test_password_bytes, backup=False, expected_filenames=['two' + file_extension])

    def test_filename_gen_one_with_password_already_exist(self):
        self.check_skip()
        buffer_plain_str = '''one

file one.

'''
        #pdb.set_trace()
        file_extension = self.handler_class.extensions[0]  # pick the first one
        folder = self.data_folder
        note_root = puren_tonbo.FileSystemNotes(folder, self.note_encoding)
        note_root.note_contents_save('junk', filename='one' + file_extension, filename_generator=None, get_pass=self.test_password_bytes)

        self.do_one_test(buffer_plain_str, dos_newlines=False, test_password_bytes=self.test_password_bytes, expected_filenames=['one(1)' + file_extension, 'one' + file_extension])

    def test_filename_gen_one_with_password(self):
        buffer_plain_str = '''one

file one.

'''
        #pdb.set_trace()
        file_extension = self.handler_class.extensions[0]  # pick the first one
        self.do_one_test(buffer_plain_str, dos_newlines=False, test_password_bytes=self.test_password_bytes, expected_filenames=['one' + file_extension])

    def test_filename_gen_one_no_password(self):
        buffer_plain_str = '''one

file one.

'''
        file_extension = self.handler_class.extensions[0]  # pick the first one
        # do NOT pass in test_password_bytes
        #pdb.set_trace()
        #if self.handler_class is puren_tonbo.RawFile:
        if isinstance(self.handler_class(key=b'junk'), puren_tonbo.RawFile):
            self.do_one_test(buffer_plain_str, dos_newlines=False, expected_filenames=['one' + file_extension])
        else:
            self.assertRaises(puren_tonbo.PurenTonboBadCall, self.do_one_test, buffer_plain_str, dos_newlines=False, expected_filenames=['one' + file_extension])


class TestFileSystemNotesWriteClassSaveRawPlainText(TestFileSystemNotesWriteFunctionSaveRawPlainText):
    def do_one_test(self, buffer_plain_str, new_filename=None, original_filename=None, folder=None, dos_newlines=None, test_password_bytes=None, backup=True, use_tempfile=True, filename_generator=puren_tonbo.FILENAME_FIRSTLINE, expected_filenames=None):
        self.check_skip()
        if not expected_filenames:
            self.assertTrue(False, 'expected_filenames required... not implemented')
        test_note_filename = new_filename or expected_filenames[0]
        folder = folder or self.data_folder
        try:

            # TODO test withOUT handler
            handler_class = self.handler_class
            password = test_password_bytes

            kwargs = dict(
                filename_generator=filename_generator,
                backup=backup,
                use_tempfile=use_tempfile,
            )
            if dos_newlines is not None:
                kwargs['dos_newlines'] = dos_newlines
            if new_filename:
                kwargs['filename'] = new_filename
            if original_filename:
                kwargs['original_filename'] = original_filename
            """
            if folder:
                kwargs['folder'] = folder
            """
            if password:
                kwargs['get_pass'] = password
            if handler_class:
                kwargs['handler_class'] = handler_class

            #pdb.set_trace()
            note_root = puren_tonbo.FileSystemNotes(folder, self.note_encoding)
            note_root.note_contents_save(buffer_plain_str, **kwargs)

            # load / decrypt / validation
            # TODO kwargs params
            if dos_newlines is None:
                # tests with default newline setting
                data = note_root.note_contents(test_note_filename, password)
            else:
                data = note_root.note_contents(test_note_filename, password, dos_newlines=dos_newlines)
            self.assertEqual(buffer_plain_str, data)

            expected_filenames.sort()
            for (dirname, dirnames, filenames) in os.walk(folder):
                filenames.sort()
                #print(dirname, dirnames, filenames)
                self.assertEqual((folder, [], expected_filenames), (dirname, dirnames, filenames))

        finally:
            # cleanup file(s)
            for filename in expected_filenames:
                full_pathname = os.path.join(folder, filename)
                if os.path.exists(full_pathname):
                    os.remove(full_pathname) # TODO ignore does not exist errors (only), for now skip attempt

            # simple, flat, non-nested cleanup
            for filename in glob.glob(os.path.join(folder, '*')):
                os.remove(filename)

    def test_filename_gen_one_rename_two_with_password_with_backup(self):
        self.skip('FIXME not implemented yet in class code')
    def test_filename_gen_one_rename_two_with_password_with_nobackup(self):
        self.skip('FIXME not implemented yet in class code')


class TestFileSystemNotesWriteClassSaveEncryptedChi(TestFileSystemNotesWriteClassSaveRawPlainText):
    handler_class = puren_tonbo.TomboBlowfish # Tombo chi

class TestFileSystemNotesWriteFunctionSaveEncryptedChi(TestFileSystemNotesWriteFunctionSaveRawPlainText):
    handler_class = puren_tonbo.TomboBlowfish # Tombo chi

class TestFileSystemNotesWriteClassSaveEncryptedCcrypt(TestFileSystemNotesWriteClassSaveRawPlainText):
    handler_class = puren_tonbo.Ccrypt

class TestFileSystemNotesWriteFunctionSaveEncryptedCcrypt(TestFileSystemNotesWriteFunctionSaveRawPlainText):
    handler_class = puren_tonbo.Ccrypt

class TestFileSystemNotesWriteClassSaveEncryptedOpenSsl10k(TestFileSystemNotesWriteClassSaveRawPlainText):
    handler_class = puren_tonbo.OpenSslEnc10k # OpenSSL aes256cbc pbkdf2 10k

class TestFileSystemNotesWriteFunctionSaveEncryptedOpenSsl10k(TestFileSystemNotesWriteFunctionSaveRawPlainText):
    handler_class = puren_tonbo.OpenSslEnc10k # OpenSSL aes256cbc pbkdf2 10k

""" TODO implement TestFileSystemNotesWriteClassSaveRawPlainText and TestFileSystemNotesWriteFunctionSaveRawPlainText for:
grep '(EncryptedFile):' puren_tonbo/__init__.py
grep '(ZipEncryptedFileBase):' puren_tonbo/__init__.py

"""

    # TODO test write file, then save/edit once - confirm have backup and new file
    # TODO test write file auto generate name
    # TODO test write file, then edit with (new/modified first line) auto generate name should be different
    # TODO test write file with characters outside of encoding
    # TODO test write file, then write 2nd time this time with characters outside of encoding - to generate error - existing file should be preserved
    # TODO no filename, generator set to none. ensure reasonable error generated

def debugTestRunner(post_mortem=None):
    """unittest runner doing post mortem debugging on failing tests"""
    if post_mortem is None:
        post_mortem = pdb.post_mortem
    class DebugTestResult(unittest.TextTestResult):
        def addError(self, test, err):
            # called before tearDown()
            traceback.print_exception(*err)
            post_mortem(err[2])
            super(DebugTestResult, self).addError(test, err)
        def addFailure(self, test, err):
            traceback.print_exception(*err)
            post_mortem(err[2])
            super(DebugTestResult, self).addFailure(test, err)
    return unittest.TextTestRunner(resultclass=DebugTestResult)

def main():
    puren_tonbo.print_version_info()
    if os.environ.get('DEBUG_ON_FAIL'):
        unittest.main(testRunner=debugTestRunner())
        ##unittest.main(testRunner=debugTestRunner(pywin.debugger.post_mortem))
        ##unittest.findTestCases(__main__).debug()
    else:
        unittest.main()

if __name__ == '__main__':
    main()
