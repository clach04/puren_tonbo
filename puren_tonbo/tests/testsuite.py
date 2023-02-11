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


class TestBaseEncryptedFileUtil(TestUtil):

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

    def check_get_what_you_put_in(self, test_data_bytes, test_password_bytes, pt_handler_class):
        if hasattr(self, 'pt_handler_class_conditional'):
            pt_handler_class_conditional = self.pt_handler_class_conditional
            if not getattr(puren_tonbo, pt_handler_class_conditional, True):
                self.skip('%r pt_handler_class_conditional not available' % pt_handler_class_conditional)

        plain_text = test_data_bytes

        fileptr1 = FakeFile()
        handler = pt_handler_class(key=test_password_bytes)
        handler.write_to(fileptr1, plain_text)
        crypted_data = fileptr1.getvalue()
        #print repr(crypted_data)

        fileptr2 = FakeFile(crypted_data)
        result_data = handler.read_from(fileptr2)  # re-use existing handler
        #print repr(result_data)
        self.assertEqual(plain_text, result_data)

class TestBaseEncryptedFile():  # mix-in with TestBaseEncryptedFileUtil

    """
    test_data_bytes = b"this is just a small piece of text."
    test_password_bytes = b'mypassword'
    pt_handler_class = puren_tonbo.VimDecrypt
    #pt_handler_class_conditional = puren_tonbo.vimdecrypt  # TODO string instead and lookup the attribute name?
    pt_handler_class_conditional = 'vimdecrypt ' # name of conditional in puren_tonbo to check, if false skip tests. if true or conditional not specified run the test(s)
    """

    def test_get_what_you_put_in(self):
        self.check_get_what_you_put_in(self.test_data_bytes, self.test_password_bytes, self.pt_handler_class)

    def test_same_input_different_crypted_text(self):
        self.check_same_input_different_crypted_text(self.test_data_bytes, self.test_password_bytes, self.pt_handler_class)

class TestBaseEncryptedPurePyZipAES(TestBaseEncryptedFileUtil, TestBaseEncryptedFile):
    test_data_bytes = b"this is just a small piece of text."
    test_password_bytes = b'mypassword'
    pt_handler_class = puren_tonbo.PurePyZipAES

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


def main():
    print(sys.version)
    print('')
    print('Formats:')
    print('')
    for file_extension in puren_tonbo.file_type_handlers:
        handler_class = puren_tonbo.file_type_handlers[file_extension]
        print('%17s - %s - %s' % (file_extension[1:], handler_class.__name__, handler_class.description))  # TODO description
    unittest.main()

if __name__ == '__main__':
    main()
